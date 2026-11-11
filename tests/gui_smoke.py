import sys
import tempfile
from pathlib import Path
import tkinter as tk
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App

with tempfile.TemporaryDirectory() as d:
    root = tk.Tk()
    app = App(root, Path(d) / 'settings.json')
    root.update()
    assert app.log.winfo_height() >= 100, 'default window must leave readable log space'
    assert app.vars['server_port'].get() == '7000'
    assert app.vars['local_port'].get() == '0'
    assert '未验证' in app.tls_hint.get()
    app.save()
    assert app.data_path.exists()
    app.system_ca.set(True)
    app.update_tls_hint()
    assert '验证节点证书' in app.tls_hint.get()
    app.close()
    assert not root.tk.call('after', 'info'), 'close must cancel its pending UI timer'
    try:
        root.update()
    except tk.TclError:
        pass
    print('PASS: native GUI constructed, offline settings saved, TLS hint updated, clean close')

with tempfile.TemporaryDirectory() as d:
    root = tk.Tk()
    root.withdraw()
    app = App(root, Path(d) / 'settings.json')
    app.vars['server'].set('127.0.0.1')
    app.vars['token'].set('test-secret')
    app.vars['local_port'].set('12345')
    app.exe.set(sys.executable)
    entered, release = threading.Event(), threading.Event()

    def stalled_check(*args):
        entered.set()
        release.wait(5)

    with patch('app.check_port', stalled_check), patch('app.Tunnel.start') as start:
        app.start()
        assert entered.wait(2)
        app.close()
        try:
            alive = bool(root.winfo_exists())
        except tk.TclError:
            alive = False
        release.set()
        assert not alive, 'closing during stalled DNS must not wait for startup check'
        import time
        time.sleep(.1)
        assert not start.called, 'cancelled startup must not launch frpc'
    print('PASS: close cancels stalled startup without launching a child')
