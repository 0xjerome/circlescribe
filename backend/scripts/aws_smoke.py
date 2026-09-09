#!/usr/bin/env python3
"""Make one real CircleScribe Strands + Amazon Bedrock extraction request.

This is intentionally separate from the normal preflight:
- preflight proves local structure/configuration
- this script proves the AWS network/model path actually works

It never prints the API key.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agent import extract_events, get_agent_config  # noqa: E402


FALLBACK_TRANSCRIPT = """Amina: I paid fifty thousand for my savings contribution.
John: I paid thirty thousand.
John: Actually, correct my contribution. Make that twenty thousand, not thirty."""


def main() -> int:
    config = get_agent_config()
    print("CircleScribe AWS smoke test")
    print("=" * 72)
    print(f"Model:     {config.model_id}")
    print(f"Region:    {config.region}")
    print(f"Auth mode: {config.auth_mode}")
    print("API key:   present" if config.api_key else "API key:   not set; using AWS credential chain")
    print()

    sample_path = ROOT / "sample_data" / "demo_transcript.txt"
    transcript = sample_path.read_text(encoding="utf-8") if sample_path.exists() else FALLBACK_TRANSCRIPT

    print("Making one real Strands + Bedrock structured-output request...")
    try:
        extraction = extract_events(transcript)
    except Exception as exc:
        print()
        print("AWS SMOKE TEST FAILED")
        print(f"Exception: {type(exc).__name__}")
        print(f"Message:   {exc}")
        print()
        print(
            "This is a real network/model failure. Check account status, Bedrock model "
            "access, Anthropic first-use approval, API-key permissions, and region."
        )
        return 2

    print()
    print("AWS SMOKE TEST PASSED")
    print(f"Summary: {extraction.meeting_summary}")
    print(f"Events:  {len(extraction.events)}")
    for event in extraction.events:
        print(
            f" - {event.id}: {event.event_type.value} "
            f"member={event.member_id or '-'} amount={event.amount_minor or '-'} "
            f"confidence={event.confidence:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
