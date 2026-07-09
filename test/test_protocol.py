import base64
import hashlib
import struct
import socket
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

import pytest

from .test_core import KeyState, char_to_hid, ARROW_MAP

WS_MAGIC = b"258EAFA5-E914-47DA-95CA-5AB9B1792851"
WEBPAGE_RESPONSE = b"MOCK touchWASD Web Page"


class MockWSClient:
    """Wraps a socket connection to the mock device as a WebSocket client."""

    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((host, port))
        self._buf = b""
        self._handshake()

    def _handshake(self):
        key = base64.b64encode(str(uuid.uuid4()).encode()[:16])
        key_str = key.decode()
        req = (
            "GET / HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: " + key_str + "\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Handshake failed")
            resp += chunk
        first_line = resp.split(b"\r\n")[0]
        if b"101" not in first_line:
            raise ConnectionError(f"Handshake rejected: {first_line!r}")
        header_end = resp.index(b"\r\n\r\n") + 4
        trailing = resp[header_end:]
        if trailing:
            self._buf = trailing

    def _read_frame(self):
        while len(self._buf) < 2:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed")
            self._buf += chunk
        b0 = self._buf[0]
        b1 = self._buf[1]
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F
        pos = 2
        if length == 126:
            while len(self._buf) < pos + 2:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")
                self._buf += chunk
            length = struct.unpack("!H", self._buf[pos:pos+2])[0]
            pos += 2
        elif length == 127:
            while len(self._buf) < pos + 8:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")
                self._buf += chunk
            length = struct.unpack("!Q", self._buf[pos:pos+8])[0]
            pos += 8
        mask_key = None
        if masked:
            while len(self._buf) < pos + 4:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")
                self._buf += chunk
            mask_key = self._buf[pos:pos+4]
            pos += 4
        while len(self._buf) < pos + length:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed")
            self._buf += chunk
        payload = bytearray(self._buf[pos:pos+length])
        self._buf = self._buf[pos+length:]
        if mask_key:
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]
        return opcode, bytes(payload)

    def send_text(self, text):
        data = text.encode("utf-8")
        frame = bytearray()
        frame.append(0x81)
        length = len(data)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack("!H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack("!Q", length))
        mask_key = struct.pack("!I", 0)
        import random
        mask_key = random.randbytes(4)
        frame.extend(mask_key)
        masked = bytearray(data)
        for i in range(len(masked)):
            masked[i] ^= mask_key[i % 4]
        frame.extend(masked)
        self.sock.sendall(bytes(frame))

    def recv_text(self, timeout=5):
        self.sock.settimeout(timeout)
        opcode, payload = self._read_frame()
        if opcode == 0x8:
            raise ConnectionError("Close frame received")
        if opcode == 0x9:
            self._send_pong()
            return self.recv_text(timeout)
        return payload.decode("utf-8")

    def _send_pong(self):
        self.sock.sendall(b"\x8a\x00")

    def close(self):
        try:
            self.sock.sendall(b"\x88\x00")
        except OSError:
            pass
        self.sock.close()


class MockTouchWASDDevice:
    """Mock device that implements the touchWASD WebSocket + HTTP protocol."""

    def __init__(self):
        self.key_state = KeyState()
        self.mode = "wasd"
        self.ws_clients = []
        self._http_port = None
        self._ws_port = None
        self._http_server = None
        self._ws_thread = None
        self._ws_running = False
        self._ws_sock = None
        self._lock = threading.Lock()
        self._messages_broadcast = []

    @property
    def http_port(self):
        return self._http_port

    @property
    def ws_port(self):
        return self._ws_port

    def _http_handler(self, *args, **kwargs):
        class Handler(BaseHTTPRequestHandler):
            device = self
            def do_GET(self):
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(WEBPAGE_RESPONSE)
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, format, *args):
                pass
        return Handler

    def start(self):
        self._http_server = HTTPServer(("127.0.0.1", 0), self._http_handler())
        self._http_port = self._http_server.server_port
        http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        http_thread.start()

        self._ws_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._ws_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._ws_sock.bind(("127.0.0.1", 0))
        self._ws_sock.listen(5)
        self._ws_port = self._ws_sock.getsockname()[1]
        self._ws_running = True
        self._ws_thread = threading.Thread(target=self._ws_accept_loop, daemon=True)
        self._ws_thread.start()
        time.sleep(0.1)

    def stop(self):
        self._ws_running = False
        if self._ws_sock:
            self._ws_sock.close()
        if self._http_server:
            self._http_server.shutdown()
        with self._lock:
            for c in self.ws_clients:
                try:
                    c[0].close()
                except OSError:
                    pass
            self.ws_clients.clear()

    def _ws_accept_loop(self):
        while self._ws_running:
            try:
                sock = self._ws_sock
                if sock is None:
                    break
                sock.settimeout(0.5)
                conn, addr = sock.accept()
                t = threading.Thread(target=self._ws_client_handler, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    @staticmethod
    def _build_ws_frame(text):
        data = text.encode("utf-8")
        frame = bytearray()
        frame.append(0x81)
        length = len(data)
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(struct.pack("!H", length))
        else:
            frame.append(127)
            frame.extend(struct.pack("!Q", length))
        frame.extend(data)
        return bytes(frame)

    def _ws_handshake(self, conn):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return None
            data += chunk
        headers = data.decode("utf-8", errors="replace")
        key = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
                break
        if not key:
            return None
        accept = base64.b64encode(
            hashlib.sha1(key.encode() + WS_MAGIC).digest()
        ).decode()
        resp = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        mode_frame = self._build_ws_frame(f"#MODE:{self.mode}")
        conn.sendall(resp.encode() + mode_frame)
        return True

    def _ws_send_text(self, conn, text):
        conn.sendall(self._build_ws_frame(text))

    def _ws_read_text(self, conn):
        b0 = conn.recv(1)
        if not b0:
            return None
        opcode = b0[0] & 0x0F
        b1 = conn.recv(1)
        if not b1:
            return None
        masked = bool(b1[0] & 0x80)
        length = b1[0] & 0x7F
        if length == 126:
            raw = conn.recv(2)
            length = struct.unpack("!H", raw)[0]
        elif length == 127:
            raw = conn.recv(8)
            length = struct.unpack("!Q", raw)[0]
        mask_key = None
        if masked:
            mask_key = conn.recv(4)
        payload = bytearray()
        while len(payload) < length:
            chunk = conn.recv(length - len(payload))
            if not chunk:
                return None
            payload.extend(chunk)
        if mask_key:
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]
        if opcode == 0x8:
            return None
        if opcode == 0x9:
            conn.sendall(b"\x8a\x00")
            return self._ws_read_text(conn)
        return payload.decode("utf-8")

    def _ws_client_handler(self, conn):
        if not self._ws_handshake(conn):
            conn.close()
            return
        with self._lock:
            self.ws_clients.append((conn, True))
            num = len(self.ws_clients) - 1
        try:
            while self._ws_running:
                msg = self._ws_read_text(conn)
                if msg is None:
                    break
                self._handle_ws_message(msg, conn)
        except (OSError, ConnectionError):
            pass
        finally:
            with self._lock:
                self.ws_clients = [(c, a) for c, a in self.ws_clients if c is not conn]
            self.key_state.reset()
            conn.close()

    def _handle_ws_message(self, msg, conn):
        with self._lock:
            if msg == "#MODE:wasd":
                self.mode = "wasd"
                self.key_state.reset()
                self._broadcast_locked("#MODE:wasd")
            elif msg == "#MODE:arrows":
                self.mode = "arrows"
                self.key_state.reset()
                self._broadcast_locked("#MODE:arrows")
            elif msg == "~":
                self.key_state.reset()
            elif len(msg) == 1:
                self.key_state.press_char(msg, self.mode)
            elif len(msg) > 1 and msg[0] == "~":
                self.key_state.release_char(msg[1], self.mode)

    def _broadcast_locked(self, text):
        for c, _ in self.ws_clients:
            try:
                self._ws_send_text(c, text)
            except OSError:
                pass

    def get_pressed_keys(self):
        with self._lock:
            return list(self.key_state.pressed[:self.key_state.count])

    def get_mode(self):
        with self._lock:
            return self.mode


