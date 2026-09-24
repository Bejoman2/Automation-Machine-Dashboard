# Windows EXE Build

This project can be packaged as a Windows installer. The installer contains:

- React/Vite frontend
- Electron desktop shell
- FastAPI/Python backend compiled to `automation-dashboard-backend.exe`
- SQLite database created in `%LOCALAPPDATA%\WIK\AutomationMachineDashboard`

## Prerequisites on the build PC

- Windows 10/11
- Python 3.11+ recommended
- Node.js LTS + npm

The target production PC does **not** need Python or Node.js after installation.

## Build

Open PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The installer is generated under:

```text
frontend\release\WIK-Automation-Machine-Dashboard-1.3.0-Setup.exe
```

## Runtime data

The packaged application stores SQLite data under:

```text
%LOCALAPPDATA%\WIK\AutomationMachineDashboard\dashboard.db
```

The Hikrobot CSV folder is configured through the dashboard's CSV SOURCE screen, so the production data does not need to be copied into the installer.

## Development desktop test

Build the backend first, then from `frontend`:

```powershell
npm install
npm run build
npm run desktop
```

## Important

The Python backend is compiled with PyInstaller. Because the backend currently uses pandas, the resulting backend executable can be relatively large. This is expected for the first packaging version.
