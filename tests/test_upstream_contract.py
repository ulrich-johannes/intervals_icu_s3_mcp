"""Contract tests against the vendored intervals-icu-mcp package itself.

Per SPECIFICATION.md §04: these assert the shape we actually depend on
still holds, so a submodule bump that silently changes it fails CI instead
of surfacing at runtime. Deliberately narrow -- we check *our* contract,
not upstream's own correctness.
"""

import pytest

from intervals_icu_s3_mcp.upstream import get_upstream_mcp

# A representative subset of tool names we know the trainer skill relies on.
# If upstream renames/removes any of these, this test fails loudly.
EXPECTED_TOOL_NAMES = {
    "icu_get_recent_activities",
    "icu_get_activity_details",
    "icu_get_athlete_profile",
    "icu_get_fitness_summary",
}


@pytest.fixture
def upstream_mcp():
    return get_upstream_mcp()


async def test_upstream_exposes_a_fastmcp_instance(upstream_mcp):
    tools = await upstream_mcp.list_tools()
    assert len(tools) > 0


async def test_expected_tool_names_still_present(upstream_mcp):
    tools = await upstream_mcp.list_tools()
    names = {t.name for t in tools}
    missing = EXPECTED_TOOL_NAMES - names
    assert not missing, f"upstream no longer exposes: {missing}"


async def test_no_duplicate_tool_names(upstream_mcp):
    tools = await upstream_mcp.list_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names))
