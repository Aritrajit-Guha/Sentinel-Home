from pydantic import BaseModel
from datetime import datetime

class AlertLog(BaseModel):
    household_id: str
    urgency_score: float
    message_sent: str
    sent_at: datetime
    acknowledged: bool = False
