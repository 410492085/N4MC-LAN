"""Versioned, bounded invitation codec. Invitations are credentials, not encryption."""
import base64
import binascii
import json
from core import Settings

PREFIX = 'N4ROOM1:'
KEYS = {'v', 'server', 'server_port', 'room_name', 'room_secret', 'system_ca', 'server_name', 'requires_ca', 'scopes'}


def _validate(data):
    if not isinstance(data, dict) or set(data) != KEYS or type(data['v']) is not int or data['v'] != 1:
        raise ValueError('不支持的房间邀请格式')
    for key in ['server', 'room_name', 'room_secret', 'server_name']:
        if not isinstance(data[key], str): raise ValueError('房间邀请字段类型错误')
    if type(data['server_port']) is not int or type(data['system_ca']) is not bool or type(data['requires_ca']) is not bool:
        raise ValueError('房间邀请字段类型错误')
    Settings(server=data['server'], server_port=data['server_port'], token='validation-only', mode='join',
             room_name=data['room_name'], room_secret=data['room_secret'], system_ca=data['system_ca'],
             server_name=data['server_name'], scopes=data['scopes']).validate()
    return data


def encode_invitation(settings):
    if settings.mode != 'host': raise ValueError('只有房主可以创建邀请')
    data = _validate(dict(v=1, server=settings.server, server_port=settings.server_port,
                          room_name=settings.room_name, room_secret=settings.room_secret,
                          system_ca=settings.system_ca, server_name=settings.server_name,
                          requires_ca=bool(settings.ca_file or settings.require_ca), scopes=settings.scopes))
    return PREFIX + base64.urlsafe_b64encode(json.dumps(data, ensure_ascii=True, separators=(',', ':')).encode()).decode().rstrip('=')


def decode_invitation(code):
    if not isinstance(code, str) or len(code) > 8192 or not code.strip().startswith(PREFIX):
        raise ValueError('请粘贴完整的 N4ROOM1: 房间邀请')
    raw = code.strip()[len(PREFIX):]
    try:
        data = json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4), altchars=b'-_', validate=True))
        return _validate(data)
    except (ValueError, TypeError, KeyError, binascii.Error, UnicodeDecodeError, RecursionError) as e:
        raise ValueError('房间邀请无效或已损坏，请让房主重新复制') from e
