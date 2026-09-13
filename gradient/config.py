from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRADIENT_", env_file=".env", extra="ignore")
    runs_dir: Path = Path("runs")
    worker_dir: Path = Path("worker-workspace")
    codex_command: str = "codex"
    inference_url: str = "http://127.0.0.1:8000/v1"
    inference_api_key: str = ""
    model: str = "Qwen/Qwen3.5-2B"
    sandbox_image: str = "gradient-sandbox:local"
    api_token: str = ""
    desktop_companion: bool = False
    timeout: int = Field(default=180, ge=1, le=1800)
