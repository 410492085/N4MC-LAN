"""A private, port-only EasyTier room and Minecraft Java LAN discovery."""

import base64
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from ipaddress import IPv4Address, IPv4Network
import json
from pathlib import Path
import re
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from zipfile import ZipFile

from app_version import APP_NAME

VERSION = '2.6.4'
ASSET = f'easytier-windows-x86_64-v{VERSION}.zip'
DOWNLOAD_URL = f'https://github.com/EasyTier/EasyTier/releases/download/v{VERSION}/{ASSET}'
ARCHIVE_HASH = '27af91e270e554709b048bd32327fefd2dfce5062ae1e8701af7550c6f525f84'
ARCHIVE_SIZE = 32657720
FILES = {
    'easytier-core.exe': 'da7eb2d24b5416f3d3407636949e964a0750e3f9dc53a828cb6799a57ead445d',
    'easytier-cli.exe': 'd8783e851e944b44a9b71b39fd02f227ec0a2a82b3165c55ead5dd32dcde53a1',
    'Packet.dll': 'c7c03a87eac7243ccbe331554624b18803010b740e311fc8cfddb573096eacac',
}
APP_DIRECTORY = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
BUNDLED_RUNTIME = APP_DIRECTORY / 'bin' / 'easytier'
BUNDLED_FILES = {
    **FILES,
    # The portable edition uses the WinPcap x64 import-compatible DLL.
    'Packet.dll': 'ab3cce674f5216895fd26a073771f82b05d4c8b214a89f0f288a59774a06b14b',
}
HOST_IP = '10.203.69.1'
ROOM_SUBNET = IPv4Network(f'{HOST_IP}/24', strict=False)
PUBLIC_PEERS = ('wss://et.chinokou.cn', 'tcp://225284.xyz:11010', 'tcp://easytier.weiai.org.cn:11010')
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
LAN_GROUP = '224.0.2.60'
LAN_PORT = 4445
LAN_PROXY_NAME = f'{APP_NAME} 房间'


class RoomError(Exception):
    pass


class Cancelled(Exception):
    pass


@dataclass(frozen=True)
class RoomCode:
    secret: bytes
    port: int

    @classmethod
    def create(cls, port):
        if not 1 <= port <= 65535:
            raise ValueError('请填写 Minecraft 显示的局域网端口（1–65535）。')
        return cls(secrets.token_bytes(16), port)

    @property
    def text(self):
        payload = self.secret + struct.pack('!H', self.port)
        digits = base64.b32encode(payload + hashlib.sha256(payload).digest()[:2]).decode('ascii')
        return 'N4E1-' + '-'.join(digits[i:i + 8] for i in range(0, len(digits), 8))

    @classmethod
    def parse(cls, text):
        match = re.fullmatch(r'N4E1-([A-Z2-7]{8}(?:-[A-Z2-7]{8}){3})', text.strip().upper())
        if not match:
            raise ValueError('请粘贴完整的 N4E1- 房间短码。')
        raw = base64.b32decode(match[1].replace('-', ''))
        port = int.from_bytes(raw[16:18], 'big')
        if not port or not secrets.compare_digest(raw[18:], hashlib.sha256(raw[:18]).digest()[:2]):
            raise ValueError('房间短码有误，请让房主重新复制。')
        return cls(raw[:16], port)


def make_config(room, local_port=None, peers=PUBLIC_PEERS, listeners=None, relay_only=False):
    host = local_port is None
    if listeners is None:
        listeners = [] if relay_only else ['tcp://0.0.0.0:0', 'udp://0.0.0.0:0']
    identity = hashlib.sha256(room.secret).hexdigest()[:24]
    lines = [
        f'hostname = "n4tsum3-{"host" if host else "guest"}"',
        f'ipv4 = "{HOST_IP}"' if host else 'dhcp = true',
        f'listeners = {json.dumps(listeners)}',
        f'tcp_whitelist = ["{room.port if host else 0}"]',
        'udp_whitelist = ["0"]',
        '[network_identity]',
        f'network_name = "n4tsum3-{identity}"',
        f'network_secret = "{room.secret.hex()}"',
        '[flags]', 'no_tun = true', 'private_mode = true',
        'enable_encryption = true', 'latency_first = true', 'bind_device = false',
    ]
    if relay_only:
        lines.extend([
            'disable_p2p = true', 'disable_tcp_hole_punching = true',
            'disable_udp_hole_punching = true', 'disable_sym_hole_punching = true', 'disable_upnp = true',
        ])
    for peer in peers:
        lines.extend(['[[peer]]', f'uri = {json.dumps(peer)}'])
    if not host:
        lines.extend([
            '[[port_forward]]', 'proto = "tcp"',
            f'bind_addr = "127.0.0.1:{local_port}"',
            f'dst_addr = "{HOST_IP}:{room.port}"',
        ])
    return '\n'.join(lines) + '\n'


