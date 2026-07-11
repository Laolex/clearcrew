"""The gated-monolith ablation.

The point of this module is to keep two claims from being confused:

    the GATE keeps the treasury safe   (any architecture can have it)
    the SOCIETY pays the right people  (no gate can do this for you)

The tests below pin both halves — including the uncomfortable one, that a gated
monolith is *safe* and the society's advantage is therefore about judgment, not
protection.
"""
import json

import pytest

from clearcrew import baseline, baseline_gated, config, data, events, policy


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(path))
    events.reset_chain(str(path))
    yield path
    events.reset_chain(str(path))


def _read(path):
    return [json.loads(line) for line in open(path) if line.strip()]


def _run_with(monkeypatch, decisions):
    """Run the gated monolith over a fixed set of pretend model verdicts."""
    monkeypatch.setattr(baseline, "_decide",
                        lambda payouts, balance, floor: {"decisions": decisions})
    batch = [{k: v for k, v in p.items() if k != "_expected"}
             for p in data.make_batch(36)]
    return baseline_gated.run_batch(batch)


def test_gate_stops_a_monolith_overdrawing_the_treasury(log, monkeypatch):
    """The headline ablation: a single agent that approves EVERYTHING still
    cannot breach the reserve floor once the gate is in front of it."""
    batch = data.make_batch(36)
    _run_with(monkeypatch, [{"payout_id": p["id"], "action": "approve"} for p in batch])

    evs = _read(log)
    approved = [e["subject"] for e in evs if e["type"] == "payout.approved"]
    amounts = {p["id"]: p["amount"] for p in batch}
    spent = sum(amounts[pid] for pid in approved)

    assert spent <= policy.CURRENT.headroom          # floor held
    assert policy.CURRENT.balance - spent >= policy.CURRENT.reserve_floor
    assert any(e["type"] == "policy.blocked" for e in evs)


def test_the_gate_does_not_care_who_proposed(log, monkeypatch):
    """A blocked monolith approval is recorded exactly like a blocked agent's —
    attributed, with the rule named. The gate is architecture-independent, and
    that is the whole point of this ablation."""
    batch = data.make_batch(36)
    _run_with(monkeypatch, [{"payout_id": p["id"], "action": "approve"} for p in batch])

    blocked = [e for e in _read(log) if e["type"] == "policy.blocked"]
    assert blocked
    assert all(e["payload"]["proposed_by"] == "monolith" for e in blocked)
    assert all(e["payload"]["rule"] in ("P1", "P2", "P3") for e in blocked)


def test_the_gate_cannot_rescue_a_stranded_payout(log, monkeypatch):
    """The other half of the story, and the society's actual claim.

    The gate is veto-only, so it can refuse a payout that breaks the rules but
    can NEVER pay one that was wrongly refused. A monolith that rejects a clean
    payout still strands it, gate or no gate — only better judgment fixes that.
    """
    batch = data.make_batch(36)
    ruled = policy.evaluate(batch)
    payable = [p for p in batch if ruled[p["id"]]["verdict"] == "approve"]
    victim = payable[0]

    # the monolith wrongly rejects a payout the policy says to approve
    decisions = [{"payout_id": p["id"],
                  "action": "reject" if p["id"] == victim["id"] else "approve"}
                 for p in batch]
    _run_with(monkeypatch, decisions)

    evs = _read(log)
    approved = {e["subject"] for e in evs if e["type"] == "payout.approved"}
    assert victim["id"] not in approved          # still stranded
    # and the gate never even looked at it — there was no approval to refuse
    blocked = {e["subject"] for e in evs if e["type"] == "policy.blocked"}
    assert victim["id"] not in blocked


def test_proposals_are_recorded_so_the_monolith_can_be_graded_too(log, monkeypatch):
    batch = data.make_batch(36)
    result = _run_with(monkeypatch,
                       [{"payout_id": p["id"], "action": "approve"} for p in batch])
    assert len(result["proposals"]) == len(batch)
    assert all(v == "approve" for v in result["proposals"].values())
    proposed = [e for e in _read(log) if e["type"] == "payout.proposed"]
    assert len(proposed) == len(batch)
    assert all(e["actor"] == "monolith" for e in proposed)


def test_chain_verifies(log, monkeypatch):
    batch = data.make_batch(36)
    _run_with(monkeypatch, [{"payout_id": p["id"], "action": "approve"} for p in batch])
    assert events.verify_chain(_read(log))["verified"] is True
