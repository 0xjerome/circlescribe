from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .demo import demo_group
from .ledger import reconcile
from .local_extractor import extract_locally
from .models import EventType, ExtractedEvent, GroupState, MeetingExtraction, ReconcileReport, ReconcileRequest

ResolutionAction = Literal["confirm", "discard"]


@dataclass
class DemoRunState:
    extraction: MeetingExtraction
    group: GroupState
    resolved_event_ids: set[str] = field(default_factory=set)
    discarded_event_ids: set[str] = field(default_factory=set)


def create_demo_run(transcript: str) -> DemoRunState:
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")
    return DemoRunState(extraction=extract_locally(transcript), group=demo_group())


def active_events(state: DemoRunState) -> list[ExtractedEvent]:
    return [event for event in state.extraction.events if event.id not in state.discarded_event_ids]


def reconcile_demo_run(state: DemoRunState) -> ReconcileReport:
    return reconcile(ReconcileRequest(group=state.group, events=active_events(state)))


def resolve_demo_event(
    state: DemoRunState,
    *,
    event_id: str,
    action: ResolutionAction,
    amount_minor: int | None = None,
    member_id: str | None = None,
) -> ReconcileReport:
    """Apply one explicit human resolution and deterministically resume the run.

    The human may confirm/replace an event's amount/member or discard the event.
    Resolution does not bypass the ledger validator; the updated event is always
    reconciled again through the same deterministic rules.
    """
    current_report = reconcile_demo_run(state)
    review_ids = {item.event_id for item in current_report.exceptions}
    if event_id not in review_ids:
        raise ValueError(f"Event '{event_id}' does not currently require human review.")

    event_index = next((i for i, e in enumerate(state.extraction.events) if e.id == event_id), None)
    if event_index is None:
        raise ValueError(f"Event '{event_id}' was not found in this run.")

    event = state.extraction.events[event_index]

    if action == "discard":
        state.discarded_event_ids.add(event_id)
        state.resolved_event_ids.add(event_id)
        return reconcile_demo_run(state)

    resolved_amount = amount_minor if amount_minor is not None else event.amount_minor
    resolved_member = member_id if member_id is not None else event.member_id

    if event.event_type in {
        EventType.CONTRIBUTION,
        EventType.LOAN_REPAYMENT,
        EventType.FINE,
        EventType.EXPENSE,
        EventType.CORRECTION,
    } and (resolved_amount is None or resolved_amount <= 0):
        raise ValueError("A confirmed financial event requires a positive amount.")

    note_parts = [part for part in [event.note, "Human-confirmed during exception review"] if part]
    updated = event.model_copy(
        update={
            "amount_minor": resolved_amount,
            "member_id": resolved_member,
            "confidence": 1.0,
            "note": " | ".join(note_parts),
        }
    )
    events = list(state.extraction.events)
    events[event_index] = updated
    state.extraction = state.extraction.model_copy(update={"events": events})
    state.resolved_event_ids.add(event_id)

    return reconcile_demo_run(state)


def generate_demo_minutes(state: DemoRunState, report: ReconcileReport) -> str:
    accepted = "\n".join(
        f"- {entry.event_type.value}: {entry.amount:,} {entry.currency} ({entry.member_id or 'group'})"
        for entry in report.entries
    ) or "- No financial ledger entries accepted."

    review = "\n".join(f"- REVIEW: {item.message}" for item in report.exceptions)
    resolved = "\n".join(f"- Resolved by human: {event_id}" for event_id in sorted(state.resolved_event_ids))
    discarded = "\n".join(f"- Discarded by human: {event_id}" for event_id in sorted(state.discarded_event_ids))

    status_line = (
        "All deterministic checks passed. No human review items remain."
        if report.status == "reconciled"
        else f"{len(report.exceptions)} item(s) still require human review."
    )

    sections = [
        "CircleScribe meeting minutes",
        "",
        state.extraction.meeting_summary,
        "",
        f"Workflow status: {status_line}",
        "",
        "Verified ledger activity:",
        accepted,
    ]

    if resolved:
        sections += ["", "Human resolutions:", resolved]
    if discarded:
        sections += ["", "Discarded events:", discarded]
    if review:
        sections += ["", "Items requiring human review:", review]

    return "\n".join(sections) + "\n"
