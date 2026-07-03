"""Settlement rail: execute approved verdicts as real testnet USDC transfers.

ClearCrew decides; Verasettle (a non-custodial USDC payout orchestrator)
executes. This client drives Verasettle's sandbox API: one single-item batch
per approved payout (unambiguous mapping, per-item idempotency on the rail
side), polled to settlement, receipt retrieved with the on-chain tx hash.

Testnet honesty: source amounts are benchmark USD figures; on-chain movement
is real USDC on Base Sepolia at an explicitly recorded 1:10,000 scale. Every
settlement event carries both numbers and the scale — the record never claims
more than what moved.

Requires VERASETTLE_API_KEY (and optionally VERASETTLE_BASE_URL) in the
environment. Never needed by the replay UI or the benchmark.
"""
import json
import os
import time
import urllib.error
import urllib.request

SCALE = 10_000  # $1 source = 0.0001 USDC settled, recorded in every event
CHAIN = "BASE-SEPOLIA"
EXPLORER = "https://sepolia.basescan.org/tx/"


class SettlementError(RuntimeError):
    pass


def _base() -> str:
    return os.environ.get("VERASETTLE_BASE_URL", "http://127.0.0.1:8786").rstrip("/")


def _req(method: str, path: str, body: dict | None = None) -> dict:
    key = os.environ.get("VERASETTLE_API_KEY")
    if not key:
        raise SettlementError("VERASETTLE_API_KEY is not set — settlement demo only")
    req = urllib.request.Request(
        _base() + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SettlementError(f"{method} {path} -> {e.code}: {e.read()[:200]!r}") from e
    except urllib.error.URLError as e:
        raise SettlementError(f"{method} {path} unreachable: {e.reason}") from e


def usdc_amount(source_usd: float) -> float:
    return round(source_usd / SCALE, 6)


def settle_payout(source_usd: float, timeout_s: float = 120.0) -> dict:
    """Move usdc_amount(source_usd) of real testnet USDC; block until the rail
    reports SETTLED (or fail loudly). Returns settlement facts for the event."""
    amount = usdc_amount(source_usd)
    created = _req("POST", "/demo/batch", {"amounts": [amount]})
    batch_id = created["batchId"]

    deadline = time.time() + timeout_s
    item = None
    while time.time() < deadline:
        batch = _req("GET", f"/batches/{batch_id}")
        items = batch.get("items", [])
        if items and items[0].get("status") == "SETTLED":
            item = items[0]
            break
        if items and items[0].get("status") == "FAILED":
            raise SettlementError(f"rail reported FAILED for batch {batch_id}")
        time.sleep(5)
    if item is None:
        raise SettlementError(f"batch {batch_id} not settled within {timeout_s}s")

    receipt = _receipt_for(item["id"])
    return {
        "rail": "verasettle-sandbox",
        "verasettle_batch": batch_id,
        "verasettle_item": item["id"],
        "source_amount_usd": source_usd,
        "settled_amount_usdc": amount,
        "scale": f"1:{SCALE} testnet conversion (recorded, not implied)",
        "chain": CHAIN,
        "tx_hash": receipt.get("outcome", {}).get("txHash"),
        "explorer": EXPLORER + receipt.get("outcome", {}).get("txHash", ""),
        "receipt_id": receipt.get("id"),
        "receipt_content_hash": receipt.get("contentHash"),
    }


def _receipt_for(item_id: str) -> dict:
    for r in _req("GET", "/receipts?limit=50").get("receipts", []):
        if r.get("subjectId") == item_id and r.get("kind") == "payout.settled":
            return r
    raise SettlementError(f"no settled receipt found for item {item_id}")
