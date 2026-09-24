import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_app_data_dir() -> Path:
    custom = os.environ.get("DASHBOARD_APP_DATA")
    if custom:
        path = Path(custom)
    else:
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        path = (Path(root) / "WIK" / "AutomationMachineDashboard") if root else (Path.home() / ".wik" / "AutomationMachineDashboard")
    path.mkdir(parents=True, exist_ok=True)
    return path


APP_DATA_DIR = default_app_data_dir()
DEFAULT_DB = APP_DATA_DIR / "dashboard.db"


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{DEFAULT_DB.as_posix()}"
    csv_folder: str = "./data"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173,null,file://"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
