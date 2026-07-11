"""External anchoring for the event log head hash.

The hash chain in the event log is tamper-*evident*, not tamper-*proof*: it is
computed by the same process that writes the file, so anyone who can write the
file can edit an event, recompute every hash after it, and the chain will
verify clean. Detecting that requires a copy of the head hash held somewhere
the writer cannot reach.

That is all an anchor is. It does not need a blockchain. RFC-3161 gives it to
us for free: a Time Stamping Authority signs `(our hash, its clock)` with its
own key, and the resulting token proves the hash existed at that time. To forge
it you would have to forge the TSA's signature.

What this buys, precisely:
  - Events committed BEFORE an anchor cannot be rewritten without detection —
    the recomputed head would no longer match the anchored one.
  - Events committed AFTER the latest anchor are unprotected. The tamper window
    is the anchor interval; we anchor at the end of every batch.
  - It proves the log's state at a time. It does not prove the log is *honest*
    about the world — only that it has not been edited since.

Verification here checks that the token is granted and that it commits to our
hash. It deliberately does NOT verify the TSA's CMS signature: that needs the
TSA's certificate chain, and leaving it to a third party means nobody has to
trust our code for the part that matters:

    openssl ts -verify -in token.tsr -digest <head_hash> -CAfile tsa-ca.pem

Why hand-roll the DER at all? `rfc3161ng` on PyPI does all of this properly and
also verifies the CMS signature in-process. We carry the ~90 lines below to keep
the event-log core stdlib-only and liftable as a single file — that is the only
reason, and it is a preference, not a gap in the ecosystem. If you want in-process
signature verification, use rfc3161ng; we deliberately leave that check to openssl.
"""
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from . import config, events

# AlgorithmIdentifier for SHA-256, DER-encoded (RFC 5754)
_SHA256_ALGID = bytes.fromhex("300d06096086480165030402010500")
_OID_TSTINFO = bytes.fromhex("2a864886f70d0109100104")   # 1.2.840.113549.1.9.16.1.4


# ── minimal DER ─────────────────────────────────────────────────────────────
# Only what RFC-3161 needs. A trust component does not get to grep its own
# proofs for a byte pattern and call that verification.

def _enc(tag: int, body: bytes) -> bytes:
    if len(body) < 0x80:
        return bytes([tag, len(body)]) + body
    ln = len(body).to_bytes((len(body).bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(ln)]) + ln + body


def _read(buf: bytes, i: int) -> tuple[int, bytes, int]:
    """Read one TLV at offset i -> (tag, content, next_offset)."""
    tag = buf[i]
    n = buf[i + 1]
    i += 2
    if n & 0x80:
        k = n & 0x7F
        n = int.from_bytes(buf[i:i + k], "big")
        i += k
    return tag, buf[i:i + n], i + n


def _children(content: bytes) -> list[tuple[int, bytes]]:
    out, i = [], 0
    while i < len(content):
        tag, body, i = _read(content, i)
        out.append((tag, body))
    return out


def _find(content: bytes, tag: int, nth: int = 0) -> bytes | None:
    hits = [b for t, b in _children(content) if t == tag]
    return hits[nth] if len(hits) > nth else None


