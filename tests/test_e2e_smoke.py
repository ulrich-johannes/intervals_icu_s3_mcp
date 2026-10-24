"""End-to-end smoke test for the composed app (SPECIFICATION.md §04).

Builds the real combined server (OAuth + mounted upstream tools + S3
state_* tools) via build_app(), then drives it with FastMCP's own
in-process Client to call one representative upstream tool (list only --
actually invoking it would need real intervals.icu credentials, which this
test deliberately does not have) and one state_* tool end to end against a
mocked S3 bucket. This is the one test that would catch "upstream changed
something and our mount silently stopped exposing tools."

The OAuth HTTP dance itself (register/authorize/login/token) is already
covered at the unit level in test_auth.py; FastMCP's in-process Client
transport talks to the server object directly and does not re-exercise
that HTTP layer, which is intentional -- see "Not in scope" in
SPECIFICATION.md §04.
"""

import boto3
import pytest
from fastmcp import Client
from moto import mock_aws

from intervals_icu_s3_mcp.config import Settings
from intervals_icu_s3_mcp.server import build_app

BUCKET = "e2e-test-bucket"


@pytest.fixture
def settings():
    return Settings(
        public_url="https://example.fly.dev",
        oauth_username="alice",
        oauth_password="s3cr3t",
        bucket_name=BUCKET,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_region="us-east-1",
    )


async def test_combined_app_exposes_upstream_and_state_tools(settings):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        mcp = build_app(settings)

        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}

            assert "icu_get_recent_activities" in names  # representative upstream tool
            assert {
                "state_create",
                "state_get",
                "state_update",
                "state_delete",
                "state_list",
            } <= names

            created = await client.call_tool(
                "state_create",
                {"var_name": "e2e_note", "description": "smoke", "content": "hello"},
            )
            assert created.data["var_name"] == "e2e_note"

            fetched = await client.call_tool("state_get", {"var_name": "e2e_note"})
            assert fetched.data["content"] == "hello"
