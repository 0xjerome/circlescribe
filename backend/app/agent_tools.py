from strands import tool

@tool
def get_supported_meeting_event_types() -> list[str]:
    """Return the event types CircleScribe supports."""
    return ["attendance", "contribution", "loan_repayment", "loan_request", "fine", "expense", "decision", "correction"]

@tool
def get_demo_group_rules() -> dict:
    """Return synthetic demo-group rules used to constrain extraction."""
    return {
        "currency": "UGX",
        "known_members": {
            "m-001": ["Amina", "Ami"],
            "m-002": ["John", "Jon"],
            "m-003": ["Mary"],
            "m-004": ["Sarah"]
        },
        "policy": {
            "never_guess_member": True,
            "never_guess_amount": True,
            "corrections_must_reference_prior_event": True
        }
    }
