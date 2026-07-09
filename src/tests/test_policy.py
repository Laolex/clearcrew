"""Executable policy: one implementation labels the benchmark AND powers
deterministic counterfactual replay, so the two can never drift."""
from dataclasses import replace

import pytest
from fastapi import HTTPException

from clearcrew import data, policy, replay

HEADLINE = "events-20260702-210640-n36.jsonl"


def test_rendered_text_stable():
    # archived runs were prompted with exactly this text; render() must not drift
    assert policy.PAYOUT_POLICY.startswith("ORG PAYOUT POLICY (binding):")
    assert "IR, KP, SY, CU" in policy.PAYOUT_POLICY
    assert "9,000 USD" in policy.PAYOUT_POLICY and "7 days" in policy.PAYOUT_POLICY


def test_evaluate_is_the_ground_truth_labeler():
    batch = data.make_batch(36)
    verdicts = policy.evaluate(batch)
    assert all(p["_expected"] == verdicts[p["id"]]["verdict"] for p in batch)


def test_evaluate_attributes_rules():
    batch = data.make_batch(36)
    verdicts = policy.evaluate(batch)
    rules = {verdicts[p["id"]]["rule"] for p in batch}
    assert "P1" in rules and "P3" in rules  # sanctions and the waterfall both bind at n=36
    assert all(v["rule"] is None for v in verdicts.values() if v["verdict"] == "approve")


def test_counterfactual_identity():
    # same parameters -> zero diffs, by construction
    assert replay.counterfactual(HEADLINE)["changes"] == []


@pytest.mark.parametrize("kwargs", [
    {"reserve_floor": -1.0},
    {"p2_amount": -500.0},
    {"p2_age_days": -1},
    {"p2_age_days": 366},
])
def test_counterfactual_rejects_out_of_range_params(kwargs):
    # the frontend's `min`/`max` are UX hints only (a button-triggered
    # fetch(), not a <form> submit, so HTML5 constraint validation never
    # runs) — this is the actual enforcement, so it must reject regardless
    # of what the client sent.
    with pytest.raises(HTTPException) as exc:
        replay.counterfactual(HEADLINE, **kwargs)
    assert exc.value.status_code == 422


def test_counterfactual_reserve_floor_is_deterministic_and_attributed():
    out = replay.counterfactual(HEADLINE, reserve_floor=40_000.0)
    again = replay.counterfactual(HEADLINE, reserve_floor=40_000.0)
    assert out["changes"] == again["changes"] and out["changes"]
    assert all("P3" in c["cause"] for c in out["changes"])
    assert out["summary"]["hypothetical"]["approve"] < out["summary"]["in_force"]["approve"]


def test_counterfactual_never_touches_recorded_outcomes():
    out = replay.counterfactual(HEADLINE, reserve_floor=40_000.0)
    detail = replay.run_detail(HEADLINE)
    recorded = {p["id"]: p["status"] for p in detail["payouts"]}
    for c in out["changes"]:
        assert c["recorded_outcome"] == recorded[c["payout_id"]]


def test_hypothetical_version_is_labeled_never_enacted():
    out = replay.counterfactual(HEADLINE, p2_amount=5_000.0)
    assert "counterfactual" in out["policy_hypothetical"]["version"]
    assert "never enacted" in out["policy_hypothetical"]["reason"]
    assert [v.version for v in policy.VERSIONS] == ["v1"]  # registry untouched


def test_policy_version_headroom():
    pv = replace(policy.CURRENT, reserve_floor=40_000.0)
    assert pv.headroom == pv.balance - 40_000.0
