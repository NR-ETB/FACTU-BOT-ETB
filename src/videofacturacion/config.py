from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ETB_", env_file=".env", extra="ignore")

    data_dir: Path = Path("var")
    max_file_mb: int = Field(default=10, ge=1, le=50)
    max_invoices: int = Field(default=100, ge=1, le=1000)
    max_lines: int = Field(default=2000, ge=1, le=20000)
    api_url: str = "http://127.0.0.1:8000"

    @property
    def max_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024
