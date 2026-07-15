"""Resolution must arbitrate a disagreement that actually happened.

The dispute used to be theatre: Treasury never saw a vetoed payout, so the
orchestrator handed Resolution a hardcoded string as Treasury's position. One
side of every recorded argument was invented. These tests pin the two properties
that make the dispute real — Treasury states its own position, and Resolution's
override can actually change an outcome — and the one that keeps it safe: an
override still cannot approve what policy forbids.
"""
import pytest

from clearcrew import agents, config, events, orchestrator, policy


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


# Legal under the written policy, but wearing every symptom of a violation:
# one dollar under the P2 threshold, brand-new recipient, no memo.
P4_TRAP = {"id": "trap", "amount": 8_999.0, "currency": "USD", "from_country": "US",
           "to_country": "PH", "recipient_age_days": 2, "memo": ""}
# Actually illegal: sanctioned destination.
SANCTIONED = {"id": "sanc", "amount": 9_500.0, "currency": "USD", "from_country": "US",
              "to_country": "IR", "recipient_age_days": 400, "memo": "x"}


def _stub(monkeypatch, *, ruling, capture=None):
    """A society that vetoes everything and rules however the test says."""
    monkeypatch.setattr(agents, "intake", lambda p: {"risk_tier": "high", "reason": "r", "flags": []})

    def compliance(payout, tri):
        events.emit("compliance.reviewed", payout["id"], "compliance",
                    {"verdict": "veto", "reason": "flags present", "policy_rule": "P4"})
        return {"verdict": "veto", "reason": "flags present", "policy_rule": "P4"}

    monkeypatch.setattr(agents, "compliance", compliance)

    def treasury(payouts, balance, floor):
        decisions = [{"payout_id": p["id"], "action": "pay_now",
                      "reason": f"{p['amount']} within headroom {balance - floor}"} for p in payouts]
        for d in decisions:
            events.emit("treasury.decided", d["payout_id"], "treasury", d)
        return {"decisions": decisions}

    monkeypatch.setattr(agents, "treasury", treasury)
    monkeypatch.setattr(agents, "build_ledger", lambda ps: [])

    def negotiate(payout, veto, treasury_position):
        if capture is not None:
            capture[payout["id"]] = treasury_position
        out = {"ruling": ruling, "reason": "because", "conditions": ["verify recipient"]}
        events.emit("dispute.resolved", payout["id"], "resolution", out)
        return out

    monkeypatch.setattr(agents, "negotiate", negotiate)
    monkeypatch.setattr(agents, "audit", lambda pid: {"explanation": "x"})


def test_treasury_states_its_own_position_on_a_contested_payout(log, monkeypatch):
    """The position Resolution rules on must be Treasury's, not the orchestrator's."""
    seen: dict[str, dict] = {}
    _stub(monkeypatch, ruling="uphold_veto", capture=seen)

    orchestrator.run_batch([P4_TRAP])

    position = seen["trap"]
    # It is a real decision by the Treasury agent, carrying its own reasoning...
    assert position["action"] == "pay_now"
    assert "headroom" in position["reason"]
    # ...and it is on the record, not merely passed in memory.
    decided = _by_type(_read(log), "treasury.decided")
    assert [e["subject"] for e in decided] == ["trap"]
    assert decided[0]["actor"] == "treasury"


def test_an_override_can_actually_change_the_outcome(log, monkeypatch):
    """A veto Resolution overturns on a policy-clean payout must end in approval.

    If this cannot happen, 'negotiated resolution' is a word for a rubber stamp.
    """
    _stub(monkeypatch, ruling="override_with_conditions")

    orchestrator.run_batch([P4_TRAP])
    evs = _read(log)

    assert [e["subject"] for e in _by_type(evs, "payout.approved")] == ["trap"]
    assert _by_type(evs, "payout.rejected") == []
    # the proposer is the speaker: `proposed_by` becomes the event's actor
    proposed = _by_type(evs, "payout.proposed")[0]
    assert proposed["actor"] == "resolution"
    assert proposed["payload"]["verdict"] == "approve"


def test_an_override_still_cannot_approve_what_policy_forbids(log, monkeypatch):
    """Resolution is an agent, and the gate refuses agents. Overriding a correct
    sanctions veto must be recorded as intent and denied as effect."""
    _stub(monkeypatch, ruling="override_with_conditions")

    orchestrator.run_batch([SANCTIONED])
    evs = _read(log)

    assert _by_type(evs, "payout.approved") == []
    assert [e["subject"] for e in _by_type(evs, "payout.rejected")] == ["sanc"]
    blocked = _by_type(evs, "policy.blocked")
    assert blocked[0]["payload"]["rule"] == "P1"
    assert blocked[0]["payload"]["proposed_by"] == "resolution"
    # the override survives on the record — only its effect is denied
    assert _by_type(evs, "payout.proposed")[0]["payload"]["verdict"] == "approve"


def test_no_position_is_recorded_as_absent_never_invented(log, monkeypatch):
    """When Treasury returns nothing, Resolution is told so in as many words."""
    seen: dict[str, dict] = {}
    _stub(monkeypatch, ruling="uphold_veto", capture=seen)
    monkeypatch.setattr(agents, "treasury", lambda ps, b, f: {"decisions": []})

    orchestrator.run_batch([P4_TRAP])

    assert seen["trap"]["action"] == "no_position"


def test_the_hard_cases_are_legal_under_the_written_policy(log):
    """The trap batch must be a test of the agents, not a stacked deck: every
    hard case is one the policy itself approves."""
    from clearcrew import data

    batch = data.make_batch(6, hard=True)
    verdicts = policy.evaluate(batch)
    hard = [p for p in batch if p["id"].startswith("hard")]
    assert hard, "hard cases missing"
    for p in hard:
        assert verdicts[p["id"]]["verdict"] == "approve"
        assert verdicts[p["id"]]["rule"] is None

    # and the default batch is untouched, or every archived run stops resolving
    assert not any(p["id"].startswith("hard") for p in data.make_batch(36))
