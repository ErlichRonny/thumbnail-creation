from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    database_ssl: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    storage_dir: str = "/data/storage"
    max_file_size_bytes: int = 10 * 1024 * 1024
    max_files_per_request: int = 20
    min_custom_dimension: int = 1
    max_custom_dimension: int = 4000
    worker_concurrency: int = 1
    worker_poll_interval_seconds: float = 1.0
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


settings = Settings()
