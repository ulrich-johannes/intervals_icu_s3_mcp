import pytest

from intervals_icu_s3_mcp.config import MissingConfigError, load_settings

REQUIRED_ENV = {
    "PUBLIC_URL": "https://example.fly.dev",
    "OAUTH_USERNAME": "alice",
    "OAUTH_PASSWORD": "s3cr3t",
    "BUCKET_NAME": "my-bucket",
    "AWS_ACCESS_KEY_ID": "AKIA...",
    "AWS_SECRET_ACCESS_KEY": "shh",
}


def _set_env(monkeypatch, overrides=None, omit=()):
    for key in (*REQUIRED_ENV, "PORT"):
        monkeypatch.delenv(key, raising=False)
    env = dict(REQUIRED_ENV)
    env.update(overrides or {})
    for key in omit:
        env.pop(key, None)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_loads_with_all_required_vars(monkeypatch):
    _set_env(monkeypatch)
    settings = load_settings()
    assert settings.public_url == "https://example.fly.dev"
    assert settings.oauth_username == "alice"
    assert settings.bucket_name == "my-bucket"
    assert settings.port == 8080  # default
    assert settings.aws_region == "auto"  # default


@pytest.mark.parametrize("missing", list(REQUIRED_ENV.keys()))
def test_missing_required_var_raises(monkeypatch, missing):
    _set_env(monkeypatch, omit=[missing])
    with pytest.raises(MissingConfigError):
        load_settings()


def test_port_overridable(monkeypatch):
    _set_env(monkeypatch, overrides={"PORT": "9000"})
    settings = load_settings()
    assert settings.port == 9000
