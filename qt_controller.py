"""Qt main-thread bridge to the existing validated frp core."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import queue
import secrets
import sys
import threading
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from core import Settings, check_port, check_listener_port, load_settings, save_settings
from rooms import encode_invitation, decode_invitation
from tunnel import Tunnel

BASE = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
RESOURCE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


class Controller(QObject):
    formChanged = Signal()
    stateChanged = Signal()
    logsChanged = Signal()
    notice = Signal(str, str)
    quitReady = Signal()

    def __init__(self, path=None):
        super().__init__()
        self.path = Path(path) if path else Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MC-Link/settings.json'
        self._form = {k: str(v) for k, v in asdict(Settings()).items() if k not in ['system_ca', 'scopes', 'require_ca']}
        self._form['require_ca'] = False
        self._form.update(system_ca=False, heartbeats=True, workconns=True, remember=False, executable=str(BASE / 'bin/frpc.exe'))
        self._status = '准备就绪'
        self._address = ''
        self._logs = []
        self._busy = False
        self._closing = False
        self._cancel = threading.Event()
        self._launch_lock = threading.Lock()
        self.events = queue.Queue()
        self.tunnel = None
        self._session_settings = None
        self.load()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)

    @Property('QVariantMap', notify=formChanged)
    def form(self): return dict(self._form)

    @Property(str, notify=stateChanged)
    def status(self): return self._status

    @Property(str, notify=stateChanged)
    def address(self): return self._address

    @Property(bool, notify=stateChanged)
    def busy(self): return self._busy or self._closing

    @Property(bool, notify=stateChanged)
    def running(self): return bool(self.tunnel and self.tunnel.running)

    @Property(str, notify=logsChanged)
    def logs(self): return '\n'.join(self._logs)

    @Slot(str, 'QVariant')
    def setField(self, key, value):
        if key in self._form:
            self._form[key] = value

    def snapshot(self):
        fields = {k: self._form[k] if k == 'token' else str(self._form[k]).strip()
                  for k in asdict(Settings()) if k not in ['system_ca', 'scopes', 'require_ca']}
        fields['room_secret'] = str(self._form['room_secret'])
        active_ports = ['server_port'] + (['visitor_port'] if fields['mode'] == 'join' else ['local_port'])
        if fields['mode'] == 'public': active_ports += ['remote_port']
        for k in ['server_port', 'local_port', 'remote_port', 'visitor_port']:
            try:
                fields[k] = int(fields[k])
            except ValueError as e:
                if k in active_ports: raise ValueError('端口应填写整数；MC 局域网端口由游戏显示。') from e
                fields[k] = 0
        fields['system_ca'] = bool(self._form['system_ca'])
        fields['require_ca'] = bool(self._form['require_ca'])
        fields['scopes'] = (['HeartBeats'] if self._form['heartbeats'] else []) + (['NewWorkConns'] if self._form['workconns'] else [])
        return Settings(**fields)

    def apply(self, settings):
        for k, v in asdict(settings).items():
            if k not in ['scopes', 'system_ca', 'require_ca']: self._form[k] = str(v)
        self._form['system_ca'] = settings.system_ca
        self._form['require_ca'] = settings.require_ca
        self._form['heartbeats'] = 'HeartBeats' in settings.scopes
        self._form['workconns'] = 'NewWorkConns' in settings.scopes
        self.formChanged.emit()

    def load(self):
        if self.path.exists():
            try:
                self.apply(load_settings(self.path))
                data = json.loads(self.path.read_text('utf-8'))
                self._form['remember'] = bool(data.get('_remember', False))
                # Old built-in executable paths are migrated to this version's bundle.
                old = data.get('_executable', '')
                old_path = Path(old)
                built_in = (old_path.name.lower() == 'frpc.exe' and old_path.parent.name.lower() == 'bin'
                            and old_path.parent.parent.name.lower() in ['mc-link', 'n4tsum3', 'n4tsum3-material', 'n4tsum3-rooms', 'n4tsum3-lan'])
                if old and not built_in:
                    self._form['executable'] = old
            except Exception:
                self.append_log('保存的配置无法读取，已恢复默认设置。')

    def append_log(self, text):
        self._logs.append(text)
        self._logs = self._logs[-500:]
        self.logsChanged.emit()

    @Slot()
    def save(self):
        try:
            save_settings(self.path, self.snapshot(), bool(self._form['remember']), self._form['executable'])
            self.append_log('设置已保存。' + ('节点 Token 和房间密钥已按选择明文保存。' if self._form['remember'] else '未保存节点 Token 和房间密钥。'))
        except Exception as e: self.notice.emit('无法保存', str(e))

    @Slot(str)
    def setMode(self, mode):
        if self.busy or self.running or mode not in ['public', 'host', 'join']: return
        self._form['mode'] = mode
        self._address = f'127.0.0.1:{self._form["visitor_port"]}' if mode == 'join' else ''
        if mode == 'host' and not self._form['room_secret']:
            self.newRoom()
        self.formChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def newRoom(self):
        if self.busy or self.running: return
        self._form.update(mode='host', room_name='mc-' + secrets.token_hex(5), room_secret=secrets.token_urlsafe(24))
        self._address = ''
        self.formChanged.emit()
        self.stateChanged.emit()
        self.append_log('已生成新房间 ID 与密钥；启动房间后把邀请发给朋友。')

    @Slot()
    def copyInvitation(self):
        try:
            settings = self._session_settings if (self.running or self._busy) and self._session_settings else self.snapshot()
            code = encode_invitation(settings)
            QApplication.clipboard().setText(code)
            self.append_log('房间邀请已复制（含房间密钥，仅发给朋友；不含节点 Token）。')
        except Exception as e: self.notice.emit('无法复制邀请', str(e))

    def apply_invitation(self, code):
        if self.busy or self.running: raise ValueError('请先停止当前连接，再导入房间邀请')
        data = decode_invitation(code)
        self._form.update(mode='join', server=data['server'], server_port=str(data['server_port']),
                          room_name=data['room_name'], room_secret=data['room_secret'], visitor_name='visit-' + data['room_name'], token='', ca_file='',
                          system_ca=data['system_ca'], server_name=data['server_name'], require_ca=data['requires_ca'],
                          heartbeats='HeartBeats' in data['scopes'], workconns='NewWorkConns' in data['scopes'])
        self._address = f'127.0.0.1:{self._form["visitor_port"]}'
        self.formChanged.emit()
        self.stateChanged.emit()
        self.append_log('已载入朋友房间。请核对节点地址，单独填写节点 Token；有自定义 CA 时需选择可信证书。')

    @Slot(str, result=bool)
    def applyInvitation(self, code):
        try:
            self.apply_invitation(code)
            return True
        except Exception as e:
            self.notice.emit('邀请无法导入', str(e))
            return False

    @Slot(result=str)
    def clipboardText(self):
        return QApplication.clipboard().text()[:8193]

    def import_path(self, path):
        path = Path(path)
        settings = Settings.from_toml(path.read_text('utf-8-sig'), path.parent)
        self.apply(settings)
        self._address = settings.join_address()
        self.stateChanged.emit()
        self.append_log('配置已导入；请确认玩家连接地址。Token 不会自动保存。')

    @Slot()
    def importConfig(self):
        if self.busy or self.running: return
        path, _ = QFileDialog.getOpenFileName(None, '导入单个 TCP / STCP 配置', '', 'TOML (*.toml)')
        if path:
            try: self.import_path(path)
            except Exception as e: self.notice.emit('无法导入', str(e))

    @Slot()
    def exportConfig(self):
        try:
            config = self.snapshot().to_toml()
            if QMessageBox.question(None, '包含认证信息', 'TOML 含明文 Token，仅供自己使用。继续导出？') != QMessageBox.StandardButton.Yes:
                return
            path, _ = QFileDialog.getSaveFileName(None, '导出 frpc 配置', 'frpc-minecraft.toml', 'TOML (*.toml)')
            if path:
                Path(path).write_text(config, encoding='utf-8')
                self.append_log('配置已导出，请勿将含 Token 的配置发给朋友。')
        except Exception as e: self.notice.emit('无法导出', str(e))

    @Slot(str)
    def chooseFile(self, key):
        if key not in ['ca_file', 'executable']: return
        filt = 'Certificate (*.pem *.crt);;All files (*)' if key == 'ca_file' else 'Executable (*.exe)'
        path, _ = QFileDialog.getOpenFileName(None, '选择可信 CA 文件' if key == 'ca_file' else '选择受信任的 frpc.exe', '', filt)
        if path:
            self._form[key] = path
            self.formChanged.emit()

    @Slot()
    def checkGame(self):
        try:
            friend = self._form['mode'] == 'join'
            hostname, port = str(self._form['local_host']).strip(), int(self._form['visitor_port' if friend else 'local_port'])
            if not 1 <= port <= 65535: raise ValueError()
        except ValueError:
            self.notice.emit('端口无效', '请填写有效的本地端口（1–65535）。')
            return
        self.append_log('正在检查本地游戏端口…')
        def run():
            try:
                if friend:
                    check_listener_port(port)
                    text = '本地入口端口可用；尚未连接房主。'
                else:
                    check_port(hostname, port)
                    text = '本地端口可连接；尚未验证 Minecraft 协议或公网可达。'
            except OSError:
                text = '本地入口端口已被占用，请更换端口或停止现有连接。' if friend else '本地端口不可连接，请检查游戏是否开放局域网以及端口是否正确。'
            self.events.put(('log', text))
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def start(self):
        if self.busy or self.running: return
        try:
            settings = self.snapshot()
            settings.validate()
            exe = str(self._form['executable']).strip()
            if not Path(exe).is_file(): raise ValueError('找不到 frpc.exe，请在安全设置中选择客户端程序。')
        except Exception as e:
            self.notice.emit('请检查配置', str(e))
            return
        self._busy = True
        self._status = '正在准备本地加入入口…' if settings.mode == 'join' else '正在检查游戏端口…'
        self._address = settings.join_address()
        self._session_settings = settings
        self._cancel.clear()
        self.tunnel = Tunnel(exe)
        self.stateChanged.emit()
        def run():
            try:
                if settings.mode == 'join': check_listener_port(settings.visitor_port)
                else: check_port(settings.local_host, settings.local_port)
                with self._launch_lock:
                    if self._cancel.is_set(): return
                    self.tunnel.start(settings)
            except PermissionError:
                self.events.put(('log', '系统拒绝执行 frpc，请查看 Windows 安全中心保护历史记录（本机曾检测到 PUA:Win32/FRProxy）。'))
                self.events.put(('status', '启动被系统拒绝'))
            except OSError:
                self.events.put(('log', '启动失败，请检查本地入口端口是否占用及客户端能否运行。' if settings.mode == 'join' else '启动失败，请检查 MC 局域网端口及客户端程序是否可运行。'))
                self.events.put(('status', '启动失败'))
            except Exception:
                self.events.put(('log', '启动失败，请检查配置与客户端。'))
                self.events.put(('status', '启动失败'))
            finally: self.events.put(('idle', ''))
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def stop(self):
        if self._busy: return
        self._busy = True
        self._status = '正在停止…'
        self.stateChanged.emit()
        def run():
            try:
                if self.tunnel: self.tunnel.stop()
            finally: self.events.put(('idle', ''))
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def copyAddress(self):
        try:
            if not self.running and not self._busy:
                s = self.snapshot()
                if s.mode == 'host': raise ValueError('房主请使用“复制房间邀请”，朋友需要先在助手中加入。')
                s.validate()
                self._address = s.join_address()
                self.stateChanged.emit()
            QApplication.clipboard().setText(self._address)
            self.append_log('已复制联机地址。朋友可在「多人游戏 → 直接连接」粘贴。')
        except Exception as e: self.notice.emit('无法复制', str(e))

    @Slot()
    def poll(self):
        for source in [self.events] + ([self.tunnel.events] if self.tunnel else []):
            for _ in range(150):
                try: kind, text = source.get_nowait()
                except queue.Empty: break
                if kind == 'log': self.append_log(text)
                elif kind == 'status': self._status = text
                elif kind == 'idle': self._busy = False
        self.stateChanged.emit()
        if self._closing and not self._busy:
            if self.running: self.stop()
            else:
                self.timer.stop()
                self.quitReady.emit()

    @Slot(result=bool)
    def requestClose(self):
        self._closing = True
        self._cancel.set()
        if self._launch_lock.acquire(blocking=False):
            try:
                if not self.running:
                    self.timer.stop()
                    return True
            finally: self._launch_lock.release()
        self._status = '正在退出并清理隧道…'
        self.stateChanged.emit()
        return False
