from typing import TypedDict, Optional

class AgentState(TypedDict):
    household_id: str
    urgency_score: float
    triggered: bool
    guidance_message: Optional[str]
    acknowledged: bool
    escalation_level: int  # 0=none, 1=call, 2=emergency contact
