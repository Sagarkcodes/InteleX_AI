import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

# Load project-level environment variables first, while keeping the legacy
# ai_module/.env location as a fallback for existing local setups.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "ai_module" / ".env")


@dataclass(frozen=True)
class AppConfig:
    secret_key: str = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    upload_folder: str = os.getenv("UPLOAD_FOLDER", "static/uploads")
    debug: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    database_uri: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(INSTANCE_DIR / 'intelex.db').as_posix()}"
    )


config = AppConfig()
