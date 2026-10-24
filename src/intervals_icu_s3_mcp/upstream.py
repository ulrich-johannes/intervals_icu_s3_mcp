"""The ONE module allowed to touch the vendored intervals-icu-mcp package.

Per SPECIFICATION.md §03: nothing else in this codebase imports from
``intervals_icu_mcp`` directly. Everything else calls into this module, so
that an upstream refactor (renamed module, changed signature, split tool)
only ever needs fixing here -- and the regression suite in
tests/test_upstream_contract.py and tests/test_upstream_integration.py
exists specifically to catch that kind of change immediately on a
submodule bump, before it reaches `main`.

Registration strategy: mount upstream's already-built FastMCP instance
wholesale, rather than importing individual tool functions. This is the
most update-resilient option -- any tool upstream adds or removes shows up
automatically on the next submodule bump, with zero code changes here.
"""

from __future__ import annotations

from fastmcp import FastMCP


def get_upstream_mcp() -> FastMCP:
    """Return upstream's own FastMCP instance, tools already registered.

    Importing `intervals_icu_mcp.server` registers upstream's tools at
    import time (number of tools depends on INTERVALS_ICU_DELETE_MODE --
    see their CLAUDE.md), but does not require the intervals.icu
    credentials to be valid yet; those are only checked when a tool
    actually calls the intervals.icu API.
    """
    from intervals_icu_mcp.server import mcp as upstream_mcp

    return upstream_mcp


def mount_upstream_tools(mcp: FastMCP) -> None:
    """Mount every upstream intervals.icu tool onto our combined server.

    Our own routes (notably `/health`) are unaffected: FastMCP.mount()
    only composes tools/resources/prompts at the MCP protocol layer, not
    upstream's Starlette `@custom_route` registrations, so there is no
    collision with our own `/health` handler in server.py.
    """
    mcp.mount(get_upstream_mcp())


def missing_intervals_config() -> list[str]:
    """Names of intervals.icu environment variables that are unset or invalid.

    Used by server.py at startup to decide whether to serve the real app
    or the "not configured" one (SPECIFICATION.md §14). Reads upstream's
    own config loader rather than duplicating its env var names here.
    """
    from intervals_icu_mcp.auth import load_config

    config = load_config()
    missing: list[str] = []
    if not config.intervals_icu_api_key or config.intervals_icu_api_key == "your_api_key_here":
        missing.append("INTERVALS_ICU_API_KEY")
    if not config.intervals_icu_athlete_id:
        missing.append("INTERVALS_ICU_ATHLETE_ID")
    return missing
