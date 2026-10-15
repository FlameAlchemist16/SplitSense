from agent.workflow_state import WorkflowState


def test_intake_missing_fields():
    state = WorkflowState()
    assert "bill image path" in state.intake_missing()
    state.image_path = "bill.jpg"
    state.member_ids = [1]
    assert state.intake_missing() == ["who paid the bill"]
    state.paid_by_id = 1
    assert state.intake_missing() == []
    state.paid_by_id = 99
    assert "payer must be one of the bill members" in state.intake_missing()
