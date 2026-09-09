from fastapi import APIRouter

router = APIRouter()

@router.post("/{household_id}/confirm-safe")
def confirm_safe(household_id: str):
    # TODO: stand down response timer (Phase 7)
    return {"status": "confirmed", "household_id": household_id}
