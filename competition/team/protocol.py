"""Length-prefixed TCP and S-expressions used by the official server."""

import re
import socket

MAX_FRAME = 1_048_576
TOKEN = re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+)')


def parse(data: str) -> list:
    root = []
    stack = [root]
    position = 0
    for match in TOKEN.finditer(data):
        if data[position:match.start()].strip():
            raise ValueError("Invalid S-expression")
        position = match.end()
        token = match.group(1)
        if token == "(":
            if len(stack) > 64:
                raise ValueError("S-expression nesting limit exceeded")
            child = []
            stack[-1].append(child)
            stack.append(child)
        elif token == ")":
            if len(stack) == 1:
                raise ValueError("Unexpected closing parenthesis")
            stack.pop()
        else:
            if len(stack) == 1:
                raise ValueError("Expected a parenthesized expression")
            stack[-1].append(token[1:-1] if token.startswith('"') else token)
    if len(stack) != 1 or data[position:].strip():
        raise ValueError("Incomplete S-expression")
    return root


def fields(node: list) -> dict:
    return {item[0]: item[1:] for item in node[1:]
            if isinstance(item, list) and item and isinstance(item[0], str)}


class Connection:
    def __init__(self, host: str, port: int, timeout: float = 10):
        self.socket = socket.create_connection((host, port), timeout=timeout)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def _read(self, count: int) -> bytes:
        data = bytearray()
        while len(data) < count:
            chunk = self.socket.recv(count - len(data))
            if not chunk:
                raise ConnectionError("Server closed the connection")
            data.extend(chunk)
        return bytes(data)

    def receive(self) -> str:
        size = int.from_bytes(self._read(4), "big")
        if not 0 < size <= MAX_FRAME:
            raise ValueError(f"Invalid frame size: {size}")
        return self._read(size).decode("utf-8")

    def send(self, message: str) -> None:
        data = message.encode("utf-8")
        if not 0 < len(data) <= MAX_FRAME:
            raise ValueError("Invalid outgoing frame size")
        self.socket.sendall(len(data).to_bytes(4, "big") + data)

    def close(self) -> None:
        self.socket.close()
