import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DEEPINFRA_API_KEY: str = os.getenv("DEEPINFRA_API_KEY", "")
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    MODEL: str = os.getenv("DEEPINFRA_MODEL", "EleutherAI/gpt-neox-20b")
    FB_PAGE_ACCESS_TOKEN: str = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    FB_VERIFY_TOKEN: str = os.getenv("FB_VERIFY_TOKEN", "chatbot_verify_2024")
    FB_APP_SECRET: str = os.getenv("FB_APP_SECRET", "")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "admin123")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@2026")
    DB_PATH: str = os.getenv("DB_PATH", "data/chatbot.db")


settings = Settings()
