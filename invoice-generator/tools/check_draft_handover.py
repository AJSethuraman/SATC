"""Does an invoice ever move from an anonymous browser into an account
without a person saying so?

NOT PART OF THE SUITE, and it cannot be: the guard is JavaScript in a real
browser and `pytest` here has no Playwright. `tests/test_generator.py` asserts
the shape of the guard; this asserts the behaviour, and it is the only
executable evidence that the fix works.

    pip install playwright                     # then a Chromium
    ./out/walk/serve.sh &                      # or any local instance
    python tools/check_draft_handover.py

RESTART THE INSTANCE AFTER EDITING A TEMPLATE. `app.run(debug=False)` caches
them, so a running server keeps serving whatever it started with; two wrong
conclusions were drawn from probing a stale one.

Four scenarios, in one browser profile so the storage persists between them:

  1. a stranger leaves an anonymous draft, then somebody else signs in
     — the account gets NOTHING until the offer is answered, and "Discard it"
       leaves nothing behind;
  2. the genuine hand-off — "Bring it over" restores exactly what was typed;
  3. nothing is adopted merely by loading the page;
  4. a signed-in draft does NOT survive to the next anonymous visitor.

The leak this exists for: one origin-wide localStorage key meant a sender's
business details, and their client's name, address and prices, came back for
whoever opened the generator next on that machine. Raised by Codex on PR #289,
rounds seven, eight and nine. Scoping the key fixed one direction; a
"who pressed the button" marker fixed another and still could not tell whether
the person who signed in was the person who pressed it. Only asking can.

Signing out here is done by dropping the session cookie rather than pressing
the button, because that is exactly the state the leak lives in: signed out,
browser storage untouched.
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("INVOICER", "http://127.0.0.1:5099")
EMAIL = os.environ.get("INVOICER_EMAIL", "billing@satcllp.example")
PW = os.environ.get("INVOICER_PASSWORD", "harbour-row-suite-400")
PROFILE = pathlib.Path(__file__).resolve().parent.parent / "out" / "draft-handover-profile"


def keys(page):
    return page.evaluate("""() => Object.fromEntries(
        Object.keys(localStorage).filter(k => k.startsWith('invoicer.'))
              .map(k => [k, (localStorage.getItem(k)||'').length]))""")


def seed_anon(page, who):
    page.goto(f"{BASE}/generator", wait_until="networkidle")
    el = page.query_selector("#gen [name='bill_to_name']")
    el.click(); el.fill(who); el.dispatch_event("input")
    page.wait_for_timeout(500)


def login(page):
    page.goto(f"{BASE}/login", wait_until="networkidle")
    if page.query_selector("input[name=password]"):
        page.fill("input[name=email]", EMAIL)
        page.fill("input[name=password]", PW)
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")


def logout(page):
    """Drop the session cookie and keep localStorage — precisely the state the
    leak lives in: signed out, browser storage untouched."""
    page.context.clear_cookies()


def bill_to(page):
    return page.query_selector("#gen [name='bill_to_name']").input_value()


def offer_shown(page):
    bar = page.query_selector("#offer")
    return bool(bar) and bar.is_visible()


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True,
            executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"),
            viewport={"width": 1280, "height": 900},
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("=== 1. a stranger's draft, then somebody else signs in ===")
        logout(page)
        seed_anon(page, "STRANGER LTD")
        login(page)
        page.goto(f"{BASE}/generator", wait_until="networkidle")
        print(f"  offer shown: {offer_shown(page)}   bill_to on arrival: {bill_to(page)!r}")
        assert offer_shown(page), "the page took the draft without asking, or lost it"
        assert "STRANGER" not in bill_to(page), "adopted before anybody answered"
        page.query_selector("#offer-no").click()
        page.wait_for_timeout(200)
        print("  after Discard:", keys(page), "| bill_to:", repr(bill_to(page)))
        assert "STRANGER" not in bill_to(page)
        assert "invoicer.draft.v2.anon" not in keys(page), "discard left it behind"

        print("\n=== 2. the genuine hand-off ===")
        page.evaluate("() => Object.keys(localStorage)"
                      ".filter(k => k.startsWith('invoicer.'))"
                      ".forEach(k => localStorage.removeItem(k))")
        logout(page)
        seed_anon(page, "NORTHWIND TRADERS")
        login(page)
        page.goto(f"{BASE}/generator", wait_until="networkidle")
        assert offer_shown(page), "the offer did not appear for a real hand-off"
        page.query_selector("#offer-yes").click()
        page.wait_for_timeout(300)
        print("  after Bring it over:", repr(bill_to(page)))
        assert "NORTHWIND" in bill_to(page), "the sender lost their own draft"
        assert "invoicer.draft.v2.anon" not in keys(page)

        print("\n=== 3. loading the page adopts nothing on its own ===")
        page.evaluate("() => Object.keys(localStorage)"
                      ".filter(k => k.startsWith('invoicer.'))"
                      ".forEach(k => localStorage.removeItem(k))")
        logout(page)
        seed_anon(page, "SOMEBODY ELSE")
        login(page)
        page.goto(f"{BASE}/generator", wait_until="networkidle")
        print("  bill_to without touching the offer:", repr(bill_to(page)))
        assert "SOMEBODY" not in bill_to(page)
        page.goto(f"{BASE}/generator", wait_until="networkidle")   # and on reload
        assert "SOMEBODY" not in bill_to(page), "a second load adopted it"

        print("\n=== 4. a signed-in draft, then the next anonymous visitor ===")
        page.evaluate("() => Object.keys(localStorage)"
                      ".filter(k => k.startsWith('invoicer.'))"
                      ".forEach(k => localStorage.removeItem(k))")
        login(page)
        page.goto(f"{BASE}/generator", wait_until="networkidle")
        assert not offer_shown(page), "offered a draft when there is none"
        el = page.query_selector("#gen [name='bill_to_name']")
        el.click(); el.fill("PRIVATE CLIENT LLC"); el.dispatch_event("input")
        page.wait_for_timeout(500)
        print("  storage while signed in:", keys(page))
        logout(page)
        page.goto(f"{BASE}/generator", wait_until="networkidle")
        print("  anonymous sees:", repr(bill_to(page)))
        assert "PRIVATE" not in bill_to(page), "the account's client leaked out"
        assert not offer_shown(page), "an anonymous viewer was offered a draft"

        print("\nall four hold.")
        ctx.close()


if __name__ == "__main__":
    sys.exit(main())
