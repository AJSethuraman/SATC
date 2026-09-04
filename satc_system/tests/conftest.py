"""Test setup: isolate the SQLite store in a temp dir (don't touch build/data)."""

import os
import pytest
import tempfile

# Must be set before satc.app.state (which builds the module-level STATE) imports.
os.environ.setdefault("SATC_DATA_DIR", tempfile.mkdtemp(prefix="satc_test_store_"))


# ── no test may drive the desktop Outlook ────────────────────────────────────
#
# `/comms/outlook` calls `open_outlook_draft` unmocked (`comms_views.py:398`),
# which on a machine with pywin32 and classic Outlook does
# `Dispatch("Outlook.Application")` and `mail.Display(False)` — a real compose
# window, on the owner's screen, for every test that posts to that route.
#
# THAT HAPPENED. A full-suite run on 4 September 2026 opened Outlook drafts on
# the firm's machine, and they noticed before we did. Nothing was sent — there
# is no `.Send()` anywhere in this codebase, and no smtplib — but a test suite
# with a visible side effect on the owner's desktop is a test suite that will
# eventually be run less often, which is the real cost.
#
# IT ALSO MADE THE SUITE DISAGREE WITH ITSELF. `outlook_available()` is True in
# the checkout that has pywin32 and False in the one that does not, so
# `test_the_outlook_route_states_the_same_fee_the_screen_does` passed in one
# checkout and failed in the other on the same commit — recorded as W7 while
# the cause was still unknown. This is the cause.
#
# Forced to the unavailable branch, which is the one every machine without
# pywin32 already takes, so the tests exercise the path most installs run.
# A test that wants the COM branch monkeypatches it back itself.
@pytest.fixture(autouse=True)
def _no_desktop_outlook(monkeypatch):
    try:
        from satc.intake import email_draft
    except ImportError:
        return
    monkeypatch.setattr(
        email_draft, "open_outlook_draft",
        lambda **kw: email_draft.DraftResult(
            False, "unavailable", "disabled in tests: no test drives desktop Outlook"))
    monkeypatch.setattr(email_draft, "outlook_available", lambda: False)
