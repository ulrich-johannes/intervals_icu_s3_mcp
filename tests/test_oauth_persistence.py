import boto3
import pytest
from moto import mock_aws

from intervals_icu_s3_mcp.oauth_persistence import EMPTY_STATE, OAuthPersistence

BUCKET = "oauth-persistence-test-bucket"


@pytest.fixture
def client():
    with mock_aws():
        c = boto3.client("s3", region_name="us-east-1")
        c.create_bucket(Bucket=BUCKET)
        yield c


def test_load_returns_empty_state_when_nothing_saved_yet(client):
    persistence = OAuthPersistence(client=client, bucket=BUCKET, secret="s3cr3t")
    assert persistence.load() == EMPTY_STATE


def test_save_then_load_roundtrips(client):
    persistence = OAuthPersistence(client=client, bucket=BUCKET, secret="s3cr3t")
    state = {"clients": {"c1": {"client_id": "c1"}}, "access_tokens": {"tok": {"token": "tok"}}}
    persistence.save(state)
    assert persistence.load() == state


def test_wrong_secret_cannot_decrypt_and_degrades_to_empty(client):
    OAuthPersistence(client=client, bucket=BUCKET, secret="right-secret").save(
        {"clients": {"c1": {}}, "access_tokens": {}}
    )
    reader = OAuthPersistence(client=client, bucket=BUCKET, secret="wrong-secret")
    assert reader.load() == EMPTY_STATE


def test_corrupted_object_degrades_to_empty(client):
    client.put_object(Bucket=BUCKET, Key="state/.oauth.json", Body=b"not encrypted at all")
    persistence = OAuthPersistence(client=client, bucket=BUCKET, secret="s3cr3t")
    assert persistence.load() == EMPTY_STATE


def test_data_is_actually_encrypted_at_rest(client):
    persistence = OAuthPersistence(client=client, bucket=BUCKET, secret="s3cr3t")
    persistence.save({"clients": {}, "access_tokens": {"super-secret-token": {}}})
    raw = client.get_object(Bucket=BUCKET, Key="state/.oauth.json")["Body"].read()
    assert b"super-secret-token" not in raw
