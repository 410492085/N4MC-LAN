$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot '.build-deps'
python -m PyInstaller --noconfirm --windowed --onedir --name N4tsum3 app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
New-Item -ItemType Directory -Force dist/N4tsum3/bin,dist/N4tsum3/licenses | Out-Null
Copy-Item -LiteralPath bin/frpc.exe -Destination dist/N4tsum3/bin/frpc.exe
Copy-Item -LiteralPath licenses/frp-LICENSE.txt -Destination dist/N4tsum3/licenses/frp-LICENSE.txt
Copy-Item -LiteralPath README.md -Destination dist/N4tsum3/README.md
Copy-Item -LiteralPath VALIDATION.md -Destination dist/N4tsum3/VALIDATION.md
Compress-Archive -Path dist/N4tsum3 -DestinationPath dist/N4tsum3-Windows.zip -Force
