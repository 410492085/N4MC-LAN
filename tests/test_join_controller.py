import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from core import Settings, check_listener_port
from rooms import encode_invitation
from qt_controller import Controller
from tunnel import redact

APP = QApplication.instance() or QApplication([])


class JoinControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = Controller(Path(self.tmp.name) / 'settings.json')

    def tearDown(self):
        self.c.requestClose(); self.c.timer.stop(); self.tmp.cleanup()

    def host(self):
        return Settings(server='relay.example', mode='host', token='node-secret', local_port=51234,
                        room_name='room-one', room_secret='room-secret-12345')

    def test_import_invitation_clears_node_credentials(self):
        self.c._form.update(token='previous-node-secret', ca_file='old-ca.crt')
        self.c.apply_invitation(encode_invitation(self.host()))
        self.assertEqual(self.c.snapshot().mode, 'join')
        self.assertEqual(self.c.form['token'], '')
        self.assertEqual(self.c.form['ca_file'], '')
        self.assertEqual(self.c.form['room_name'], 'room-one')
        self.assertEqual(self.c.address, '127.0.0.1:25566')

    def test_friend_does_not_probe_mc_port(self):
        self.c.apply(self.host())
        self.c.setMode('join')
        self.c.setField('executable', sys.executable)
        self.c.setField('local_port', '0')
        done = threading.Event()
        with patch('qt_controller.check_port') as mc, patch('qt_controller.check_listener_port') as listener, patch('qt_controller.Tunnel.start', side_effect=lambda s: done.set()):
            self.c.start()
            self.assertTrue(done.wait(1))
            mc.assert_not_called()
            listener.assert_called_once_with(25566)

    def test_copy_active_host_invitation_uses_captured_room(self):
        from rooms import decode_invitation
        original = self.host()
        self.c.apply(original)
        self.c._session_settings = original
        self.c._busy = True
        self.c.setField('room_secret', 'edited-secret-12345')
        with patch('qt_controller.QApplication.clipboard') as clipboard:
            self.c.copyInvitation()
            code = clipboard.return_value.setText.call_args.args[0]
        self.assertEqual(decode_invitation(code)['room_secret'], original.room_secret)
        self.c._busy = False

    def test_generate_room_is_unique_and_does_not_leak_logs(self):
        self.c.setMode('host')
        first = self.c.form['room_secret']
        self.c.newRoom()
        self.assertNotEqual(first, self.c.form['room_secret'])
        self.assertNotIn(self.c.form['room_secret'], self.c.logs)

    def test_custom_ca_requirement_survives_invitation(self):
        s = self.host(); s.ca_file = 'host-ca.crt'
        self.c.apply_invitation(encode_invitation(s))
        self.c.setField('token', 'authorized-node-token')
        with self.assertRaisesRegex(ValueError, 'CA'):
            self.c.snapshot().validate()

    def test_node_and_room_secrets_both_redacted(self):
        self.assertEqual(redact('node-secret room-secret', ('node-secret', 'room-secret')), '*** ***')

    def test_local_listener_collision_detected(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); s.listen()
            with self.assertRaises(OSError): check_listener_port(s.getsockname()[1])


if __name__ == '__main__': unittest.main()
