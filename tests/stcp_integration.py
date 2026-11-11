"""Real local STCP host + visitor transfer. Requires Windows to permit official frpc."""
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import Settings
from tunnel import Tunnel


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]


def main():
    control, entry = free_port(), free_port()
    echo = socket.socket(); echo.bind(('127.0.0.1', 0)); echo.listen(); echo.settimeout(20)
    game_port = echo.getsockname()[1]
    def serve():
        try:
            conn, _ = echo.accept()
            with conn:
                while data := conn.recv(65536): conn.sendall(data)
        except OSError: pass
        finally: echo.close()
    threading.Thread(target=serve, daemon=True).start()
    owner, visitor = Tunnel(ROOT / 'bin/frpc.exe'), Tunnel(ROOT / 'bin/frpc.exe')
    with tempfile.TemporaryDirectory() as d:
        cfg = Path(d) / 'frps.toml'
        cfg.write_text(f'bindAddr="127.0.0.1"\nbindPort={control}\nauth.token="local-node-secret"\n'
                       'auth.additionalScopes=["HeartBeats","NewWorkConns"]\ntransport.tls.force=true\n', encoding='utf-8')
        server = subprocess.Popen([str(ROOT / 'test-tools/frps.exe'), '-c', str(cfg)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            common = dict(server='127.0.0.1', server_port=control, token='local-node-secret',
                          room_name='local-test-room', room_secret='local-room-secret-12345')
            owner.start(Settings(**common, mode='host', local_port=game_port))
            visitor.start(Settings(**common, mode='join', visitor_port=entry))
            deadline = time.monotonic() + 15
            while True:
                try:
                    conn = socket.create_connection(('127.0.0.1', entry), timeout=1)
                    with conn:
                        conn.settimeout(2)
                        data = b'Minecraft-STCP-friend-join\x00\xff' * 100
                        conn.sendall(data)
                        received = bytearray()
                        while len(received) < len(data):
                            part = conn.recv(65536)
                            if not part: break
                            received.extend(part)
                        if bytes(received) == data: break
                except OSError: pass
                if time.monotonic() > deadline: raise AssertionError('STCP transfer did not succeed')
                time.sleep(.15)
            print('PASS: real STCP host/visitor data round-trip')
        finally:
            visitor.stop(); owner.stop()
            server.terminate(); server.wait(timeout=5)
            echo.close()
            for client in [owner, visitor]:
                assert not client.running
                assert client.config_path is None or not client.config_path.exists()


if __name__ == '__main__': main()
