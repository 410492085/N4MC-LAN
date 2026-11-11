$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot '.build-deps'
python -m PyInstaller --noconfirm --windowed --onedir --name N4tsum3-Material --add-data 'qml;qml' --add-data 'assets;assets' --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineQuick --exclude-module PySide6.QtWebEngineWidgets material_app.py
if ($LASTEXITCODE -ne 0) { throw 'Material build failed' }
# Qt 6.12 uses Windows' unversioned ICU API. PATH may contain Poppler's
# incompatible icuuc.dll (exports *_78); bundling it prevents QtCore import.
# Windows 10/11 supplies the correct OS ICU. Never ship this PATH collision.
$icuCollision = Join-Path $PSScriptRoot 'dist/N4tsum3-Material/_internal/icuuc.dll'
if (Test-Path -LiteralPath $icuCollision) { Remove-Item -LiteralPath $icuCollision }
New-Item -ItemType Directory -Force dist/N4tsum3-Material/bin,dist/N4tsum3-Material/licenses | Out-Null
Copy-Item -LiteralPath bin/frpc.exe -Destination dist/N4tsum3-Material/bin/frpc.exe
Copy-Item -LiteralPath licenses/frp-LICENSE.txt -Destination dist/N4tsum3-Material/licenses/frp-LICENSE.txt
Copy-Item -LiteralPath licenses/Qt-LGPL-3.0.txt,licenses/Qt-GPL-3.0.txt -Destination dist/N4tsum3-Material/licenses
Copy-Item -LiteralPath README.md,VALIDATION.md -Destination dist/N4tsum3-Material
Compress-Archive -Path dist/N4tsum3-Material -DestinationPath dist/N4tsum3-Material-Windows.zip -Force
