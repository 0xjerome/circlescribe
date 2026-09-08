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
