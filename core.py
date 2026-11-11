"""Validated configuration for one Minecraft Java TCP tunnel (no third party dependencies)."""
from dataclasses import asdict, dataclass, field
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import tomllib


def host(value: str, label: str, optional=False):
    if optional and not value:
        return
    try:
        ipaddress.ip_address(value)
        return
    except ValueError:
        pass
    if not value or len(value) > 253 or not all(
        re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', part)
        for part in value.rstrip('.').split('.')
    ):
        raise ValueError(f'{label}应填写 IP 或域名，不要包含协议、空格或端口')


@dataclass
class Settings:
    server: str = ''
    server_port: int = 7000
    token: str = ''
    name: str = 'minecraft'
    local_host: str = '127.0.0.1'
    local_port: int = 0
    remote_port: int = 25565
    public_host: str = ''
    ca_file: str = ''
    system_ca: bool = False
    server_name: str = ''
    scopes: list = field(default_factory=lambda: ['HeartBeats', 'NewWorkConns'])
    mode: str = 'public'
    room_name: str = 'minecraft-room'
    room_secret: str = ''
    visitor_port: int = 25566
    visitor_name: str = 'minecraft-visitor'
    require_ca: bool = False

    def validate(self):
        host(self.server, '节点地址')
        host(self.server_name, 'TLS 服务器名', True)
        if self.mode not in ['public', 'host', 'join']:
            raise ValueError('不支持的联机模式')
        if self.mode != 'join': host(self.local_host, '本地地址')
        if self.mode == 'public': host(self.public_host, '玩家连接地址', True)
        ports = [('server_port', '控制端口')]
        ports += [('visitor_port', '朋友本地入口端口')] if self.mode == 'join' else [('local_port', 'MC 局域网端口')]
        if self.mode == 'public': ports += [('remote_port', '公网游戏端口')]
        for key, label in ports:
            value = getattr(self, key)
            if type(value) is not int or not 1 <= value <= 65535:
                raise ValueError(f'{label}必须是 1–65535 的整数')
        if not self.token:
            raise ValueError('请填写节点 Token（需与服务端一致）')
        if self.mode == 'public' and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', self.name):
            raise ValueError('隧道名称仅支持 1–64 位英文字母、数字、下划线和短横线')
        if self.mode == 'join' and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', self.visitor_name):
            raise ValueError('访问端名称仅支持 1–64 位英文字母、数字、下划线和短横线')
        if self.ca_file and not Path(self.ca_file).is_file():
            raise ValueError('找不到可信 CA 文件，请重新选择')
        if self.require_ca and not self.ca_file:
            raise ValueError('此房间要求自定义 CA，请在安全设置中选择房主提供的可信 CA 文件')
        if self.mode != 'public':
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', self.room_name):
                raise ValueError('房间 ID 应为 1–48 位字母、数字、下划线或短横线')
            if not isinstance(self.room_secret, str) or not 8 <= len(self.room_secret) <= 256:
                raise ValueError('房间密钥应为 8–256 个字符，可点击生成新房间')
        if type(self.system_ca) is not bool:
            raise ValueError('系统 CA 必须是布尔值')
        if not isinstance(self.scopes, list) or any(x not in ['HeartBeats', 'NewWorkConns'] for x in self.scopes):
            raise ValueError('不支持的附加鉴权范围')

    def join_address(self):
        if self.mode == 'join': return f'127.0.0.1:{self.visitor_port}'
        if self.mode == 'host': return f'房间 · {self.room_name}'
        value = self.public_host or self.server
        return f'[{value}]:{self.remote_port}' if ':' in value else f'{value}:{self.remote_port}'

    def to_toml(self):
        self.validate()
        q = lambda x: json.dumps(x, ensure_ascii=True)
        common = (f'serverAddr = {q(self.server)}\nserverPort = {self.server_port}\n'
                f'auth.method = "token"\nauth.token = {q(self.token)}\n'
                f'auth.additionalScopes = {q(self.scopes)}\n'
                'transport.tls.enable = true\n'
                f'transport.tls.useSystemCa = {str(self.system_ca).lower()}\n'
                f'transport.tls.trustedCaFile = {q(self.ca_file)}\n'
                f'transport.tls.serverName = {q(self.server_name)}\n\n')
        if self.mode == 'host':
            return common + (f'[[proxies]]\nname = {q(self.room_name)}\ntype = "stcp"\n'
                             f'secretKey = {q(self.room_secret)}\nlocalIP = {q(self.local_host)}\nlocalPort = {self.local_port}\n')
        if self.mode == 'join':
            return common + (f'[[visitors]]\nname = {q(self.visitor_name)}\ntype = "stcp"\n'
                             f'serverName = {q(self.room_name)}\nsecretKey = {q(self.room_secret)}\n'
                             f'bindAddr = "127.0.0.1"\nbindPort = {self.visitor_port}\n')
        return common + (f'[[proxies]]\nname = {q(self.name)}\ntype = "tcp"\n'
                f'localIP = {q(self.local_host)}\nlocalPort = {self.local_port}\n'
                f'remotePort = {self.remote_port}\n')

    @classmethod
    def from_toml(cls, text, base_dir=None):
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise ValueError('TOML 格式错误，请检查原配置') from e
        flat = {}

        def flatten(obj, prefix=''):
            for k, v in obj.items():
                key = prefix + k
                if isinstance(v, dict):
                    flatten(v, key + '.')
                else:
                    flat[key] = v

        proxies = data.pop('proxies', [])
        visitors = data.pop('visitors', [])
        if not isinstance(proxies, list) or not isinstance(visitors, list) or len(proxies) + len(visitors) != 1:
            raise ValueError('仅支持单个 TCP / STCP 房主或朋友配置，不能混合多个隧道')
        flatten(data)
        mapping = {'serverAddr': 'server', 'serverPort': 'server_port', 'auth.token': 'token',
                   'auth.additionalScopes': 'scopes', 'transport.tls.trustedCaFile': 'ca_file',
                   'transport.tls.useSystemCa': 'system_ca', 'transport.tls.serverName': 'server_name'}
        constants = {'auth.method': 'token', 'transport.tls.enable': True}
        values = {'scopes': []}
        for k, v in flat.items():
            if k in constants:
                if type(v) is not type(constants[k]) or v != constants[k]:
                    raise ValueError(f'不支持配置项 {k} 的此取值')
            elif k in mapping:
                values[mapping[k]] = v
            else:
                raise ValueError(f'不支持配置项 {k}；为保留原配置含义，请使用服务商专用客户端')
        proxy = (proxies or visitors)[0]
        if not isinstance(proxy, dict): raise ValueError('无效隧道配置')
        proxy_type = proxy.get('type', 'tcp')
        if visitors:
            if proxy_type != 'stcp' or proxy.get('bindAddr', '127.0.0.1') != '127.0.0.1':
                raise ValueError('朋友模式仅支持 STCP 且只监听 127.0.0.1')
            values['mode'] = 'join'
            pm = {'name': 'visitor_name', 'serverName': 'room_name', 'secretKey': 'room_secret', 'bindPort': 'visitor_port'}
            required = ['name', 'serverName', 'secretKey', 'bindPort']
        elif proxy_type == 'stcp':
            values['mode'] = 'host'
            pm = {'name': 'room_name', 'secretKey': 'room_secret', 'localIP': 'local_host', 'localPort': 'local_port'}
            required = ['name', 'secretKey', 'localPort']
        elif proxy_type == 'tcp':
            pm = {'name': 'name', 'localIP': 'local_host', 'localPort': 'local_port', 'remotePort': 'remote_port'}
            required = ['name', 'localPort', 'remotePort']
        else:
            raise ValueError('仅支持 TCP 或 STCP 模式')
        if any(k not in proxy for k in required):
            raise ValueError('缺少必需配置项：' + ', '.join(k for k in required if k not in proxy))
        for k, v in proxy.items():
            if k == 'type' or (visitors and k == 'bindAddr'):
                continue
            if k not in pm:
                raise ValueError(f'不支持代理配置项 {k}，仅支持普通 TCP 隧道')
            values[pm[k]] = v
        result = cls(**values)
        if result.ca_file and base_dir:
            result.ca_file = str((Path(base_dir) / result.ca_file).resolve())
        # Fail closed on wrong primitive types instead of crashing later in validation/UI.
        defaults = cls()
        for key, value in asdict(result).items():
            if type(value) is not type(getattr(defaults, key)):
                raise ValueError(f'配置项 {key} 类型错误')
        result.validate()
        return result


def save_settings(path: Path, settings: Settings, remember=False, executable=''):
    data = asdict(settings)
    if not remember:
        data['token'] = ''
        data['room_secret'] = ''
    data['_remember'] = remember
    data['_executable'] = executable
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def load_settings(path: Path):
    data = json.loads(Path(path).read_text('utf-8'))
    return Settings(**{k: v for k, v in data.items() if not k.startswith('_')})


def check_port(hostname, port, timeout=2):
    with socket.create_connection((hostname, int(port)), timeout=timeout):
        return True


def check_listener_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(('127.0.0.1', port))
