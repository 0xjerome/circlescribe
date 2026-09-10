# CircleScribe — Demo Video Script

Target length: **4:15–4:40** (under the 5-minute limit).

## 0:00–0:25 — Problem

> Community savings groups often conduct their real financial workflow in a meeting before anything reaches a digital ledger. Existing software can store the ledger — CircleScribe automates the meeting that creates it.

Show the home screen and explain that CircleScribe creates structured records, reconciled ledger entries, receipts, minutes, follow-ups, and an audit trail.

## 0:25–0:45 — Trust model

Show the architecture diagram.

> AI interprets language, deterministic code validates financial state, and humans resolve genuine ambiguity. The language model never becomes the ledger.

If AWS is still externally blocked when recording, say clearly that the repository contains the real Strands/Bedrock adapter but this recording uses the labeled local development adapter. If AWS is restored, show the real production path instead.

## 0:45–2:05 — Correction scenario

Process the correction meeting. Show that:

- Amina → 50,000 UGX contribution
- John → 20,000 UGX contribution after correcting 30,000
- Mary → 40,000 UGX loan repayment
- Sarah → 100,000 UGX loan request becomes a follow-up, not a ledger entry

Show receipts, minutes, and evidence controls.

## 2:05–3:25 — Ambiguity + human review

Process `Mary: Maybe I paid fifty thousand, I am not sure.`

Show `needs_review`, blocked final artifacts, and the review card.

Confirm 50,000 UGX.

Explain that the human decision does not bypass validation; the same deterministic validator runs again before reconciliation succeeds.

## 3:25–3:55 — Persistence + evidence

Open Recent meetings and reopen the resolved run. Show the evidence bundle/audit export.

## 3:55–4:20 — Engineering proof

Show the GitHub Actions page and tests briefly.

Explain that corrections, unknown members, currency mismatch, low-confidence events, non-mutating loan requests, human resolution, persistence, API flows, and production frontend build are regression-tested.

## 4:20–4:40 — Close

> CircleScribe is not trying to replace the people who govern a savings group. It automates the administrative work around them and preserves human judgment where trust actually matters.

> Everybody digitized the ledger. CircleScribe automates the meeting that creates the ledger.
