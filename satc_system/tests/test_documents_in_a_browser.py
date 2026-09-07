"""The Documents screen, opened and used the way a preparer uses it.

THE FIRM, 4 September 2026, on being shown a screenshot of the chase panel:

    "do the instructions you understand have you not only open screens and
     screenshot them, but you are pressing buttons and opening screens and
     'typing' stuff to make sure it actually works? like if you were testing
     youtube you wouldn't just make sure video was there you would want the
     audio to work too"

They did not. The panel had been rendered, photographed and reported as
verified. Not one button on it had ever been pressed by anything.

S28 asks for the whole path a person walks, front to back. Behaviour 11 carries
the incident: *"the most productive act in a week-long session was the user
opening a payment page in a browser and photographing it. Sixty-plus tests were
passing. Not one of them opened the page."* This file is the half that
photographing does not reach.

WHAT ONLY A BROWSER CAN SEE, and what 1,685 passing tests could not: on
4 September the count beside every panel heading was `--charcoal` on `--navy`,
1.10:1, invisible. The span was in the DOM and its text was correct, so the
Flask test client was satisfied. A person could not see it. That is the whole
argument for this file existing, and the contrast assertion below is here so
that particular failure cannot come back unnoticed.

Skipped, loudly, where Playwright or Chromium is absent. A skipped check that
reports as a pass is the same failure in a smaller costume.
"""

from __future__ import annotations

import os
import socket
import tempfile
import threading

import pytest

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _p:                     # a browser must be there
        _b = _p.chromium.launch()
        _b.close()
    HAS_BROWSER = True
except Exception:                    # pragma: no cover - no playwright/chromium
    HAS_BROWSER = False

needs_browser = pytest.mark.skipif(
    not HAS_BROWSER,
    reason="no Playwright/Chromium here — the screen is NOT being opened, and "
           "nothing below is being asserted")

pytestmark = [pytest.mark.renders, needs_browser]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    """The real app, on a real port, against a throwaway seeded store.

    NEVER the firm's own data directory. The seeded demo store is what the
    screen shows when `SATC_DATA_DIR` points somewhere empty, and it is the
    only thing a browser test may look at.
    """
    os.environ["SATC_DATA_DIR"] = tempfile.mkdtemp(prefix="satc_browser_")
    from satc.app.server import create_app

    port = _free_port()
    app = create_app()
    t = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port,
                               debug=False, use_reloader=False),
        daemon=True)
    t.start()

    from urllib.request import urlopen
    import time
    for _ in range(100):                              # up to ~10s to come up
        try:
            urlopen(f"http://127.0.0.1:{port}/documents", timeout=1).read()
            break
        except Exception:                             # noqa: BLE001
            time.sleep(0.1)
    else:
        pytest.fail("the app never answered on its own port")
    return f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def page(server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": 1400, "height": 900})
        pg.goto(f"{server}/documents", wait_until="networkidle")
        yield pg
        browser.close()


# ── what the eye can see and a test client cannot ────────────────────────────

def test_every_panel_count_is_actually_legible(page):
    """THE ONE THAT WOULD HAVE CAUGHT IT.

    `.muted` inside a panel heading was `#1F2733` on `#0B1F3A` — 1.10:1, where
    WCAG AA asks 4.5:1. Present, correct, and invisible. Computed here from
    what the browser actually paints, so a future palette change that
    reintroduces it fails rather than ships.
    """
    def luminance(rgb):
        vals = [int(v) / 255 for v in rgb]
        vals = [(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
                for v in vals]
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]

    counts = page.locator(".panel h2 .muted")
    assert counts.count() > 0, "no panel counts on the page at all"

    for i in range(counts.count()):
        el = counts.nth(i)
        fg, bg = el.evaluate("""e => {
            const s = getComputedStyle(e);
            let p = e.parentElement, bg = getComputedStyle(p).backgroundColor;
            while (p && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
                p = p.parentElement;
                bg = p ? getComputedStyle(p).backgroundColor : 'rgb(255,255,255)';
            }
            return [s.color, bg];
        }""")
        nums = lambda c: c[c.index("(") + 1:c.index(")")].replace(",", " ").split()[:3]
        lf, lb = luminance(nums(fg)), luminance(nums(bg))
        ratio = (max(lf, lb) + 0.05) / (min(lf, lb) + 0.05)
        assert ratio >= 4.5, (
            f"{el.inner_text()!r} is {ratio:.2f}:1 against its background "
            f"({fg} on {bg}). WCAG AA asks 4.5:1. This is how the count beside "
            f"every heading went invisible on 4 September 2026.")


def test_the_chase_panel_is_on_the_page_and_ordered_longest_first(page):
    panel = page.locator(".panel:has(h2:has-text('Who owes us a document'))")
    rows = panel.locator("tr:has(td)")
    assert rows.count() > 0, "the chase panel rendered no rows"
    waits = []
    for i in range(rows.count()):
        text = rows.nth(i).locator("td").first.inner_text()
        digits = "".join(c for c in text if c.isdigit())
        if digits:
            waits.append(int(digits))
    assert waits == sorted(waits, reverse=True), (
        f"longest wait must be first; got {waits}")


# ── and the half a screenshot cannot reach ───────────────────────────────────

def test_pressing_received_actually_closes_the_request(page, server):
    """THE FIRM'S QUESTION, ASSERTED. A screenshot proves the button is drawn.
    Only pressing it proves the request closes."""
    page.goto(f"{server}/documents", wait_until="networkidle")
    before = page.locator("form button:has-text('Received')").count()
    assert before > 0, "no Received button to press"

    page.locator("form button:has-text('Received')").first.click()
    page.wait_for_load_state("networkidle")

    after = page.locator("form button:has-text('Received')").count()
    assert after == before - 1, (
        f"pressing Received left {after} open rows, was {before}. The button "
        f"is drawn but the request did not close.")


def test_marking_not_applicable_without_a_reason_is_refused(page, server):
    """The page says so in its own words: *"Marking something not applicable
    needs a reason — a bare N/A is indistinguishable from never having asked."*
    A promise printed under a form is worth what the form enforces."""
    page.goto(f"{server}/documents", wait_until="networkidle")
    na = page.locator("form button:has-text('N/A')")
    if na.count() == 0:
        pytest.skip("nothing outstanding left to mark N/A")
    before = na.count()

    na.first.click()
    page.wait_for_load_state("networkidle")

    still = page.locator("form button:has-text('N/A')").count()
    assert still == before, (
        "an empty N/A closed a request. Worse than it sounds: the route "
        "branched on whether a reason was typed, so a blank N/A took the "
        "SATISFIED path and recorded the document as RECEIVED — the register "
        "then said a client had sent something they had not.")
    assert "needs a reason" in page.content().lower() or "not closed" in page.content().lower(), (
        "it refused, silently. The reader is left looking at an unchanged row "
        "with no idea why.")


def test_a_reason_typed_into_the_box_is_kept(page, server):
    """Typing, then reading it back — the third thing a screenshot cannot do."""
    page.goto(f"{server}/documents", wait_until="networkidle")
    box = page.locator("input[placeholder*='not applicable']")
    if box.count() == 0:
        pytest.skip("nothing outstanding left to mark N/A")

    box.first.fill("they closed that account in March")
    page.locator("form button:has-text('N/A')").first.click()
    page.wait_for_load_state("networkidle")

    assert "closed that account in March" in page.content(), (
        "the reason was typed and accepted and is nowhere on the page "
        "afterwards — a record that was considered and then lost")
