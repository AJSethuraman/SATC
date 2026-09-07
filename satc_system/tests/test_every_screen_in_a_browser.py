"""Every screen in the app, opened in a real browser and looked at.

THE FIRM, 4 September 2026: *"it's time to work through all of the screens —
like for real."*

The day had already shown why. `test_documents_in_a_browser.py` opened ONE
screen and found two things 1,685 passing tests could not see: a heading count
rendering at 1.10:1 against its own background, and an N/A button that recorded
documents as received. The contrast fault was never local to that page — it was
one CSS rule under 32 headings across ten templates. Nothing had ever opened the
other twenty-nine screens.

**THE LIST COMES FROM THE APP, NOT FROM THIS FILE.** Every screen is discovered
from `url_map` at run time, so a route added next month is covered the day it
lands and a route deleted stops being asserted. A hand-written list of screens
is a list that goes stale exactly when somebody adds the screen nobody checked —
which is the shape of every other stale count found in this repository today.

**EVERY FAILURE IS COLLECTED, NEVER THE FIRST ONE.** A sweep that stops at the
first bad screen tells you about one screen. Behaviour 2: report the
denominator, and say how many of what you examined.
"""

from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
from urllib.request import urlopen

import pytest

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _p:
        _p.chromium.launch().close()
    HAS_BROWSER = True
except Exception:                    # pragma: no cover - no playwright/chromium
    HAS_BROWSER = False

needs_browser = pytest.mark.skipif(
    not HAS_BROWSER,
    reason="no Playwright/Chromium here — NO SCREEN IS BEING OPENED, and "
           "nothing below is being asserted")

pytestmark = [pytest.mark.renders, needs_browser]

