from fastapi import APIRouter
from app.models.household import HouseholdCreate

router = APIRouter()

@router.post("/")
def register_household(payload: HouseholdCreate):
    # TODO: persist to MongoDB (Phase 1)
    return {"status": "registered", "household": payload}
