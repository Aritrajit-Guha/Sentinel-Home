# Phase 4: below threshold -> silent monitoring; above -> trigger response workflow
THRESHOLD = 0.6

def threshold_check(state):
    state["triggered"] = state["urgency_score"] >= THRESHOLD
    return state
