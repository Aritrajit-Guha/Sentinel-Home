# Phase 7: if no response, escalate (call -> emergency contact)
def escalation(state):
    if not state["acknowledged"]:
        state["escalation_level"] += 1
    return state
