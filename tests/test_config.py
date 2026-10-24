from intervals_icu_s3_mcp.config import REQUIRED_ENV_VARS, load_settings, missing_env_vars

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
    assert missing_env_vars(settings) == []


def test_never_raises_with_everything_missing(monkeypatch):
    _set_env(monkeypatch, omit=list(REQUIRED_ENV))
    settings = load_settings()  # must not raise
    assert missing_env_vars(settings) == list(REQUIRED_ENV)


def test_missing_vars_reported_individually(monkeypatch):
    _set_env(monkeypatch, omit=["OAUTH_PASSWORD", "BUCKET_NAME"])
    settings = load_settings()
    assert missing_env_vars(settings) == ["OAUTH_PASSWORD", "BUCKET_NAME"]


def test_port_overridable(monkeypatch):
    _set_env(monkeypatch, overrides={"PORT": "9000"})
    settings = load_settings()
    assert settings.port == 9000


def test_invalid_port_falls_back_to_default(monkeypatch):
    _set_env(monkeypatch, overrides={"PORT": "not-a-number"})
    settings = load_settings()  # must not raise
    assert settings.port == 8080
    assert missing_env_vars(settings) == []


def test_required_env_vars_cover_every_settings_dependency():
    # sanity check that the mapping used for reporting stays in sync with
    # the field names on Settings
    assert set(REQUIRED_ENV_VARS) == {
        "public_url",
        "oauth_username",
        "oauth_password",
        "bucket_name",
        "aws_access_key_id",
        "aws_secret_access_key",
    }
