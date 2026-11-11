import sys
import tempfile
import time
import unittest
from pathlib import Path
from core import Settings
from tunnel import Tunnel, redact


class TunnelTests(unittest.TestCase):
    def test_redaction(self):
        secret = 'secret"\\\n中文'
        import json
        self.assertNotIn('secret', redact('error ' + secret, secret))
        self.assertNotIn('secret', redact(json.dumps(secret, ensure_ascii=False), secret))

    def test_owned_process_cleanup_and_double_start(self):
        # Python acts as a harmless long-lived subprocess and ignores frpc arguments.
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / 'worker.py'
            script.write_text('import time\nprint("start proxy success", flush=True)\ntime.sleep(30)\n')
            tunnel = Tunnel(sys.executable, prefix_args=[str(script)])
            s = Settings(server='127.0.0.1', token='testsecret', local_port=12345)
            tunnel.start(s)
            cfg = tunnel.config_path
            self.assertTrue(cfg.exists())
            with self.assertRaises(RuntimeError):
                tunnel.start(s)
            tunnel.stop()
            self.assertFalse(tunnel.running)
            self.assertFalse(cfg.exists())
            tunnel.stop()


if __name__ == '__main__':
    unittest.main()
