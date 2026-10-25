"""Self-issued, single-user OAuth 2.1 authorization server.

FastMCP's own auth providers (OAuthProxy, RemoteAuthProvider, GitHubProvider,
etc.) all delegate real user login to an external identity provider -- see
SPECIFICATION.md §02. This module implements the lower-level
``mcp.server.auth.provider.OAuthAuthorizationServerProvider`` /
``fastmcp.server.auth.OAuthProvider`` abstraction directly, the same way
datastore-mcp's SingleUserAuthProvider does in Node/TS, ported to Python:

- Dynamic Client Registration stays open (any client may self-register);
  the real access boundary is the login form (``OAUTH_USERNAME`` /
  ``OAUTH_PASSWORD``), checked in the ``/login`` route below.
- ``authorize()`` does NOT redirect straight back to the client. It stashes
  the pending authorization request under a one-time ``login_id`` and
  returns a URL to our own login page; only a successful ``POST /login``
  mints an authorization code and completes the OAuth redirect.
- Access tokens are opaque, one-hour TTL. No refresh tokens.
- All state (registered clients, pending logins, issued codes, issued
  tokens) lives in plain in-process dicts, which is still why the
  deployment is pinned to one machine (SPECIFICATION.md §02/§08) -- but
  registered clients and issued access tokens are now also written
  through to S3 (optionally, via `persistence`; see oauth_persistence.py
  and SPECIFICATION.md §15), so a machine *restart* doesn't force every
  connected client to fully re-register and re-login. Pending logins and
  authorization codes are deliberately NOT persisted -- both are
  single-use and short-lived enough that it isn't worth the complexity.
"""

from __future__ import annotations

import asyncio
import html
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastmcp.server.auth import OAuthProvider
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthToken,
    RefreshToken,
    TokenError,
)
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

if TYPE_CHECKING:
    from .oauth_persistence import OAuthPersistence

ACCESS_TOKEN_TTL_SECONDS = 3600
LOGIN_ID_TTL_SECONDS = 600
AUTH_CODE_TTL_SECONDS = 300

# Minimal brute-force guard on /login: more than this many failed attempts
# from one IP within the window locks that IP out for the rest of the window.
LOGIN_MAX_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 300


@dataclass
class _PendingLogin:
    client: OAuthClientInformationFull
    params: AuthorizationParams
    expires_at: float


