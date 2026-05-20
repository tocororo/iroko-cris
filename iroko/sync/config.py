from pydantic_settings import BaseSettings

class SyncSettings(BaseSettings):
    sync_enabled: bool = False
    sync_interval_seconds: int = 60
    sync_server_id: str = ""

    class Config:
        env_prefix = "SYNC_"
        env_file = ".env"
        extra = "ignore"

sync_settings = SyncSettings()
