from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import extract_events
from .audio import LocalTranscriptionUnavailable, UnsupportedAudioError, transcribe_wav_bytes
from .artifacts import AuditRecord, FollowUpAction, Receipt, generate_completion_artifacts
from .demo import correction_demo_request
from .ledger import reconcile
from .models import MeetingExtraction, ReconcileReport, ReconcileRequest
from .store import LocalRunStore
from .workflow import (
    DemoRunState,
    create_demo_run,
    generate_demo_minutes,
    reconcile_demo_run,
    resolve_demo_event,
)

app = FastAPI(title="CircleScribe API", version="0.6.0")
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
    artifacts_finalized: bool
    receipts: list[Receipt]
    follow_up_actions: list[FollowUpAction]
    audit_log: list[AuditRecord]




class DemoRunSummary(BaseModel):
    run_id: str
    created_at: str
    updated_at: str
    meeting_summary: str
    status: Literal["reconciled", "needs_review"]
    review_items: int
    ledger_entries: int
    artifacts_finalized: bool


class LocalAudioTranscriptionResponse(BaseModel):
    transcript: str
    mode: Literal["local-mlx-whisper"] = "local-mlx-whisper"
    model: str
    duration_seconds: float
    warning: str = (
        "Development fallback only. Final hackathon inference uses AWS Strands Agents "
        "and Amazon Transcribe/Bedrock once AWS account access is restored."
    )


class HumanResolutionRequest(BaseModel):
    run_id: str
    event_id: str
    action: Literal["confirm", "discard"]
    amount_minor: int | None = Field(default=None, gt=0)
    member_id: str | None = None


# Local SQLite persistence keeps demo workflow state durable across backend
# restarts. The AWS deployment will replace this adapter with DynamoDB while
# preserving the same workflow-state boundary.
_demo_store = LocalRunStore.from_env()


def _demo_response(run_id: str, state: DemoRunState) -> DemoProcessResponse:
    report = reconcile_demo_run(state)
    artifacts = generate_completion_artifacts(state, report)
    return DemoProcessResponse(
        run_id=run_id,
        mode="local-deterministic-fallback",
        extraction=state.extraction,
        reconciliation=report,
        generated_minutes=generate_demo_minutes(state, report),
        resolved_event_ids=sorted(state.resolved_event_ids),
        discarded_event_ids=sorted(state.discarded_event_ids),
        artifacts_finalized=artifacts.finalized,
        receipts=artifacts.receipts,
        follow_up_actions=artifacts.follow_up_actions,
        audit_log=artifacts.audit_log,
    )


def _store_demo_run(run_id: str, state: DemoRunState) -> None:
    _demo_store.save(run_id, state)


def _load_demo_run(run_id: str) -> DemoRunState | None:
    record = _demo_store.get(run_id)
    return record.state if record is not None else None


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


@app.post("/api/v1/demo/audio/transcribe", response_model=LocalAudioTranscriptionResponse)
async def demo_audio_transcribe(audio: UploadFile = File(...)) -> LocalAudioTranscriptionResponse:
    """Transcribe a real microphone recording locally on Apple Silicon.

    This endpoint is a development fallback and is intentionally separate from
    the production Amazon Transcribe path described in the submission architecture.
    """
    data = await audio.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file exceeds the 25 MB local demo limit.")

    try:
        transcript, model, duration = transcribe_wav_bytes(data)
    except UnsupportedAudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LocalTranscriptionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Local transcription failed. Check backend logs.") from exc

    return LocalAudioTranscriptionResponse(
        transcript=transcript,
        model=model,
        duration_seconds=round(duration, 2),
    )


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
    state = _load_demo_run(request.run_id)
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

    _store_demo_run(request.run_id, state)
    return _demo_response(request.run_id, state)


@app.get("/api/v1/demo/runs", response_model=list[DemoRunSummary])
def demo_list_runs(limit: int = 10) -> list[DemoRunSummary]:
    """List durable local demo sessions, most recently updated first."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50.")

    summaries: list[DemoRunSummary] = []
    for record in _demo_store.list_runs(limit=limit):
        report = reconcile_demo_run(record.state)
        artifacts = generate_completion_artifacts(record.state, report)
        summaries.append(DemoRunSummary(
            run_id=record.run_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            meeting_summary=record.state.extraction.meeting_summary,
            status=report.status,
            review_items=len(report.exceptions),
            ledger_entries=len(report.entries),
            artifacts_finalized=artifacts.finalized,
        ))
    return summaries


@app.get("/api/v1/demo/runs/{run_id}", response_model=DemoProcessResponse)
def demo_get_run(run_id: str) -> DemoProcessResponse:
    """Retrieve a durable local demo session by id."""
    state = _load_demo_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Demo run not found.")
    return _demo_response(run_id, state)
