import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from lan_controller import LanController

APP = QApplication.instance() or QApplication([])
CONNECTED = {'ready': True, 'state': 'Running', 'ip': '100.90.1.2',
             'peers': [{'name': 'host', 'ip': '100.90.1.3', 'ips': ['100.90.1.3'], 'online': True}]}


class LanControllerTests(unittest.TestCase):
    def setUp(self): self.lan = LanController()
    def tearDown(self): self.lan.close()

    def test_host_and_friend_address(self):
        self.lan.apply_status(CONNECTED)
        self.lan.setPort('51234')
        self.assertEqual(self.lan.address, '100.90.1.2:51234')
        self.lan.setRole('friend'); self.lan.setTarget('100.90.1.3')
        self.assertEqual(self.lan.address, '100.90.1.3:51234')

    def test_offline_or_error_clears_stale_address(self):
        self.lan.apply_status(CONNECTED); self.lan.setPort('51234')
        self.lan.apply_status({'ready': False, 'state': 'NeedsLogin', 'ip': '', 'peers': []})
        self.assertEqual(self.lan.address, '')
        self.assertEqual(self.lan.peers, [])

    def test_friend_must_be_visible_online_peer(self):
        self.lan.apply_status(CONNECTED); self.lan.setRole('friend'); self.lan.setTarget('192.168.1.1'); self.lan.setPort('51234')
        self.assertEqual(self.lan.address, '')

    def test_copy_uses_validated_address(self):
        self.lan.apply_status(CONNECTED); self.lan.setPort('51234')
        with patch('lan_controller.QApplication.clipboard') as clipboard:
            self.lan.copyAddress()
            clipboard.return_value.setText.assert_called_once_with('100.90.1.2:51234')

    def test_selection_tracks_ip_when_peer_order_changes(self):
        self.lan.apply_status(CONNECTED)
        self.lan.setTarget('100.90.1.3')
        self.assertEqual(self.lan.selectedIndex, 0)
        extra = dict(CONNECTED, peers=[{'name': 'other', 'ip': '100.90.1.9', 'ips': ['100.90.1.9'], 'online': True}, *CONNECTED['peers']])
        self.lan.apply_status(extra)
        self.assertEqual(self.lan.selectedIndex, 1)

if __name__ == '__main__': unittest.main()
