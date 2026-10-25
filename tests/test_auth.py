import boto3
import pytest
from mcp.server.auth.provider import AuthorizationParams, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from moto import mock_aws
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from intervals_icu_s3_mcp.auth import SingleUserOAuthProvider
from intervals_icu_s3_mcp.oauth_persistence import OAuthPersistence

PERSISTENCE_BUCKET = "auth-persistence-test-bucket"

USERNAME = "alice"
PASSWORD = "s3cr3t"


@pytest.fixture
def provider():
    return SingleUserOAuthProvider(
        base_url="https://example.fly.dev",
        username=USERNAME,
        password=PASSWORD,
    )


@pytest.fixture
def client_info():
    return OAuthClientInformationFull(
        client_id="client-123",
        redirect_uris=["https://client.example/callback"],
    )


def _auth_params(**overrides):
    defaults = dict(
        state="xyz",
        scopes=["mcp"],
        code_challenge="challenge-value",
        redirect_uri="https://client.example/callback",
        redirect_uri_provided_explicitly=True,
    )
    defaults.update(overrides)
    return AuthorizationParams(**defaults)


def _login_app(provider):
    return Starlette(routes=[Route("/login", provider.handle_login, methods=["GET", "POST"])])


def test_registration_endpoint_is_actually_exposed(provider):
    # Regression test: the MCP SDK's ClientRegistrationOptions defaults to
    # enabled=False, which silently drops the /register route -- a client
    # then reports DCR as unsupported and asks for a manually-issued
    # Client ID, which this server has no concept of. See auth.py.
    paths = [route.path for route in provider.get_routes()]
    assert "/register" in paths
    assert provider.client_registration_options.enabled is True


async def test_register_client_then_get_client(provider, client_info):
    await provider.register_client(client_info)
    fetched = await provider.get_client("client-123")
    assert fetched is not None
    assert fetched.client_id == "client-123"


async def test_unknown_client_returns_none(provider):
    assert await provider.get_client("nope") is None


async def test_authorize_stashes_pending_login_and_returns_login_url(provider, client_info):
    url = await provider.authorize(client_info, _auth_params())
    assert url.startswith("https://example.fly.dev/login?login_id=")
    login_id = url.split("login_id=", 1)[1]
    assert login_id in provider._pending_logins


def test_login_wrong_password_rejected(provider, client_info):
    import anyio

    login_id = anyio.run(provider.authorize, client_info, _auth_params())
    login_id = login_id.split("login_id=", 1)[1]

    with TestClient(_login_app(provider)) as c:
        resp = c.post(
            "/login",
            data={"login_id": login_id, "username": USERNAME, "password": "wrong"},
            follow_redirects=False,
        )
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.text
    # the pending login survives a failed attempt, so the user can retry
    assert login_id in provider._pending_logins


def test_login_correct_credentials_redirects_with_code(provider, client_info):
    import anyio

    login_url = anyio.run(provider.authorize, client_info, _auth_params(state="xyz"))
    login_id = login_url.split("login_id=", 1)[1]

    with TestClient(_login_app(provider)) as c:
        resp = c.post(
            "/login",
            data={"login_id": login_id, "username": USERNAME, "password": PASSWORD},
            follow_redirects=False,
        )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://client.example/callback?")
    assert "code=" in location
    assert "state=xyz" in location
    # consumed: the login_id cannot be replayed
    assert login_id not in provider._pending_logins


async def test_full_code_exchange_issues_bearer_access_token(provider, client_info):
    await provider.register_client(client_info)
    params = _auth_params()
    login_url = await provider.authorize(client_info, params)
    login_id = login_url.split("login_id=", 1)[1]

    with TestClient(_login_app(provider)) as c:
        resp = c.post(
            "/login",
            data={"login_id": login_id, "username": USERNAME, "password": PASSWORD},
            follow_redirects=False,
        )
    code = resp.headers["location"].split("code=", 1)[1].split("&", 1)[0]

    auth_code = await provider.load_authorization_code(client_info, code)
    assert auth_code is not None
    assert auth_code.code_challenge == params.code_challenge

    token = await provider.exchange_authorization_code(client_info, auth_code)
    assert token.token_type == "Bearer"
    assert token.refresh_token is None

    access_token = await provider.load_access_token(token.access_token)
    assert access_token is not None
    assert access_token.client_id == client_info.client_id

    # the code is single-use
    assert await provider.load_authorization_code(client_info, code) is None


