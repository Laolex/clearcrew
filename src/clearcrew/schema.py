"""Event schema definitions with best-effort structural validation.
Every event type has a typed payload dataclass; when validation succeeds the
payload is normalized to match the schema. Unknown payload shapes or missing
fields emit a warning but never block the event — breaking a live run on
schema drift would be worse than letting a loosely-typed event through.
"""
import logging
from dataclasses import dataclass, asdict
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class IntakeClassified:
    risk_tier: Literal["low", "medium", "high"]
    reason: str
    flags: list[str]


@dataclass
class ComplianceReviewed:
    verdict: Literal["clear", "veto"]
    reason: str
    policy_rule: Literal["P1", "P2", "none"]


@dataclass
class TreasuryDecided:
    payout_id: str
    action: Literal["pay_now", "reject"]
    reason: str


@dataclass
class DisputeResolved:
    ruling: str
    reason: str
    conditions: list[str] | None = None


@dataclass
class SettlementConfirmed:
    rail: str
    source_amount_usd: float
    settled_amount_usdc: float
    chain: str
    tx_hash: str | None = None


EVENT_SCHEMA: dict[str, type[dataclass]] = {
    "intake.classified": IntakeClassified,
    "compliance.reviewed": ComplianceReviewed,
    "treasury.decided": TreasuryDecided,
    "dispute.resolved": DisputeResolved,
    "settlement.confirmed": SettlementConfirmed,
}


def validate(event: dict) -> dict:
    cls = EVENT_SCHEMA.get(event["type"])
    if cls:
        try:
            event["payload"] = asdict(cls(**event["payload"]))
        except (TypeError, ValueError) as exc:
            logger.warning("schema validation skipped for %s: %s", event["type"], exc)
    event.setdefault("schema_version", 1)
    return event
