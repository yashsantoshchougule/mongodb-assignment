

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _integer_setting(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class Config:

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or secrets.token_urlsafe(32)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "valuevista_mini")
    MONGO_SERVER_SELECTION_TIMEOUT_MS = _integer_setting(
        "MONGO_SERVER_SELECTION_TIMEOUT_MS", 5000
    )
MONGO_URI = Config.MONGO_URI
DATABASE_NAME = Config.MONGO_DB_NAME
MONGO_DB_NAME = Config.MONGO_DB_NAME
