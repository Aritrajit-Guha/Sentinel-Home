from pydantic import BaseModel
from typing import List, Optional

class HouseholdCreate(BaseModel):
    location: str
    latitude: float
    longitude: float
    building_type: str
    household_size: int
    vulnerable_members: Optional[List[str]] = []
    emergency_contact: str
