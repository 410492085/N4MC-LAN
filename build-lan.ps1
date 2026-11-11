param([string]$OutputRoot = 'dist')

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot '.build-deps'
$version = python -c "from app_version import APP_VERSION; print(APP_VERSION)"
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^0\.[0-9]+$') { throw 'Expected a 0.x app version' }
$appName = python -c "from app_version import APP_NAME; print(APP_NAME)"
if ($LASTEXITCODE -ne 0 -or $appName -notmatch '^[a-zA-Z0-9-]+$') { throw 'Invalid app name' }
$runtime = @('bin/easytier/easytier-core.exe', 'bin/easytier/easytier-cli.exe', 'bin/easytier/Packet.dll')
$licenses = @(
    'licenses/Qt-LGPL-3.0.txt', 'licenses/Qt-GPL-3.0.txt',
    'licenses/EasyTier-LGPL-3.0.txt', 'licenses/WinPcap-LICENSE.html', 'licenses/EasyTier-NOTICE.md',
    'licenses/Python-3.13.9-LICENSE.txt', 'licenses/PyInstaller-6.22.3-COPYING.txt',
    'licenses/OpenSSL-3.0.18-LICENSE.txt', 'licenses/OpenSSL-3.6.5-LICENSE.txt',
    'licenses/ICU-78.3-LICENSE.txt', 'licenses/Mesa-11.2.2-LICENSE.html', 'licenses/LLVM-3.6.2-LICENSE.txt',
    'licenses/frp-LICENSE.txt'
)
python -c "from easytier import BUNDLED_RUNTIME, BUNDLED_FILES, _verified; raise SystemExit(0 if _verified(BUNDLED_RUNTIME, BUNDLED_FILES) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'EasyTier bundle missing or invalid' }
Get-Item -LiteralPath $licenses | Out-Null
python -m PyInstaller --noconfirm --windowed --onedir --distpath $OutputRoot --name $appName --icon assets/n4tsum3.ico --add-data 'qml;qml' --add-data 'assets/n4tsum3.ico;assets' --additional-hooks-dir packaging/pyinstaller-hooks --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineQuick --exclude-module PySide6.QtWebEngineWidgets material_app.py
if ($LASTEXITCODE -ne 0) { throw 'LAN build failed' }
$package = Join-Path $OutputRoot $appName
$icuCollision = Join-Path $package '_internal/icuuc.dll'
if (Test-Path -LiteralPath $icuCollision) { Remove-Item -LiteralPath $icuCollision }
$runtimeDestination = Join-Path $package 'bin/easytier'
$licenseDestination = Join-Path $package 'licenses'
New-Item -ItemType Directory -Force $runtimeDestination,$licenseDestination | Out-Null
Copy-Item -LiteralPath $runtime -Destination $runtimeDestination
Copy-Item -LiteralPath $licenses -Destination $licenseDestination
Copy-Item -LiteralPath LICENSE,THIRD-PARTY-NOTICES.md,README.md,VALIDATION.md -Destination $package
Compress-Archive -LiteralPath $package -DestinationPath (Join-Path $OutputRoot "$appName-v$version-Windows.zip") -Force
