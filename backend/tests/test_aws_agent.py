from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main
from app.agent import (
    DEFAULT_AWS_REGION,
    DEFAULT_STRANDS_MODEL,
    extract_events,
    get_agent_config,
    validate_extraction_contract,
)
from app.models import EventType, ExtractedEvent, MeetingExtraction


def valid_extraction() -> MeetingExtraction:
    return MeetingExtraction(
        meeting_summary="Two member statements were captured.",
        events=[
            ExtractedEvent(
                id="evt-1",
                event_type=EventType.CONTRIBUTION,
                member_id="m-001",
                amount_minor=50000,
                currency="UGX",
                confidence=0.99,
                source_text="Amina: I paid fifty thousand.",
            )
        ],
    )


class FakeAgent:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def __call__(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return SimpleNamespace(structured_output=self.output)


class AwsAgentContractTests(unittest.TestCase):
    def test_default_config_is_explicit_and_does_not_require_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            config = get_agent_config()

        self.assertEqual(config.model_id, DEFAULT_STRANDS_MODEL)
        self.assertEqual(config.region, DEFAULT_AWS_REGION)
        self.assertIsNone(config.api_key)
        self.assertEqual(config.auth_mode, "aws-credential-chain")

    def test_api_key_and_region_are_loaded_without_exposing_key_publicly(self):
        with patch.dict(
            os.environ,
            {
                "AWS_BEARER_TOKEN_BEDROCK": "secret-test-token",
                "AWS_REGION": "eu-north-1",
                "STRANDS_MODEL": "global.anthropic.claude-sonnet-4-6",
            },
            clear=True,
        ):
            config = get_agent_config()

        public = config.public_dict()
        self.assertEqual(config.auth_mode, "bedrock-api-key")
        self.assertEqual(config.region, "eu-north-1")
        self.assertTrue(public["api_key_present"])
        self.assertNotIn("secret-test-token", repr(public))

    def test_fake_strands_result_is_contract_validated(self):
        fake = FakeAgent(valid_extraction())
        output = extract_events("Amina: I paid fifty thousand.", agent=fake)

        self.assertEqual(output.events[0].amount_minor, 50000)
        self.assertEqual(len(fake.calls), 1)
        self.assertIs(fake.calls[0][1]["structured_output_model"], MeetingExtraction)

    def test_duplicate_agent_event_ids_are_rejected(self):
        event = valid_extraction().events[0]
        extraction = MeetingExtraction(
            meeting_summary="Duplicate ids",
            events=[event, event.model_copy()],
        )

        with self.assertRaisesRegex(ValueError, "duplicate event id"):
            validate_extraction_contract(extraction)

    def test_missing_source_evidence_is_rejected(self):
        extraction = valid_extraction()
        extraction.events[0].source_text = "  "

        with self.assertRaisesRegex(ValueError, "missing source evidence"):
            validate_extraction_contract(extraction)

    def test_non_correction_cannot_supersede_an_event(self):
        extraction = valid_extraction()
        extraction.events[0].supersedes_event_id = "evt-old"

        with self.assertRaisesRegex(ValueError, "Only correction events"):
            validate_extraction_contract(extraction)

    def test_readiness_endpoint_never_claims_network_was_tested(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/aws/readiness")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["configured"])
        self.assertFalse(data["network_tested"])
        self.assertIn(data["auth_mode"], {"bedrock-api-key", "aws-credential-chain"})
        self.assertNotIn("api_key", data)


if __name__ == "__main__":
    unittest.main()
