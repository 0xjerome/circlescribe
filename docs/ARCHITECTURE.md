# CircleScribe Architecture

## Trust boundary

CircleScribe separates **probabilistic interpretation** from **deterministic financial state**.

### Probabilistic layer
AWS Strands Agents + Amazon Bedrock interpret speech, classify event types, recognize corrections, preserve evidence, and assign confidence.

### Deterministic layer
Python code validates members, amounts, currency, duplicate identifiers, corrections, confidence thresholds, and ledger invariants.

### Human layer
Humans resolve ambiguous identity, unclear amounts, contradictions, and other exceptions that cannot be resolved safely.

AgentCore Runtime and observability will host and trace the Strands execution for the hackathon deployment.
