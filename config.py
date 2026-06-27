import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DEEPINFRA_API_KEY: str = os.getenv("DEEPINFRA_API_KEY", "")
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    MODEL: str = os.getenv("DEEPINFRA_MODEL", "google/gemma-3-12b-it")

    # Per-agent model routing — use a smaller/faster model for intent,
    # a more capable one for closing/general if needed.
    AGENT_MODELS: dict = {
        "intent":  os.getenv("MODEL_INTENT",  os.getenv("DEEPINFRA_MODEL", "google/gemma-3-12b-it")),
        "closing": os.getenv("MODEL_CLOSING", os.getenv("DEEPINFRA_MODEL", "google/gemma-3-12b-it")),
        "general": os.getenv("MODEL_GENERAL", os.getenv("DEEPINFRA_MODEL", "google/gemma-3-12b-it")),
    }

    FB_PAGE_ACCESS_TOKEN: str = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    FB_VERIFY_TOKEN: str = os.getenv("FB_VERIFY_TOKEN", "chatbot_verify_2024")
    FB_APP_SECRET: str = os.getenv("FB_APP_SECRET", "")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8290"))

    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "admin123")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@2026")

    DB_PATH: str = os.getenv("DB_PATH", "data/chatbot.db")

    REDIS_URL: str = os.getenv("REDIS_URL", "")

    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # Escalation — set to a webhook URL to receive real-time handoff events
    # e.g. Slack incoming webhook, Freshdesk, Zalo OA webhook, etc.
    ESCALATION_WEBHOOK_URL: str = os.getenv("ESCALATION_WEBHOOK_URL", "")


settings = Settings()
