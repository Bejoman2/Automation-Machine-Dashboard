from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./dashboard.db"
    csv_folder: str = "./data"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173,null"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
