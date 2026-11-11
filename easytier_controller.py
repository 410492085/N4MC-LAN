"""Qt bridge for the managed EasyTier room."""

from collections import deque
from datetime import datetime
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Event, Thread

from PySide6.QtCore import QObject, Property, QStandardPaths, QTimer, Signal, Slot
from PySide6.QtNetwork import QAbstractSocket, QNetworkInterface
from PySide6.QtWidgets import QApplication

from easytier import Cancelled, RoomCode, RoomError, discover_lan_worlds, run_room


class EasyTierController(QObject):
    changed = Signal()
    scanChanged = Signal()
    scanFinished = Signal(str)

    def __init__(self):
        super().__init__()
        self._host = True
        self._busy = False
        self._ready = False
        self._message = '在 Minecraft 单人世界开放局域网，然后检测端口或手动填写。'
        self._share = ''
        self._game = (None, -1, -1)
        self._network = {}
        self._world = ('', '')
        self._history = deque(maxlen=30)
        self._seen_game = False
        self._seen_ready = False
        self._scan_busy = False
        self._scan_hint = ''
        self._worlds = []
        self._scan_stop = Event()
        self._last_issue = ''
        self._relay_only = False
        self._stop = Event()
        self._worker = None
        self._events = SimpleQueue()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(100)

    @Property(bool, notify=changed)
    def host(self):
        return self._host

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(bool, notify=changed)
    def ready(self):
        return self._ready

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property(str, notify=changed)
    def share(self):
        return self._share

    @Property(int, notify=changed)
    def onlinePlayers(self):
        return self._game[1]

    @Property(int, notify=changed)
    def playerLimit(self):
        return self._game[2]

    @Property(str, notify=changed)
    def gameCheck(self):
        return {None: '未检测', True: '有响应', False: '无响应'}[self._game[0]]

    @Property('QVariantMap', notify=changed)
    def network(self):
        return dict(self._network)

    @Property(str, notify=changed)
    def lastIssue(self):
        return self._last_issue

    @Property(str, notify=changed)
    def worldName(self):
        return self._world[0]

    @Property(str, notify=changed)
    def worldVersion(self):
        return self._world[1]

    @Property('QStringList', notify=changed)
    def history(self):
        return list(self._history)

    @Property(bool, notify=scanChanged)
    def scanBusy(self):
        return self._scan_busy

    @Property(str, notify=scanChanged)
    def scanHint(self):
        return self._scan_hint

    @Property('QVariantList', notify=scanChanged)
    def worlds(self):
        return self._worlds

    @Slot()
    def scanLan(self):
        if self._scan_busy or self._busy or not self._host:
            return
        self._scan_busy = True
        self._worlds = []
        self._scan_hint = '正在查找本机开放的 Minecraft 世界…'
        self.scanChanged.emit()
        local_ips = {address.toString() for address in QNetworkInterface.allAddresses()
                     if address.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol}
        local_ips.add('127.0.0.1')

        def work():
            try:
                worlds = discover_lan_worlds(local_ips, self._scan_stop)
            except OSError:
                worlds = None
            self._events.put(('scan', worlds))

        Thread(target=work, name='minecraft-lan-scan', daemon=True).start()

    @Property(str, notify=changed)
    def diagnosticHint(self):
        path = self._network.get('path', '')
        if self._game[0] is False:
            if self._host:
                return '确认世界仍开启，游戏里的局域网端口是否与助手一致。重新开放后，按新端口创建房间。'
            if path == '未发现房主':
                return '请房主确认助手仍在运行，并核对短码。双方近期切换过网络时，可重新建房再试。'
            return '请房主检查局域网世界和端口。保持助手运行，游戏探测恢复后再进多人游戏。'
        if not self._busy:
            return '创建或加入后自动检测。若游戏报错，可把诊断和 Minecraft 的掉线提示一起发给对方。'
        if self._game[0] is None:
            return '等待游戏探测。确认双方助手已开启，房主已在 Minecraft 开放局域网。'
        if '中继' in path:
            return ('当前包含中继链路。反复掉线时，可取消「仅中继」后重建，对比是否能直连。' if self._relay_only else
                    '当前包含中继链路。反复掉线时，可对照两边的延迟与连接方式，排查跨网链路波动。')
        return '游戏有响应但仍掉线时，先在游戏里重新进入，再对照双方的游戏版本、模组和掉线提示。'

    def _record_issue(self, detail):
        self._last_issue = self._record(detail)

    def _record(self, detail):
        entry = f'{datetime.now():%H:%M:%S} · {detail}'
        self._history.append(entry)
        return entry

    @Slot(bool)
    def setHost(self, host):
        if self._busy or self._host == host:
            return
        self._host = host
        self._last_issue = ''
        self._message = ('在 Minecraft 单人世界开放局域网，然后检测端口或手动填写。' if host else
                         '粘贴房主发来的短码。连接成功后，在 Minecraft 的多人游戏列表里选择房间。')
        self.changed.emit()

    @Slot(str, bool)
    def start(self, text, relay_only):
        if self._busy:
            return
        host = self._host
        try:
            if host:
                digits = text.strip()
                if not digits.isascii() or not digits.isdecimal() or len(digits) > 5:
                    raise ValueError('请填写 Minecraft 显示的局域网端口（1–65535）。')
                room = RoomCode.create(int(digits))
            else:
                room = RoomCode.parse(text)
        except ValueError as exc:
            self._message = str(exc)
            self.changed.emit()
            return

        cache = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'EasyTier'
        self._stop = Event()
        stop = self._stop
        self._busy = True
        self._ready = False
        self._share = ''
        self._game = (None, -1, -1)
        self._network = {}
        self._world = ('', '')
        self._history.clear()
        self._seen_game = False
        self._seen_ready = False
        self._last_issue = ''
        self._relay_only = relay_only
        self._message = '正在检查游戏端口…' if host else '正在准备加入房间…'
        self._record('开始创建房间' if host else '开始加入房间')

        def work():
            end = '房间已停止。' if host else '已离开房间。'
            try:
                run_room(room, host, cache, stop, lambda *state: self._events.put(('status', state)), relay_only,
                         on_game=lambda game: self._events.put(('game', game)),
                         on_network=lambda network: self._events.put(('network', network)),
                         on_world=lambda world: self._events.put(('world', world)))
            except Cancelled:
                pass
            except RoomError as exc:
                end = str(exc)
            except Exception:
                end = '无法启动或管理 EasyTier。请检查本机权限和安全软件后重试。'
            finally:
                self._events.put(('finished', end))

        self._worker = Thread(target=work, name='easytier-room', daemon=True)
        self._worker.start()
        self.changed.emit()

    @Slot()
    def stop(self):
        if self._busy and not self._stop.is_set():
            self._stop.set()
            self._ready = False
            self._share = ''
            self._game = (None, -1, -1)
            self._network = {}
            self._world = ('', '')
            self._message = '正在停止 EasyTier…'
            self.changed.emit()

    @Slot()
    def copy(self):
        if self._share:
            QApplication.clipboard().setText(self._share)
            self._message = ('已复制房间短码，请私发给朋友。' if self._host else
                             '已复制本地地址，可在 Minecraft「多人游戏 → 直接连接」中使用。')
            self.changed.emit()

    @Slot()
    def copyDiagnostics(self):
        network = self._network
        role = '房主' if self._host else '访客'
        count = str(self.onlinePlayers) if self.onlinePlayers >= 0 else '—'
        limit = str(self.playerLimit) if self.playerLimit >= 0 else '—'
        QApplication.clipboard().setText('\n'.join([
            f'{QApplication.applicationDisplayName()} v{QApplication.applicationVersion()} · {role}',
            f'游戏状态：{self.gameCheck} · 在线玩家：{count} / {limit}',
            f"设备数：{network.get('devices', '—')} · 连接方式：{network.get('path', '—')}",
            f"链路延迟：{network.get('latency', '—')} · 直连丢包：{network.get('loss', '—')}",
            f"最近异常：{self._last_issue or '未记录'}",
            '本次联机记录',
            *self._history,
        ]))

    def _poll(self):
        while True:
            try:
                event, data = self._events.get_nowait()
            except Empty:
                return
            if event == 'scan':
                self._scan_busy = False
                self._worlds = data or []
                if data is None:
                    self._scan_hint = '无法监听局域网公告，请手动填写游戏显示的端口。'
                elif len(data) == 1:
                    self._scan_hint = '检测到 1 个世界。可以使用检测到的端口，或手动修改。'
                elif data:
                    self._scan_hint = '检测到多个世界，请选择要分享的世界。'
                else:
                    self._scan_hint = '未检测到本机世界。请先开放局域网，或手动填写端口。'
                self.scanChanged.emit()
                if len(self._worlds) == 1 and self._host and not self._busy:
                    self.scanFinished.emit(str(self._worlds[0]['port']))
                continue
            if event == 'finished':
                self._busy = False
                self._ready = False
                self._share = ''
                self._game = (None, -1, -1)
                self._network = {}
                self._world = ('', '')
                if self._stop.is_set():
                    self._message = '房间已停止。' if self._host else '已离开房间。'
                    self._record(self._message)
                else:
                    self._message = data
                    self._record_issue(data)
            elif not self._stop.is_set():
                if event == 'game':
                    if self._game[0] is True and data[0] is False:
                        self._record_issue('本机 Minecraft 未响应。' if self._host else '房主 Minecraft 未响应。')
                    elif self._game[0] is False and data[0] is True and self._seen_game:
                        self._record('Minecraft 游戏探测已恢复')
                    if data[0] is True:
                        self._seen_game = True
                    self._game = data
                elif event == 'world':
                    self._world = data
                elif event == 'network':
                    network = data or {}
                    if network == self._network:
                        continue
                    path = network.get('path')
                    if path and path != self._network.get('path'):
                        self._record(f'EasyTier 路径 · {path}')
                    self._network = network
                elif event == 'status':
                    self._message, self._ready, self._share = data
                    if self._ready and not self._seen_ready:
                        self._seen_ready = True
                        self._record('房间已创建' if self._host else '已连接到房主')
            self.changed.emit()

    def close(self):
        self._timer.stop()
        self._scan_stop.set()
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=10)
