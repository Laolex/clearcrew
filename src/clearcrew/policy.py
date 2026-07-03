"""The org's payout policy — versioned, parameterized, executable.

Policy is data, not prose: each PolicyVersion carries the parameters and
renders the binding text that both the society and the monolithic baseline
receive. The mechanical layer (P1 sanctions, P2 threshold, P3 reserve-floor
waterfall — everything decidable from known amounts) is `evaluate()`, one
function that is simultaneously the benchmark's ground-truth labeler and the
engine for deterministic counterfactual replay: fold the same recorded batch
through a different PolicyVersion, zero model calls, no simulated judgment.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PolicyVersion:
    version: str
    enacted: str
    reason: str
    sanctioned: tuple[str, ...] = ("IR", "KP", "SY", "CU")
    p2_amount: float = 9_000.0
    p2_age_days: int = 7
    balance: float = 100_000.0
    reserve_floor: float = 10_000.0

    @property
    def headroom(self) -> float:
        return self.balance - self.reserve_floor

    def params(self) -> dict:
        return asdict(self)

    def render(self) -> str:
        return f"""ORG PAYOUT POLICY (binding):
P1. REJECT any payout to a sanctioned destination country: {", ".join(self.sanctioned)}.
P2. REJECT payouts >= {self.p2_amount:,.0f} USD to recipients whose account is <= {self.p2_age_days} days old.
P3. Everything else is APPROVED unless treasury balance would fall below the
    reserve floor, in which case lowest-amount payouts are paid first.
P4. Flags (missing memo, round amounts, new recipients under P2 threshold) are
    recorded for audit but are NOT grounds for rejection on their own."""


# Enacted versions, oldest first. Only one so far: the governance repairs in
# this repo's history (separation of duties, ledger, reconciliation) changed
# agent CONTRACTS, not policy parameters — so we don't pretend they were
# policy versions. Future parameter changes append here with their reason.
VERSIONS = [
    PolicyVersion(
        version="v1",
        enacted="2026-07-01",
        reason="initial written policy — one text given identically to society and monolith",
    ),
]
CURRENT = VERSIONS[-1]

# Aliases for existing callers; PAYOUT_POLICY is byte-identical to the text
# every archived run was prompted with.
BALANCE = CURRENT.balance
RESERVE_FLOOR = CURRENT.reserve_floor
PAYOUT_POLICY = CURRENT.render()


def evaluate(batch: list[dict], pv: PolicyVersion = CURRENT) -> dict[str, dict]:
    """What the written policy itself rules for each payout — the deterministic
    layer only. Agent judgment (triage nuance, veto reasoning, negotiated
    rulings) is NOT modeled here; this is the arithmetic the policy pins down.

    Returns {payout_id: {"verdict": "approve"|"reject", "rule": "P1"|"P2"|"P3"|None}}.
    """
    out: dict[str, dict] = {}
    clean: list[dict] = []
    for p in batch:
        if p["to_country"] in pv.sanctioned:
            out[p["id"]] = {"verdict": "reject", "rule": "P1"}
        elif p["amount"] >= pv.p2_amount and p["recipient_age_days"] <= pv.p2_age_days:
            out[p["id"]] = {"verdict": "reject", "rule": "P2"}
        else:
            clean.append(p)
    # P3 waterfall: lowest-amount first until the reserve floor binds
    spent = 0.0
    for p in sorted(clean, key=lambda p: p["amount"]):
        if spent + p["amount"] <= pv.headroom:
            spent += p["amount"]
            out[p["id"]] = {"verdict": "approve", "rule": None}
        else:
            out[p["id"]] = {"verdict": "reject", "rule": "P3"}
    return out
