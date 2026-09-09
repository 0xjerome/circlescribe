from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import extract_events
from .demo import correction_demo_request
from .ledger import reconcile
from .models import MeetingExtraction, ReconcileReport, ReconcileRequest
from .workflow import (
    DemoRunState,
    create_demo_run,
    generate_demo_minutes,
    reconcile_demo_run,
    resolve_demo_event,
)

app = FastAPI(title="CircleScribe API", version="0.3.0")
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
    run_id: str
    mode: str
    extraction: MeetingExtraction
    reconciliation: ReconcileReport
    generated_minutes: str
    resolved_event_ids: list[str]
    discarded_event_ids: list[str]


class HumanResolutionRequest(BaseModel):
    run_id: str
    event_id: str
    action: Literal["confirm", "discard"]
    amount_minor: int | None = Field(default=None, gt=0)
    member_id: str | None = None


# In-memory state is intentionally limited to the local-development demo. The
# production AWS deployment will persist workflow state outside the web process.
_demo_runs: dict[str, DemoRunState] = {}
_MAX_DEMO_RUNS = 100


def _demo_response(run_id: str, state: DemoRunState) -> DemoProcessResponse:
    report = reconcile_demo_run(state)
    return DemoProcessResponse(
        run_id=run_id,
        mode="local-deterministic-fallback",
        extraction=state.extraction,
        reconciliation=report,
        generated_minutes=generate_demo_minutes(state, report),
        resolved_event_ids=sorted(state.resolved_event_ids),
        discarded_event_ids=sorted(state.discarded_event_ids),
    )


def _store_demo_run(run_id: str, state: DemoRunState) -> None:
    # Keep this bounded during local testing. This is not production persistence.
    if len(_demo_runs) >= _MAX_DEMO_RUNS:
        oldest = next(iter(_demo_runs))
        _demo_runs.pop(oldest, None)
    _demo_runs[run_id] = state


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
    """Create a local workflow run while AWS account access is unavailable.

    This endpoint is deliberately labeled local-fallback and must not be
    represented in the hackathon demo as Strands/Bedrock inference.
    """
    try:
        state = create_demo_run(request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = str(uuid4())
    _store_demo_run(run_id, state)
    return _demo_response(run_id, state)


@app.post("/api/v1/demo/resolve", response_model=DemoProcessResponse)
def demo_resolve(request: HumanResolutionRequest) -> DemoProcessResponse:
    """Apply one human decision and resume the deterministic workflow."""
    state = _demo_runs.get(request.run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Demo run not found or expired.")

    try:
        resolve_demo_event(
            state,
            event_id=request.event_id,
            action=request.action,
            amount_minor=request.amount_minor,
            member_id=request.member_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _demo_response(request.run_id, state)
