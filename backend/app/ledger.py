from __future__ import annotations

from collections import defaultdict

from .models import EventType, ExceptionItem, ExtractedEvent, LedgerEntry, ReconcileReport, ReconcileRequest

# Only events that represent an already-realized financial movement may mutate
# the ledger. A loan request is operational state, not money movement.
LEDGER_MUTATION_TYPES = {
    EventType.CONTRIBUTION,
    EventType.LOAN_REPAYMENT,
    EventType.FINE,
    EventType.EXPENSE,
}


def make_exception(event: ExtractedEvent, code: str, message: str) -> ExceptionItem:
    return ExceptionItem(event_id=event.id, code=code, message=message, source_text=event.source_text)


def reconcile(request: ReconcileRequest) -> ReconcileReport:
    """Validate structured meeting events without any model calls.

    Corrections inherit the financial type of the event they supersede. Loan
    requests never become ledger entries merely because they were discussed.
    """
    known = {m.id for m in request.group.members}
    by_id: dict[str, ExtractedEvent] = {}
    duplicate_ids: set[str] = set()
    exceptions: list[ExceptionItem] = []

    for event in request.events:
        if event.id in by_id:
            duplicate_ids.add(event.id)
            exceptions.append(make_exception(event, "duplicate_event_id", f"Event id '{event.id}' appears more than once."))
        else:
            by_id[event.id] = event

    superseded: set[str] = set()
    correction_targets: dict[str, ExtractedEvent] = {}

    for event in request.events:
        if event.id in duplicate_ids or not event.supersedes_event_id:
            continue
        target = by_id.get(event.supersedes_event_id)
        if target is None:
            exceptions.append(make_exception(event, "missing_superseded_event", f"Correction references unknown event '{event.supersedes_event_id}'."))
            continue
        if target.id == event.id:
            exceptions.append(make_exception(event, "self_supersede", "An event cannot supersede itself."))
            continue
        if event.event_type != EventType.CORRECTION:
            exceptions.append(make_exception(event, "invalid_supersede_type", "Only explicit correction events may supersede prior events."))
            continue
        superseded.add(target.id)
        correction_targets[event.id] = target

    entries: list[LedgerEntry] = []
    seen_keys: set[tuple] = set()
    totals = defaultdict(int)

    for event in request.events:
        if event.id in duplicate_ids or event.id in superseded:
            continue
        if event.confidence < request.confidence_threshold:
            exceptions.append(make_exception(event, "low_confidence", f"Confidence {event.confidence:.2f} is below {request.confidence_threshold:.2f}."))
            continue

        target = correction_targets.get(event.id)
        effective_member_id = event.member_id or (target.member_id if target else None)
        effective_type = target.event_type if target else event.event_type

        if effective_member_id is not None and effective_member_id not in known:
            exceptions.append(make_exception(event, "unknown_member", f"Member '{effective_member_id}' is not in this group."))
            continue

        # Operational events such as attendance, decisions and loan requests are
        # preserved in extraction output but never mutate the ledger here.
        if effective_type not in LEDGER_MUTATION_TYPES:
            continue

        if event.amount_minor is None or event.amount_minor <= 0:
            exceptions.append(make_exception(event, "invalid_amount", "Financial events require a positive amount."))
            continue
        if event.currency != request.group.currency:
            exceptions.append(make_exception(event, "currency_mismatch", f"Expected {request.group.currency}, received {event.currency}."))
            continue

        key = (
            effective_member_id,
            effective_type.value,
            event.amount_minor,
            event.currency,
            event.source_text.strip().lower(),
        )
        if key in seen_keys:
            exceptions.append(make_exception(event, "possible_duplicate", "This financial event duplicates an already accepted event."))
            continue
        seen_keys.add(key)

        entries.append(LedgerEntry(
            event_id=event.id,
            member_id=effective_member_id,
            event_type=effective_type,
            amount=event.amount_minor,
            currency=event.currency or request.group.currency,
            source_text=event.source_text,
        ))
        totals[effective_type.value] += event.amount_minor

    return ReconcileReport(
        status="needs_review" if exceptions else "reconciled",
        entries=entries,
        exceptions=exceptions,
        superseded_event_ids=sorted(superseded),
        totals_by_type=dict(totals),
    )