def _read_exact(sock, count, deadline):
    data = bytearray()
    while len(data) < count:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        sock.settimeout(remaining)
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise EOFError()
        data.extend(chunk)
    return bytes(data)


def _varint(read_byte):
    result = 0
    for shift in range(0, 35, 7):
        byte = read_byte()
        result |= (byte & 127) << shift
        if byte < 128:
            return result
    raise ValueError('Invalid VarInt')


def minecraft_status(port, timeout=2.5):
    # Java Server List Ping: status handshake followed by packet 0 (status request).
    handshake = b'\x00\xff\xff\xff\xff\x0f\x09127.0.0.1' + struct.pack('!H', port) + b'\x01'
    deadline = time.monotonic() + timeout
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout) as sock:
            sock.sendall(bytes([len(handshake)]) + handshake + b'\x01\x00')
            length = _varint(lambda: _read_exact(sock, 1, deadline)[0])
            if not 2 <= length <= 256 * 1024:
                return None
            packet = iter(_read_exact(sock, length, deadline))
            if _varint(lambda: next(packet)) != 0:
                return None
            size = _varint(lambda: next(packet))
            body = bytes(packet)
            if size != len(body):
                return None
            status = json.loads(body.decode('utf-8'))
            return status if isinstance(status, dict) else None
    except (OSError, EOFError, StopIteration, ValueError, RecursionError):
        return None


def _game_port_refused(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            return False
    except ConnectionRefusedError:
        return True
    except OSError:
        return False


def announce_lan(port, discovery_port=LAN_PORT):
    message = f'[MOTD]{LAN_PROXY_NAME}[/MOTD][AD]{port}[/AD]'.encode('utf-8')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1', 0))
        sock.sendto(message, ('127.0.0.1', discovery_port))


def lan_game_port(packet):
    match = re.fullmatch(rb'\[MOTD\](.*?)\[/MOTD\]\[AD\]([0-9]{1,5})\[/AD\]', packet, re.DOTALL)
    if match and match[1] != LAN_PROXY_NAME.encode('utf-8'):
        port = int(match[2])
        if 1 <= port <= 65535:
            return port
    return None


def world_details(status):
    def flatten(value, depth=0):
        if depth == 8:
            return ''
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ''.join(flatten(item, depth + 1) for item in value[:32])
        if isinstance(value, dict):
            return flatten(value.get('text', value.get('fallback')), depth + 1) + flatten(value.get('extra'), depth + 1)
        return ''

    def clean(value, limit):
        if not isinstance(value, str):
            return ''
        text = re.sub(r'§[0-9a-fk-orx]', '', value, flags=re.IGNORECASE)
        return ' '.join(text.split())[:limit]

    if status is None:
        return '', ''
    version = status.get('version')
    name = version.get('name') if isinstance(version, dict) else None
    return clean(flatten(status.get('description')), 120), clean(name, 64)


def discover_lan_worlds(local_ips, stop):
    ports = set()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('', LAN_PORT))
        group = socket.inet_aton(LAN_GROUP)
        joined = False
        for ip in sorted(local_ips - {'127.0.0.1'}):
            try:
                listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group + socket.inet_aton(ip))
                joined = True
            except OSError:
                continue
        if not joined:
            listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group + b'\x00' * 4)
        listener.settimeout(0.2)
        deadline = time.monotonic() + 4
        while len(ports) < 12 and not stop.is_set() and time.monotonic() < deadline:
            try:
                packet, sender = listener.recvfrom(8192)
            except TimeoutError:
                continue
            if sender[0] in local_ips and (port := lan_game_port(packet)) is not None:
                ports.add(port)

    worlds = []
    for port in sorted(ports):
        if stop.is_set():
            break
        status = minecraft_status(port, timeout=0.5)
        if status is not None:
            name, version = world_details(status)
            worlds.append(dict(port=port, label=' · '.join(filter(None, (name, version, str(port))))))
    return worlds


