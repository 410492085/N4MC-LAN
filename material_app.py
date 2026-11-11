"""N4MC-LAN: Qt Quick Material desktop entry point."""
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QUICK_CONTROLS_MATERIAL_VARIANT', 'Dense')
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from lan_controller import LanController
from easytier_controller import EasyTierController
from app_version import APP_NAME, APP_VERSION

RESOURCE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def main():
    QQuickStyle.setStyle('Material')
    app = QApplication(sys.argv)
    # Keep the Qt data directory identifier for the existing EasyTier cache.
    app.setApplicationName('N4tsum3')
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName('N4tsum3')
    app.setWindowIcon(QIcon(str(RESOURCE / 'assets/n4tsum3.ico')))
    app.setFont(QFont('Microsoft YaHei UI', 10))
    smoke = len(sys.argv) == 3 and sys.argv[1] == '--smoke-test'
    capture = len(sys.argv) == 3 and sys.argv[1] == '--capture'
    lan = LanController()
    easy = EasyTierController()
    app.aboutToQuit.connect(lan.close)
    app.aboutToQuit.connect(easy.close)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('lanBridge', lan)
    engine.rootContext().setContextProperty('easyBridge', easy)
    engine.load(QUrl.fromLocalFile(str(RESOURCE / 'qml/Main.qml')))
    if not engine.rootObjects(): return 1
    window = engine.rootObjects()[0]
    if not smoke: QTimer.singleShot(250, lan.refresh)
    if smoke or capture:
        def finish():
            if smoke:
                if APP_NAME not in window.title() or app.windowIcon().isNull(): app.exit(2); return
                if window.property('page') != 'easy' or not window.findChild(QObject, 'easyStartButton'): app.exit(7); return
                if not window.findChild(QObject, 'easyDiagnostics'): app.exit(8); return
                window.setProperty('page', 'tailscale')
                if not window.findChild(QObject, 'lanCheck') or lan.ready: app.exit(6); return
                Path(sys.argv[2]).write_text('PASS: N4MC-LAN Material UI, EasyTier diagnostics and Tailscale loaded', encoding='utf-8')
            else:
                if not window.grabWindow().save(sys.argv[2]): app.exit(4); return
            window.close()
        QTimer.singleShot(1500, finish)
    result = app.exec()
    engine.deleteLater()
    return result


if __name__ == '__main__': sys.exit(main())
