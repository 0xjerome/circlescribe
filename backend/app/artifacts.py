from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .models import EventType, ReconcileReport
from .workflow import DemoRunState, active_events


class Receipt(BaseModel):
    id: str
    event_id: str
    member_id: str | None
    member_name: str
    event_type: EventType
    amount: int
    currency: str
    status: Literal["final"] = "final"


class FollowUpAction(BaseModel):
    id: str
    event_id: str
    title: str
    owner: str
    amount: int | None = None
    currency: str | None = None
    status: Literal["open"] = "open"


class AuditRecord(BaseModel):
    sequence: int
    actor: Literal["extractor", "validator", "human", "system"]
    stage: str
    detail: str
    event_id: str | None = None


class CompletionArtifacts(BaseModel):
    finalized: bool
    receipts: list[Receipt]
    follow_up_actions: list[FollowUpAction]
    audit_log: list[AuditRecord]


def _member_names(state: DemoRunState) -> dict[str, str]:
    return {member.id: member.display_name for member in state.group.members}


def generate_completion_artifacts(
    state: DemoRunState,
    report: ReconcileReport,
) -> CompletionArtifacts:
    """Generate post-meeting work only after deterministic reconciliation passes.

    Draft/review runs intentionally do not emit final receipts or operational
    follow-ups. This prevents partially reviewed financial data from looking
    completed to the operator.
    """
    audit: list[AuditRecord] = [
        AuditRecord(
            sequence=1,
            actor="extractor",
            stage="meeting_interpreted",
            detail=f"{len(state.extraction.events)} structured event(s) were extracted from the meeting.",
        ),
        AuditRecord(
            sequence=2,
            actor="validator",
            stage="ledger_validated",
            detail=(
                f"{len(report.entries)} ledger mutation(s) accepted; "
                f"{len(report.exceptions)} item(s) require review."
            ),
        ),
    ]

    seq = 3
    for event_id in report.superseded_event_ids:
        audit.append(AuditRecord(
            sequence=seq,
            actor="validator",
            stage="correction_applied",
            detail="An earlier event was superseded by an explicit correction.",
            event_id=event_id,
        ))
        seq += 1

    for event_id in sorted(state.resolved_event_ids):
        actor = "human"
        stage = "event_discarded" if event_id in state.discarded_event_ids else "exception_resolved"
        detail = (
            "Human reviewer discarded the ambiguous event."
            if event_id in state.discarded_event_ids
            else "Human reviewer confirmed the ambiguous event; deterministic validation was rerun."
        )
        audit.append(AuditRecord(
            sequence=seq,
            actor=actor,
            stage=stage,
            detail=detail,
            event_id=event_id,
        ))
        seq += 1

    if report.status != "reconciled":
        audit.append(AuditRecord(
            sequence=seq,
            actor="system",
            stage="outputs_blocked",
            detail="Final receipts and follow-up actions are blocked until all review items are resolved.",
        ))
        return CompletionArtifacts(
            finalized=False,
            receipts=[],
            follow_up_actions=[],
            audit_log=audit,
        )

    names = _member_names(state)
    receipts = [
        Receipt(
            id=f"receipt-{entry.event_id}",
            event_id=entry.event_id,
            member_id=entry.member_id,
            member_name=names.get(entry.member_id or "", "Group"),
            event_type=entry.event_type,
            amount=entry.amount,
            currency=entry.currency,
        )
        for entry in report.entries
    ]

    actions: list[FollowUpAction] = []
    for event in active_events(state):
        if event.event_type != EventType.LOAN_REQUEST:
            continue
        if event.confidence < 0.85 or event.amount_minor is None or event.amount_minor <= 0:
            continue
        member_name = names.get(event.member_id or "", "Unknown member")
        actions.append(FollowUpAction(
            id=f"action-{event.id}",
            event_id=event.id,
            title=f"Review loan request for {member_name}",
            owner="Group committee",
            amount=event.amount_minor,
            currency=event.currency or state.group.currency,
        ))

    audit.append(AuditRecord(
        sequence=seq,
        actor="system",
        stage="outputs_finalized",
        detail=f"Generated {len(receipts)} receipt(s) and {len(actions)} follow-up action(s).",
    ))

    return CompletionArtifacts(
        finalized=True,
        receipts=receipts,
        follow_up_actions=actions,
        audit_log=audit,
    )
