from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import extract_events
from .demo import correction_demo_request, demo_group
from .ledger import reconcile
from .local_extractor import extract_locally
from .models import MeetingExtraction, ReconcileReport, ReconcileRequest

app = FastAPI(title="CircleScribe API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptRequest(BaseModel):
    transcript: str


class DemoProcessResponse(BaseModel):
    mode: str
    extraction: MeetingExtraction
    reconciliation: ReconcileReport
    generated_minutes: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "circlescribe-api"}


@app.post("/api/v1/extract", response_model=MeetingExtraction)
def extract(request: TranscriptRequest) -> MeetingExtraction:
    """Production AI adapter: real Strands + Amazon Bedrock."""
    try:
        return extract_events(request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Agent extraction failed. Check AWS credentials, model access, and server logs.",
        ) from exc


@app.post("/api/v1/reconcile", response_model=ReconcileReport)
def reconcile_events(request: ReconcileRequest) -> ReconcileReport:
    return reconcile(request)


@app.post("/api/v1/demo/reconcile", response_model=ReconcileReport)
def demo_reconcile() -> ReconcileReport:
    return reconcile(correction_demo_request())


@app.post("/api/v1/demo/process", response_model=DemoProcessResponse)
def demo_process(request: TranscriptRequest) -> DemoProcessResponse:
    """Full local workflow while AWS account access is unavailable.

    This endpoint is deliberately labeled local-fallback and must not be
    represented in the hackathon demo as Strands/Bedrock inference.
    """
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    extraction = extract_locally(request.transcript)
    report = reconcile(ReconcileRequest(group=demo_group(), events=extraction.events))

    accepted = "\n".join(
        f"- {entry.event_type.value}: {entry.amount:,} {entry.currency} ({entry.member_id or 'group'})"
        for entry in report.entries
    ) or "- No financial ledger entries accepted."
    review = "\n".join(f"- REVIEW: {item.message}" for item in report.exceptions)
    generated_minutes = (
        "CircleScribe draft minutes\n\n"
        f"{extraction.meeting_summary}\n\n"
        "Verified ledger activity:\n"
        f"{accepted}\n"
        + (f"\nItems requiring human review:\n{review}\n" if review else "\nNo human review items remain.\n")
    )

    return DemoProcessResponse(
        mode="local-deterministic-fallback",
        extraction=extraction,
        reconciliation=report,
        generated_minutes=generated_minutes,
    )
