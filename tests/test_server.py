"""Unit tests for the configured/misconfigured branching in server.py."""

import boto3
import pytest
from fastmcp import Client
from moto import mock_aws

from intervals_icu_s3_mcp.config import Settings
from intervals_icu_s3_mcp.server import build_app

BUCKET = "server-test-bucket"


@pytest.fixture(autouse=True)
def _intervals_icu_env(monkeypatch):
    # Keep upstream's own config happy by default; individual tests remove
    # these to exercise the misconfigured path.
    monkeypatch.setenv("INTERVALS_ICU_API_KEY", "test-key")
    monkeypatch.setenv("INTERVALS_ICU_ATHLETE_ID", "i123456")


def _settings(**overrides):
    defaults = dict(
        public_url="https://example.fly.dev",
        oauth_username="alice",
        oauth_password="s3cr3t",
        bucket_name=BUCKET,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_region="us-east-1",
    )
    defaults.update(overrides)
    return Settings(**defaults)


async def test_fully_configured_exposes_real_tools():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        mcp = build_app(_settings())
        async with Client(mcp) as client:
            names = {t.name for t in await client.list_tools()}
            assert "state_create" in names
            assert "icu_get_recent_activities" in names
            assert "check_configuration" not in names


async def test_missing_our_env_var_serves_check_configuration_only():
    mcp = build_app(_settings(oauth_password=None))
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
        assert names == {"check_configuration"}

        result = await client.call_tool("check_configuration", {})
        assert result.data["configured"] is False
        assert "OAUTH_PASSWORD" in result.data["missing"]


async def test_missing_intervals_icu_env_var_serves_check_configuration_only(monkeypatch):
    monkeypatch.delenv("INTERVALS_ICU_API_KEY", raising=False)
    mcp = build_app(_settings())
    async with Client(mcp) as client:
        result = await client.call_tool("check_configuration", {})
        assert "INTERVALS_ICU_API_KEY" in result.data["missing"]


def test_misconfigured_health_route_reports_missing():
    from starlette.testclient import TestClient

    mcp = build_app(_settings(bucket_name=None))
    with TestClient(mcp.http_app()) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert "BUCKET_NAME" in body["missing"]
