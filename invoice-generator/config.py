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


def _normalize_db_url(url):
    """Make a managed-Postgres URL compatible with SQLAlchemy + psycopg v3.

    Hosts like Render/Heroku hand out ``postgres://...`` which SQLAlchemy no
    longer accepts; rewrite it to the explicit ``postgresql+psycopg://`` form.
    """
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Config:
    # Flask
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

    # Database: SQLite by default; set DATABASE_URL to a Postgres URL in prod.
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'invoices.db'}")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Filesystem location for transient generated PDFs (regenerated on demand).
    INVOICES_DIR = BASE_DIR / "invoices"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload cap

    # Session cookie hardening. SECURE is enabled in production (see
    # create_app); SameSite=Lax mitigates cross-site request forgery.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Public base URL used when building Stripe redirect / webhook URLs
    # and absolute links (e.g. PDF URLs) in JSON API responses. On Render,
    # RENDER_EXTERNAL_URL is provided automatically, so this needs no manual
    # setup when hosted there.
    APP_BASE_URL = (
        os.environ.get("APP_BASE_URL")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or "http://localhost:5000"
    )

    # Set to "production" to enable secure cookies and disable debug niceties.
    ENV = os.environ.get("APP_ENV", "development")

    # Error monitoring (optional): set a Sentry DSN to capture exceptions.
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

    # Rate limiting storage (in-memory by default; set a redis:// URL when
    # running multiple instances so limits are shared).
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Email verification is enforced only when email is actually configured
    # (so a fresh deploy without SMTP never locks anyone out). Override with
    # REQUIRE_EMAIL_VERIFICATION=always / never if needed.
    REQUIRE_EMAIL_VERIFICATION = os.environ.get(
        "REQUIRE_EMAIL_VERIFICATION", "auto"
    )

    # --- Monetization (built but OFF by default; flip on when ready) -----
    # Per-payment platform fee taken via Stripe Connect (your cut). 0 = off.
    PLATFORM_FEE_PERCENT = float(os.environ.get("PLATFORM_FEE_PERCENT", "0"))
    PLATFORM_FEE_FLAT_CENTS = int(
        os.environ.get("PLATFORM_FEE_FLAT_CENTS", "0")
    )
    # Subscription tiers / paywall. When False, everything is free and no
    # plan limits are enforced.
    BILLING_ENABLED = os.environ.get("BILLING_ENABLED", "false").lower() == "true"

    # PDF rendering engine: "auto" (default), "weasyprint", or "xhtml2pdf".
    # auto uses WeasyPrint when its native libraries are available and falls
    # back to the pure-Python xhtml2pdf engine otherwise (e.g. on Windows).
    PDF_ENGINE = os.environ.get("PDF_ENGINE", "auto")

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
