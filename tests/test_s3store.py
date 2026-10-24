import boto3
import pytest
from moto import mock_aws

from intervals_icu_s3_mcp.s3store import StateConflictError, StateNotFoundError, StateStore

BUCKET = "test-bucket"


@pytest.fixture
def store():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield StateStore(bucket=BUCKET, client=client)


def test_create_then_get(store):
    created = store.create("ftp_note", description="FTP trend", content="stable at 250W")
    assert created["var_name"] == "ftp_note"
    assert created["deleted"] is False

    fetched = store.get("ftp_note")
    assert fetched["description"] == "FTP trend"
    assert fetched["content"] == "stable at 250W"


def test_create_conflict_on_existing(store):
    store.create("x", content="1")
    with pytest.raises(StateConflictError):
        store.create("x", content="2")


def test_get_missing_raises_not_found(store):
    with pytest.raises(StateNotFoundError):
        store.get("does-not-exist")


def test_update_patches_only_supplied_fields(store):
    store.create("x", description="d1", content="c1")
    updated = store.update("x", content="c2")
    assert updated["description"] == "d1"
    assert updated["content"] == "c2"


def test_update_missing_raises_not_found(store):
    with pytest.raises(StateNotFoundError):
        store.update("missing", content="c")


def test_delete_is_soft_and_reads_as_not_found(store):
    store.create("x", content="1")
    deleted = store.delete("x")
    assert deleted["deleted"] is True

    with pytest.raises(StateNotFoundError):
        store.get("x")


def test_delete_missing_raises_not_found(store):
    with pytest.raises(StateNotFoundError):
        store.delete("missing")


def test_create_revives_soft_deleted_var(store):
    store.create("x", content="1")
    store.delete("x")
    revived = store.create("x", content="2")
    assert revived["deleted"] is False
    assert revived["content"] == "2"


def test_list_excludes_deleted_by_default(store):
    store.create("a", description="A")
    store.create("b", description="B")
    store.delete("b")

    listed = store.list()
    names = {r["var_name"] for r in listed}
    assert names == {"a"}
    # list never returns content
    assert all("content" not in r for r in listed)


def test_list_include_deleted(store):
    store.create("a", description="A")
    store.create("b", description="B")
    store.delete("b")

    listed = store.list(include_deleted=True)
    names = {r["var_name"] for r in listed}
    assert names == {"a", "b"}
