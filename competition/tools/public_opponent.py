"""Byte-for-byte agent-protocol relay for pinned public opponents.

This recorder never adds/replaces perceptions or actions. It records health so
an opponent crash or lack of working motors cannot be counted as a victory.
"""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time

from team.world import World
from tools.opponents import PUBLIC_KINDS, PYTHON_FIELDS, GRU_KINDS, native_assets


def read_frame(sock):
    def exact(size):
        result = bytearray()
        while len(result) < size:
            part = sock.recv(size - len(result))
            if not part:
                raise ConnectionError('Connection closed')
            result.extend(part)
        return bytes(result)
    header = exact(4)
    count = int.from_bytes(header, 'big')
    if count > 1_048_576:
        raise ValueError('Oversized opponent frame')
    return header + exact(count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=PUBLIC_KINDS, required=True)
    parser.add_argument('--team', required=True)
    parser.add_argument('--number', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--stop-file', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    world = World(args.team)
    summary = {'team': args.team, 'number': args.number, 'public_opponent': args.kind,
               'frames': 0, 'motor_frames': 0, 'actions': 0, 'distance_walked': 0.,
               'fallen_frames': 0, 'parse_errors': 0, 'error': None, 'start_position': None,
               'end_position': None, 'states': {}, 'messages_received': 0}
    running = threading.Event(); running.set()
    upstream = socket.create_connection(('127.0.0.1', args.port), timeout=20)
    upstream.settimeout(None)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0)); listener.listen(1); listener.settimeout(30)
    private_port = listener.getsockname()[1]
    if args.kind in PYTHON_FIELDS:
        command = [sys.executable, '-m', 'tools.bahia_opponent', '--team', args.team,
                   '--number', str(args.number), '--port', str(private_port),'--source',args.kind]
        commit = json.loads((root / f'third_party/{args.kind}/PROVENANCE.json').read_text())['commit']
        cwd = root
    elif args.kind in GRU_KINDS:
        command=[sys.executable,'-m','tools.gru_opponent','--team',args.team,'--number',str(args.number),'--port',str(private_port),
                 '--work-dir',str(args.summary.parent/f'gru-{args.number}'),'--source',args.kind]
        commit=json.loads((root/f'third_party/{args.kind}/PROVENANCE.json').read_text())['commit']
        cwd=root
    else:
        default_home = f'E:/RoboCup3D/opponents/{args.kind}' if sys.platform == 'win32' else str(root/(f'third_party/{args.kind}/runtime/apollo/build' if args.kind=='my3d' else 'third_party/apollo/build'))
        cwd = Path(os.environ.get('MY3D_HOME' if args.kind=='my3d' else 'APOLLO_HOME', default_home)).resolve()
        executable = cwd / ('ApolloCodeBase.exe' if sys.platform == 'win32' else 'ApolloCodeBase')
        assets = native_assets(root, args.kind, cwd)
        command = [str(executable), '--team', args.team,
                   '--player-number', str(args.number), '--host', '127.0.0.1', '--port', str(private_port),
                   '--asset-root', str(assets)]
        commit = json.loads((root/f'third_party/{args.kind}/PROVENANCE.json').read_text())['commit']
    summary['public_commit'] = commit
    env = dict(os.environ, PYTHONUTF8='1')
    process = None
    peer = None
    errors = []
    threads = []
    try:
        with args.summary.with_suffix('.upstream.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env)
            peer, _ = listener.accept()
            peer.settimeout(None)
            previous_position = None
            def perceptions():
                nonlocal previous_position
                try:
                    while running.is_set():
                        frame = read_frame(upstream)
                        peer.sendall(frame)
                        try:
                            world.update(frame[4:].decode('utf-8'))
                            summary['frames'] += 1
                            summary['fallen_frames'] += int(world.fallen)
                            summary['states'][world.play_mode] = summary['states'].get(world.play_mode, 0) + 1
                            if world.position:
                                if summary['frames'] > 10 and summary['start_position'] is None:
                                    summary['start_position'] = world.position
                                if previous_position is not None:
                                    gap = ((world.position[0] - previous_position[0]) ** 2 + (world.position[1] - previous_position[1]) ** 2) ** .5
                                    if gap < .5:
                                        summary['distance_walked'] += gap
                                previous_position = world.position
                                summary['end_position'] = world.position
                        except (ValueError, KeyError):
                            summary['parse_errors'] += 1
                except (OSError, ConnectionError) as error:
                    if not args.stop_file.exists():
                        errors.append(str(error))
            def actions():
                try:
                    while running.is_set():
                        frame = read_frame(peer)
                        upstream.sendall(frame)
                        summary['actions'] += 1
                        if re.search(rb'\((?:he|lae|rae|lle|rle|te)\d+ ', frame[4:]):
                            summary['motor_frames'] += 1
                except (OSError, ConnectionError) as error:
                    if not args.stop_file.exists():
                        errors.append(str(error))
            threads = [threading.Thread(target=perceptions, daemon=True), threading.Thread(target=actions, daemon=True)]
            for thread in threads:
                thread.start()
            while not args.stop_file.exists():
                if process.poll() is not None or errors:
                    raise RuntimeError(f'Public client exited ({process.poll()}), relay errors={errors}')
                time.sleep(.1)
    except Exception as error:
        if not args.stop_file.exists():
            summary['error'] = str(error)
    finally:
        running.clear()
        for sock in [peer, upstream, listener]:
            if sock is not None:
                try: sock.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                sock.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=1)
        args.summary.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary))
    return int(summary['error'] is not None)


if __name__ == '__main__':
    raise SystemExit(main())
