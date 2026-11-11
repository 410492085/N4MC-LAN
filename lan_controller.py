"""Independent managed virtual-LAN UI; frpc is never used on this page."""
from pathlib import Path
import queue
import subprocess
import threading
from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication
from lan_backend import discover_cli, read_status, format_address, probe_tcp


class LanController(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._state = {'ready': False, 'state': 'Unknown', 'ip': '', 'peers': []}
        self._role = 'host'
        self._target = ''
        self._port = '0'
        self._busy = False
        self._message = '先安装并登录 Tailscale，然后刷新状态。'
        self._revision = 0
        self._closed = False
        self.events = queue.Queue()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)

    @Property(bool, notify=changed)
    def ready(self): return self._state['ready']
    @Property(bool, notify=changed)
    def busy(self): return self._busy
    @Property(str, notify=changed)
    def role(self): return self._role
    @Property(str, notify=changed)
    def ip(self): return self._state['ip']
    @Property(str, notify=changed)
    def message(self): return self._message
    @Property('QVariantList', notify=changed)
    def peers(self): return self._state['peers']
    @Property(int, notify=changed)
    def selectedIndex(self):
        return next((i for i, peer in enumerate(self.peers) if self._target in peer['ips']), -1)
    @Property(str, notify=changed)
    def address(self):
        if not self.ready: return ''
        target = self.ip if self._role == 'host' else self._target
        if self._role == 'friend' and not any(p['online'] and target in p['ips'] for p in self.peers): return ''
        try: return format_address(target, self._port)
        except ValueError: return ''

    def apply_status(self, data):
        self._state = data
        self._revision += 1
        self._message = ('本机已接入 Tailscale。设备在线不代表 MC 端口可达，请继续检查游戏连接。' if self.ready else
                         '需要登录 Tailscale。' if data['state'] == 'NeedsLogin' else
                         'Tailscale 尚未连接，请在官方客户端完成登录并启用连接。')
        self.changed.emit()

    @Slot(str)
    def setRole(self, role):
        if role in ['host', 'friend']:
            self._role = role; self._revision += 1; self.changed.emit()
    @Slot(str)
    def setPort(self, text):
        self._port = text.strip(); self._revision += 1; self.changed.emit()
    @Slot(str)
    def setTarget(self, ip):
        self._target = ip.strip(); self._revision += 1; self.changed.emit()

    @Slot()
    def refresh(self):
        if self._busy or self._closed: return
        cli = discover_cli()
        if not cli:
            self.apply_status({'ready': False, 'state': 'NotInstalled', 'ip': '', 'peers': []})
            self._message = '尚未检测到 Tailscale。点击「官方下载」，安装并登录后刷新状态。'
            self.changed.emit(); return
        self._busy = True; self._message = '正在读取 Tailscale 状态…'; self.changed.emit()
        def work():
            try: self.events.put(('status', read_status(cli)))
            except Exception: self.events.put(('error', '无法读取 Tailscale 服务，请打开官方客户端并登录后重试。'))
        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def checkConnection(self):
        if self._busy or self._closed: return
        if not self.address:
            self._message = '请先连接 Tailscale，填写游戏显示的端口；朋友还需选择在线房主设备。'
            self.changed.emit(); return
        target = '127.0.0.1' if self._role == 'host' else self._target
        role, port, revision = self._role, int(self._port), self._revision
        self._busy = True; self._message = '正在检查游戏 TCP 端口…'; self.changed.emit()
        def work():
            try:
                probe_tcp(target, port)
                text = ('房主本地游戏端口可连接。请把组网地址发给朋友；远端仍需通过防火墙与网络权限。' if role == 'host' else
                        '房主的 TCP 端口可连接。现在可以在 MC 中直接连接；这尚未验证游戏版本或模组兼容性。')
            except OSError:
                text = '端口不可连接：核对局域网端口、房主在线状态、Tailscale 共享权限与 Java 防火墙权限。'
            self.events.put(('probe', (revision, text)))
        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def copyAddress(self):
        if self.address:
            QApplication.clipboard().setText(self.address)
            self._message = '已复制组网地址。朋友在 Minecraft「多人游戏 → 直接连接」粘贴；不保证已连通。'
        else: self._message = '还没有有效组网地址，请先刷新状态、填写端口并选择房主。'
        self.changed.emit()

    @Slot()
    def download(self): QDesktopServices.openUrl(QUrl('https://tailscale.com/download/windows'))
    @Slot()
    def openAdmin(self): QDesktopServices.openUrl(QUrl('https://login.tailscale.com/admin/machines'))
    @Slot()
    def openClient(self):
        cli = discover_cli()
        gui = Path(cli).with_name('tailscale-ipn.exe') if cli else None
        if gui and gui.is_file():
            try: subprocess.Popen([str(gui)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError: self._message = '无法打开客户端，请从 Windows 开始菜单启动 Tailscale。'
        else: self._message = '请先从官网安装 Tailscale，然后在 Windows 托盘菜单选择 Log in。'
        self.changed.emit()

    @Slot()
    def poll(self):
        if self._closed: return
        while True:
            try: kind, data = self.events.get_nowait()
            except queue.Empty: break
            self._busy = False
            if kind == 'status': self.apply_status(data)
            elif kind == 'error':
                self._state = {'ready': False, 'state': 'Error', 'ip': '', 'peers': []}
                self._revision += 1; self._message = data
            elif kind == 'probe':
                self._message = data[1] if data[0] == self._revision else '检查期间配置已变化，请重新检查。'
            self.changed.emit()

    def close(self):
        self._closed = True
        self.timer.stop()
