# N4MC-LAN 第三方组件声明

N4MC-LAN 自有代码采用 [MIT 许可证](LICENSE)。以下组件保留各自的许可证和版权。

| 组件 | 许可及对应版本的来源 |
| --- | --- |
| EasyTier 2.6.4（Windows x64） | LGPL-3.0。包内的两个 EasyTier 可执行文件来自 [官方发行包](https://github.com/EasyTier/EasyTier/releases/tag/v2.6.4)。[对应源码](https://github.com/EasyTier/EasyTier/archive/refs/tags/v2.6.4.zip) · [许可文本](licenses/EasyTier-LGPL-3.0.txt) |
| WinPcap 4.1.3（`Packet.dll`） | 采用该版本随附的 BSD 许可及版权声明。[官方安装包](https://www.winpcap.org/install/) · [许可和版权声明](licenses/WinPcap-LICENSE.html) |
| Qt、PySide6 Essentials、Shiboken6 6.12.0 | Copyright The Qt Company Ltd. and other contributors。此便携包按 LGPL-3.0 分发所用 Qt 和 Qt for Python 库。[Qt 对应源码与模块版本](https://code.qt.io/cgit/qt/qt5.git/tag/?h=v6.12.0) · [PySide6 和 Shiboken6 对应源码](https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.12.0) · [LGPL 文本](licenses/Qt-LGPL-3.0.txt) · [GPL 文本](licenses/Qt-GPL-3.0.txt) |
| CPython 3.13.9 | Python Software Foundation License 及随附声明。[对应源码](https://www.python.org/downloads/release/python-3139/) · [许可文本](licenses/Python-3.13.9-LICENSE.txt) |
| PyInstaller 6.22.3 | GPL-2.0-or-later，含允许分发打包程序的 bootloader 例外。[对应源码](https://github.com/pyinstaller/pyinstaller/tree/v6.22.3) · [许可与例外](licenses/PyInstaller-6.22.3-COPYING.txt) |
| OpenSSL 3.0.18、3.6.5 | Apache-2.0。[3.0.18 源码](https://github.com/openssl/openssl/tree/openssl-3.0.18) · [3.0.18 许可](licenses/OpenSSL-3.0.18-LICENSE.txt) · [3.6.5 源码](https://github.com/openssl/openssl/tree/openssl-3.6.5) · [3.6.5 许可](licenses/OpenSSL-3.6.5-LICENSE.txt) |
| ICU 78.3 | Unicode License V3 及上游随附声明。[对应源码](https://github.com/unicode-org/icu/tree/release-78.3) · [许可文本](licenses/ICU-78.3-LICENSE.txt) |
| Mesa 11.2.2、LLVM 3.6.2 | Qt 提供的 Windows 软件 OpenGL 渲染器 `opengl32sw.dll`。[Mesa 源码](https://archive.mesa3d.org/older-versions/11.x/11.2.2/mesa-11.2.2.tar.xz) · [Mesa 许可](licenses/Mesa-11.2.2-LICENSE.html) · [LLVM 源码](https://github.com/llvm/llvm-project/tree/llvmorg-3.6.2/llvm) · [LLVM 许可](licenses/LLVM-3.6.2-LICENSE.txt) |
| Microsoft Visual C++ 运行库和 Universal CRT | Microsoft 运行库按相应再分发条款提供。[Microsoft 再分发说明](https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files) |

Qt 与 PySide6 的库以独立文件放在 `_internal/`。用户可以替换为 ABI 兼容的修改版，也可以为调试这些修改进行逆向工程。Qt 和 Qt for Python 内部采用的其他代码及其版权，见各模块的源码和上游归属说明。 [Qt 第三方代码声明](https://doc.qt.io/qt-6/licenses-used-in-qt.html) · [Qt for Python 许可清单](https://doc.qt.io/qtforpython-6/licenses.html)

源码树中保留的旧版 frp 功能使用 Apache-2.0 的 frp。 [frp 源码](https://github.com/fatedier/frp/tree/v0.72.0) · [frp 许可](licenses/frp-LICENSE.txt)
