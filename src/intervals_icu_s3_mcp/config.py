"""Environment-variable configuration for our own (non-upstream) functionality.

Mirrors datastore-mcp's config.ts: everything required is validated eagerly,
before anything else runs, with a clean named error on a missing variable
rather than a half-configured start. Upstream's own intervals.icu credentials
(INTERVALS_ICU_API_KEY etc.) are loaded separately by the vendored package
itself — see upstream.py — not duplicated here.
"""

from __future__ import annotations

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingConfigError(RuntimeError):
    """Raised when one or more required environment variables are missing."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Our OAuth-gated public endpoint.
    public_url: str
    port: int = 8080

    # Self-issued OAuth login gate (auth.py).
    oauth_username: str
    oauth_password: str

    # S3 / Tigris, as provisioned by `fly storage create`.
    bucket_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_endpoint_url_s3: str | None = None
    aws_region: str = "auto"


def load_settings() -> Settings:
    """Load and validate settings, failing fast with a named error.

    Raises:
        MissingConfigError: if one or more required variables are missing or invalid.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = ", ".join(str(err["loc"][0]) for err in exc.errors())
        raise MissingConfigError(
            f"Missing or invalid required environment variable(s): {missing}"
        ) from exc
