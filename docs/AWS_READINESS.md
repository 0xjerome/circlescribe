# AWS production-path readiness

CircleScribe keeps the production AI boundary separate from the local fallback.

## Production extraction path

```text
meeting transcript
    ↓
Strands Agent
    ↓
Amazon Bedrock / Claude Sonnet 4.6
    ↓
validated MeetingExtraction schema
    ↓
deterministic ledger validator
    ↓
human review only when needed
```

The production model adapter is `backend/app/agent.py`.

It uses an explicit `BedrockModel` configuration so the selected region is not
silently changed by an unrelated local AWS profile.

Default configuration:

```text
region: us-east-1
model:  global.anthropic.claude-sonnet-4-6
```

## Authentication

CircleScribe supports both:

1. Amazon Bedrock API key through `AWS_BEARER_TOKEN_BEDROCK`
2. the normal AWS/boto3 credential chain

A secret is never returned by the readiness endpoint.

## Configuration-only check

With the backend running:

```bash
curl http://localhost:8000/api/v1/aws/readiness
```

This endpoint deliberately returns `network_tested: false`.

## Real network smoke test

Once the AWS account is active:

```bash
cd ~/Downloads/circlescribe
source backend/.venv/bin/activate

export AWS_BEARER_TOKEN_BEDROCK='YOUR_KEY'
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1

python backend/scripts/aws_smoke.py
```

This makes a real Strands structured-output request through Amazon Bedrock.

A successful run ends with:

```text
AWS SMOKE TEST PASSED
```
