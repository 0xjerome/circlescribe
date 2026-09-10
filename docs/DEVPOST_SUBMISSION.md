# CircleScribe — Devpost Submission Copy

## Project name

**CircleScribe**

## Elevator pitch

**Turn community savings-group meetings into reconciled ledgers, receipts, minutes, and follow-ups automatically — flagging only ambiguous decisions for a human.**

## Inspiration

Community savings groups often run their most important financial workflow in conversation before anything reaches a digital ledger. Members announce contributions and loan repayments, correct themselves, request loans, dispute amounts, and make decisions together.

Software can digitize the final ledger, but somebody still has to interpret the meeting that created it. I built CircleScribe around one question: **what if the administrative work of a savings-group meeting could be automated without giving an AI authority to silently invent financial truth?**

The answer became the core principle: **AI interprets language. Deterministic code validates financial state. Humans resolve genuine ambiguity.**

## What it does

CircleScribe turns a savings-group meeting transcript into structured meeting events and reconciles them against deterministic financial rules. It can identify contributions and loan repayments, understand explicit corrections, prevent corrected/original values from both entering the ledger, distinguish loan requests from transactions, generate receipts and minutes, create operational follow-ups, produce an audit trail, and persist meeting history.

If a member says, “Maybe I paid fifty thousand, I am not sure,” CircleScribe does not guess. The validator blocks the event and final outputs, then asks a human to confirm or discard it. After the human responds, the same deterministic validator runs again before the workflow can complete.

## How I built it

I built CircleScribe as a separation between probabilistic language interpretation and deterministic financial validation.

The frontend is Next.js/TypeScript and the backend is FastAPI/Python. The production AI adapter uses **AWS Strands Agents** with **Amazon Bedrock** and structured Pydantic output. The agent interprets meeting language into typed events while preserving source evidence; it is explicitly not responsible for approving loans, doing ledger arithmetic, moving money, or inventing missing facts.

Before AI output reaches the ledger, CircleScribe validates the agent contract. A separate deterministic validator then enforces financial invariants including member identity, currency, confidence, correction semantics, transaction type, and human-review requirements.

The local workflow persists state in SQLite so meetings and human resolutions survive backend restarts. For microphone development on Apple Silicon, I added a clearly labeled MLX Whisper fallback that is kept separate from the production Amazon Transcribe path and is never presented as AWS inference.

The repository also contains automated backend safety/API integration tests, GitHub Actions CI, production frontend build verification, AWS readiness diagnostics, and a real Strands/Bedrock smoke-test script.

### AWS status — update before final submission

At the time this draft was written, my AWS account was temporarily suspended for an AWS account-verification review and AWS Support escalated it to the internal verification team. The Strands + Bedrock production adapter is implemented and contract-tested, but live AWS execution should only be claimed in the final submission if the real smoke test succeeds before the deadline.

## Challenges I ran into

The hardest problem was defining where AI authority should stop. “I paid 30,000 — actually make that 20,000” is one corrected contribution, not two payments. “I want a loan of 100,000” is a request, not money movement. “Maybe I paid 50,000” contains an amount but not enough certainty to alter financial state. A chair asking Mary to confirm her contribution is not evidence that Mary paid anything.

I solved this by treating the agent as an interpreter rather than the financial source of truth. I also made human intervention composable with deterministic validation: a human decision updates workflow state, and the validator runs again rather than writing directly to the ledger.

## Accomplishments that I'm proud of

CircleScribe demonstrably supersedes corrected statements instead of double-counting them, rejects unknown members and currency mismatches, escalates low-confidence events, keeps loan requests outside the ledger, blocks final receipts/minutes while ambiguity remains, reruns validation after human judgment, preserves review decisions across restarts, and generates auditable evidence for completed meetings.

The project also has automated regression coverage and CI around these behaviors, so the demo scenarios are not one-off hard-coded UI tricks.

## What I learned

Useful human-centered agents do not need to maximize autonomy. In a trust-sensitive workflow, a stronger design can come from giving the agent a smaller, clearer authority boundary. LLMs are good at interpreting messy language, deterministic software is better at enforcing accounting invariants, and humans are better at resolving genuine uncertainty.

I also learned that an audit trail is part of the user experience for an agentic system: people need to see what the agent inferred, what deterministic code accepted or rejected, what a human changed, and why the final record exists.

## What's next for CircleScribe

The immediate next step is completing the production AWS deployment: Amazon Transcribe for meeting audio, Strands Agents + Amazon Bedrock for interpretation, DynamoDB for durable workflow state, S3 for evidence artifacts, and AgentCore/CloudWatch where appropriate for runtime and observability.

Beyond the hackathon, I would focus on real savings-group pilots, multilingual meetings, configurable group constitutions/rules, stronger speaker attribution, offline/low-bandwidth workflows, and integrations with bookkeeping/mobile-money systems.

The product goal remains the same: **automate the administrative burden of the meeting without automating away the group's financial authority.**
