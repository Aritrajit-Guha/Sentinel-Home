import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
# Support both local development (backend/.env) and a root-level .env while
# allowing Render or the shell to override either file.
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(PROJECT_DIR / ".env", override=False)


class Settings:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentinelhome")
    PERSISTENCE = os.getenv("PERSISTENCE", "memory").lower()
    REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
    TWILIO_SID = os.getenv("TWILIO_SID", "")
    TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
    APP_ENV = os.getenv("APP_ENV", "development")
    ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"
    MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "5"))

settings = Settings()
