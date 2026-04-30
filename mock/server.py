#!/usr/bin/env python3
"""
Mock Minecraft Java server for verification environments.

Implements the Server List Ping (SLP) protocol and exposes an HTTP control API
to switch server state at runtime.

Minecraft port behavior by state:
  running  → responds to SLP with player data (mcstatus returns state="running")
  stopped  → accepts TCP but never responds, causes socket.timeout (state="stopped")
  starting → port is closed, causes ConnectionRefusedError (state="starting")
  unknown  → sends malformed data (state="unknown")

HTTP control API (default port 8080):
  GET  /state          → {"state": "running"}
  POST /state          → body: {"state": "stopped"}, response: {"state": "stopped"}
  GET  /config         → current mock player/server config
  POST /config         → update mock data (online, max, motd, version)
"""

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Shared mock configuration
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_state = "running"

_config = {
    "online": int(os.getenv("MOCK_PLAYERS_ONLINE", "3")),
    "max": int(os.getenv("MOCK_PLAYERS_MAX", "20")),
    "motd": os.getenv("MOCK_MOTD", "Mock Minecraft Server"),
    "version": os.getenv("MOCK_VERSION", "1.20.1"),
    "protocol": int(os.getenv("MOCK_PROTOCOL", "763")),
}

VALID_STATES = {"running", "stopped", "starting", "unknown"}

# ---------------------------------------------------------------------------
# VarInt / packet helpers
# ---------------------------------------------------------------------------


def encode_varint(value: int) -> bytes:
    buf = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        buf.append(byte)
        if not value:
            break
    return bytes(buf)


def decode_varint_stream(sock: socket.socket) -> int:
    result = 0
    shift = 0
    while True:
        raw = sock.recv(1)
        if not raw:
            raise ConnectionError("connection closed while reading varint")
        b = raw[0]
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result
        shift += 7
        if shift >= 35:
            raise ValueError("varint too large")


def recv_packet(sock: socket.socket) -> tuple[int, bytes]:
    length = decode_varint_stream(sock)
    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            raise ConnectionError("connection closed while reading packet")
        payload += chunk
    packet_id, offset = _decode_varint_bytes(payload, 0)
    return packet_id, payload[offset:]


def _decode_varint_bytes(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, offset
        shift += 7


def encode_string(s: str) -> bytes:
    encoded = s.encode("utf-8")
    return encode_varint(len(encoded)) + encoded


def make_packet(packet_id: int, data: bytes = b"") -> bytes:
    payload = encode_varint(packet_id) + data
    return encode_varint(len(payload)) + payload


# ---------------------------------------------------------------------------
# Client handlers (one per state)
# ---------------------------------------------------------------------------


def _handle_running(conn: socket.socket) -> None:
    conn.settimeout(5.0)
    recv_packet(conn)   # handshake
    recv_packet(conn)   # status request

    with _lock:
        cfg = dict(_config)

    status_json = json.dumps({
        "version": {"name": cfg["version"], "protocol": cfg["protocol"]},
        "players": {"max": cfg["max"], "online": cfg["online"], "sample": []},
        "description": {"text": cfg["motd"]},
    })
    conn.sendall(make_packet(0x00, encode_string(status_json)))

    try:
        packet_id, ping_data = recv_packet(conn)
        if packet_id == 0x01:
            conn.sendall(make_packet(0x01, ping_data))
    except Exception:
        pass


def _handle_stopped(conn: socket.socket) -> None:
    # Accept the connection but never respond → client hits socket.timeout
    time.sleep(30)


def _handle_unknown(conn: socket.socket) -> None:
    # Send garbage that mcstatus cannot parse
    conn.sendall(b"\x00\x01\x02\x03")


# ---------------------------------------------------------------------------
# Dynamic TCP server (supports closing/reopening the listening socket)
# ---------------------------------------------------------------------------


class _MCServer:
    """Manages the Minecraft TCP listener; reopened when leaving 'starting'."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._sock_lock = threading.Lock()
        self._sock: socket.socket | None = None

    def _open(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(10)
        self._sock = s

    def _close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def apply_state(self, new_state: str) -> None:
        with self._sock_lock:
            if new_state == "starting":
                self._close()
            elif self._sock is None:
                self._open()

    def serve(self) -> None:
        # Socket lifecycle is managed by apply_state; just loop and accept.
        while True:
            with self._sock_lock:
                sock = self._sock

            if sock is None:
                time.sleep(0.05)
                continue

            try:
                sock.settimeout(0.5)
                conn, addr = sock.accept()
            except socket.timeout:
                continue
            except OSError:
                time.sleep(0.05)
                continue

            with _lock:
                current = _state

            print(f"[mc] connection from {addr}, state={current}")
            threading.Thread(
                target=self._dispatch,
                args=(conn, current),
                daemon=True,
            ).start()

    @staticmethod
    def _dispatch(conn: socket.socket, state: str) -> None:
        try:
            if state == "running":
                _handle_running(conn)
            elif state == "stopped":
                _handle_stopped(conn)
            elif state == "unknown":
                _handle_unknown(conn)
            # "starting" → port is closed, this branch is unreachable
        except Exception as exc:
            print(f"[mc] handler error: {exc}")
        finally:
            try:
                conn.close()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# HTTP control server
# ---------------------------------------------------------------------------

_mc_server_ref: _MCServer | None = None


class _ControlHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return None

    def do_GET(self) -> None:
        if self.path == "/state":
            with _lock:
                self._send_json(200, {"state": _state})
        elif self.path == "/config":
            with _lock:
                self._send_json(200, dict(_config))
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        global _state
        body = self._read_json()
        if body is None:
            self._send_json(400, {"error": "invalid JSON"})
            return

        if self.path == "/state":
            new_state = body.get("state")
            if new_state not in VALID_STATES:
                self._send_json(400, {"error": f"state must be one of {sorted(VALID_STATES)}"})
                return
            with _lock:
                _state = new_state
            if _mc_server_ref:
                _mc_server_ref.apply_state(new_state)
            print(f"[ctrl] state → {new_state}")
            self._send_json(200, {"state": new_state})

        elif self.path == "/config":
            with _lock:
                for key in ("online", "max", "motd", "version", "protocol"):
                    if key in body:
                        _config[key] = body[key]
                self._send_json(200, dict(_config))
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[ctrl] {self.address_string()} {fmt % args}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    global _mc_server_ref

    mc_host = os.getenv("MC_HOST", "0.0.0.0")
    mc_port = int(os.getenv("MC_PORT", "25565"))
    ctrl_host = os.getenv("CTRL_HOST", "0.0.0.0")
    ctrl_port = int(os.getenv("CTRL_PORT", "8080"))
    initial_state = os.getenv("INITIAL_STATE", "running")

    if initial_state not in VALID_STATES:
        raise ValueError(f"INITIAL_STATE must be one of {sorted(VALID_STATES)}")

    global _state
    _state = initial_state

    mc = _MCServer(mc_host, mc_port)
    _mc_server_ref = mc
    mc.apply_state(initial_state)

    mc_thread = threading.Thread(target=mc.serve, daemon=True)
    mc_thread.start()
    print(f"[mc] mock Minecraft server on {mc_host}:{mc_port} (state={initial_state})")

    httpd = HTTPServer((ctrl_host, ctrl_port), _ControlHandler)
    print(f"[ctrl] control API on {ctrl_host}:{ctrl_port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
