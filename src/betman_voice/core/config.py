from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BETMAN_VOICE_", env_file=".env", extra="ignore")

    env: str = "development"
    public_base_url: str = "http://127.0.0.1:8088"
    secret_key: str = Field(default="dev-only-change-me", min_length=12)
    admin_email: str = "ops@betman.co.nz"
    admin_password: str = "change-me"
    default_tenant: str = "betman"
    default_api_key: str = "dev-api-key"
    database_url: str = "sqlite:///./data/betman_voice.db"
    storage_backend: str = "local"
    local_storage_dir: Path = Path("./data/audio")
    spaces_bucket: str = ""
    spaces_region: str = "sgp1"
    spaces_endpoint: str = "https://sgp1.digitaloceanspaces.com"
    spaces_access_key_id: str = ""
    spaces_secret_access_key: str = ""
    spaces_public_base_url: str = ""
    model_backend: str = "auto"
    model_name: str = "qwen3-tts"
    model_dir: Path = Path("./models")
    max_workers: int = 1
    job_poll_seconds: int = 2
    elevenlabs_poll_seconds: int = 3600
    training_command: str = ""
    audio_format: str = "wav"
    allow_synthetic_fallback: bool = True
    request_timeout_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
