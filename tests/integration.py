"""Real frps/frpc loopback transfer; no public network or Minecraft required."""
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
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    control, remote = free_port(), free_port()
    echo = socket.socket()
    echo.bind(('127.0.0.1', 0))
    echo.listen()
    echo.settimeout(15)

    def serve():
        try:
            conn, _ = echo.accept()
            with conn:
                while data := conn.recv(65536):
                    conn.sendall(data)
        finally:
            echo.close()

    threading.Thread(target=serve, daemon=True).start()
    tunnel = Tunnel(ROOT / 'bin/frpc.exe')
    with tempfile.TemporaryDirectory() as d:
        config = Path(d) / 'frps.toml'
        config.write_text(f'bindAddr="127.0.0.1"\nbindPort={control}\nauth.token="integration-secret"\n'
                          'auth.additionalScopes=["HeartBeats","NewWorkConns"]\ntransport.tls.force=true\n'
                          f'allowPorts=[{{single={remote}}}]\n', encoding='utf-8')
        server = subprocess.Popen([str(ROOT / 'test-tools/frps.exe'), '-c', str(config)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            tunnel.start(Settings(server='127.0.0.1', server_port=control, token='integration-secret',
                                  local_port=echo.getsockname()[1], remote_port=remote))
            deadline = time.monotonic() + 15
            while True:
                try:
                    client = socket.create_connection(('127.0.0.1', remote), timeout=2)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError('frp loopback tunnel did not become reachable')
                    time.sleep(.15)
            with client:
                client.settimeout(5)
                payload = b'Minecraft-Java-LAN-test\x00\xff' * 1000
                client.sendall(payload)
                received = bytearray()
                while len(received) < len(payload):
                    chunk = client.recv(65536)
                    if not chunk:
                        break
                    received.extend(chunk)
                assert bytes(received) == payload, 'TCP data mismatch'
            print(f'PASS: real frps/frpc TLS + Token TCP round-trip ({len(payload)} bytes)')
        finally:
            cfg = tunnel.config_path
            tunnel.stop()
            server.terminate()
            server.wait(timeout=5)
            assert not tunnel.running
            assert cfg is None or not cfg.exists(), 'secret config not cleaned'
            print('PASS: owned processes stopped and temporary secret config removed')


if __name__ == '__main__':
    main()
