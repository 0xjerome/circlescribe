from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class EventType(str, Enum):
    ATTENDANCE = "attendance"
    CONTRIBUTION = "contribution"
    LOAN_REPAYMENT = "loan_repayment"
    LOAN_REQUEST = "loan_request"
    FINE = "fine"
    EXPENSE = "expense"
    DECISION = "decision"
    CORRECTION = "correction"

class Member(BaseModel):
    id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)

class ExtractedEvent(BaseModel):
    id: str
    event_type: EventType
    member_id: str | None = None
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = "UGX"
    confidence: float = Field(ge=0, le=1)
    source_text: str
    supersedes_event_id: str | None = None
    note: str | None = None

class MeetingExtraction(BaseModel):
    meeting_summary: str
    events: list[ExtractedEvent]

class GroupState(BaseModel):
    group_id: str
    currency: str = "UGX"
    members: list[Member]
    opening_balances: dict[str, int] = Field(default_factory=dict)

class ExceptionItem(BaseModel):
    event_id: str
    code: str
    message: str
    source_text: str
    requires_human: bool = True

class LedgerEntry(BaseModel):
    event_id: str
    member_id: str | None
    event_type: EventType
    amount: int
    currency: str
    source_text: str

class ReconcileRequest(BaseModel):
    group: GroupState
    events: list[ExtractedEvent]
    confidence_threshold: float = Field(default=0.85, ge=0, le=1)

class ReconcileReport(BaseModel):
    status: Literal["reconciled", "needs_review"]
    entries: list[LedgerEntry]
    exceptions: list[ExceptionItem]
    superseded_event_ids: list[str]
    totals_by_type: dict[str, int]
