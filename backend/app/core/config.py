import os

class Settings:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
    TWILIO_SID = os.getenv("TWILIO_SID", "")
    TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")

settings = Settings()
