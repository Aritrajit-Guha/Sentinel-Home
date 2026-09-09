from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def system_status():
    # TODO: expose monitoring/scheduler health for debugging
    return {"status": "running"}
