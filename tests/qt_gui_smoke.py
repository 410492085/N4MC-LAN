"""Exercise the real QML UI; no public network or frpc execution."""
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QMetaObject, QUrl, Q_ARG
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lan_controller import LanController
from easytier_controller import EasyTierController
from app_version import APP_NAME, APP_VERSION

QQuickStyle.setStyle('Material')
app = QApplication([])
app.setApplicationDisplayName(APP_NAME)
app.setApplicationVersion(APP_VERSION)
lan = LanController()
easy = EasyTierController()
engine = QQmlApplicationEngine()
warnings = []
engine.warnings.connect(lambda errors: warnings.extend(str(x) for x in errors))
engine.rootContext().setContextProperty('lanBridge', lan)
engine.rootContext().setContextProperty('easyBridge', easy)
engine.load(QUrl.fromLocalFile(str(ROOT / 'qml/Main.qml')))
assert engine.rootObjects(), 'QML must load'
window = engine.rootObjects()[0]
app.processEvents()
assert window.property('page') == 'easy'
assert window.findChild(QQuickItem, 'easyPortField').isVisible()
easy._events.put(('scan', [{'port': 51234, 'label': '樱花谷 · 1.21.4 · 51234'}]))
easy._poll()
assert window.findChild(QObject, 'easyPortField').property('text') == '51234'
if '--preview' in sys.argv:
    QTest.qWait(250)
    assert window.grabWindow().save(str(ROOT / f'build/{APP_NAME}-v{APP_VERSION}-lan-discovery.png'))
easy._events.put(('scan', [{'port': 51234, 'label': '樱花谷 · 51234'}, {'port': 51235, 'label': '另一世界 · 51235'}]))
easy._poll()
picker = window.findChild(QQuickItem, 'easyWorldPicker')
assert picker.isVisible() and picker.property('count') == 2
assert QMetaObject.invokeMethod(picker, 'activated', Q_ARG(int, 1))
assert window.findChild(QObject, 'easyPortField').property('text') == '51235'
assert QMetaObject.invokeMethod(window.findChild(QObject, 'easyGuestButton'), 'clicked')
assert window.findChild(QQuickItem, 'easyInviteField').isVisible()
assert window.findChild(QObject, 'easyStartButton').property('text') == '加入房间'
assert f'{APP_NAME} v{APP_VERSION}' in window.property('title')
assert not window.findChild(QObject, 'wallpaper')
players = window.findChild(QQuickItem, 'easyPlayersCard')
assert players.isVisible()
easy._busy = True
easy._events.put(('status', ('已连接 · 界面预览使用示例数据', True, '127.0.0.1:25566')))
easy._events.put(('game', (True, 2, 8)))
easy._events.put(('world', ('樱花谷', '1.21.4')))
easy._events.put(('network', dict(devices=2, path='直连', latency='86 ms', loss='0.4%')))
easy._poll()
assert window.findChild(QObject, 'easyPlayerCount').property('text') == '2 / 8'
assert window.findChild(QObject, 'easyNetworkPath').property('text') == '直连'
assert window.findChild(QObject, 'easyWorldName').property('text') == '樱花谷'
assert window.findChild(QObject, 'easyWorldVersion').property('text') == '1.21.4'
easy._events.put(('game', (False, -1, -1)))
easy._events.put(('world', ('', '')))
easy._events.put(('network', dict(devices=2, path='中继', latency='95 ms', loss='—')))
easy._events.put(('status', ('暂时无法访问房主，正在继续重试。', False, '')))
easy._poll()
assert window.findChild(QObject, 'easyPlayerCount').property('text') == '—'
assert window.findChild(QObject, 'easyGameCheck').property('text') == '无响应'
issue = window.findChild(QQuickItem, 'easyLastIssue')
assert '房主 Minecraft 未响应' in issue.property('text')
if '--preview' in sys.argv:
    # Captures the real UI with synthetic state for a reproducible preview.
    QTest.qWait(250)
    assert window.grabWindow().save(str(ROOT / f'build/{APP_NAME}-v{APP_VERSION}-diagnostics.png'))
