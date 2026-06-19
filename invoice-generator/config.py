"""Application configuration loaded from environment variables.

Secrets are read from a local ``.env`` file (see ``.env.example``) using
python-dotenv. Nothing sensitive is hard-coded here.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load variables from .env if present.
load_dotenv(BASE_DIR / ".env")


class Config:
    # Flask
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

    # Database (SQLite)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'invoices.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Filesystem locations
    INVOICES_DIR = BASE_DIR / "invoices"
    UPLOAD_DIR = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload cap

    # Public base URL used when building Stripe redirect / webhook URLs
    # and absolute links (e.g. PDF URLs) in JSON API responses.
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

    # JSON REST API access token. When empty, the /api/* endpoints are
    # disabled (return 503) so the API is never unintentionally public.
    API_KEY = os.environ.get("API_KEY", "")

    # Stripe
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

    # SMTP / email
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    FROM_EMAIL = os.environ.get("FROM_EMAIL", "")
