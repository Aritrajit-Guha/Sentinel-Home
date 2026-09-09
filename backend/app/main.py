from fastapi import FastAPI
from app.api import households, alerts, admin

app = FastAPI(title="SentinelHome API")

app.include_router(households.router, prefix="/api/households", tags=["households"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

@app.get("/health")
def health():
    return {"status": "ok"}
