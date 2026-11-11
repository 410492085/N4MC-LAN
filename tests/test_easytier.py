from contextlib import nullcontext
import hashlib
from pathlib import Path
import socket
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import Mock, patch

from easytier import RoomCode, HOST_IP, make_config, minecraft_status, announce_lan, ensure_runtime, run_room


class EasyTierTests(unittest.TestCase):
    def test_lan_port_advertisement_rejects_invalid_and_assistant_announcements(self):
        from easytier import lan_game_port

        self.assertEqual(lan_game_port(b'[MOTD]Local world[/MOTD][AD]51234[/AD]'), 51234)
        for packet in (b'[MOTD]Other[/MOTD][AD]65536[/AD]',
                       b'[MOTD]Other[/MOTD][AD]0[/AD]',
                       b'[MOTD]Other[/MOTD][AD]51234[/AD]extra',
                       '[MOTD]N4MC-LAN 房间[/MOTD][AD]51234[/AD]'.encode()):
            self.assertIsNone(lan_game_port(packet))

    def test_world_details_normalize_minecraft_chat_components(self):
        from easytier import world_details

        status = {'description': {'text': '§a樱花谷', 'extra': [{'text': ' · 朋友联机'}]},
                  'version': {'name': '1.21.4'}}
        self.assertEqual(world_details(status), ('樱花谷 · 朋友联机', '1.21.4'))
        self.assertEqual(world_details({'description': 42, 'version': {'name': False}}), ('', ''))
        self.assertEqual(world_details(None), ('', ''))

    def test_lan_discovery_checks_only_local_announcements_and_verifies_ports(self):
        from easytier import discover_lan_worlds

        def advert(port, ip):
            return f'[MOTD]World[/MOTD][AD]{port}[/AD]'.encode(), (ip, 5555)

        listener = Mock()
        listener.recvfrom.side_effect = [advert(51111, '192.0.2.99'),
                                         advert(51234, '192.0.2.2'),
                                         advert(51235, '192.0.2.2')]
        clock = iter([0, 0, 1, 2, 4])
        stop = threading.Event()
        with (patch('easytier.socket.socket', return_value=nullcontext(listener)),
              patch('easytier.time.monotonic', side_effect=clock),
              patch('easytier.minecraft_status', side_effect=[{'description': 'My World'}, None]) as probe):
            self.assertEqual(discover_lan_worlds({'192.0.2.2'}, stop),
                             [{'port': 51234, 'label': 'My World · 51234'}])
        self.assertEqual([call.args[0] for call in probe.call_args_list], [51234, 51235])

    def test_established_rooms_survive_status_outages_and_recover(self):
        for host in (True, False):
            with self.subTest(host=host):
                elapsed = 0.0
                updates = []

                def wait(seconds):
                    nonlocal elapsed
                    elapsed += seconds

                stop = Mock(is_set=lambda: elapsed >= 84, wait=wait)
                core = Mock(poll=lambda: None)
                room = RoomCode.create(51234)
                with (patch('easytier.time.monotonic', lambda: elapsed),
                      patch('easytier.ensure_runtime'), patch('easytier.free_port', side_effect=[7777, 25566]),
                      patch('easytier.start_core', return_value=nullcontext(core)) as start,
                      patch('easytier.connected', return_value=True), patch('easytier.announce_lan'),
                      patch('easytier.socket.create_connection', return_value=nullcontext()),
                      patch('easytier.minecraft_status',
                            side_effect=lambda *args: {} if elapsed < 5 or elapsed >= 70 else None)):
                    run_room(room, host, Path('unused'), stop, lambda *state: updates.append(state))

                start.assert_called_once()
                address = room.text if host else '127.0.0.1:25566'
                self.assertEqual(updates[1][2], address)
                self.assertEqual(updates[-1][1:], (True, address))
                self.assertGreaterEqual(len(updates), 4)

    def test_game_counts_refresh_for_both_roles_and_clear_on_outage(self):
        for host in (True, False):
            with self.subTest(host=host):
                self.check_counts(host)

    def check_counts(self, host):
        elapsed = 0.0
        counts = []
        worlds = []

        def wait(seconds):
            nonlocal elapsed
            elapsed += seconds

        replies = [{'players': {'online': 2, 'max': 8}, 'description': 'World', 'version': {'name': '1.21.4'}},
                   {'players': {'online': 3, 'max': 8}, 'description': 'World', 'version': {'name': '1.21.4'}},
                   None, {'players': {'online': True, 'max': -1}}, {'players': {'online': 0}}]
        with (patch('easytier.time.monotonic', lambda: elapsed),
              patch('easytier.ensure_runtime'), patch('easytier.free_port', side_effect=[7777, 25566]),
              patch('easytier.start_core', return_value=nullcontext(Mock(poll=lambda: None))),
              patch('easytier.connected', return_value=True),
              patch('easytier.announce_lan'),
              patch('easytier._game_port_refused', return_value=False),
              patch('easytier.minecraft_status', side_effect=replies) as status):
            stop = Mock(is_set=lambda: status.call_count >= len(replies), wait=wait)
            run_room(RoomCode.create(51234), host, Path('unused'), stop, Mock(),
                     on_game=counts.append, on_world=worlds.append)
        self.assertEqual(counts, [(True, 2, 8), (True, 3, 8), (False, -1, -1),
                                  (True, -1, -1), (True, 0, -1)])
        self.assertEqual(worlds, [('World', '1.21.4'), ('', '')])

    def test_room_network_excludes_public_nodes_and_does_not_invent_relay_loss(self):
        from easytier import room_network

        rows = [
            dict(hostname='n4tsum3-guest', ipv4='10.203.69.2', cost='Local'),
            dict(hostname='n4tsum3-host', ipv4=HOST_IP, cost='relay(2)', lat_ms='185.00', loss_rate='0.0%'),
            dict(hostname='n4tsum3-guest', ipv4='10.203.69.3', cost='p2p', lat_ms='30.25',
                 loss_rate='1.2%', tunnel_proto='udp'),
            dict(hostname='PublicServer', ipv4='', cost='p2p', lat_ms='3', loss_rate='0.0%'),
        ]
        guest = room_network(rows, host=False)
        self.assertEqual(guest, dict(devices=3, path='中继', latency='185 ms', loss='—'))
        self.assertEqual(room_network(rows[:1], host=False),
                         dict(devices=1, path='未发现房主', latency='—', loss='—'))
        self.assertIsNone(room_network(None, host=False))
        host = [dict(rows[1], cost='Local'), rows[2], dict(rows[0], cost='relay(2)', lat_ms='102')]
        self.assertEqual(room_network(host, host=True),
                         dict(devices=3, path='直连 + 中继', latency='102 ms', loss='1.2%'))

    def test_portable_runtime_starts_with_an_empty_cache_and_no_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundled = root / 'bin' / 'easytier'
            bundled.mkdir(parents=True)
            cache = root / 'fresh-cache'
            files = {}
            for name in ('easytier-core.exe', 'easytier-cli.exe', 'Packet.dll'):
                payload = name.encode()
                (bundled / name).write_bytes(payload)
                files[name] = hashlib.sha256(payload).hexdigest()
            with (patch('easytier.BUNDLED_RUNTIME', bundled),
                  patch('easytier.BUNDLED_FILES', files),
                  patch('easytier.urlopen', side_effect=AssertionError('unexpected download'))):
                self.assertEqual(ensure_runtime(cache, threading.Event(), self.fail), bundled)
            self.assertFalse(cache.exists())

    def test_invite_round_trip_and_typo(self):
        room = RoomCode.create(51234)
        self.assertEqual(RoomCode.parse('  ' + room.text.lower() + '\n'), room)
        typo = room.text[:-1] + ('B' if room.text[-1] == 'A' else 'A')
        with self.assertRaises(ValueError):
            RoomCode.parse(typo)
        self.assertNotEqual(room.secret, RoomCode.create(51234).secret)

    def test_room_exposes_only_selected_port_and_guest_uses_loopback(self):
        room = RoomCode.create(51234)
        host = tomllib.loads(make_config(room))
        guest = tomllib.loads(make_config(room, local_port=25566))
        self.assertEqual(host['network_identity'], guest['network_identity'])
        self.assertNotIn(room.text, host['network_identity']['network_name'])
        self.assertEqual(host['ipv4'], HOST_IP)
        self.assertEqual(host['tcp_whitelist'], ['51234'])
        self.assertEqual(guest['tcp_whitelist'], ['0'])
        self.assertEqual(guest['udp_whitelist'], ['0'])
        self.assertTrue(guest['flags']['no_tun'])
        self.assertEqual(guest['port_forward'], [dict(proto='tcp', bind_addr='127.0.0.1:25566', dst_addr=f'{HOST_IP}:51234')])

    def test_status_probe_distinguishes_minecraft_from_an_open_tcp_port(self):
        payload = b'{"players":{"online":2}}'
        packet = bytes([len(payload) + 2, 0, len(payload)]) + payload
        for reply, expected in [(packet, {'players': {'online': 2}}), (b'HTTP/1.1', None)]:
            with self.subTest(reply=reply), socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                listener.listen()
                listener.settimeout(2)
                def respond():
                    with listener.accept()[0] as client:
                        client.settimeout(2)
                        request = client.recv(256)
                        if request:
                            client.sendall(reply)
                worker = threading.Thread(target=respond)
                worker.start()
                try:
                    self.assertEqual(minecraft_status(listener.getsockname()[1]), expected)
                finally:
                    worker.join(2)

    def test_lan_datagram_points_to_loopback_entry(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(('127.0.0.1', 0))
            receiver.settimeout(1)
            announce_lan(25566, receiver.getsockname()[1])
            packet, sender = receiver.recvfrom(1024)
        self.assertEqual(sender[0], '127.0.0.1')
        self.assertEqual(packet.decode(), '[MOTD]N4MC-LAN 房间[/MOTD][AD]25566[/AD]')
