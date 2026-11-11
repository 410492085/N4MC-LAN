import json
import tempfile
import unittest
from pathlib import Path

from core import Settings, load_settings, save_settings


class SettingsTests(unittest.TestCase):
    def sample(self, **kw):
        return Settings(**dict(server='example.com', token='secret"\\\n中文', remote_port=25565,
                               local_port=51234, **kw))

    def test_round_trip_and_secret_escaping(self):
        s = self.sample()
        self.assertEqual(Settings.from_toml(s.to_toml()), s)

    def test_tls_round_trip(self):
        with tempfile.NamedTemporaryFile() as ca:
            s = self.sample(ca_file=ca.name, system_ca=True, server_name='tls.example.com')
            self.assertEqual(Settings.from_toml(s.to_toml()), s)

    def test_bad_ports_and_host(self):
        for field, val in [('local_port', 0), ('server_port', 65536),
                           ('remote_port', True), ('server', 'http://example.com'),
                           ('public_host', 'host:25565')]:
            s = self.sample()
            setattr(s, field, val)
            with self.assertRaises(ValueError, msg=field):
                s.validate()

    def test_ipv6_join_address(self):
        s = self.sample(public_host='2001:db8::1')
        self.assertEqual(s.join_address(), '[2001:db8::1]:25565')

    def test_import_rejects_unsupported_security_or_extra_proxy(self):
        cfg = self.sample().to_toml()
        for text in [cfg + '\n[[proxies]]\nname="other"\ntype="tcp"\nlocalPort=1\nremotePort=2',
                     'auth.method="oidc"\n' + cfg,
                     'transport.protocol="quic"\n' + cfg,
                     cfg.replace('type = "tcp"', 'type = "udp"'),
                     cfg + '\nplugin.type="socks5"']:
            with self.assertRaises(ValueError):
                Settings.from_toml(text)

    def test_legacy_tls_disabled_is_rejected(self):
        with self.assertRaises(ValueError):
            Settings.from_toml(self.sample().to_toml().replace('enable = true', 'enable = false'))

    def test_secret_persistence_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'settings.json'
            s = self.sample()
            save_settings(path, s, False)
            self.assertNotIn(s.token, path.read_text('utf-8'))
            self.assertEqual(load_settings(path).token, '')
            save_settings(path, s, True)
            self.assertEqual(load_settings(path), s)

    def test_missing_ca_rejected(self):
        with self.assertRaises(ValueError):
            self.sample(ca_file='Z:/missing-file.crt').validate()

    def test_import_rejects_server_allocated_port(self):
        for cfg in [self.sample().to_toml().replace('remotePort = 25565\n', ''),
                    self.sample().to_toml().replace('remotePort = 25565', 'remotePort = 0')]:
            with self.assertRaises(ValueError):
                Settings.from_toml(cfg)

    def test_toml_escapes_del_in_secret(self):
        settings = self.sample()
        settings.token = 'secret' + chr(127)
        self.assertEqual(Settings.from_toml(settings.to_toml()), settings)


if __name__ == '__main__':
    unittest.main()
