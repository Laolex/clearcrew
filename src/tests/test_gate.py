"""The policy gate: agents propose, policy promotes.

The property under test is an invariant, not a score: no run may record an
approval the deterministic policy forbids — however confidently an agent
proposed it. And the gate must never do the opposite, or the agents are
decorative and the benchmark is a tautology.
"""
import json

import pytest

from clearcrew import config, events, orchestrator, policy


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(path))
    events.reset_chain(str(path))
    yield path
    events.reset_chain(str(path))


def _read(path):
    return events.read_all(str(path))


def _by_type(evs, t):
    return [e for e in evs if e["type"] == t]


SANCTIONED = {"id": "p1", "amount": 1_000.0, "currency": "USD", "from_country": "US",
              "to_country": "IR", "recipient_age_days": 400, "memo": "x"}
CLEAN = {"id": "p2", "amount": 1_000.0, "currency": "USD", "from_country": "US",
         "to_country": "NG", "recipient_age_days": 400, "memo": "x"}
NEW_BIG = {"id": "p3", "amount": 15_000.0, "currency": "USD", "from_country": "US",
           "to_country": "NG", "recipient_age_days": 2, "memo": "x"}


def test_blocks_an_approval_policy_forbids(log):
    """Treasury insists on paying a sanctioned destination. It cannot happen."""
    orchestrator._promote(
        [SANCTIONED],
        {"p1": {"verdict": "approve", "proposed_by": "treasury"}},
        policy.BALANCE, policy.RESERVE_FLOOR,
    )
    evs = _read(log)
    assert _by_type(evs, "payout.approved") == []          # the invariant
    assert len(_by_type(evs, "payout.rejected")) == 1
    blocked = _by_type(evs, "policy.blocked")
    assert len(blocked) == 1
    assert blocked[0]["payload"]["rule"] == "P1"
    assert blocked[0]["payload"]["proposed_by"] == "treasury"
    # the agent's intent survives on the record — only its effect is denied
    proposed = _by_type(evs, "payout.proposed")
    assert proposed[0]["payload"]["verdict"] == "approve"


def test_gate_is_veto_only_and_never_manufactures_an_approval(log):
    """A payout policy would happily approve, but the society rejected it.
    The gate must NOT overrule the agents in that direction."""
    orchestrator._promote(
        [CLEAN],
        {"p2": {"verdict": "reject", "proposed_by": "compliance"}},
        policy.BALANCE, policy.RESERVE_FLOOR,
    )
    evs = _read(log)
    assert _by_type(evs, "payout.approved") == []
    assert len(_by_type(evs, "payout.rejected")) == 1
    assert _by_type(evs, "policy.blocked") == []   # nothing to block: no approval proposed


def test_clean_approval_passes_through(log):
    orchestrator._promote(
        [CLEAN],
        {"p2": {"verdict": "approve", "proposed_by": "treasury"}},
        policy.BALANCE, policy.RESERVE_FLOOR,
    )
    evs = _read(log)
    assert len(_by_type(evs, "payout.approved")) == 1
    assert _by_type(evs, "policy.blocked") == []


def test_reserve_floor_is_an_invariant_not_a_grade(log):
    """The regression that broke run 20260702-204555: Treasury approves the whole
    batch one payout at a time and overdraws the treasury. Post-gate, that run
    is no longer expressible — the floor holds even against a unanimous society."""
    balance, floor = 100_000.0, 10_000.0
    batch = [{"id": f"b{i}", "amount": 15_000.0, "currency": "USD", "from_country": "US",
              "to_country": "NG", "recipient_age_days": 400, "memo": "x"} for i in range(10)]
    proposals = {p["id"]: {"verdict": "approve", "proposed_by": "treasury"} for p in batch}

    orchestrator._promote(batch, proposals, balance, floor)

    evs = _read(log)
    approved = {e["subject"] for e in _by_type(evs, "payout.approved")}
    amounts = {p["id"]: p["amount"] for p in batch}
    spent = sum(amounts[pid] for pid in approved)

    # every one of the 10 was proposed for approval...
    assert len(_by_type(evs, "payout.proposed")) == 10
    # ...but the floor held anyway
    assert spent <= balance - floor, f"floor breached: spent {spent}"
    assert len(_by_type(evs, "policy.blocked")) == 10 - len(approved)
    assert all(e["payload"]["rule"] == "P3" for e in _by_type(evs, "policy.blocked"))


def test_blocked_payouts_are_rejected_with_the_rule_named(log):
    orchestrator._promote(
        [NEW_BIG],
        {"p3": {"verdict": "approve", "proposed_by": "treasury"}},
        policy.BALANCE, policy.RESERVE_FLOOR,
    )
    evs = _read(log)
    rejected = _by_type(evs, "payout.rejected")[0]
    assert rejected["payload"]["blocked_rule"] == "P2"   # new recipient, >= 9k


def test_every_payout_reaches_exactly_one_terminal_decision(log):
    batch = [SANCTIONED, CLEAN, NEW_BIG]
    proposals = {p["id"]: {"verdict": "approve", "proposed_by": "treasury"} for p in batch}
    orchestrator._promote(batch, proposals, policy.BALANCE, policy.RESERVE_FLOOR)
    evs = _read(log)
    terminal = _by_type(evs, "payout.approved") + _by_type(evs, "payout.rejected")
    assert sorted(e["subject"] for e in terminal) == ["p1", "p2", "p3"]


def test_chain_still_verifies_with_the_new_event_types(log):
    orchestrator._promote(
        [SANCTIONED], {"p1": {"verdict": "approve", "proposed_by": "treasury"}},
        policy.BALANCE, policy.RESERVE_FLOOR,
    )
    assert events.verify_chain(_read(log))["verified"] is True