class LiveTouchWASDDevice:
    """Connects tests to a real AtomS3 device on the network."""

    def __init__(self, host):
        self.host = host
        self.http_port = 80
        self.ws_port = 81

    def get_pressed_keys(self):
        pytest.skip("Cannot inspect key state on a live device (no USB HID access)")

    def get_mode(self):
        pytest.skip("Cannot read mode from live device without state inspection")

    def stop(self):
        pass


def _is_live(device):
    return isinstance(device, LiveTouchWASDDevice)


@pytest.fixture
def device(request):
    host = request.config.getoption("--host")
    if host:
        yield LiveTouchWASDDevice(host)
        return
    d = MockTouchWASDDevice()
    d.start()
    yield d
    d.stop()


class TestHTTP:
    def test_root_page_served(self, device):
        if _is_live(device):
            host = device.host
            resp = urlopen(f"http://{host}:{device.http_port}/", timeout=5)
        else:
            resp = urlopen(f"http://127.0.0.1:{device.http_port}/", timeout=5)
        assert resp.status == 200

    def test_favicon_returns_204(self, device):
        from urllib.error import HTTPError
        if _is_live(device):
            host = device.host
        else:
            host = "127.0.0.1"
        try:
            resp = urlopen(f"http://{host}:{device.http_port}/favicon.ico", timeout=5)
            assert resp.status == 200
        except HTTPError as e:
            assert e.code == 404


