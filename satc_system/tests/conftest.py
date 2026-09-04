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

# ── a run that opened no screen has to say so ────────────────────────────────
#
# `client-documents` has had this since August, after a proof declared 190
# documents fine when every one was unreadable. `satc_system` did not, and on
# 4 September the count beside every panel heading rendered at 1.10:1 against
# its own background -- invisible -- through 1,685 passing tests. Every one
# drove Flask's test client, which proves a page came back and cannot tell
# dark-on-dark from readable, or a live button from a dead one.
#
# So: a run that skipped or deselected the `renders` tests must SAY SO, at the
# end, where the number is read. A green line from a run that opened no screen
# looks exactly like a green line from one that opened all of them, and only
# one means what the reader takes it to mean. Behaviour 2 -- report the
# denominator -- applied to the test run itself.
#
# THE MARKER ALONE WOULD BE A SMOKE ALARM WITH NO BATTERY. It only fires when
# something is skipped, so it is worth nothing without at least one real
# browser test to skip: `tests/test_documents_in_a_browser.py`.

_UNOPENED: list = []


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "renders: opens the app in a real browser. Skipped without Playwright, "
        "and a run that skips them says so.")


def pytest_deselected(items):
    """What pytest actually dropped -- not what this file guesses it dropped.

    `pytest_collection_modifyitems` sees only THIS run's collection, so
    selecting a single file leaves nothing to count and the banner goes silent
    on exactly the runs most likely to mislead. This hook is handed the real
    deselections whatever was selected. Learned the same way in
    `client-documents/tests/conftest.py`.
    """
    _UNOPENED.extend(i for i in items if i.get_closest_marker("renders"))


def pytest_runtest_logreport(report):
    if report.when == "setup" and report.skipped and "renders" in report.keywords:
        _UNOPENED.append(report.nodeid)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _UNOPENED:
        return
    write = terminalreporter.write_line
    write("")
    write("=" * 70)
    write(f"  NO SCREEN WAS OPENED. {len(_UNOPENED)} browser test(s) did not run.")
    write("")
    write("  Everything above drove Flask's test client, which proves a page")
    write("  came back. It cannot see that a heading is invisible against its")
    write("  own background, or that a button posts nothing.")
    write("")
    write("  Both of those were real here on 4 September 2026.")
    write("")
    write("  Green above does not mean the screen works. Install Playwright")
    write("  and its browser, then run the whole suite:")
    write("      pip install playwright && python -m playwright install chromium")
    write("=" * 70)

# ── a number means nothing without the environment that produced it ──────────
#
# W7: the same commit passed in one checkout and failed in the other. Identical
# source, identical config, identically seeded store. The cause turned out to be
# pywin32 -- present in one venv, absent in the other -- so `/comms/outlook`
# took the COM branch in one and the mailto fallback in the other.
#
# Finding that one cause was not the same as finding the cause LIST, and I
# stopped at the first. Counted afterwards: the two checkouts differ by 35
# installed packages, and this source has eight `except ImportError` /
# `*_available()` probes that change behaviour on what happens to be installed.
# Any of them can do the same thing again, quietly, and the failure looks like
# a flaky test rather than an environment.
#
# So every run says what it had. Two runs whose capability lines match are
# comparable; two whose lines differ have explained their own disagreement
# before anybody goes looking for a bug. Behaviour 2 -- report the denominator
# -- applied to the environment rather than to the count.

def _capabilities() -> list[tuple[str, bool, str]]:
    """(name, present, what it changes). Probed, never assumed."""
    out = []

    def probe(name, fn, changes):
        try:
            out.append((name, bool(fn()), changes))
        except Exception:                     # noqa: BLE001 - absent is an answer
            out.append((name, False, changes))

    def _outlook():
        from satc.intake.email_draft import outlook_available
        return outlook_available()

    def _browser():
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True

    def _corpus():
        """ASKED THE WAY THE TESTS ASK IT.

        The first version checked that `corpus/` existed and was not empty. It
        is never empty -- it ships a README, a manifest and two fetch scripts --
        so the line said "yes" on a machine where every corpus test skipped for
        want of documents. A capability row that disagrees with the suite it
        describes is worse than no row: it is a denominator that lies.
        """
        from satc.scoreboard import load_corpus
        return bool(load_corpus())

    probe("desktop Outlook (pywin32)", _outlook, "/comms/outlook: COM draft vs mailto fallback")
    probe("Playwright + Chromium", _browser, "whether any screen is opened at all")
    probe("document corpus", _corpus, "the scoreboard tests")
    try:
        from satc import settings
        probe("local OCR (Tesseract)", settings.ocr_enabled, "the reader ladder's OCR rung")
        probe("local vision (Ollama)", settings.ollama_enabled, "the reader ladder's model rung")
        probe("cloud vision", settings.cloud_vision_enabled, "whether documents may leave the machine")
    except Exception:                          # noqa: BLE001
        pass
    return out


def pytest_report_header(config):
    """Printed at the TOP, where somebody reading a number will see it."""
    rows = _capabilities()
    width = max(len(n) for n, _, _ in rows)
    lines = ["what this run could reach (a different answer here is a different suite):"]
    for name, present, changes in rows:
        lines.append(f"  {'yes' if present else 'NO ':4} {name:<{width}}   {changes}")
    return lines