easy._events.put(('game', (True, 2, 8)))
easy._events.put(('world', ('樱花谷', '1.21.4')))
easy._events.put(('network', dict(devices=2, path='直连', latency='86 ms', loss='0.4%')))
easy._events.put(('status', ('连接已恢复 · 界面预览使用示例数据', True, '127.0.0.1:25566')))
easy._poll()
assert window.findChild(QObject, 'easyPlayerCount').property('text') == '2 / 8'
assert '房主 Minecraft 未响应' in issue.property('text')
assert any('Minecraft 游戏探测已恢复' in entry for entry in easy.history)
assert any('EasyTier 路径 · 中继' in entry for entry in easy.history)
if '--preview' in sys.argv:
    QTest.qWait(250)
    assert window.grabWindow().save(str(ROOT / f'build/{APP_NAME}-v{APP_VERSION}-preview.png'))
window.setWidth(920); window.setHeight(720); app.processEvents()
assert issue.mapToScene(issue.boundingRect().bottomLeft()).y() <= 672
assert QMetaObject.invokeMethod(window.findChild(QObject, 'easyCopyDiagnostics'), 'clicked')
report = app.clipboard().text()
assert '2 / 8' in report and '86 ms' in report and '127.0.0.1' not in report
assert '本次联机记录' in report and '游戏探测已恢复' in report
easy._events.put(('finished', '已离开房间'))
easy._poll()
assert window.findChild(QObject, 'easyPlayerCount').property('text') == '—'
assert not window.findChild(QObject, 'serverField')
assert not window.findChild(QObject, 'startButton')
assert QMetaObject.invokeMethod(window.findChild(QObject, 'lanNav'), 'clicked')
app.processEvents()
assert window.property('page') == 'tailscale'
assert window.findChild(QQuickItem, 'lanPage').isVisible()
assert not window.findChild(QQuickItem, 'lanPeers').isVisible()
assert not window.findChild(QObject, 'lanCheck').property('enabled')
lan.apply_status({'ready': True, 'state': 'Running', 'ip': '100.90.1.2', 'peers': []})
port = window.findChild(QObject, 'lanPort')
port.setProperty('text', '51234')
assert QMetaObject.invokeMethod(port, 'textEdited')
app.processEvents()
assert window.findChild(QObject, 'lanAddress').property('text') == '100.90.1.2:51234'
peers = [{'name': '朋友的电脑', 'ip': '100.90.1.3', 'ips': ['100.90.1.3'], 'online': True},
         {'name': '房主电脑', 'ip': '100.90.1.4', 'ips': ['100.90.1.4'], 'online': True}]
status = {'ready': True, 'state': 'Running', 'ip': '100.90.1.2', 'peers': peers}
lan.apply_status(status)
assert QMetaObject.invokeMethod(window.findChild(QObject, 'lanGuestButton'), 'clicked')
lan.setTarget('100.90.1.4')
app.processEvents()
assert lan.role == 'friend'
assert window.findChild(QQuickItem, 'lanPeers').isVisible()
check = window.findChild(QQuickItem, 'lanCheck')
assert check.property('enabled')
assert check.mapToScene(check.boundingRect().bottomLeft()).y() <= 672
selector = window.findChild(QObject, 'lanPeers')
assert selector.property('currentIndex') == 1
lan.apply_status(dict(status, peers=list(reversed(peers)))); app.processEvents()
assert selector.property('currentIndex') == 0
assert lan.address == '100.90.1.4:51234'
if '--preview' in sys.argv:
    window.setWidth(1200)
    window.setHeight(850)
    QTest.qWait(250)
    assert window.grabWindow().save(str(ROOT / f'build/{APP_NAME}-v{APP_VERSION}-tailscale-join.png'))
    assert QMetaObject.invokeMethod(window.findChild(QObject, 'lanHostButton'), 'clicked')
    QTest.qWait(250)
    assert window.grabWindow().save(str(ROOT / f'build/{APP_NAME}-v{APP_VERSION}-tailscale-host.png'))
assert not warnings, warnings
lan.close()
easy.close()
window.close()
app.processEvents()
print('PASS: N4MC-LAN Material UI, player counts, dropout and recovery, diagnostic copy, navigation and minimum size')
