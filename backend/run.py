import os
import sys
from pathlib import Path

import uvicorn

# Import the FastAPI app directly so PyInstaller can discover the app package.
from app.main import app


def app_data_dir() -> Path:
    custom = os.environ.get("DASHBOARD_APP_DATA")
    if custom:
        path = Path(custom)
    else:
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if root:
            path = Path(root) / "WIK" / "AutomationMachineDashboard"
        else:
            path = Path.home() / ".wik" / "AutomationMachineDashboard"
    path.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    # Packaged EXE: keep writable application data outside Program Files.
    os.environ.setdefault("DASHBOARD_APP_DATA", str(app_data_dir()))
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