def build_request(digest: bytes, nonce: int | None = None) -> bytes:
    """TimeStampReq: version 1, our SHA-256 imprint, certReq TRUE."""
    imprint = _enc(0x30, _SHA256_ALGID + _enc(0x04, digest))
    body = _enc(0x02, b"\x01") + imprint
    if nonce is not None:
        nb = nonce.to_bytes((nonce.bit_length() + 8) // 8 or 1, "big")
        body += _enc(0x02, nb)
    body += _enc(0x01, b"\xff")          # certReq: return the signing cert
    return _enc(0x30, body)


def parse_response(der: bytes) -> dict:
    """Walk TimeStampResp down to TSTInfo and read what the token commits to.

    TimeStampResp ::= SEQ { PKIStatusInfo, ContentInfo }
      ContentInfo ::= SEQ { OID signedData, [0] SignedData }
        SignedData ::= SEQ { ver, SET digestAlgs, EncapsulatedContentInfo, ... }
          EncapContentInfo ::= SEQ { OID id-ct-TSTInfo, [0] OCTET STRING TSTInfo }
            TSTInfo ::= SEQ { ver, policy, MessageImprint, serial, genTime, ... }
    """
    _, resp, _ = _read(der, 0)
    kids = _children(resp)
    seqs = [b for t, b in kids if t == 0x30]

    # PKIStatus 0 = granted, 1 = granted with mods; anything else is a refusal
    status_int = _find(seqs[0], 0x02) if seqs else None
    granted = status_int is not None and int.from_bytes(status_int, "big") in (0, 1)
    empty = {"granted": False, "imprint": None, "gen_time": None, "serial": None}
    if not granted or len(seqs) < 2:
        return empty

    signed_data = _find(_find(seqs[1], 0xA0) or b"", 0x30)
    if signed_data is None:
        raise ValueError("no SignedData in timestamp token")

    encap = next((b for t, b in _children(signed_data)
                  if t == 0x30 and _OID_TSTINFO in b), None)
    if encap is None:
        raise ValueError("no TSTInfo content type in token")

    tst_octets = _find(_find(encap, 0xA0) or b"", 0x04)
    if tst_octets is None:
        raise ValueError("no TSTInfo eContent in token")

    _, tst, _ = _read(tst_octets, 0)          # the TSTInfo SEQUENCE itself
    kids = _children(tst)

    imprint_seq = next((b for t, b in kids if t == 0x30 and _SHA256_ALGID in b), None)
    imprint = _find(imprint_seq or b"", 0x04)
    gen_time = next((b for t, b in kids if t == 0x18), None)
    # TSTInfo has two INTEGERs: version (always 1) first, then serialNumber.
    # Taking the first one silently reports every token's serial as 1 —
    # openssl caught exactly that.
    ints = [b for t, b in kids if t == 0x02]
    serial = ints[1] if len(ints) > 1 else None

    return {
        "granted": True,
        "imprint": imprint.hex() if imprint else None,
        "serial": int.from_bytes(serial, "big") if serial else None,
        "gen_time": gen_time.decode() if gen_time else None,
    }


def verify_token(token_hex: str, head_hash: str) -> dict:
    """Does this token actually commit to this head hash?

    Scope, stated plainly: this proves the TSA signed OUR hash and not somebody
    else's. It does not check the TSA's signature — the module docstring has the
    openssl command that does, and that check should not run on our machine.
    """
    try:
        info = parse_response(bytes.fromhex(token_hex))
    except (ValueError, IndexError) as exc:
        return {"valid": False, "reason": f"unparseable token: {exc}"}
    if not info["granted"]:
        return {"valid": False, "reason": "TSA did not grant the timestamp"}
    if info["imprint"] != head_hash:
        return {"valid": False, "reason": "token commits to a different hash",
                "committed_to": info["imprint"], "expected": head_hash}
    return {"valid": True, "gen_time": info["gen_time"], "serial": info["serial"],
            "committed_to": info["imprint"]}


# ── providers ───────────────────────────────────────────────────────────────

@dataclass
class AnchorResult:
    provider: str
    head_hash: str
    token: str | None = None
    url: str | None = None
    gen_time: str | None = None
    serial: int | None = None


class AnchorProvider(ABC):
    @abstractmethod
    def anchor(self, log_path: str, head_hash: str) -> AnchorResult:
        ...


class TsaAnchor(AnchorProvider):
    """RFC-3161 timestamp over the log's head hash.

    Three independent authorities, tried in order: an anchor with a single
    point of failure is a single point of trust, which is the thing we are
    trying to remove.
    """
    TSA_URLS: ClassVar[tuple[str, ...]] = (
        "https://freetsa.org/tsr",
        "http://timestamp.digicert.com",
        "http://timestamp.sectigo.com",
    )

    def anchor(self, log_path: str, head_hash: str) -> AnchorResult:
        body = build_request(bytes.fromhex(head_hash),
                             int.from_bytes(os.urandom(8), "big"))
        errors = []
        for url in self.TSA_URLS:
            try:
                req = urllib.request.Request(
                    url, data=body,
                    headers={"Content-Type": "application/timestamp-query"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    token = r.read()
                info = parse_response(token)
                if not info["granted"]:
                    errors.append(f"{url}: not granted")
                    continue
                # never accept a token that commits to something other than us
                if info["imprint"] != head_hash:
                    errors.append(f"{url}: token commits to {info['imprint']}")
                    continue
                return AnchorResult(provider=url, head_hash=head_hash,
                                    token=token.hex(), url=url,
                                    gen_time=info["gen_time"], serial=info["serial"])
            except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                    ValueError, IndexError) as exc:
                errors.append(f"{url}: {exc}")
        raise RuntimeError("all TSAs failed: " + "; ".join(errors))


class NoopAnchor(AnchorProvider):
    """Record the intent, call nothing. The default — an offline run must never
    silently claim an anchor it did not obtain."""
    def anchor(self, log_path: str, head_hash: str) -> AnchorResult:
        return AnchorResult(provider="noop", head_hash=head_hash)


def _provider() -> AnchorProvider:
    return TsaAnchor() if os.environ.get("CLEARCREW_ANCHOR") == "tsa" else NoopAnchor()


def anchor_now() -> dict:
    """Anchor the log's current head hash externally, and record the outcome.

    The `chain.anchored` event is itself appended to the chain, so it commits to
    the prefix that preceded it — exactly what the token covers. A failed anchor
    is recorded as a failure and never as a success.
    """
    head = events.tail_hash(config.EVENT_LOG_PATH)
    try:
        result = _provider().anchor(config.EVENT_LOG_PATH, head)
    except RuntimeError as exc:
        return events.emit("chain.anchor_failed", "log", "anchor",
                           {"head_hash": head, "error": str(exc)})
    return events.emit("chain.anchored", "log", "anchor", {
        "provider": result.provider,
        "head_hash": result.head_hash,
        "token": result.token,
        "url": result.url,
        "tsa_time": result.gen_time,
        "serial": result.serial,
    })
