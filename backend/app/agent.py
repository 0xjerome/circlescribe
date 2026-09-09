from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from strands import Agent
from strands.models import BedrockModel

from .agent_tools import get_demo_group_rules, get_supported_meeting_event_types
from .models import EventType, MeetingExtraction

DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_STRANDS_MODEL = "global.anthropic.claude-sonnet-4-6"

SYSTEM_PROMPT = """
You are CircleScribe's meeting event extraction agent.

Your job is interpretation, not financial authorization.

Interpret a community savings-group transcript and return structured events.
Do not perform ledger arithmetic, approve loans, move money, or invent missing facts.
Use the tools to learn the supported schema and synthetic demo-group rules.
Preserve exact source evidence for every event.
Never guess a member or unclear amount.
When confidence is low, keep confidence low so deterministic code can escalate it.
If a speaker explicitly corrects an earlier statement, emit a correction event and
set supersedes_event_id to the earlier event.
A discussion of a possible loan is not an approval or disbursement.

The deterministic validator outside this agent is the financial source of truth.
"""


@dataclass(frozen=True)
class AwsAgentConfig:
    model_id: str
    region: str
    api_key: str | None
    auth_mode: Literal["bedrock-api-key", "aws-credential-chain"]

    def public_dict(self) -> dict[str, str | bool]:
        """Return diagnostic configuration without exposing credentials."""
        return {
            "model_id": self.model_id,
            "region": self.region,
            "auth_mode": self.auth_mode,
            "api_key_present": self.api_key is not None,
            "runtime_endpoint": f"https://bedrock-runtime.{self.region}.amazonaws.com",
        }


def get_agent_config() -> AwsAgentConfig:
    """Resolve CircleScribe's Bedrock configuration explicitly.

    Passing the region directly to BedrockModel prevents an unrelated local AWS
    profile from silently overriding the region selected for the hackathon.
    """
    model_id = os.getenv("STRANDS_MODEL", DEFAULT_STRANDS_MODEL).strip()
    region = (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_AWS_REGION
    ).strip()
    api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    api_key = api_key.strip() if api_key and api_key.strip() else None

    return AwsAgentConfig(
        model_id=model_id,
        region=region,
        api_key=api_key,
        auth_mode="bedrock-api-key" if api_key else "aws-credential-chain",
    )


def get_aws_readiness() -> dict[str, Any]:
    """Describe configuration only; this does not claim AWS is reachable."""
    config = get_agent_config()
    return {
        **config.public_dict(),
        "configured": bool(config.model_id and config.region),
        "network_tested": False,
        "note": (
            "Configuration only. Run backend/scripts/aws_smoke.py to make a real "
            "Strands + Bedrock request."
        ),
    }


def build_agent(config: AwsAgentConfig | None = None) -> Agent:
    config = config or get_agent_config()
    model = BedrockModel(
        model_id=config.model_id,
        region_name=config.region,
        api_key=config.api_key,
        temperature=0.0,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_supported_meeting_event_types, get_demo_group_rules],
        callback_handler=None,
    )


def validate_extraction_contract(extraction: MeetingExtraction) -> MeetingExtraction:
    """Reject malformed agent output before it reaches financial validation.

    This is not ledger validation. It only protects the boundary between the
    probabilistic agent and the deterministic workflow.
    """
    if not extraction.meeting_summary.strip():
        raise ValueError("Agent extraction must include a non-empty meeting summary.")

    seen_ids: set[str] = set()
    for event in extraction.events:
        if not event.id.strip():
            raise ValueError("Every extracted event requires a non-empty id.")
        if event.id in seen_ids:
            raise ValueError(f"Agent extraction returned duplicate event id '{event.id}'.")
        seen_ids.add(event.id)

        if not event.source_text.strip():
            raise ValueError(f"Event '{event.id}' is missing source evidence.")

        if event.event_type != EventType.CORRECTION and event.supersedes_event_id is not None:
            raise ValueError(
                f"Only correction events may supersede another event ('{event.id}')."
            )
        if event.supersedes_event_id == event.id:
            raise ValueError(f"Correction event '{event.id}' cannot supersede itself.")

    return extraction


def extract_events(transcript: str, *, agent: Any | None = None) -> MeetingExtraction:
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    runner = agent or build_agent()
    result = runner(transcript, structured_output_model=MeetingExtraction)
    structured = getattr(result, "structured_output", None)
    if structured is None:
        raise RuntimeError("Strands returned no structured meeting extraction.")

    if not isinstance(structured, MeetingExtraction):
        structured = MeetingExtraction.model_validate(structured)

    return validate_extraction_contract(structured)