# Routes that answer with a FILE rather than a page. Opening them in a browser
# asserts nothing about a screen; they are counted and named so the denominator
# stays honest rather than quietly shrinking.
NOT_SCREENS = {
    "/export", "/intake/organizer.pdf", "/withholding/audit.xlsx",
    # NOT A SCREEN, AND ITS 404 IS THE POINT. `/source?path=…` serves an
    # original document, and only one that the last intake actually read
    # (`STATE.intake_sources`). Asked for with no path -- which is what a
    # screen sweep does -- it correctly refuses. The sweep found it and called
    # it a broken screen; it is a path allow-list working. Asserted below
    # rather than merely excluded, because a control nobody has watched refuse
    # is not known to work.
    "/source",
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def app_and_url():
    """The real app, real port, throwaway seeded store. Never the firm's data."""
    os.environ["SATC_DATA_DIR"] = tempfile.mkdtemp(prefix="satc_screens_")
    from satc.app.server import create_app

    app = create_app()
    port = _free_port()
    threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port,
                               debug=False, use_reloader=False),
        daemon=True).start()
    for _ in range(100):
        try:
            urlopen(f"http://127.0.0.1:{port}/today", timeout=1).read()
            break
        except Exception:                                  # noqa: BLE001
            time.sleep(0.1)
    else:
        pytest.fail("the app never answered on its own port")
    return app, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def screens(app_and_url):
    """Every parameterless GET screen, discovered from the app itself."""
    app, _ = app_and_url
    found = sorted({
        str(r.rule) for r in app.url_map.iter_rules()
        if "GET" in r.methods and "<" not in str(r.rule)
        and not str(r.rule).startswith(("/static", "/api"))
    })
    return [s for s in found if s not in NOT_SCREENS]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _luminance(rgb):
    vals = [int(v) / 255 for v in rgb]
    vals = [(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
            for v in vals]
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def _contrast(fg: str, bg: str) -> float:
    nums = lambda c: c[c.index("(") + 1:c.index(")")].replace(",", " ").split()[:3]
    lf, lb = _luminance(nums(fg)), _luminance(nums(bg))
    return (max(lf, lb) + 0.05) / (min(lf, lb) + 0.05)


# ── the sweep ────────────────────────────────────────────────────────────────

def test_every_screen_opens_without_falling_over(app_and_url, screens, browser):
    """Not 'returns 200' — a Flask error page is a 500 and a rendered traceback
    is a 200 with a stack trace on it. This looks at what arrived."""
    _, base = app_and_url
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    broken = []
    for route in screens:
        resp = page.goto(base + route, wait_until="networkidle")
        body = page.content()
        if resp is None or resp.status >= 400:
            broken.append(f"{route}: HTTP {resp.status if resp else '—'}")
        elif "Traceback (most recent call last)" in body or "werkzeug" in body.lower():
            broken.append(f"{route}: a traceback rendered as a page")
        elif len(page.locator("body").inner_text().strip()) < 40:
            broken.append(f"{route}: opened blank")
    page.close()
    assert not broken, (
        f"{len(broken)} of {len(screens)} screens did not open:\n  "
        + "\n  ".join(broken))


def test_no_text_on_any_screen_is_invisible_against_its_background(
        app_and_url, screens, browser):
    """THE ONE THE CONTRAST BUG WOULD HAVE FAILED, on all thirty screens.

    `--charcoal` on `--navy` measured 1.10:1 under 32 headings in ten
    templates, and every one of those pages had been green for months. This
    reads what the browser actually paints, so a palette change that
    reintroduces it fails on the screen it breaks.

    Only the small print is checked — `.muted`, `.note`, badges, table headers.
    Body text on paper was never the failure and asserting it everywhere would
    make this a style test rather than a legibility one.
    """
    _, base = app_and_url
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    faint, looked_at = [], 0
    for route in screens:
        page.goto(base + route, wait_until="networkidle")
        rows = page.evaluate("""() => {
            const out = [];
            for (const e of document.querySelectorAll(
                    '.muted, .note, .badge, th, .chip, small')) {
                const t = (e.innerText || '').trim();
                if (!t || e.offsetParent === null) continue;
                const s = getComputedStyle(e);
                // START AT THE ELEMENT ITSELF. The first version initialised bg
                // to transparent and stepped to the parent before reading
                // anything, so an element WITH its own background was measured
                // against whatever sat behind it. That reported a badge --
                // dark red on pale pink, perfectly legible -- as 2.08:1 red on
                // navy, and would have had someone "fix" a colour that was
                // never wrong. Check the checker.
                let p = e, bg = s.backgroundColor;
                while (p && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
                    p = p.parentElement;
                    bg = p ? getComputedStyle(p).backgroundColor : 'rgb(255,255,255)';
                }
                out.push([t.slice(0, 40), s.color, bg]);
            }
            return out;
        }""")
        for text, fg, bg in rows:
            looked_at += 1
            ratio = _contrast(fg, bg)
            if ratio < 4.5:
                faint.append(f"{route}: {text!r} at {ratio:.2f}:1 ({fg} on {bg})")
    page.close()
    assert not faint, (
        f"{len(faint)} of {looked_at} pieces of small print, across "
        f"{len(screens)} screens, are below WCAG AA's 4.5:1:\n  "
        + "\n  ".join(sorted(set(faint))[:25]))


def test_no_screen_shows_a_raw_template_placeholder(app_and_url, screens, browser):
    """A merge field that reached the screen unfilled. `{{ }}`, `[CONFIRM:` or
    `None` standing where a value belongs is the failure this repository names
    first: nothing is produced until it has been opened."""
    _, base = app_and_url
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    leaks = []
    for route in screens:
        page.goto(base + route, wait_until="networkidle")
        text = page.locator("body").inner_text()
        for marker in ("{{", "}}", "[CONFIRM:", "<<", ">>"):
            if marker in text:
                i = text.index(marker)
                leaks.append(f"{route}: {marker} in {text[max(0,i-30):i+40]!r}")
    page.close()
    assert not leaks, (
        f"{len(leaks)} unrendered placeholder(s) reached a screen:\n  "
        + "\n  ".join(leaks[:15]))


def test_every_screen_was_actually_examined(screens):
    """The denominator, asserted rather than assumed.

    If route discovery silently returns nothing — a refactor moves the
    blueprint, `url_map` changes shape — every sweep above passes over an empty
    list and reports success. That is the failure mode this whole file exists
    to prevent, so it is worth one test.
    """
    assert len(screens) >= 25, (
        f"only {len(screens)} screens were discovered; the app had 27 "
        f"parameterless page routes on 4 September 2026. If screens were "
        f"deliberately removed, move this number down on purpose.")


# ── the one that is not a screen, and must keep refusing ─────────────────────

def test_the_source_endpoint_refuses_a_path_it_was_not_given(app_and_url, browser):
    """`/source` hands back an ORIGINAL CLIENT DOCUMENT off this disk. The only
    thing standing between that and any path on the machine is an allow-list of
    files the last intake read.

    A screen sweep asks for it with no path and gets a 404 -- which is the
    control working, and is why it is excluded from the sweep. Excluded and
    unasserted would be worse than never noticing: the exclusion would outlive
    the guard.
    """
    _, base = app_and_url
    page = browser.new_page()
    for probe in ("", "?path=C:/Windows/win.ini",
                  "?path=../../../../etc/passwd",
                  "?path=satc_vault.db"):
        resp = page.goto(base + "/source" + probe)
        assert resp is not None and resp.status == 404, (
            f"/source{probe} returned {resp.status if resp else '—'}; it must "
            f"serve only files the last intake read")
        assert "not available" in page.locator("body").inner_text().lower()
    page.close()
