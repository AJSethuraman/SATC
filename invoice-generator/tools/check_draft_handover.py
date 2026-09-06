"""Does the browser draft change hands only when somebody said so?

NOT PART OF THE SUITE, and it cannot be: the guard is JavaScript in a real
browser and `pytest` here has no Playwright. `tests/test_generator.py` asserts
the shape of the guard; this asserts the behaviour, and it is the only
executable evidence that the fix works.

    pip install playwright        # then a Chromium; see the repo README
    python out/walk/serve.sh &    # or any local instance
    python tools/check_draft_handover.py

Four scenarios, in one browser profile so the storage persists between them:

  1. a stranger leaves an anonymous draft, then somebody else logs in
     — the account must NOT inherit it;
  2. the real hand-off: type it signed out, press "Save & send it", make an
     account, come back — the draft MUST survive;
  3. the marker is spent — a second login must not re-adopt;
  4. a signed-in draft must NOT survive to the next anonymous visitor.

The leak this exists for: one origin-wide localStorage key meant a sender's
business details, and their client's name, address and prices, came back for
whoever opened the generator next on that machine. Raised by Codex on PR #289,
rounds seven and eight. Scoping the key fixed the obvious direction; only the
hand-off marker closed the rest.

Signing out here is done by dropping the session cookie rather than pressing
the button, because that is exactly the state the leak lives in: signed out,
browser storage untouched.
"""
import os
import pathlib
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5099"
EMAIL, PW = "billing@satcllp.example", "harbour-row-suite-400"
PROFILE = pathlib.Path(__file__).resolve().parent.parent / "out" / "draft-handover-profile"

def keys(page):
    return page.evaluate("""() => Object.fromEntries(
        Object.keys(localStorage).filter(k => k.startsWith('invoicer.'))
              .map(k => [k, (localStorage.getItem(k)||'').slice(0, 26)]))""")

def seed_anon(page, who):
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    el = page.query_selector("#gen [name='bill_to_name']")
    el.click(); el.fill(who); el.dispatch_event("input")
    page.wait_for_timeout(500)

def login(page):
    page.goto(f"{BASE}/login", wait_until="networkidle")
    if page.query_selector("input[name=password]"):
        page.fill("input[name=email]", EMAIL); page.fill("input[name=password]", PW)
        page.click("button[type=submit]"); page.wait_for_load_state("networkidle")

def logout(page):
    """Drop the session cookie and keep localStorage — which is precisely the
    state the leak lives in: signed out, browser storage untouched."""
    page.context.clear_cookies()

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE), headless=True, executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"),
        viewport={"width": 1280, "height": 900},
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("=== 1. a stranger leaves a draft, then somebody logs in ===")
    logout(page)
    seed_anon(page, "STRANGER LTD")
    print("  anonymous storage:", keys(page))
    login(page)
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    got = page.query_selector("#gen [name='bill_to_name']").input_value()
    print(f"  signed-in sees bill_to = {got!r}")
    assert "STRANGER" not in got, "the stranger's client leaked to the account"
    print("  storage after:", keys(page))

    print("\n=== 2. the real hand-off: type signed out, press Save & send it ===")
    logout(page)
    seed_anon(page, "NORTHWIND TRADERS")
    page.query_selector("#handoff").click()
    page.wait_for_load_state("networkidle")
    print("  marker set:", "invoicer.handoff.v1" in keys(page))
    login(page)
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    got = page.query_selector("#gen [name='bill_to_name']").input_value()
    print(f"  signed-in sees bill_to = {got!r}")
    assert "NORTHWIND" in got, "the sender lost their own draft across signup"
    print("  storage after:", keys(page))
    assert "invoicer.handoff.v1" not in keys(page), "the marker outlived its trip"

    print("\n=== 3. the marker is spent: a second login does not re-adopt ===")
    page.evaluate("() => Object.keys(localStorage).filter(k=>k.startsWith('invoicer.draft'))"
                  ".forEach(k => localStorage.removeItem(k))")
    logout(page)
    seed_anon(page, "SOMEBODY ELSE")
    login(page)
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    got = page.query_selector("#gen [name='bill_to_name']").input_value()
    print(f"  signed-in sees bill_to = {got!r}")
    assert "SOMEBODY" not in got, "adopted without a marker"

    print("\n=== 4. a signed-in draft does not survive to the next anonymous visitor ===")
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    el = page.query_selector("#gen [name='bill_to_name']")
    el.click(); el.fill("PRIVATE CLIENT LLC"); el.dispatch_event("input")
    page.wait_for_timeout(500)
    print("  storage while signed in:", keys(page))
    logout(page)
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    got = page.query_selector("#gen [name='bill_to_name']").input_value()
    print(f"  anonymous sees bill_to = {got!r}")
    assert "PRIVATE" not in got, "the account's client leaked to an anonymous visitor"
    print("  storage after:", keys(page))

    print("\nall four hold.")
    ctx.close()
