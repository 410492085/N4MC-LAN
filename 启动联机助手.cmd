@echo off
cd /d "%~dp0"
if exist "dist\N4MC-LAN\N4MC-LAN.exe" (
  start "" "dist\N4MC-LAN\N4MC-LAN.exe"
  exit /b
)
if exist "dist\N4tsum3-LAN\N4tsum3-LAN.exe" (
  start "" "dist\N4tsum3-LAN\N4tsum3-LAN.exe"
  exit /b
)
if exist "dist\N4tsum3-Rooms\N4tsum3-Rooms.exe" (
  start "" "dist\N4tsum3-Rooms\N4tsum3-Rooms.exe"
  exit /b
)
if exist "dist\N4tsum3-Material\N4tsum3-Material.exe" (
  start "" "dist\N4tsum3-Material\N4tsum3-Material.exe"
  exit /b
)
set "PYTHONPATH=%~dp0.build-deps;%PYTHONPATH%"
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
  start "" pythonw "%~dp0material_app.py"
  exit /b
)
echo Please install Python 3.11+ and PySide6, or run N4MC-LAN.exe.
pause
