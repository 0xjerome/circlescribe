from __future__ import annotations
import os
from strands import Agent
from .agent_tools import get_demo_group_rules, get_supported_meeting_event_types
from .models import MeetingExtraction

SYSTEM_PROMPT = """
You are CircleScribe's meeting event extraction agent.
Interpret a community savings-group transcript and return structured events.
Do not perform ledger arithmetic, approve loans, move money, or invent missing facts.
Use the tools to learn the supported schema and group rules.
Preserve source evidence. Never guess a member or unclear amount.
If a speaker explicitly corrects an earlier statement, emit a correction event and set supersedes_event_id.
A discussion of a possible loan is not an approval.
"""

def build_agent() -> Agent:
    model_id = os.getenv("STRANDS_MODEL", "global.anthropic.claude-sonnet-4-6")
    return Agent(model=model_id, system_prompt=SYSTEM_PROMPT, tools=[get_supported_meeting_event_types, get_demo_group_rules], callback_handler=None)

def extract_events(transcript: str) -> MeetingExtraction:
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")
    result = build_agent()(transcript, structured_output_model=MeetingExtraction)
    return result.structured_output
