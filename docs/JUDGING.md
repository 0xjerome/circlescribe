# CircleScribe — Judge Walkthrough

CircleScribe is designed around one safety boundary:

> **AI interprets language. Deterministic code validates financial state. Humans resolve genuine ambiguity.**

## Recommended evaluation path

### 1. Correction scenario

Choose **Correction demo** and process the meeting.

Expected outcome:

- Amina contribution: **50,000 UGX**
- John contribution: **20,000 UGX**
- Mary's loan repayment: **40,000 UGX**
- John's earlier **30,000 UGX** statement is superseded
- Sarah's **100,000 UGX loan request** becomes a follow-up action, not a ledger mutation
- receipts, minutes and audit evidence finalize automatically

This demonstrates that interpreting a financial conversation is different from
blindly turning every amount into a transaction.

### 2. Human judgment scenario

Choose **Ambiguity demo** and process the meeting.

Mary says that she *may* have paid 50,000 UGX but is not sure.

Expected outcome:

- the financial event is blocked
- no receipt is generated
- final outputs remain blocked
- one human-review item appears

Confirm 50,000 UGX.

CircleScribe reruns the same deterministic validator, resumes the workflow,
finalizes the receipt/minutes, and records the human decision in the audit log.

### 3. Durability

Restart the backend and reopen the meeting from **Recent meetings**.

The resolved decision and finalized artifacts should still be present.

### 4. Evidence

For a finalized meeting, use:

- **Download minutes**
- per-member **Download receipt**
- **Export audit JSON**
- **Download evidence bundle**

The evidence bundle contains the structured events, deterministic reconciliation,
human resolutions, receipts, follow-up actions, minutes and audit trail.

## AWS vs local development adapters

The production AI path is:

**Amazon Transcribe → AWS Strands Agents → Amazon Bedrock → deterministic validator**

The repository also contains clearly labeled local fallbacks used while the AWS
account is unavailable:

- MLX Whisper for local microphone transcription
- a narrow deterministic transcript extractor for exercising the rest of the workflow

These fallbacks are not presented as AWS inference. They exist so the complete
human-in-the-loop product workflow remains testable during development.

## What to inspect in the code

- `backend/app/agent.py` — Strands + Bedrock extraction adapter
- `backend/app/ledger.py` — deterministic financial integrity boundary
- `backend/app/workflow.py` — human exception resolution + workflow resume
- `backend/app/artifacts.py` — receipts, follow-ups and audit evidence
- `backend/app/store.py` — durable local state adapter
- `backend/tests/` — safety, persistence and API integration tests
