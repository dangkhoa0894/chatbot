import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    FB_PAGE_ACCESS_TOKEN: str = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    FB_VERIFY_TOKEN: str = os.getenv("FB_VERIFY_TOKEN", "chatbot_verify_2024")
    FB_APP_SECRET: str = os.getenv("FB_APP_SECRET", "")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


settings = Settings()
