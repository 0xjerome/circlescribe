from __future__ import annotations

import re
from itertools import count

from .models import EventType, ExtractedEvent, MeetingExtraction

_MEMBER_IDS = {
    "amina": "m-001",
    "ami": "m-001",
    "john": "m-002",
    "jon": "m-002",
    "mary": "m-003",
    "sarah": "m-004",
}

_UNITS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _words_to_number(text: str) -> int | None:
    """Parse the small set of English amount phrases used in the local demo.

    This is intentionally a deterministic development adapter, not an AI model.
    It exists so the full workflow can be exercised while AWS is unavailable.
    For correction phrases such as "make that twenty thousand, not thirty",
    only the corrected amount is parsed.
    """
    lowered = text.lower()
    if "make that" in lowered:
        text = text[lowered.index("make that") + len("make that"):]
        text = re.split(r"[,;]|\bnot\b", text, maxsplit=1, flags=re.IGNORECASE)[0]

    # Amount phrases often continue with a duration or purpose, e.g.
    # "one hundred thousand for one month". Stop parsing at those semantic
    # boundaries so duration numbers cannot leak into the money amount.
    text = re.split(r"\b(?:for|until|by)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]

    numeric = re.search(r"\b([0-9][0-9,]*)\b", text)
    if numeric:
        return int(numeric.group(1).replace(",", ""))

    tokens = re.findall(r"[a-z]+", text.lower())
    current = 0
    total = 0
    saw_number = False
    for token in tokens:
        if token in _UNITS:
            current += _UNITS[token]
            saw_number = True
        elif token in _TENS:
            current += _TENS[token]
            saw_number = True
        elif token == "hundred":
            current = max(current, 1) * 100
            saw_number = True
        elif token == "thousand":
            total += max(current, 1) * 1000
            current = 0
            saw_number = True
    return (total + current) if saw_number else None


def _speaker_and_body(line: str) -> tuple[str, str]:
    if ":" not in line:
        return "", line.strip()
    speaker, body = line.split(":", 1)
    return speaker.strip(), body.strip()


def _member_id(speaker: str) -> str | None:
    return _MEMBER_IDS.get(speaker.strip().lower())


def extract_locally(transcript: str) -> MeetingExtraction:
    """Deterministic local-development extractor.

    It is deliberately narrow and clearly separated from the production
    Strands/Bedrock adapter. It should never be presented as AI extraction.
    """
    event_ids = count(1)
    events: list[ExtractedEvent] = []
    last_contribution_by_member: dict[str, str] = {}

    for raw in transcript.splitlines():
        line = raw.strip()
        if not line:
            continue
        speaker, body = _speaker_and_body(line)
        lower = body.lower()
        member_id = _member_id(speaker)

        # Attendance sentence from the chair, e.g. "Amina is here, John is here".
        if speaker.lower() == "chair" and "is here" in lower:
            for name, mid in [("Amina", "m-001"), ("John", "m-002"), ("Mary", "m-003"), ("Sarah", "m-004")]:
                if re.search(rf"\b{name.lower()}\s+is\s+here\b", lower):
                    events.append(ExtractedEvent(
                        id=f"evt-{next(event_ids):03d}",
                        event_type=EventType.ATTENDANCE,
                        member_id=mid,
                        confidence=1.0,
                        source_text=line,
                        note="present",
                    ))
            continue

        # The chair often repeats or questions a member's statement. Those
        # prompts are context, not member financial events. Preserve explicit
        # chair decisions below, but never infer a contribution merely because
        # the chair says words like "confirm your contribution".
        if speaker.lower() == "chair":
            if "review" in lower or "approved" in lower or "decision" in lower:
                events.append(ExtractedEvent(
                    id=f"evt-{next(event_ids):03d}",
                    event_type=EventType.DECISION,
                    member_id=None,
                    confidence=0.95,
                    source_text=line,
                    note=body,
                ))
            continue

        amount = _words_to_number(body)

        if "not sure" in lower or "unclear" in lower or "maybe" in lower:
            confidence = 0.55
        else:
            confidence = 0.98

        if ("actually" in lower or "correct" in lower or "make that" in lower) and member_id:
            target = last_contribution_by_member.get(member_id)
            events.append(ExtractedEvent(
                id=f"evt-{next(event_ids):03d}",
                event_type=EventType.CORRECTION,
                member_id=member_id,
                amount_minor=amount,
                currency="UGX",
                confidence=confidence if amount is not None else 0.4,
                source_text=line,
                supersedes_event_id=target,
                note="Explicit correction to an earlier contribution",
            ))
            continue

        if "repay" in lower and "loan" in lower:
            events.append(ExtractedEvent(
                id=f"evt-{next(event_ids):03d}",
                event_type=EventType.LOAN_REPAYMENT,
                member_id=member_id,
                amount_minor=amount,
                currency="UGX",
                confidence=confidence if amount is not None else 0.4,
                source_text=line,
            ))
            continue

        if "request" in lower and "loan" in lower:
            events.append(ExtractedEvent(
                id=f"evt-{next(event_ids):03d}",
                event_type=EventType.LOAN_REQUEST,
                member_id=member_id,
                amount_minor=amount,
                currency="UGX",
                confidence=confidence if amount is not None else 0.4,
                source_text=line,
                note="Request only; not an approved ledger mutation",
            ))
            continue

        if "paid" in lower or "contribution" in lower or "savings" in lower:
            event_id = f"evt-{next(event_ids):03d}"
            events.append(ExtractedEvent(
                id=event_id,
                event_type=EventType.CONTRIBUTION,
                member_id=member_id,
                amount_minor=amount,
                currency="UGX",
                confidence=confidence if amount is not None else 0.4,
                source_text=line,
            ))
            if member_id:
                last_contribution_by_member[member_id] = event_id
            continue

        if "review" in lower or "approved" in lower or "decision" in lower:
            events.append(ExtractedEvent(
                id=f"evt-{next(event_ids):03d}",
                event_type=EventType.DECISION,
                member_id=member_id,
                confidence=0.95,
                source_text=line,
                note=body,
            ))

    return MeetingExtraction(
        meeting_summary=(
            f"Local development extraction produced {len(events)} structured events. "
            "This adapter is deterministic and is not the production Strands/Bedrock path."
        ),
        events=events,
    )
