from .models import EventType, ExtractedEvent, GroupState, Member, ReconcileRequest

def demo_group() -> GroupState:
    return GroupState(group_id="circle-demo-001", currency="UGX", members=[
        Member(id="m-001", display_name="Amina", aliases=["Ami"]),
        Member(id="m-002", display_name="John", aliases=["Jon"]),
        Member(id="m-003", display_name="Mary"),
        Member(id="m-004", display_name="Sarah"),
    ])

def correction_demo_request() -> ReconcileRequest:
    return ReconcileRequest(group=demo_group(), events=[
        ExtractedEvent(id="evt-001", event_type=EventType.CONTRIBUTION, member_id="m-002", amount_minor=30000, currency="UGX", confidence=0.98, source_text="John: I paid thirty thousand."),
        ExtractedEvent(id="evt-002", event_type=EventType.CORRECTION, member_id="m-002", amount_minor=20000, currency="UGX", confidence=0.99, source_text="John: Actually, make that twenty thousand.", supersedes_event_id="evt-001"),
    ])