async def test_load_access_token_expired_returns_none(provider):
    from mcp.server.auth.provider import AccessToken

    provider._access_tokens["expired-token"] = AccessToken(
        token="expired-token", client_id="c", scopes=[], expires_at=1
    )
    assert await provider.load_access_token("expired-token") is None


async def test_no_refresh_token_support(provider, client_info):
    assert await provider.load_refresh_token(client_info, "whatever") is None
    with pytest.raises(TokenError):
        await provider.exchange_refresh_token(client_info, object(), [])


def test_login_lockout_after_too_many_failures(provider, client_info):
    import anyio

    from intervals_icu_s3_mcp.auth import LOGIN_MAX_ATTEMPTS

    with TestClient(_login_app(provider)) as c:
        for _ in range(LOGIN_MAX_ATTEMPTS):
            login_url = anyio.run(provider.authorize, client_info, _auth_params())
            login_id = login_url.split("login_id=", 1)[1]
            c.post(
                "/login",
                data={"login_id": login_id, "username": USERNAME, "password": "wrong"},
            )

        login_url = anyio.run(provider.authorize, client_info, _auth_params())
        login_id = login_url.split("login_id=", 1)[1]
        resp = c.post(
            "/login",
            data={"login_id": login_id, "username": USERNAME, "password": PASSWORD},
        )
    assert resp.status_code == 429


async def test_persisted_state_survives_a_restart(client_info):
    """Simulates a machine restart: a second provider, built fresh against
    the same persisted bucket, must see the first provider's registered
    client and issued access token without redoing DCR or login."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=PERSISTENCE_BUCKET)

        def new_provider():
            persistence = OAuthPersistence(
                client=s3, bucket=PERSISTENCE_BUCKET, secret="shared-secret"
            )
            return SingleUserOAuthProvider(
                base_url="https://example.fly.dev",
                username=USERNAME,
                password=PASSWORD,
                persistence=persistence,
            )

        first = new_provider()
        await first.register_client(client_info)
        params = _auth_params()
        login_url = await first.authorize(client_info, params)
        login_id = login_url.split("login_id=", 1)[1]

        with TestClient(_login_app(first)) as c:
            resp = c.post(
                "/login",
                data={"login_id": login_id, "username": USERNAME, "password": PASSWORD},
                follow_redirects=False,
            )
        code = resp.headers["location"].split("code=", 1)[1].split("&", 1)[0]
        auth_code = await first.load_authorization_code(client_info, code)
        token = await first.exchange_authorization_code(client_info, auth_code)

        # "restart": a brand new provider instance, nothing shared but the bucket.
        second = new_provider()
        assert await second.get_client(client_info.client_id) is not None
        access_token = await second.load_access_token(token.access_token)
        assert access_token is not None
        assert access_token.client_id == client_info.client_id


async def test_persisted_state_without_persistence_configured_is_a_noop():
    provider = SingleUserOAuthProvider(
        base_url="https://example.fly.dev", username=USERNAME, password=PASSWORD
    )
    client = OAuthClientInformationFull(client_id="c1")
    await provider.register_client(client)  # must not raise with no persistence set
    assert await provider.get_client("c1") is not None


async def test_wrong_state_secret_does_not_crash_startup(client_info):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=PERSISTENCE_BUCKET)

        writer = SingleUserOAuthProvider(
            base_url="https://example.fly.dev",
            username=USERNAME,
            password=PASSWORD,
            persistence=OAuthPersistence(
                client=s3, bucket=PERSISTENCE_BUCKET, secret="correct-secret"
            ),
        )
        await writer.register_client(client_info)

        reader = SingleUserOAuthProvider(
            base_url="https://example.fly.dev",
            username=USERNAME,
            password=PASSWORD,
            persistence=OAuthPersistence(
                client=s3, bucket=PERSISTENCE_BUCKET, secret="wrong-secret"
            ),
        )
        # degrades to empty state rather than raising
        assert await reader.get_client(client_info.client_id) is None
