"""External anchoring: RFC-3161 over the log's head hash.

The network tests are opt-in (CLEARCREW_TSA_TESTS=1) so CI stays hermetic. The
DER encode/parse round-trip runs everywhere — that's where a bug would silently
produce an "anchor" that proves nothing, which is worse than having none.
"""
import hashlib
import json
import os

import pytest

from clearcrew import anchor, config, events

NET = pytest.mark.skipif(
    os.environ.get("CLEARCREW_TSA_TESTS") != "1",
    reason="set CLEARCREW_TSA_TESTS=1 to hit real Time Stamping Authorities",
)


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(path))
    events.reset_chain(str(path))
    yield path
    events.reset_chain(str(path))


def test_request_is_well_formed_der():
    digest = hashlib.sha256(b"x").digest()
    req = anchor.build_request(digest, nonce=12345)
    assert req[0] == 0x30                       # SEQUENCE
    assert anchor._SHA256_ALGID in req          # sha256 AlgorithmIdentifier
    assert digest in req                        # commits to our digest
    _, _, end = anchor._read(req, 0)
    assert end == len(req)                      # lengths are self-consistent


def test_der_reader_handles_long_form_lengths():
    """Real tokens are 4-6 KB, so every length in them is long-form. Getting
    this wrong would only surface against a live TSA — i.e. in production."""
    body = b"\x00" * 400
    enc = anchor._enc(0x04, body)
    tag, content, end = anchor._read(enc, 0)
    assert tag == 0x04 and content == body and end == len(enc)


def test_verify_rejects_garbage():
    assert anchor.verify_token("not-hex", "a" * 64)["valid"] is False
    assert anchor.verify_token("30030201", "a" * 64)["valid"] is False


def test_noop_anchor_does_not_claim_a_token():
    """An offline run must not look anchored. Silence beats a false proof."""
    result = anchor.NoopAnchor().anchor("log", "a" * 64)
    assert result.token is None and result.provider == "noop"


def test_anchor_now_commits_to_the_head_before_itself(log, monkeypatch):
    monkeypatch.delenv("CLEARCREW_ANCHOR", raising=False)
    events.emit("batch.received", "batch", "orchestrator", {"count": 1})
    ev = anchor.anchor_now()
    assert ev["type"] == "chain.anchored"
    assert ev["actor"] == "anchor"
    assert ev["payload"]["provider"] == "noop"
    # the anchor commits to the head BEFORE itself — exactly the prefix a real
    # token would cover
    prior = [json.loads(line) for line in open(log) if line.strip()][-2]
    assert ev["payload"]["head_hash"] == prior["event_hash"]


def test_anchor_on_an_empty_log_anchors_genesis(log, monkeypatch):
    monkeypatch.delenv("CLEARCREW_ANCHOR", raising=False)
    ev = anchor.anchor_now()
    assert ev["payload"]["head_hash"] == events.GENESIS


def test_anchor_failure_is_recorded_as_failure(log, monkeypatch):
    class Broken(anchor.AnchorProvider):
        def anchor(self, log_path, head_hash):
            raise RuntimeError("all TSAs failed: nope")

    monkeypatch.setattr(anchor, "_provider", lambda: Broken())
    ev = anchor.anchor_now()
    assert ev["type"] == "chain.anchor_failed"      # never a false success
    assert "nope" in ev["payload"]["error"]


@NET
def test_real_tsa_signs_our_head_hash():
    head = hashlib.sha256(b"clearcrew-test").hexdigest()
    result = anchor.TsaAnchor().anchor("log", head)
    assert result.token and result.gen_time
    v = anchor.verify_token(result.token, head)
    assert v["valid"] is True
    assert v["committed_to"] == head


@NET
def test_real_token_does_not_verify_against_a_tampered_hash():
    """The whole point: a rewritten log cannot reuse its old anchor."""
    head = hashlib.sha256(b"clearcrew-test").hexdigest()
    result = anchor.TsaAnchor().anchor("log", head)
    tampered = hashlib.sha256(b"clearcrew-test-EDITED").hexdigest()
    v = anchor.verify_token(result.token, tampered)
    assert v["valid"] is False
    assert v["committed_to"] == head           # it still names the true hash
