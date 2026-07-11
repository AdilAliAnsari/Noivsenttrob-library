"""
Central configuration for the noivsenttrob backend.
All secrets are read from environment variables (see .env.example).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = os.getenv("NOIVSENTTROB_DB", str(BASE_DIR / "noivsenttrob.db"))

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")

APP_URL = os.getenv("APP_URL", "http://localhost:8000")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# Clerk configuration
def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    value = value.strip().lower()
    return "..." in value or value.startswith("your-") or value.startswith("pk_test_") or value.startswith("sk_test_")


def get_clerk_settings() -> dict[str, str]:
    publishable_key = os.getenv("CLERK_PUBLISHABLE_KEY", "").strip()
    secret_key = os.getenv("CLERK_SECRET_KEY", "").strip()
    frontend_api = os.getenv("CLERK_FRONTEND_API", "").strip()

    if _is_placeholder(publishable_key):
        publishable_key = ""
    if _is_placeholder(secret_key):
        secret_key = ""
    if _is_placeholder(frontend_api):
        frontend_api = ""

    js_src = ""
    if frontend_api:
        base_url = frontend_api.rstrip("/")
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = f"https://{base_url}"
        js_src = f"{base_url}/npm/@clerk/clerk-js@latest/dist/clerk.browser.js"

    return {
        "publishable_key": publishable_key,
        "secret_key": secret_key,
        "frontend_api": frontend_api,
        "js_src": js_src,
    }


_CLERK_SETTINGS = get_clerk_settings()
CLERK_PUBLISHABLE_KEY = _CLERK_SETTINGS["publishable_key"]
CLERK_SECRET_KEY = _CLERK_SETTINGS["secret_key"]
CLERK_FRONTEND_API = _CLERK_SETTINGS["frontend_api"]
CLERK_JS_SRC = _CLERK_SETTINGS["js_src"]

# Loan periods (days) and borrowing caps per member type
LOAN_RULES = {
    "Student": {"max_books": 3, "loan_days": 14, "fine_rate": 0.5},
    "Faculty": {"max_books": 10, "loan_days": 30, "fine_rate": 0.0},
    "Member": {"max_books": 2, "loan_days": 14, "fine_rate": 1.0},
}