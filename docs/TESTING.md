# Testing

CircleScribe treats financial-state correctness as a testable software property,
not an LLM prompt instruction.

## Backend test suite

Run:

```bash
cd backend
source .venv/bin/activate
python -m unittest discover -s tests -v
```

The suite covers:

- explicit corrections superseding earlier statements
- correction transaction-type inheritance
- low-confidence financial events requiring human review
- unknown members being rejected
- currency mismatch rejection
- loan requests not mutating the ledger
- parsing boundaries such as "100,000 for one month"
- WAV validation and 48 kHz → 16 kHz resampling
- final artifact blocking while review remains
- human confirmation and discard paths
- SQLite workflow persistence across store reconstruction
- HTTP API processing, resolution, reopening and recent-run listing

## Frontend production build

```bash
cd frontend
npm ci
npm run build
```

## Full submission check

With backend dependencies already installed:

```bash
./scripts/submission_check.sh
```

## AWS preflight

The normal preflight does not require AWS credentials:

```bash
python backend/scripts/preflight.py
```

Once AWS access is active:

```bash
export AWS_BEARER_TOKEN_BEDROCK='...'
export AWS_REGION=us-east-1
python backend/scripts/preflight.py --require-aws
```

Never commit the Bedrock key.
