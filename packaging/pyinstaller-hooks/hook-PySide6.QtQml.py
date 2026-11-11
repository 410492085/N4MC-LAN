"""Bundle the QML modules reached from this app and their native dependencies."""

import json
from pathlib import Path, PurePath
import subprocess

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


qt = pyside6_library_info
qml_source = Path(__file__).resolve().parents[2] / 'qml'
qml_imports = Path(qt.location['QmlImportsPath'])
scanner = qml_imports.parent / 'qmlimportscanner.exe'
scan = subprocess.run(
    [str(scanner), '-rootPath', str(qml_source), '-importPath', str(qml_imports)],
    check=True, capture_output=True, encoding='utf-8',
)
modules = [entry for entry in json.loads(scan.stdout) if entry.get('type') == 'module']
unresolved = [entry['name'] for entry in modules if not entry.get('relativePath') and entry['name'] != 'QML']
if not modules or unresolved:
    raise RuntimeError(f'QML dependency scan incomplete: {unresolved}')

qml_dest = PurePath(qt.qt_rel_dir) / 'qml'
module_dirs = {qml_dest / entry['relativePath'] for entry in modules if entry.get('relativePath')}

# The Qt collector keeps nested modules separate. Asset directories inside
# selected modules travel with their parent (icons, fonts, and style assets).
def is_required(entry):
    source, destination = entry
    dest = PurePath(destination)
    return dest in module_dirs or (Path(source).is_dir() and dest.parent in module_dirs)


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# The Qt Quick 3D profiler is a developer tool and pulls in Qt Quick 3D.
binaries = [entry for entry in binaries if Path(entry[0]).name.lower() != 'qmldbg_quick3dprofiler.dll']
qml_binaries, qml_datas = qt.collect_qtqml_files()
binaries.extend(filter(is_required, qml_binaries))
datas.extend(filter(is_required, qml_datas))
