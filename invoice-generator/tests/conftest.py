"""Shared pytest setup for the Invoicer suite.

The environment is configured *here* rather than inside a test module because
``config.Config`` reads ``os.environ`` at class-definition time, which happens
on the first ``import config`` anywhere in the process. A test module that set
these afterwards would already be pointed at the developer's real
``invoices.db`` and, worse, at whatever real Stripe/SMTP credentials happened
to be sitting in a local ``.env``.

Every value below is obviously synthetic. No test in this suite talks to
Stripe, to an SMTP server, or to any database other than a per-test temporary
SQLite file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Neutralise anything a local .env would otherwise supply. These are set
# unconditionally (not setdefault) so a developer's real keys can never be
# picked up by a test run.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["FLASK_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["APP_ENV"] = "development"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "never"
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["STRIPE_PUBLISHABLE_KEY"] = ""
os.environ["STRIPE_WEBHOOK_SECRET"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["FROM_EMAIL"] = ""
os.environ["SENTRY_DSN"] = ""
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["PLATFORM_FEE_PERCENT"] = "0"
os.environ["PLATFORM_FEE_FLAT_CENTS"] = "0"
