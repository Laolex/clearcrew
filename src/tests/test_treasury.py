"""The treasury eval bar: a fold over recorded terminal decisions.

These run against the REAL archived runs, not a fixture — the bar's whole claim
is that it reports the position a run actually recorded, including the runs
where the reserve floor broke. A fixture would let that claim pass vacuously.
"""
import pytest
from fastapi.testclient import TestClient

from clearcrew import policy, replay

HELD = "events-20260702-210640-n36.jsonl"    # current architecture: floor holds
BREACHED = "events-20260702-204555-n36.jsonl"  # treasury judged payouts alone


@pytest.fixture(autouse=True)
def _no_auth():
    replay.API_TOKEN = ""
    yield


@pytest.fixture
def client():
    return TestClient(replay.app)


def _treasury(client, run):
    r = client.get(f"/api/runs/{run}/treasury")
    assert r.status_code == 200
    return r.json()


def test_fold_is_self_consistent(client):
    """Each step's balance is the previous balance minus what that step spent —
    i.e. the trajectory really is a fold, not a series of independent numbers."""
    t = _treasury(client, HELD)
    balance = t["balance"]
    for step in t["steps"]:
        if step["approved"]:
            balance -= step["amount"]
        assert step["balance"] == pytest.approx(balance)
    assert t["final_balance"] == pytest.approx(balance)
    assert t["spent"] == pytest.approx(t["balance"] - t["final_balance"])


def test_current_architecture_holds_the_floor(client):
    t = _treasury(client, HELD)
    assert t["breached"] is False
    assert t["breach_amount"] == 0.0
    assert t["final_balance"] > t["reserve_floor"]
    assert t["held"] > 0                  # the floor bound, and payouts were held back
    assert t["reasoned_cumulatively"] is True
    assert not any(s["below_floor"] for s in t["steps"])


def test_breached_run_reports_its_breach(client):
    """The run where Treasury judged each payout in isolation overdrew the
    treasury. The bar must say so — this is the regression the ladder fixed."""
    t = _treasury(client, BREACHED)
    assert t["breached"] is True
    assert t["breach_amount"] > 0
    assert t["final_balance"] < t["reserve_floor"]
    assert t["reasoned_cumulatively"] is False   # never recorded a running total
    assert t["steps"][-1]["below_floor"] is True


def test_held_steps_are_floor_holds_not_policy_rejections(client):
    """A 'held' step is one the reserve-floor waterfall (P3) caused — a payout
    rejected under P1/P2 is not a floor hold and must not be counted as one."""
    t = _treasury(client, HELD)
    assert t["held"] == sum(1 for s in t["steps"] if s["held"])
    for step in t["steps"]:
        if step["held"]:
            assert step["approved"] is False


def test_uses_the_policy_in_force(client):
    t = _treasury(client, HELD)
    assert t["balance"] == policy.CURRENT.balance
    assert t["reserve_floor"] == policy.CURRENT.reserve_floor
    assert t["headroom"] == policy.CURRENT.headroom


def test_unknown_run_404s(client):
    assert client.get("/api/runs/events-nope-n12.jsonl/treasury").status_code == 404
