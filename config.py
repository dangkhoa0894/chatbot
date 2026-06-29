import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DEEPINFRA_API_KEY: str = os.getenv("DEEPINFRA_API_KEY", "")
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    # Llama-3.3-70B has much better Vietnamese understanding and instruction following
    # than Gemma-3-12B. Override with DEEPINFRA_MODEL env var if needed.
    MODEL: str = os.getenv("DEEPINFRA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")

    # Per-agent model routing: intent uses a lighter model for speed;
    # closing/general use the full model for quality responses.
    AGENT_MODELS: dict = {
        "intent":  os.getenv("MODEL_INTENT",  os.getenv("DEEPINFRA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")),
        "closing": os.getenv("MODEL_CLOSING", os.getenv("DEEPINFRA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")),
        "general": os.getenv("MODEL_GENERAL", os.getenv("DEEPINFRA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")),
    }

    FB_PAGE_ACCESS_TOKEN: str = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    FB_VERIFY_TOKEN: str = os.getenv("FB_VERIFY_TOKEN", "")
    FB_APP_SECRET: str = os.getenv("FB_APP_SECRET", "")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8290"))

    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")

    DB_PATH: str = os.getenv("DB_PATH", "data/chatbot.db")

    REDIS_URL: str = os.getenv("REDIS_URL", "")

    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # Escalation — set to a webhook URL to receive real-time handoff events
    # e.g. Slack incoming webhook, Freshdesk, Zalo OA webhook, etc.
    ESCALATION_WEBHOOK_URL: str = os.getenv("ESCALATION_WEBHOOK_URL", "")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:8290")
    SESSION_MAX_ENTRIES: int = int(os.getenv("SESSION_MAX_ENTRIES", "5000"))


settings = Settings()


def validate_config() -> None:
    errors = []
    if not settings.DEEPINFRA_API_KEY:
        errors.append("DEEPINFRA_API_KEY is required")
    if not settings.ADMIN_TOKEN:
        errors.append("ADMIN_TOKEN is required (set a strong random string)")
    if not settings.JWT_SECRET:
        errors.append("JWT_SECRET is required (min 32 chars)")
    if settings.JWT_SECRET and len(settings.JWT_SECRET) < 32:
        errors.append("JWT_SECRET must be at least 32 characters")
    if not settings.ADMIN_PASSWORD:
        errors.append("ADMIN_PASSWORD is required")
    if errors:
        raise RuntimeError("Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
