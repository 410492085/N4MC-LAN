"""Readonly Tailscale integration. Never changes routes, login state or firewall."""
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess


def discover_cli():
    candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Tailscale/tailscale.exe'
    if candidate.is_file(): return str(candidate)
    return shutil.which('tailscale') or ''


def valid_ips(values):
    if not isinstance(values, list): return []
    result = []
    for value in values:
        if not isinstance(value, str): continue
        try: result.append(str(ipaddress.ip_address(value)))
        except (ValueError, TypeError): continue
    return sorted(result, key=lambda value: ':' in value)


def parse_status(text):
    try:
        data = json.loads(text)
        if not isinstance(data, dict): raise ValueError()
        state = data.get('BackendState', 'Unknown')
        own = data.get('Self') if data.get('Self') is not None else {}
        peers = data.get('Peer') if data.get('Peer') is not None else {}
        if not isinstance(own, dict) or not isinstance(peers, dict): raise ValueError()
        if 'Online' in own and type(own['Online']) is not bool: raise ValueError()
        ips = valid_ips(own.get('TailscaleIPs', []))
        ready = state == 'Running' and bool(ips) and own.get('Online') is not False
        rows = []
        if ready:
            for value in peers.values():
                if not isinstance(value, dict): continue
                addresses = valid_ips(value.get('TailscaleIPs', []))
                if not addresses: continue
                name = str(value.get('HostName') or value.get('DNSName') or addresses[0])[:80]
                rows.append({'name': name, 'ip': addresses[0], 'ips': addresses, 'online': value.get('Online') is True})
            rows.sort(key=lambda item: (not item['online'], item['name']))
        return {'ready': ready, 'state': str(state), 'ip': ips[0] if ready else '', 'peers': rows}
    except (ValueError, TypeError, RecursionError) as e:
        raise ValueError('无法解析 Tailscale 状态，请更新官方客户端后重试') from e


def read_status(cli):
    try:
        result = subprocess.run([cli, 'status', '--json'], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=6,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ValueError('无法连接 Tailscale 服务，请安装或打开官方客户端') from e
    if result.stdout.strip():
        return parse_status(result.stdout)
    raise ValueError('Tailscale 服务未返回状态，请打开官方客户端并登录')


def format_address(ip, port):
    try:
        address = str(ipaddress.ip_address(ip))
        if isinstance(port, bool): raise ValueError()
        number = int(port)
        if str(port).strip() != str(number) or not 1 <= number <= 65535: raise ValueError()
        return f'[{address}]:{number}' if ':' in address else f'{address}:{number}'
    except (ValueError, TypeError) as e:
        raise ValueError('请填写有效的组网 IP 和游戏显示的端口（1–65535）') from e


def probe_tcp(ip, port):
    format_address(ip, port)
    with socket.create_connection((ip, int(port)), timeout=3): pass
