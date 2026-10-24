"""Composition root: wires OAuth, the upstream intervals.icu tools, and our
own S3-backed state_* tools onto one FastMCP instance.

See SPECIFICATION.md for the overall design. This module should stay thin --
it only composes; the OAuth logic lives in auth.py, upstream integration in
upstream.py, S3 tool logic in s3store.py, and config loading in config.py.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import SingleUserOAuthProvider
from .config import MissingConfigError, Settings, load_settings
from .s3store import StateConflictError, StateNotFoundError, StateStore
from .upstream import mount_upstream_tools


def build_app(settings: Settings) -> FastMCP:
    auth = SingleUserOAuthProvider(
        base_url=settings.public_url,
        username=settings.oauth_username,
        password=settings.oauth_password,
    )
    mcp = FastMCP("intervals-icu-s3-mcp", auth=auth)

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/login", methods=["GET", "POST"], include_in_schema=False)
    async def login(request: Request):
        return await auth.handle_login(request)

    store = StateStore(
        bucket=settings.bucket_name,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url_s3,
        region_name=settings.aws_region,
    )
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
        if it was soft-deleted, revives it with the new values.
        """
        try:
            return store.create(var_name, description=description, content=content)
        except StateConflictError as exc:
            return {"error": "conflict", "message": str(exc)}

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
    try:
        settings = load_settings()
    except MissingConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    mcp = build_app(settings)
    port = args.port if args.port is not None else settings.port
    mcp.run(transport=args.transport, host=args.host, port=port)


if __name__ == "__main__":
    main()
