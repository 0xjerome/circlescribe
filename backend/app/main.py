from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .agent import extract_events
from .demo import correction_demo_request
from .ledger import reconcile
from .models import MeetingExtraction, ReconcileReport, ReconcileRequest

app = FastAPI(title="CircleScribe API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class TranscriptRequest(BaseModel):
    transcript: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "circlescribe-api"}

@app.post("/api/v1/extract", response_model=MeetingExtraction)
def extract(request: TranscriptRequest):
    try:
        return extract_events(request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Agent extraction failed. Check AWS credentials, Bedrock model access, and server logs.") from exc

@app.post("/api/v1/reconcile", response_model=ReconcileReport)
def reconcile_events(request: ReconcileRequest):
    return reconcile(request)

@app.post("/api/v1/demo/reconcile", response_model=ReconcileReport)
def demo_reconcile():
    return reconcile(correction_demo_request())