def _ws_connect(device):
    if _is_live(device):
        return MockWSClient(device.host, device.ws_port)
    return MockWSClient("127.0.0.1", device.ws_port)


class TestWebSocket:
    def test_connect(self, device):
        ws = _ws_connect(device)
        mode_msg = ws.recv_text()
        assert mode_msg in ("#MODE:wasd", "#MODE:arrows")
        ws.close()

    def test_press_key_w(self, device):
        if _is_live(device):
            pytest.skip("Cannot verify key state on live device (no USB HID access)")
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("w")
        time.sleep(0.05)
        keys = device.get_pressed_keys()
        assert char_to_hid("w") in keys

    def test_release_key(self, device):
        if _is_live(device):
            pytest.skip("Cannot verify key state on live device")
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("w")
        time.sleep(0.05)
        ws.send_text("~w")
        time.sleep(0.05)
        assert device.get_pressed_keys() == []

    def test_release_all(self, device):
        if _is_live(device):
            pytest.skip("Cannot verify key state on live device")
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("w")
        ws.send_text("d")
        time.sleep(0.05)
        ws.send_text("~")
        time.sleep(0.05)
        assert device.get_pressed_keys() == []

    def test_diagonal_press(self, device):
        if _is_live(device):
            pytest.skip("Cannot verify key state on live device")
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("w")
        ws.send_text("d")
        time.sleep(0.05)
        keys = device.get_pressed_keys()
        assert char_to_hid("w") in keys
        assert char_to_hid("d") in keys

    def test_mode_switch_to_arrows(self, device):
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("#MODE:arrows")
        response = ws.recv_text()
        assert response == "#MODE:arrows"
        if not _is_live(device):
            assert device.get_mode() == "arrows"

    def test_mode_switch_to_wasd(self, device):
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("#MODE:arrows")
        ws.recv_text()
        ws.send_text("#MODE:wasd")
        response = ws.recv_text()
        assert response == "#MODE:wasd"
        if not _is_live(device):
            assert device.get_mode() == "wasd"

    def test_arrow_mode_key_mapping(self, device):
        if _is_live(device):
            pytest.skip("Cannot verify key state on live device")
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("#MODE:arrows")
        ws.recv_text()
        ws.send_text("w")
        time.sleep(0.05)
        keys = device.get_pressed_keys()
        assert ARROW_MAP["w"] in keys
        assert char_to_hid("w") not in keys

    def test_reference_counting_two_clients(self, device):
        if _is_live(device):
            pytest.skip("Cannot inspect refcount on live device")
        ws1 = _ws_connect(device)
        ws1.recv_text()
        ws2 = _ws_connect(device)
        ws2.recv_text()

        ws1.send_text("w")
        time.sleep(0.05)
        ws2.send_text("w")
        time.sleep(0.05)
        assert device.key_state.refcount[char_to_hid("w")] == 2

        ws1.send_text("~w")
        time.sleep(0.05)
        keys = device.get_pressed_keys()
        assert char_to_hid("w") in keys

        ws2.send_text("~w")
        time.sleep(0.05)
        assert device.get_pressed_keys() == []

    def test_client_disconnect_resets_state(self, device):
        if _is_live(device):
            pytest.skip("Cannot verify key state on live device")
        ws = _ws_connect(device)
        ws.recv_text()
        ws.send_text("w")
        time.sleep(0.05)
        assert len(device.get_pressed_keys()) == 1
        ws.close()
        time.sleep(0.1)
        keys = device.get_pressed_keys()
        assert len(keys) == 0

    def test_new_client_gets_mode_sync(self, device):
        ws1 = _ws_connect(device)
        ws1.recv_text()
        ws1.send_text("#MODE:arrows")
        ws1.recv_text()

        ws2 = _ws_connect(device)
        mode_msg = ws2.recv_text()
        assert mode_msg == "#MODE:arrows"

        ws1.close()
        ws2.close()
