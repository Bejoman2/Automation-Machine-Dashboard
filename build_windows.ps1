$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host '=== 1/3 Build Python backend ===' -ForegroundColor Cyan
Set-Location "$Root\backend"
if (!(Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
}
& .venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if (Test-Path 'build') { Remove-Item 'build' -Recurse -Force }
if (Test-Path 'dist') { Remove-Item 'dist' -Recurse -Force }
& .venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --onefile --name automation-dashboard-backend --paths . --collect-submodules app run.py
if (!(Test-Path 'dist\automation-dashboard-backend.exe')) { throw 'Backend EXE was not created.' }

Write-Host '=== 2/3 Build React frontend ===' -ForegroundColor Cyan
Set-Location "$Root\frontend"
if (!(Test-Path 'node_modules')) { npm install }
npm install
npm run build

Write-Host '=== 3/3 Build Windows installer ===' -ForegroundColor Cyan
npx electron-builder --win nsis

Write-Host ''
Write-Host 'BUILD COMPLETE' -ForegroundColor Green
Write-Host "Installer output: $Root\frontend\release"
