$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot '.build-deps'
python -m PyInstaller --noconfirm --windowed --onedir --name N4tsum3-Rooms --add-data 'qml;qml' --add-data 'assets;assets' --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineQuick --exclude-module PySide6.QtWebEngineWidgets material_app.py
if ($LASTEXITCODE -ne 0) { throw 'Rooms build failed' }
# Do not bundle Poppler's incompatible PATH icuuc.dll; use Windows OS ICU.
$icuCollision = Join-Path $PSScriptRoot 'dist/N4tsum3-Rooms/_internal/icuuc.dll'
if (Test-Path -LiteralPath $icuCollision) { Remove-Item -LiteralPath $icuCollision }
New-Item -ItemType Directory -Force dist/N4tsum3-Rooms/bin,dist/N4tsum3-Rooms/licenses | Out-Null
Copy-Item -LiteralPath bin/frpc.exe -Destination dist/N4tsum3-Rooms/bin/frpc.exe
Copy-Item -LiteralPath licenses/frp-LICENSE.txt,licenses/Qt-LGPL-3.0.txt,licenses/Qt-GPL-3.0.txt -Destination dist/N4tsum3-Rooms/licenses
Copy-Item -LiteralPath README.md,VALIDATION.md -Destination dist/N4tsum3-Rooms
Compress-Archive -Path dist/N4tsum3-Rooms -DestinationPath dist/N4tsum3-Rooms-Windows.zip -Force
