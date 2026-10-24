"""S3/Tigris-backed implementation of the five state_* tools.

Mirrors datastore-mcp's mcp_state table semantics (see SPECIFICATION.md §06),
one JSON object per var_name under the `state/` prefix. Soft delete only --
state_delete never issues DeleteObject.

Known trade-off (documented in the spec): S3 has no row locks or
transactions, so the create-if-absent check below is a read-then-write, not
atomic. Acceptable for a single-user, low-concurrency use case.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

PREFIX = "state/"


class StateNotFoundError(KeyError):
    """Raised when var_name does not exist, or exists but is soft-deleted."""


class StateConflictError(ValueError):
    """Raised by create() when var_name already exists and is not deleted."""


@dataclass
class StateRecord:
    var_name: str
    description: str | None
    content: str | None
    created: str
    last_updated: str
    deleted: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(var_name: str) -> str:
    return f"{PREFIX}{var_name}.json"


class StateStore:
    """boto3-backed store implementing create/get/update/delete/list."""

    def __init__(self, bucket: str, client: Any | None = None, **client_kwargs: Any) -> None:
        self.bucket = bucket
        self.client = client if client is not None else boto3.client("s3", **client_kwargs)

    def _get_raw(self, var_name: str) -> StateRecord | None:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=_key(var_name))
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "404"):
                return None
            raise
        body = json.loads(resp["Body"].read())
        return StateRecord(**body)

    def _put_raw(self, record: StateRecord) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=_key(record.var_name),
            Body=json.dumps(record.to_dict()).encode("utf-8"),
            ContentType="application/json",
        )

    def create(
        self, var_name: str, description: str | None = None, content: str | None = None
    ) -> dict[str, Any]:
        existing = self._get_raw(var_name)
        now = _now()
        if existing is not None and not existing.deleted:
            raise StateConflictError(f"var_name already exists: {var_name}")
        record = StateRecord(
            var_name=var_name,
            description=description,
            content=content,
            created=now,
            last_updated=now,
            deleted=False,
        )
        self._put_raw(record)
        return record.to_dict()

    def get(self, var_name: str) -> dict[str, Any]:
        record = self._get_raw(var_name)
        if record is None or record.deleted:
            raise StateNotFoundError(var_name)
        return record.to_dict()

    def update(
        self, var_name: str, description: str | None = None, content: str | None = None
    ) -> dict[str, Any]:
        record = self._get_raw(var_name)
        if record is None or record.deleted:
            raise StateNotFoundError(var_name)
        if description is not None:
            record.description = description
        if content is not None:
            record.content = content
        record.last_updated = _now()
        self._put_raw(record)
        return record.to_dict()

    def delete(self, var_name: str) -> dict[str, Any]:
        record = self._get_raw(var_name)
        if record is None or record.deleted:
            raise StateNotFoundError(var_name)
        record.deleted = True
        record.last_updated = _now()
        self._put_raw(record)
        return record.to_dict()

    def list(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=PREFIX):
            for obj in page.get("Contents", []):
                var_name = obj["Key"][len(PREFIX) : -len(".json")]
                record = self._get_raw(var_name)
                if record is None:
                    continue
                if record.deleted and not include_deleted:
                    continue
                results.append({"var_name": record.var_name, "description": record.description})
        return results
