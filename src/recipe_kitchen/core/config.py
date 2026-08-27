from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""
    supabase_api_key: str = ""

    @property
    def secret_key(self) -> str:
        """Secret API key, preferring SUPABASE_SECRET_KEY over the legacy alias."""
        return self.supabase_secret_key or self.supabase_api_key

    @property
    def jwks_url(self) -> str:
        """JWKS URL for JWT verification, derived from SUPABASE_URL when unset."""
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    """Return cached app settings loaded from the environment and `.env`."""
    return Settings()