class SingleUserOAuthProvider(OAuthProvider):
    """One hardcoded username/password gate; no third-party IdP involved."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        persistence: "OAuthPersistence | None" = None,
    ) -> None:
        # The MCP SDK's ClientRegistrationOptions defaults to enabled=False,
        # which silently drops the /register route and the
        # registration_endpoint from the metadata -- a client then sees no
        # way to self-register and asks the human for a manually-issued
        # Client ID instead (which we don't have, since we never pre-issue
        # one). Open DCR is the whole point of this design (see the module
        # docstring and SPECIFICATION.md §08), so it must be turned on
        # explicitly here.
        super().__init__(
            base_url=base_url,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )
        self._username = username
        self._password = password
        self._persistence = persistence
        self._persist_lock = asyncio.Lock()

        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending_logins: dict[str, _PendingLogin] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}

        # ip -> list of failure timestamps, for the brute-force guard.
        self._login_failures: dict[str, list[float]] = {}

        if persistence is not None:
            self._load_persisted_state(persistence)

    def _load_persisted_state(self, persistence: "OAuthPersistence") -> None:
        state = persistence.load()
        now = time.time()
        for client_id, data in state.get("clients", {}).items():
            try:
                self._clients[client_id] = OAuthClientInformationFull.model_validate(data)
            except Exception:  # noqa: BLE001 -- one bad record must not break the rest
                continue
        for token_value, data in state.get("access_tokens", {}).items():
            try:
                access_token = AccessToken.model_validate(data)
            except Exception:  # noqa: BLE001
                continue
            if access_token.expires_at is None or access_token.expires_at >= now:
                self._access_tokens[token_value] = access_token

    async def _persist(self) -> None:
        """Write-through: called after any mutation to clients/access_tokens."""
        if self._persistence is None:
            return
        async with self._persist_lock:
            now = time.time()
            state = {
                "clients": {
                    cid: c.model_dump(mode="json") for cid, c in self._clients.items()
                },
                "access_tokens": {
                    t: at.model_dump(mode="json")
                    for t, at in self._access_tokens.items()
                    if at.expires_at is None or at.expires_at >= now
                },
            }
            await asyncio.to_thread(self._persistence.save, state)

    # -- Dynamic client registration -----------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info
        await self._persist()

    # -- Authorization: the login-gate diversion -------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        self._purge_expired()
        login_id = secrets.token_urlsafe(32)
        self._pending_logins[login_id] = _PendingLogin(
            client=client,
            params=params,
            expires_at=time.time() + LOGIN_ID_TTL_SECONDS,
        )
        return f"{str(self.base_url).rstrip('/')}/login?login_id={login_id}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._codes.get(authorization_code)
        if code is None or code.client_id != client.client_id:
            return None
        if code.expires_at < time.time():
            self._codes.pop(authorization_code, None)
            return None
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        token = secrets.token_urlsafe(32)
        self._access_tokens[token] = AccessToken(
            token=token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + ACCESS_TOKEN_TTL_SECONDS,
            subject=authorization_code.subject,
        )
        await self._persist()
        return OAuthToken(
            access_token=token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
        )

    # -- No refresh tokens (deliberate; see SPECIFICATION.md §08/§09) ---

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        raise TokenError(
            error="unsupported_grant_type",
            error_description="Refresh tokens are not supported; re-authenticate instead.",
        )

    # -- Token verification / revocation ---------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self._access_tokens.get(token)
        if access_token is None:
            return None
        if access_token.expires_at is not None and access_token.expires_at < time.time():
            self._access_tokens.pop(token, None)
            return None
        return access_token

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self._access_tokens.pop(token.token, None)
        await self._persist()

    # -- The /login route itself (not part of the OAuth SDK's routes) ----

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._pending_logins.items() if v.expires_at < now]
        for k in expired:
            self._pending_logins.pop(k, None)

    def _is_locked_out(self, client_ip: str) -> bool:
        now = time.time()
        attempts = self._login_failures.get(client_ip, [])
        attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SECONDS]
        self._login_failures[client_ip] = attempts
        return len(attempts) >= LOGIN_MAX_ATTEMPTS

    def _record_failure(self, client_ip: str) -> None:
        self._login_failures.setdefault(client_ip, []).append(time.time())

    @staticmethod
    def _login_form(login_id: str, error: str | None = None) -> str:
        error_html = (
            f'<p class="error" role="alert">{html.escape(error)}</p>' if error else ""
        )
        safe_login_id = html.escape(login_id)
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in</title>
<style>
  :root {{
    --bg: #f4f5f7;
    --card-bg: #ffffff;
    --text: #1a1d23;
    --muted: #6b7280;
    --border: #e2e4e9;
    --accent: #4f46e5;
    --accent-hover: #4338ca;
    --error-bg: #fef2f2;
    --error-text: #b91c1c;
    --error-border: #fecaca;
    --shadow: 0 1px 3px rgba(16, 24, 40, 0.06), 0 8px 24px rgba(16, 24, 40, 0.08);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f1115;
      --card-bg: #181b21;
      --text: #f2f3f5;
      --muted: #9aa1ac;
      --border: #2a2e37;
      --accent: #6366f1;
      --accent-hover: #818cf8;
      --error-bg: #2a1518;
      --error-text: #fca5a5;
      --error-border: #5b2228;
      --shadow: 0 1px 3px rgba(0, 0, 0, 0.3), 0 8px 24px rgba(0, 0, 0, 0.4);
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .card {{
    width: 100%;
    max-width: 380px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: var(--shadow);
    padding: 36px 32px;
  }}
  .icon {{
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
  }}
  .icon svg {{ width: 22px; height: 22px; stroke: #fff; }}
  h1 {{
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 4px;
    letter-spacing: -0.01em;
  }}
  .subtitle {{
    font-size: 14px;
    color: var(--muted);
    margin: 0 0 24px;
  }}
  .error {{
    background: var(--error-bg);
    color: var(--error-text);
    border: 1px solid var(--error-border);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    margin: 0 0 20px;
  }}
  label {{
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--muted);
    margin-bottom: 6px;
  }}
  .field {{ margin-bottom: 18px; }}
  input[type="text"],
  input[type="password"] {{
    width: 100%;
    padding: 10px 12px;
    font-size: 15px;
    color: var(--text);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    outline: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }}
  input[type="text"]:focus,
  input[type="password"]:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent);
  }}
  button {{
    width: 100%;
    padding: 11px 0;
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    background: var(--accent);
    border: none;
    border-radius: 8px;
    cursor: pointer;
    margin-top: 6px;
    transition: background 0.15s ease;
  }}
  button:hover {{ background: var(--accent-hover); }}
  button:active {{ transform: translateY(1px); }}
  .footer {{
    margin-top: 24px;
    font-size: 12px;
    color: var(--muted);
    text-align: center;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="icon">
    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="11" width="18" height="10" rx="2"></rect>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
    </svg>
  </div>
  <h1>Sign in</h1>
  <p class="subtitle">Enter your credentials to continue to your coach's MCP server.</p>
  {error_html}
  <form method="post" action="/login">
    <input type="hidden" name="login_id" value="{safe_login_id}">
    <div class="field">
      <label for="username">Username</label>
      <input type="text" id="username" name="username" autocomplete="username" autofocus required>
    </div>
    <div class="field">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" autocomplete="current-password" required>
    </div>
    <button type="submit">Sign in</button>
  </form>
  <p class="footer">This login is private to your own deployment.</p>
</div>
</body>
</html>"""

    async def handle_login(self, request: Request) -> Response:
        self._purge_expired()
        client_ip = request.client.host if request.client else "unknown"

        if request.method == "GET":
            login_id = request.query_params.get("login_id", "")
            if login_id not in self._pending_logins:
                return HTMLResponse("This login link has expired.", status_code=400)
            return HTMLResponse(self._login_form(login_id))

        form = await request.form()
        login_id = str(form.get("login_id", ""))
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        pending = self._pending_logins.get(login_id)
        if pending is None:
            return HTMLResponse("This login link has expired.", status_code=400)

        if self._is_locked_out(client_ip):
            return HTMLResponse("Too many attempts. Try again later.", status_code=429)

        if not (
            secrets.compare_digest(username, self._username)
            and secrets.compare_digest(password, self._password)
        ):
            self._record_failure(client_ip)
            return HTMLResponse(
                self._login_form(login_id, error="Invalid username or password."),
                status_code=401,
            )

        self._pending_logins.pop(login_id, None)
        client, params = pending.client, pending.params

        code_value = secrets.token_urlsafe(32)
        self._codes[code_value] = AuthorizationCode(
            code=code_value,
            scopes=params.scopes or [],
            expires_at=time.time() + AUTH_CODE_TTL_SECONDS,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            subject=self._username,
        )

        redirect_url = self._build_redirect(params, code_value)
        return RedirectResponse(redirect_url, status_code=302)

    @staticmethod
    def _build_redirect(params: AuthorizationParams, code: str) -> str:
        from urllib.parse import urlencode

        query: dict[str, Any] = {"code": code}
        if params.state is not None:
            query["state"] = params.state
        separator = "&" if "?" in str(params.redirect_uri) else "?"
        return f"{params.redirect_uri}{separator}{urlencode(query)}"
