import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from core import Settings, save_settings, load_settings
from rooms import encode_invitation, decode_invitation


def room(mode='host'):
    return Settings(server='relay.example', token='node-secret', mode=mode, local_port=51234,
                    room_name='mc-test', room_secret='room-secret-12345')


class RoomTests(unittest.TestCase):
    def test_host_uses_stcp_without_public_port(self):
        s = room()
        data = tomllib.loads(s.to_toml())
        p = data['proxies'][0]
        self.assertEqual(p['type'], 'stcp')
        self.assertEqual(p['name'], 'mc-test')
        self.assertEqual(p['secretKey'], s.room_secret)
        self.assertEqual(p['localPort'], 51234)
        self.assertNotIn('remotePort', p)
        self.assertEqual(Settings.from_toml(s.to_toml()), s)

    def test_friend_uses_loopback_visitor_without_local_mc(self):
        s = room('join')
        s.local_port = 0
        s.validate()
        data = tomllib.loads(s.to_toml())
        p = data['visitors'][0]
        self.assertEqual(p['type'], 'stcp')
        self.assertEqual(p['serverName'], s.room_name)
        self.assertEqual(p['bindAddr'], '127.0.0.1')
        self.assertEqual(p['bindPort'], 25566)
        self.assertEqual(s.join_address(), '127.0.0.1:25566')
        imported = Settings.from_toml(s.to_toml())
        self.assertEqual(imported.mode, 'join')
        self.assertEqual(imported.room_secret, s.room_secret)
        self.assertEqual(imported.visitor_port, s.visitor_port)

    def test_roles_and_room_credentials_validated(self):
        for key, value in [('mode', 'bad'), ('room_secret', ''), ('room_name', '../bad')]:
            s = room()
            setattr(s, key, value)
            with self.assertRaises(ValueError): s.validate()
        s = room('join'); s.visitor_port = 0
        with self.assertRaises(ValueError): s.validate()

    def test_invitation_roundtrip_excludes_node_secret_and_local_settings(self):
        s = room()
        s.ca_file = 'local-sensitive-ca-path'
        code = encode_invitation(s)
        data = decode_invitation(code)
        self.assertEqual(data['room_secret'], s.room_secret)
        self.assertEqual(data['server'], s.server)
        self.assertNotIn('token', data)
        self.assertNotIn('ca_file', data)
        self.assertNotIn('executable', data)
        self.assertNotIn(s.token, json.dumps(data))

    def test_invitation_rejects_unsupported_or_malformed(self):
        for code in ['', 'bad', 'N4ROOM1:' + 'a' * 20000]:
            with self.assertRaises(ValueError): decode_invitation(code)

    def test_room_secret_persistence_is_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'settings.json'
            s = room()
            save_settings(path, s, False)
            self.assertEqual(load_settings(path).room_secret, '')
            save_settings(path, s, True)
            self.assertEqual(load_settings(path), s)

    def test_import_rejects_public_listener_and_mixed_roles(self):
        s = room('join')
        for cfg in [s.to_toml().replace('127.0.0.1', '0.0.0.0'),
                    s.to_toml() + '\n[[proxies]]\nname="x"\ntype="stcp"']:
            with self.assertRaises(ValueError): Settings.from_toml(cfg)

    def test_unused_public_fields_do_not_block_private_roles(self):
        s = room('join')
        s.local_host = 'http://invalid-local'
        s.public_host = 'public:25565'
        s.name = 'bad public name'
        s.validate()
        s = room('host'); s.public_host = 'public:25565'; s.name = 'bad public name'
        s.validate()

    def test_visitor_name_preserved_and_type_checked(self):
        text = room('join').to_toml()
        original = tomllib.loads(text)['visitors'][0]['name']
        custom = text.replace(f'name = "{original}"', 'name = "custom-visitor"')
        imported = Settings.from_toml(custom)
        self.assertEqual(tomllib.loads(imported.to_toml())['visitors'][0]['name'], 'custom-visitor')
        bad = text.replace(f'name = "{original}"', 'name = 123')
        with self.assertRaises(ValueError): Settings.from_toml(bad)


if __name__ == '__main__': unittest.main()
