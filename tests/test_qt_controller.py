import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from core import Settings
from qt_controller import Controller

APP = QApplication.instance() or QApplication([])


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ctrl = Controller(Path(self.tmp.name) / 'settings.json')

    def tearDown(self):
        self.ctrl.requestClose()
        self.ctrl.timer.stop()
        self.tmp.cleanup()

    def test_offline_save_and_reload_without_token(self):
        self.ctrl.setField('token', 'test-secret')
        self.ctrl.save()
        fresh = Controller(self.ctrl.path)
        self.assertEqual(fresh.form['token'], '')
        self.assertEqual(fresh.form['local_port'], '0')
        fresh.timer.stop()

    def test_import_preserves_tls_and_resolves_ca(self):
        ca = Path(self.tmp.name) / 'ca.crt'
        ca.write_text('test')
        s = Settings(server='example.com', token='secret', local_port=50001, ca_file=str(ca), system_ca=True)
        config = Path(self.tmp.name) / 'frpc.toml'
        config.write_text(s.to_toml().replace(str(ca).replace('\\', '\\\\'), 'ca.crt'), encoding='utf-8')
        self.ctrl.import_path(config)
        result = self.ctrl.snapshot()
        self.assertEqual(Path(result.ca_file).resolve(), Path(s.ca_file).resolve())
        result.ca_file = s.ca_file
        self.assertEqual(result, s)
        self.assertEqual(self.ctrl.address, 'example.com:25565')

    def test_active_address_does_not_follow_edited_form(self):
        self.ctrl._address = 'active.example:25565'
        class Running:
            running = True
            def stop(self): pass
        self.ctrl.tunnel = Running()
        self.ctrl.setField('server', 'other.example')
        with patch('qt_controller.QApplication.clipboard') as clipboard:
            self.ctrl.copyAddress()
            clipboard.return_value.setText.assert_called_once_with('active.example:25565')
        self.ctrl.tunnel = None

    def test_cancel_stalled_startup_never_spawns(self):
        for k, v in dict(server='127.0.0.1', token='secret', local_port='51234').items():
            self.ctrl.setField(k, v)
        self.ctrl.setField('executable', __import__('sys').executable)
        entered, release, ended = threading.Event(), threading.Event(), threading.Event()
        def stall(*args):
            entered.set()
            release.wait(3)
            ended.set()
        with patch('qt_controller.check_port', stall), patch('qt_controller.Tunnel.start') as start:
            self.ctrl.start()
            self.assertTrue(entered.wait(1))
            self.assertTrue(self.ctrl.requestClose())
            release.set()
            self.assertTrue(ended.wait(1))
            time.sleep(.05)
            self.assertFalse(start.called)

    def test_worker_events_only_applied_on_poll(self):
        self.ctrl.events.put(('status', 'test-state'))
        self.assertNotEqual(self.ctrl.status, 'test-state')
        self.ctrl.poll()
        self.assertEqual(self.ctrl.status, 'test-state')

    def test_custom_executable_in_bin_is_preserved_even_when_missing(self):
        from core import save_settings
        custom = str(Path(self.tmp.name) / 'provider/bin/frpc.exe')
        save_settings(self.ctrl.path, Settings(), False, custom)
        self.ctrl.load()
        self.assertEqual(self.ctrl.form['executable'], custom)

    def test_starting_address_is_not_replaced_by_form_edits(self):
        self.ctrl._address = 'starting.example:25565'
        self.ctrl._busy = True
        for k, v in dict(server='edited.example', token='secret', local_port='51234', remote_port='25566').items():
            self.ctrl.setField(k, v)
        self.ctrl.copyAddress()
        self.assertEqual(self.ctrl.address, 'starting.example:25565')
        self.ctrl._busy = False


if __name__ == '__main__': unittest.main()
