"""External anchoring for the event log head hash.

The hash chain inside events.jsonl is tamper-evident only if an attacker
cannot rewrite the file. External anchoring proves the head hash existed at
a given time by publishing it to an independent source of truth.

Two providers are built-in:
- TsaAnchor: POST the head hash to an RFC-3161 TSA (free: freetsa.org),
  returns a timestamp token that proves existence before a point in time.
- NoopAnchor: records the anchor event but does nothing externally (default).
"""
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from . import config, events


@dataclass
class AnchorResult:
    provider: str
    head_hash: str
    token: str | None = None
    url: str | None = None


class AnchorProvider(ABC):
    @abstractmethod
    def anchor(self, log_path: str, head_hash: str) -> AnchorResult:
        ...


class TsaAnchor(AnchorProvider):
    """Anchor via RFC-3161 TSA (https://freetsa.org).
    Posts the head hash as a plain-text request and stores the returned
    timestamp token (hex-encoded) in a chain.anchored event.
    """
    TSA_URL: ClassVar[str] = "https://freetsa.org/tsr"

    def anchor(self, log_path: str, head_hash: str) -> AnchorResult:
        data = f"HEAD_HASH={head_hash}".encode()
        req = urllib.request.Request(
            self.TSA_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                token = r.read().hex()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            raise RuntimeError(f"TSA anchoring failed: {exc}") from exc
        return AnchorResult(
            provider="freetsa.org",
            head_hash=head_hash,
            token=token,
            url=self.TSA_URL,
        )


class NoopAnchor(AnchorProvider):
    """Record the intent but don't call any external service."""
    def anchor(self, log_path: str, head_hash: str) -> AnchorResult:
        return AnchorResult(provider="noop", head_hash=head_hash)


def _provider() -> AnchorProvider:
    mode = os.environ.get("CLEARCREW_ANCHOR", "noop")
    if mode == "tsa":
        return TsaAnchor()
    return NoopAnchor()


def anchor_now() -> dict:
    """Anchor the current event log head hash to an external source.
    Returns the emitted chain.anchored event so callers can log or display it.
    """
    head = events._tail_hash(config.EVENT_LOG_PATH)
    prov = _provider()
    result = prov.anchor(config.EVENT_LOG_PATH, head)
    return events.emit("chain.anchored", "log", "anchor", {
        "provider": result.provider,
        "head_hash": result.head_hash,
        "token": result.token,
        "url": result.url,
    })
