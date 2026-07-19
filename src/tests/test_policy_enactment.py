from clearcrew import agents, config, events, policy, replay
from fastapi.testclient import TestClient


RUN = "events-20260702-210640-n36.jsonl"


def _proposal():
    return policy.proposed_version({"p2_age_days": 30}, "Extends P2 to 30 days.")


def test_proposed_policy_replay_is_deterministic_with_exact_flips_and_dollars():
    first = replay.proposed_policy_impact(RUN, _proposal())
    second = replay.proposed_policy_impact(RUN, _proposal())

    assert first == second
    assert [change["payout_id"] for change in first["changes"]] == [
        "62c33a4f", "dbf4a8b2", "1818e811", "6d76b07e", "ca02135e",
    ]
    assert first["dollars"] == {
        "in_force_paid": 84_460.0,
        "in_force_held": 145_290.0,
        "proposed_paid": 85_060.0,
        "proposed_held": 144_690.0,
        "additional_held": 29_400.0,
        "released": 30_000.0,
        "net_paid_change": 600.0,
    }
    assert first["summary"] == {
        "in_force": {"approve": 22, "reject": 14},
        "proposed": {"approve": 21, "reject": 15},
        "changed": 5,
    }


def test_enactment_appends_version_and_hash_chained_event(monkeypatch, tmp_path):
    original_versions = list(policy.VERSIONS)
    original_current = policy.CURRENT
    original_balance = policy.BALANCE
    original_floor = policy.RESERVE_FLOOR
    original_text = policy.PAYOUT_POLICY
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))
    events.reset_chain(config.EVENT_LOG_PATH)
    proposal = _proposal()
    proposed_event = events.emit("policy.proposed", "policy", "policy", {
        "status": "proposal",
        "diff": {"p2_age_days": 30},
        "reason": proposal.reason,
        "before": original_current.params(),
        "after": proposal.params(),
    })

    client = TestClient(replay.app)
    impact = client.post(
        f"/api/policies/proposals/{proposed_event['id']}/impact",
        json={"run": RUN},
    )
    response = client.post(f"/api/policies/proposals/{proposed_event['id']}/enact")

    try:
        assert impact.status_code == 200
        assert impact.json()["impact"]["dollars"]["additional_held"] == 29_400.0
        assert response.status_code == 200
        assert response.json()["version"] == "v2"
        assert policy.CURRENT.version == "v2"
        assert policy.CURRENT.p2_age_days == 30
        assert "30 days" in agents._active_policy_prompt(agents.INTAKE_SYS)
        log = events.read_all()
        assert log[-1]["type"] == "policy.enacted"
        assert log[-1]["actor"] == "policy"
        assert events.verify_chain(log)["verified"] is True
    finally:
        policy.VERSIONS[:] = original_versions
        policy.CURRENT = original_current
        policy.BALANCE = original_balance
        policy.RESERVE_FLOOR = original_floor
        policy.PAYOUT_POLICY = original_text
