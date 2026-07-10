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

# Loan periods (days) and borrowing caps per member type
LOAN_RULES = {
    "Student": {"max_books": 3, "loan_days": 14, "fine_rate": 0.5},
    "Faculty": {"max_books": 10, "loan_days": 30, "fine_rate": 0.0},
    "Member": {"max_books": 2, "loan_days": 14, "fine_rate": 1.0},
}