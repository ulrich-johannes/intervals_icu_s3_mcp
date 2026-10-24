"""Environment-variable configuration for our own (non-upstream) functionality.

Deliberately permissive, unlike datastore-mcp's config.ts: a missing or
invalid variable must NOT crash the process at boot. Instead the app still
starts, and every MCP endpoint reports clearly that it isn't configured yet
and exactly which variable(s) are missing -- see server.py's
`build_misconfigured_app()`. This matters for a non-technical deployer: a
crash-looping Fly machine with no visible reason is much harder to debug
than a running server that just says what to fix.

Upstream's own intervals.icu credentials (INTERVALS_ICU_API_KEY etc.) are
loaded separately by the vendored package itself -- see upstream.py's
`missing_intervals_config()`, not duplicated here.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# field name -> the environment variable a deployer actually sets, in the
# order they're listed in README.md's secrets table.
REQUIRED_ENV_VARS: dict[str, str] = {
    "public_url": "PUBLIC_URL",
    "oauth_username": "OAUTH_USERNAME",
    "oauth_password": "OAUTH_PASSWORD",
    "bucket_name": "BUCKET_NAME",
    "aws_access_key_id": "AWS_ACCESS_KEY_ID",
    "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Our OAuth-gated public endpoint.
    public_url: str | None = None
    port: int = 8080

    # Self-issued OAuth login gate (auth.py).
    oauth_username: str | None = None
    oauth_password: str | None = None

    # S3 / Tigris, as provisioned by `fly storage create` or Fly's Object
    # Storage dashboard page.
    bucket_name: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_endpoint_url_s3: str | None = None
    aws_region: str = "auto"

    @field_validator("port", mode="before")
    @classmethod
    def _port_falls_back_to_default(cls, value: object) -> object:
        # A typo'd PORT secret (e.g. "8O80") must not crash the whole app --
        # just ignore it and use the default instead.
        if value is None or value == "":
            return 8080
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 8080


def load_settings() -> Settings:
    """Load settings. Always succeeds -- missing values just come back as None."""
    return Settings()  # type: ignore[call-arg]


def missing_env_vars(settings: Settings) -> list[str]:
    """Names of required environment variables that are unset or empty."""
    return [
        env_name
        for field, env_name in REQUIRED_ENV_VARS.items()
        if not getattr(settings, field, None)
    ]
