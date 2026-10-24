"""Composition root: wires OAuth, the upstream intervals.icu tools, and our
own S3-backed state_* tools onto one FastMCP instance.

See SPECIFICATION.md §14 for why there's a second, "misconfigured" app
here: a missing or invalid environment variable must never crash the
process or leave Fly in a silent crash loop. Instead the app always
starts, and if required configuration is missing, every MCP endpoint
instead serves a clear explanation of exactly what to fix -- important for
a non-technical deployer working only from Fly's dashboard, with no logs
they'd know how to read.

This module should stay thin -- it only composes; the OAuth logic lives in
auth.py, upstream integration in upstream.py, S3 tool logic in s3store.py,
and config loading in config.py.
"""

from __future__ import annotations

import argparse
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import SingleUserOAuthProvider
from .config import Settings, load_settings, missing_env_vars
from .oauth_persistence import OAuthPersistence
from .s3store import ReservedNameError, StateConflictError, StateNotFoundError, StateStore
from .upstream import missing_intervals_config, mount_upstream_tools


def build_app(settings: Settings) -> FastMCP:
    """Build the real app, or a clear "not configured" stand-in for it.

    Every required environment variable (ours in config.py, plus
    upstream's intervals.icu credentials) is checked up front. If any are
    missing, none of the real tools are registered at all -- they would
    just fail confusingly against an unconfigured S3 bucket or
    intervals.icu account -- and the server instead exposes exactly one
    tool that explains what's missing.
    """
    missing = missing_env_vars(settings) + missing_intervals_config()
    if missing:
        return build_misconfigured_app(missing)
    return build_configured_app(settings)


def build_misconfigured_app(missing: list[str]) -> FastMCP:
    message = (
        "This intervals-icu-s3-mcp server is not configured yet. "
        f"Missing or invalid environment variable(s): {', '.join(missing)}. "
        "An admin needs to set these as Secrets on the Fly.io dashboard -- "
        "see README.md for what each one means and where to get it. "
        "No tools are available until this is fixed."
    )
    mcp = FastMCP("intervals-icu-s3-mcp", instructions=message)

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "configured": False, "missing": missing})

    @mcp.tool
    def check_configuration() -> dict[str, Any]:
        """Call this first if no other tools seem to work -- explains why."""
        return {"configured": False, "missing": missing, "message": message}

    return mcp


def build_configured_app(settings: Settings) -> FastMCP:
    store = StateStore(
        bucket=settings.bucket_name,  # type: ignore[arg-type]
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url_s3,
        region_name=settings.aws_region,
    )

    # Persists registered OAuth clients + issued access tokens to the same
    # bucket (SPECIFICATION.md §15), so a machine restart doesn't force
    # every connected client to fully re-register and re-login. Loaded
    # once, synchronously, right here at startup.
    persistence = OAuthPersistence(
        client=store.client,
        bucket=store.bucket,
        secret=settings.oauth_state_secret,  # type: ignore[arg-type]
    )
    auth = SingleUserOAuthProvider(
        base_url=settings.public_url,  # type: ignore[arg-type]
        username=settings.oauth_username,  # type: ignore[arg-type]
        password=settings.oauth_password,  # type: ignore[arg-type]
        persistence=persistence,
    )
    mcp = FastMCP("intervals-icu-s3-mcp", auth=auth)

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "configured": True})

    @mcp.custom_route("/login", methods=["GET", "POST"], include_in_schema=False)
    async def login(request: Request):
        return await auth.handle_login(request)

    register_state_tools(mcp, store)

    mount_upstream_tools(mcp)

    return mcp


def register_state_tools(mcp: FastMCP, store: StateStore) -> None:
    """Register the five state_* tools against the given StateStore."""

    @mcp.tool
    def state_create(
        var_name: str, description: str | None = None, content: str | None = None
    ) -> dict[str, Any]:
        """Create a new named value in the trainer's durable memory store.

        Fails with a conflict if var_name already exists and isn't deleted;
        if it was soft-deleted, revives it with the new values. var_name
        may not start with "." -- that's reserved for this server's own
        internal state.
        """
        try:
            return store.create(var_name, description=description, content=content)
        except StateConflictError as exc:
            return {"error": "conflict", "message": str(exc)}
        except ReservedNameError as exc:
            return {"error": "reserved_name", "message": str(exc)}

    @mcp.tool
    def state_get(var_name: str) -> dict[str, Any]:
        """Return the full record (description, content, timestamps) for var_name."""
        try:
            return store.get(var_name)
        except StateNotFoundError:
            return {"error": "not_found", "var_name": var_name}

    @mcp.tool
    def state_update(
        var_name: str, description: str | None = None, content: str | None = None
    ) -> dict[str, Any]:
        """Patch only the fields supplied; omitted fields keep their current value."""
        try:
            return store.update(var_name, description=description, content=content)
        except StateNotFoundError:
            return {"error": "not_found", "var_name": var_name}

    @mcp.tool
    def state_delete(var_name: str) -> dict[str, Any]:
        """Soft-delete var_name. No hard delete is exposed."""
        try:
            return store.delete(var_name)
        except StateNotFoundError:
            return {"error": "not_found", "var_name": var_name}

    @mcp.tool
    def state_list(include_deleted: bool = False) -> list[dict[str, Any]]:
        """List var_name + description for every stored value (never content)."""
        return store.list(include_deleted=include_deleted)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="intervals-icu-s3-mcp server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--transport", default="http")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = load_settings()

    mcp = build_app(settings)
    port = args.port if args.port is not None else settings.port
    mcp.run(transport=args.transport, host=args.host, port=port)


if __name__ == "__main__":
    main()
