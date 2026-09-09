# CircleScribe

**Turn community savings-group meetings into reconciled ledgers, receipts, minutes, and follow-ups — escalating only genuine ambiguity to a human.**

CircleScribe is being built for the **AWS Agents for Humans Hackathon** using **AWS Strands Agents** and Amazon Bedrock.

## Core principle

> **AI interprets language. Deterministic code validates financial state. Humans resolve genuine ambiguity.**

The LLM is never the source of truth for ledger arithmetic.

## Current milestone

This starter repository separates the system into:

1. **Strands extraction layer** — converts a transcript into typed meeting events.
2. **Deterministic reconciliation layer** — validates member IDs, corrections, duplicates, amounts, confidence thresholds, and ledger invariants.
3. **Exception layer** — returns human-review items instead of silently guessing.
4. **FastAPI interface** — exposes health, extraction, and reconciliation endpoints.
5. **Minimal Next.js operator UI** — exercises the deterministic correction scenario.

## Architecture

The submission architecture image is in `docs/CircleScribe_Architecture_Submission.png`.

```text
Meeting Audio
    |
    v
Amazon S3 -> Amazon Transcribe
                    |
                    v
             Strands Agent
          + Amazon Bedrock
                    |
                    v
          Structured Events
                    |
                    v
     Deterministic Ledger Validator
             /              \
            /                \
      verified              ambiguous
         |                     |
         v                     v
   commit/output       human decision card
                               |
                               v
                         resume workflow
```


### Human-in-the-loop workflow resume

The local development workflow now supports a complete exception cycle:

```text
ambiguous event
    ↓
deterministic validator blocks ledger mutation
    ↓
human confirms / replaces the amount OR discards the event
    ↓
same validator runs again
    ↓
workflow resumes only if all invariants pass
```

Human review never bypasses deterministic validation. The local demo keeps run
state in memory; the production AWS deployment will persist workflow state.

## Backend quickstart

Requirements: Python 3.10+ and AWS credentials with Bedrock model access for AI extraction.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
cd backend
python -m unittest discover -s tests -v
```

The default Strands model is `global.anthropic.claude-sonnet-4-6`; override with `STRANDS_MODEL`.

## Frontend quickstart

```bash
cd frontend
npm install
npm run dev
```

The frontend expects `http://localhost:8000`; override with `NEXT_PUBLIC_API_URL`.

## API endpoints

- `GET /health`
- `POST /api/v1/extract` — real Strands + Bedrock structured extraction
- `POST /api/v1/reconcile` — deterministic validation
- `POST /api/v1/demo/reconcile` — synthetic 30,000 → corrected 20,000 UGX scenario

## Hackathon track

**Good Neighbor Agents**

## License

MIT

## Local full-workflow fallback

If AWS account access is temporarily unavailable, `POST /api/v1/demo/process`
exercises the full meeting → structured events → deterministic reconciliation →
draft minutes pipeline using a deliberately narrow deterministic extractor.

This endpoint returns `mode: local-deterministic-fallback` and must **never** be
presented as Strands or Bedrock inference. The production AI adapter remains
`POST /api/v1/extract`.

## Milestone 4 — completed-work artifacts

After deterministic reconciliation succeeds, the local workflow now produces:

- final per-member receipts for accepted ledger mutations
- operational follow-up actions such as reviewing a loan request
- an ordered audit trail showing extraction, validation, corrections, human resolutions, and output finalization
- downloadable meeting minutes and audit JSON in the UI

Final artifacts are deliberately blocked while any human-review item remains unresolved.
The local demo session can also be retrieved by run id from `GET /api/v1/demo/runs/{run_id}`.

## Local microphone transcription while AWS is suspended

Milestone 5 adds a real browser microphone recorder. For local development on
Apple Silicon, CircleScribe can transcribe the browser-generated PCM WAV with
MLX Whisper before sending the reviewed transcript through the existing
meeting workflow.

This is deliberately labeled a **development fallback**. The final AWS path
remains Amazon Transcribe + Strands Agents + Bedrock.

Install the optional local audio adapter:

```bash
cd backend
source .venv/bin/activate
uv pip install -e ".[dev,audio]"
```

The first transcription downloads the configured Whisper model. The default is
`mlx-community/whisper-tiny`; override it with:

```bash
export CIRCLESCRIBE_LOCAL_WHISPER_MODEL=mlx-community/whisper-small
```

Because the browser records 16-bit PCM WAV and the backend passes a NumPy
waveform directly to MLX Whisper, this development path does not depend on an
ffmpeg executable.

## Milestone 6 — durable local meeting history

Local development workflow state is now persisted in SQLite instead of an
in-memory dictionary. This means review decisions and finalized meetings
survive backend restarts and can be reopened from the Recent meetings panel.

The default database is `backend/.circlescribe/runs.sqlite3` and is git-ignored.
Override it for tests or alternate local environments with:

```bash
export CIRCLESCRIBE_RUN_DB=/path/to/runs.sqlite3
```

This is still a clearly labeled local-development adapter. The production AWS
deployment will move the same durable workflow-state boundary to DynamoDB.
Finalized sessions can also export a judge-friendly evidence bundle containing
structured extraction, deterministic reconciliation, receipts, follow-ups,
minutes, and the audit trail.
