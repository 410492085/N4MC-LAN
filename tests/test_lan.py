import json
import subprocess
import unittest
from unittest.mock import patch
from lan_backend import parse_status, read_status, format_address, probe_tcp


SAMPLE = {'BackendState': 'Running', 'Self': {'TailscaleIPs': ['100.90.1.2', 'fd7a:115c:a1e0::1'], 'HostName': 'owner'},
          'Peer': {'a': {'HostName': 'friend', 'TailscaleIPs': ['100.90.1.3'], 'Online': True},
                   'b': {'HostName': 'offline', 'TailscaleIPs': ['100.90.1.4'], 'Online': False}}}


class LanTests(unittest.TestCase):
    def test_connected_status_and_peer_ips(self):
        data = parse_status(json.dumps(SAMPLE))
        self.assertTrue(data['ready'])
        self.assertEqual(data['ip'], '100.90.1.2')
        self.assertEqual(len(data['peers']), 2)
        self.assertTrue(data['peers'][0]['online'])

    def test_needslogin_never_retains_ips(self):
        data = dict(SAMPLE, BackendState='NeedsLogin')
        result = parse_status(json.dumps(data))
        self.assertFalse(result['ready'])
        self.assertEqual(result['ip'], '')
        self.assertEqual(result['peers'], [])

    def test_malformed_status_is_rejected(self):
        for text in ['bad', '[]', '{"BackendState":"Running","Self":[]}']:
            with self.assertRaises(ValueError): parse_status(text)

    def test_cli_readonly_bounded_and_no_shell(self):
        with patch('lan_backend.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, json.dumps(SAMPLE), '')
            read_status('C:/Tailscale/tailscale.exe')
            args, kw = run.call_args
            self.assertEqual(args[0], ['C:/Tailscale/tailscale.exe', 'status', '--json'])
            self.assertLessEqual(kw['timeout'], 8)
            self.assertFalse(kw.get('shell', False))

    def test_cli_error_not_rendered_as_raw_private_json(self):
        with patch('lan_backend.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess([], 1, '', 'private credentials')
            with self.assertRaisesRegex(ValueError, '服务') as exc: read_status('tailscale.exe')
            self.assertNotIn('private credentials', str(exc.exception))

    def test_address_ipv6_and_invalid_ports(self):
        self.assertEqual(format_address('100.90.1.2', '51234'), '100.90.1.2:51234')
        self.assertEqual(format_address('fd7a:115c:a1e0::1', 51234), '[fd7a:115c:a1e0::1]:51234')
        for ip, port in [('http://x', 1), ('100.90.1.2', 0), ('100.90.1.2', True)]:
            with self.assertRaises(ValueError): format_address(ip, port)

    def test_wrong_json_primitive_types_cannot_report_ready(self):
        for value in [True, 1]:
            data = {'BackendState': 'Running', 'Self': {'TailscaleIPs': [value]}}
            self.assertFalse(parse_status(json.dumps(data))['ready'])
        data = dict(SAMPLE, Self=dict(SAMPLE['Self'], Online='false'))
        with self.assertRaises(ValueError): parse_status(json.dumps(data))


if __name__ == '__main__': unittest.main()
