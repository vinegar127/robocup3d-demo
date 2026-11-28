"""Verify the installed server with a real T1 connection, then stop it."""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path


def receive_exact(sock, count):
    data = bytearray()
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise RuntimeError("Server closed the connection before a complete frame")
        data.extend(chunk)
    return bytes(data)


def main():
    workspace = Path(__file__).resolve().parents[1]
    work = workspace / "tmp" / "rcssmj-smoke"
    work.mkdir(parents=True, exist_ok=True)
    log_path = work / "server.log"
    result = {"success": False}
    # Select unused loopback ports without touching any existing server.
    with socket.socket() as agent_probe, socket.socket() as monitor_probe:
        agent_probe.bind(("127.0.0.1", 0))
        monitor_probe.bind(("127.0.0.1", 0))
        agent_port = agent_probe.getsockname()[1]
        monitor_port = monitor_probe.getsockname()[1]
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "rcsssmj", "--host", "127.0.0.1",
             "--aport", str(agent_port), "--mport", str(monitor_port),
             "--rules", "ssim26", "--no-render"],
            cwd=work, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            connection = None
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Server exited with code {process.returncode}")
                try:
                    connection = socket.create_connection(("127.0.0.1", agent_port), timeout=0.3)
                    break
                except OSError:
                    time.sleep(0.1)
            if connection is None:
                raise RuntimeError("Server did not open its agent port")
            with connection:
                connection.settimeout(15)
                message = b"(init T1 WindowsSmoke 1)"
                connection.sendall(len(message).to_bytes(4, "big") + message)
                for _ in range(5):
                    size = int.from_bytes(receive_exact(connection, 4), "big")
                    if not 0 < size < 10_000_000:
                        raise RuntimeError(f"Invalid perception size: {size}")
                    frame = receive_exact(connection, size)
                    if b"(time" in frame and (b"(HJ" in frame or b"(hj" in frame):
                        result = {"success": True, "t1_perception_bytes": size,
                                  "preview": frame[:700].decode("utf-8", errors="replace")}
                        break
                if not result["success"]:
                    raise RuntimeError("No T1 joint perception received")
        except Exception as error:
            result["error"] = str(error)
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    (work / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["success"]:
        print(log_path.read_text(encoding="utf-8", errors="replace")[-6000:])
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
