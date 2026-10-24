"""Durable OAuth state (SPECIFICATION.md §15).

Persists registered OAuth clients and issued access tokens to the same S3
bucket the trainer's memory lives in, at the reserved key
`state/.oauth.json` -- so a machine restart doesn't force every connected
client to fully re-register and re-login, which is what happens when this
state lives only in process memory (see auth.py's module docstring and
SPECIFICATION.md §08).

Deliberately NOT persisted: pending logins and authorization codes. Both
are single-use and short-lived (10 minutes / 5 minutes), so persisting
them buys nothing worth the complexity -- a restart in that narrow window
just means redoing that one login attempt.

The blob is encrypted with OAUTH_STATE_SECRET before it's written, since
it contains live bearer tokens: without this, the same S3 credentials
that let someone read a trainer's notes would also hand them a working
session.

Every failure mode here degrades gracefully rather than raising: a
missing file, a corrupted file, or an unreachable bucket all just mean
"start fresh" on load, and "skip this write" on save -- persistence is a
convenience on top of the in-memory state that remains the source of
truth for the lifetime of the process, never a hard dependency of it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

from botocore.exceptions import ClientError
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

OAUTH_STATE_KEY = "state/.oauth.json"

EMPTY_STATE: dict[str, Any] = {"clients": {}, "access_tokens": {}}


def _derive_fernet_key(secret: str) -> bytes:
    """Turns an arbitrary deployer-chosen secret into a valid Fernet key."""
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())


class OAuthPersistence:
    """Loads/saves the clients + access_tokens dicts to S3, encrypted."""

    def __init__(self, client: Any, bucket: str, secret: str) -> None:
        self._client = client
        self._bucket = bucket
        self._fernet = Fernet(_derive_fernet_key(secret))

    def load(self) -> dict[str, Any]:
        """Returns {"clients": {...}, "access_tokens": {...}}, or empty on any problem."""
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=OAUTH_STATE_KEY)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code not in ("NoSuchKey", "404"):
                logger.warning("Could not load persisted OAuth state, starting fresh: %s", exc)
            return dict(EMPTY_STATE)
        except Exception as exc:  # noqa: BLE001 -- any failure degrades to fresh state
            logger.warning("Could not load persisted OAuth state, starting fresh: %s", exc)
            return dict(EMPTY_STATE)

        try:
            decrypted = self._fernet.decrypt(resp["Body"].read())
            state = json.loads(decrypted)
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Persisted OAuth state unreadable, starting fresh: %s", exc)
            return dict(EMPTY_STATE)

        state.setdefault("clients", {})
        state.setdefault("access_tokens", {})
        return state

    def save(self, state: dict[str, Any]) -> None:
        """Best-effort write. Never raises -- a failed save just means the
        next restart falls back to the previously-saved (or empty) state."""
        try:
            encrypted = self._fernet.encrypt(json.dumps(state).encode("utf-8"))
            self._client.put_object(
                Bucket=self._bucket,
                Key=OAUTH_STATE_KEY,
                Body=encrypted,
                ContentType="application/octet-stream",
            )
        except Exception as exc:  # noqa: BLE001 -- persistence is best-effort
            logger.warning("Could not persist OAuth state: %s", exc)