def _digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def _verified(directory, files=FILES):
    return all((directory / name).is_file() and _digest(directory / name) == expected
               for name, expected in files.items())


def install_archive(archive, directory):
    if _digest(archive) != ARCHIVE_HASH:
        raise RoomError('EasyTier 下载校验失败，请重试。')
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent) as staging, ZipFile(archive) as package:
        staged = Path(staging)
        for name in FILES:
            (staged / name).write_bytes(package.read(f'easytier-windows-x86_64/{name}'))
        if not _verified(staged):
            raise RoomError('EasyTier 组件校验失败。')
        for name in FILES:
            target = directory / name
            if not target.is_file() or _digest(target) != FILES[name]:
                (staged / name).replace(target)


def ensure_runtime(cache, stop, update):
    if _verified(BUNDLED_RUNTIME, BUNDLED_FILES):
        return BUNDLED_RUNTIME
    directory = cache / f'{VERSION}-x64'
    if _verified(directory):
        return directory
    cache.mkdir(parents=True, exist_ok=True)
    update('正在从官方 GitHub 下载 EasyTier（约 33 MB）…')
    with tempfile.TemporaryDirectory(dir=cache) as staging:
        archive = Path(staging) / ASSET
        try:
            with urlopen(DOWNLOAD_URL, timeout=8) as response, archive.open('wb') as output:
                size = 0
                deadline = time.monotonic() + 180
                while True:
                    if stop.is_set():
                        raise Cancelled()
                    if time.monotonic() >= deadline:
                        raise TimeoutError()
                    chunk = response.read1(128 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > ARCHIVE_SIZE:
                        raise RoomError('EasyTier 下载文件大小异常。')
                    output.write(chunk)
        except OSError as exc:
            raise RoomError('无法下载 EasyTier，请确认能访问 GitHub 后重试。') from exc
        if stop.is_set():
            raise Cancelled()
        install_archive(archive, directory)
    return directory


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@contextmanager
def start_core(directory, config, rpc_port):
    with tempfile.TemporaryDirectory(prefix='n4tsum3-room-') as staging:
        path = Path(staging) / 'room.toml'
        path.write_text(config, encoding='utf-8')
        process = subprocess.Popen(
            [str(directory / 'easytier-core.exe'), '-c', str(path), '-r', f'127.0.0.1:{rpc_port}'],
            cwd=staging, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=NO_WINDOW,
        )
        try:
            yield process
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()


def _cli_list(directory, rpc_port, command):
    try:
        result = subprocess.run(
            [str(directory / 'easytier-cli.exe'), '-p', f'127.0.0.1:{rpc_port}', '-o', 'json', command],
            capture_output=True, stdin=subprocess.DEVNULL, timeout=2, creationflags=NO_WINDOW,
        )
        if result.returncode != 0:
            return None
        rows = json.loads(result.stdout)
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else None
    except (OSError, ValueError, RecursionError, subprocess.TimeoutExpired):
        return None


def connected(directory, rpc_port):
    return any(row.get('status') == 0 for row in _cli_list(directory, rpc_port, 'connector') or ())


def _metric(value, unit, minimum, maximum):
    if not isinstance(value, str) or not value.endswith(unit):
        return None
    try:
        number = float(value.removesuffix(unit))
    except ValueError:
        return None
    return number if minimum <= number < maximum else None


def room_network(rows, host):
    if rows is None:
        return None
    devices = set()
    paths = set()
    latencies = []
    losses = []
    for row in rows:
        hostname = row.get('hostname')
        if hostname not in ('n4tsum3-host', 'n4tsum3-guest'):
            continue
        try:
            ip = IPv4Address(str(row.get('ipv4')))
        except ValueError:
            continue
        is_host = str(ip) == HOST_IP
        if ip not in ROOM_SUBNET or is_host != (hostname == 'n4tsum3-host'):
            continue
        devices.add(ip)
        cost = row.get('cost')
        if cost == 'Local' or is_host == host:
            continue
        direct = cost == 'p2p'
        if not direct and not (isinstance(cost, str) and cost.startswith('relay(')):
            continue
        paths.add('直连' if direct else '中继')
        latency = _metric(row.get('lat_ms'), '', 0.01, float('inf'))
        if latency is not None:
            latencies.append(latency)
        # EasyTier reports 0% by default when there are no direct connection stats.
        if direct and row.get('tunnel_proto') not in (None, '', '-') and latency is not None:
            loss = _metric(row.get('loss_rate'), '%', 0, 100.1)
            if loss is not None:
                losses.append(loss)
    return dict(devices=len(devices), path=' + '.join(path for path in ('直连', '中继') if path in paths) or
                ('等待朋友加入' if host else '未发现房主'),
                latency=f'{max(latencies):.0f} ms' if latencies else '—',
                loss=f'{max(losses):.1f}%' if losses else '—')


def _player_count(players, key):
    count = players.get(key) if isinstance(players, dict) else None
    return count if type(count) is int and 0 <= count <= 2**31 - 1 else -1


def run_room(room, host, cache, stop, update, relay_only=False, *, on_game=None, on_network=None, on_world=None):
    initial_status = minecraft_status(room.port) if host else None
    if host and initial_status is None:
        raise RoomError('这个端口没有回应 Minecraft 状态查询。请先在游戏里开放局域网，再填写显示的端口。')
    directory = ensure_runtime(cache, stop, lambda message: update(message, False, ''))
    if stop.is_set():
        return
    rpc_port = free_port()
    local_port = None if host else free_port()
    update('正在连接 EasyTier 公共节点…' if host else '正在寻找房主并检查游戏连接…', False, '')
    with start_core(directory, make_config(room, local_port, relay_only=relay_only), rpc_port) as process:
        started = time.monotonic()
        deadline = started + 50
        ready = False
        established = False
        probe_at = 0
        refused_checks = 0
        last_game = None
        last_world = None
        network_at = 0
        address = room.text if host else f'127.0.0.1:{local_port}'
        while not stop.is_set():
            if process.poll() is not None:
                raise RoomError(f'EasyTier 已退出（{process.returncode}）。请重试。')
            if time.monotonic() >= probe_at:
                if host and established:
                    status = minecraft_status(room.port)
                    reachable = status is not None
                    refused_checks = refused_checks + 1 if not reachable and _game_port_refused(room.port) else 0
                    if refused_checks >= 2:
                        raise RoomError('房主的游戏端口已关闭，房间已停止。重新开放局域网后请创建新房间。')
                elif host:
                    status = initial_status
                    reachable = connected(directory, rpc_port)
                    # Recheck the game after waiting for a public node.
                    if reachable and time.monotonic() - started >= 5:
                        status = minecraft_status(room.port)
                        if status is None:
                            raise RoomError('房主的游戏端口未回复。请确认世界仍开放局域网，然后重新创建房间。')
                else:
                    status = minecraft_status(local_port)
                    reachable = status is not None
                players = status.get('players') if status is not None else None
                game = (status is not None, _player_count(players, 'online'), _player_count(players, 'max'))
                if on_game is not None and game != last_game:
                    last_game = game
                    on_game(game)
                if on_world is not None:
                    world = world_details(status)
                    if world != last_world:
                        last_world = world
                        on_world(world)
                if reachable and not ready:
                    if established:
                        message = ('游戏状态查询已恢复，原短码仍有效。' if host else
                                   '游戏连接已恢复。如果 Minecraft 已掉线，请重新进入房间。')
                    else:
                        message = ('房间已创建。把短码私发给朋友，保持游戏和助手开启。' if host else
                                   f'游戏连接已就绪。请在 Minecraft「多人游戏」里点击 {APP_NAME} 房间。')
                    established = True
                    update(message, True, address)
                elif not reachable and ready:
                    if host:
                        update('Minecraft 暂未回复状态查询，房间和短码仍保留。正在重试…', True, address)
                    else:
                        update('暂时无法访问房主，正在继续重试。连接恢复后可以重新进入游戏。', False, '')
                ready = reachable
                probe_at = time.monotonic() + (5 if ready else 1)
                if not established and time.monotonic() >= deadline:
                    raise RoomError('无法连接公共节点，请检查网络后重试。' if host else
                                    '未连到房主的游戏。请确认房主仍在房间内、游戏已开放局域网，且双方能访问 EasyTier 公共节点。')
            if not host and ready and not stop.is_set():
                try:
                    announce_lan(local_port)
                except OSError:
                    update('游戏已连通，但局域网广播失败。可以复制地址到 Minecraft「直接连接」。',
                           True, f'127.0.0.1:{local_port}')
            if on_network is not None and not stop.is_set() and time.monotonic() >= network_at:
                on_network(room_network(_cli_list(directory, rpc_port, 'peer'), host))
                network_at = time.monotonic() + 5
            stop.wait(1.5 if ready else 0.4)
