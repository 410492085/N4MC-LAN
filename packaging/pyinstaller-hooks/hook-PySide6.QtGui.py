"""Collect Qt GUI dependencies for the Windows desktop application."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# Keep the Windows platform and input method plugins. The app has no PDF
# viewer or Qt Virtual Keyboard, which have their own redistribution terms.
excluded = {'qpdf.dll', 'qtvirtualkeyboardplugin.dll'}
binaries = [entry for entry in binaries if Path(entry[0]).name.lower() not in excluded]
