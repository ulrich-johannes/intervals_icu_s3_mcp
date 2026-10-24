"""Integration tests for our upstream.py abstraction layer (SPECIFICATION.md §04).

Asserts mounting works through OUR wrapper and that nothing we add
(state_* tools, /health) collides with what upstream brings in.
"""

from fastmcp import FastMCP

from intervals_icu_s3_mcp.upstream import missing_intervals_config, mount_upstream_tools


async def test_mount_upstream_tools_onto_fresh_server():
    mcp = FastMCP("test-combined")
    mount_upstream_tools(mcp)
    tools = await mcp.list_tools()
    assert len(tools) > 0
    assert any(t.name == "icu_get_recent_activities" for t in tools)


async def test_no_collision_with_state_tools():
    mcp = FastMCP("test-combined")

    @mcp.tool
    def state_create(var_name: str) -> dict:
        return {"var_name": var_name}

    mount_upstream_tools(mcp)
    tools = await mcp.list_tools()
    names = [t.name for t in tools]
    assert names.count("state_create") == 1
    assert len(names) == len(set(names))


def test_missing_intervals_config_reports_both_when_unset(monkeypatch):
    monkeypatch.delenv("INTERVALS_ICU_API_KEY", raising=False)
    monkeypatch.delenv("INTERVALS_ICU_ATHLETE_ID", raising=False)
    assert missing_intervals_config() == ["INTERVALS_ICU_API_KEY", "INTERVALS_ICU_ATHLETE_ID"]


def test_missing_intervals_config_empty_when_set(monkeypatch):
    monkeypatch.setenv("INTERVALS_ICU_API_KEY", "real-key")
    monkeypatch.setenv("INTERVALS_ICU_ATHLETE_ID", "i123456")
    assert missing_intervals_config() == []


def test_missing_intervals_config_rejects_placeholder_key(monkeypatch):
    monkeypatch.setenv("INTERVALS_ICU_API_KEY", "your_api_key_here")
    monkeypatch.setenv("INTERVALS_ICU_ATHLETE_ID", "i123456")
    assert missing_intervals_config() == ["INTERVALS_ICU_API_KEY"]
