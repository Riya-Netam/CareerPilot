from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_KEYS = {"", "change-me-to-a-long-string", "change-me-to-a-long-random-string", "secret", "changeme"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    DATABASE_URL: str = "postgresql+psycopg://careerpilot:careerpilot@localhost:5432/careerpilot"

    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_DAYS: int = 7
    TRUST_PROXY: bool = False

    EMAIL_MODE: Literal["console", "smtp"] = "console"
    EMAIL_FROM: str = "CareerPilot AI <no-reply@example.com>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    UPLOAD_DIR: str = "./private_uploads"
    MAX_UPLOAD_MB: int = 5
    STORE_ORIGINAL_FILES: bool = True

    AI_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    AI_TIMEOUT_SECONDS: int = 90

    RATE_LIMIT_ENABLED: bool = True

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        # Hosts such as Render/Neon give "postgres://" or "postgresql://"; make SQLAlchemy use psycopg 3.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @model_validator(mode="after")
    def _production_checks(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            problems = []
            if self.SECRET_KEY in INSECURE_KEYS or len(self.SECRET_KEY) < 32:
                problems.append("SECRET_KEY must be a random string of at least 32 characters")
            if not self.COOKIE_SECURE:
                problems.append("COOKIE_SECURE must be true in production (HTTPS)")
            if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
                problems.append("SameSite=None requires COOKIE_SECURE=true")
            if problems:
                raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT in ("development", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
