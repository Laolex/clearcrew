"""End-to-end: the society decides, then its verdicts move real money.

Runs a 6-payout batch through the full agent society (live Qwen calls), then
executes every APPROVED payout as a real testnet USDC transfer through the
Verasettle sandbox rail. Every settlement is recorded in the same hash-chained
event log as the decisions that caused it: requested -> confirmed (with the
on-chain tx hash and rail receipt) -> payout.settled. Failures are recorded
too (settlement.failed) — the trail says what happened, not what we hoped.

    cd src && python -m clearcrew.settle_demo
"""
import os
import time

from . import config, data, events, orchestrator, settlement


def run() -> None:
    batch = data.make_batch(6)
    print(f"batch of {len(batch)}; society deciding (live model calls)...")
    orchestrator.run_batch([{k: v for k, v in p.items() if k != "_expected"} for p in batch])

    state = events.fold_state()
    approved = [p for p in batch if state.get(p["id"], {}).get("status") == "approved"]
    print(f"approved: {len(approved)} / {len(batch)} — settling via Verasettle rail")

    for p in approved:
        events.emit("settlement.requested", p["id"], "orchestrator", {
            "rail": "verasettle-sandbox",
            "source_amount_usd": p["amount"],
            "settled_amount_usdc": settlement.usdc_amount(p["amount"]),
            "scale": f"1:{settlement.SCALE} testnet conversion",
            "chain": settlement.CHAIN,
        })
        try:
            facts = settlement.settle_payout(p["amount"])
            events.emit("settlement.confirmed", p["id"], "verasettle", facts)
            events.emit("payout.settled", p["id"], "orchestrator",
                        {"tx_hash": facts["tx_hash"], "chain": facts["chain"]})
            print(f"  {p['id']} ${p['amount']:.0f} -> {facts['settled_amount_usdc']} USDC "
                  f"tx {facts['tx_hash']}")
        except settlement.SettlementError as e:
            events.emit("settlement.failed", p["id"], "verasettle", {"error": str(e)})
            print(f"  {p['id']} settlement FAILED: {e}")

    chain = events.verify_chain(events.read_all())
    print(f"chain: hashed={chain['hashed']} verified={chain['verified']} events={chain['events']}")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    os.makedirs("runs", exist_ok=True)
    dest = f"runs/events-{stamp}-settled-n{len(batch)}.jsonl"
    events.export_jsonl(dest)
    print(f"run archived: {dest}")


if __name__ == "__main__":
    run()
