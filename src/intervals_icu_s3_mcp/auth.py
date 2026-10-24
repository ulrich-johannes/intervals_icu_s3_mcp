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
  tokens) lives in plain in-process dicts -- there is no database or file
  backing it, which is why the deployment is pinned to one machine
  (SPECIFICATION.md §02/§08).
"""

from __future__ import annotations

import html
import secrets
import time
from dataclasses import dataclass
from typing import Any

from fastmcp.server.auth import OAuthProvider
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthToken,
    RefreshToken,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

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

    def __init__(self, *, base_url: str, username: str, password: str) -> None:
        super().__init__(base_url=base_url)
        self._username = username
        self._password = password

        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending_logins: dict[str, _PendingLogin] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}

        # ip -> list of failure timestamps, for the brute-force guard.
        self._login_failures: dict[str, list[float]] = {}

    # -- Dynamic client registration -----------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

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
        error_html = f'<p style="color:red">{html.escape(error)}</p>' if error else ""
        safe_login_id = html.escape(login_id)
        return f"""<!doctype html>
<html><body>
<h1>Sign in</h1>
{error_html}
<form method="post" action="/login">
  <input type="hidden" name="login_id" value="{safe_login_id}">
  <label>Username <input type="text" name="username" autofocus></label><br>
  <label>Password <input type="password" name="password"></label><br>
  <button type="submit">Sign in</button>
</form>
</body></html>"""

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
