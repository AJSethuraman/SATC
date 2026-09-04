"""Every button in the app: where it goes, and what happens when it is pressed.

THE FIRM, 4 September 2026: *"it's time to work through all of the screens —
like for real."* Opening every screen was half of it. This is the other half.

**THE PAGES COME FROM FOLLOWING LINKS, not from a list.** A person reaches a
client by clicking a client, so this crawls the way they walk: start at the
parameterless screens and follow every same-origin link. That reaches 46 pages
where a hand-written list reached 27, and the difference is every detail
screen — which is where most of the buttons live.

**WHAT THIS FOUND THE FIRST TIME IT RAN — and the finding was mine.** The
census reported two dead buttons, on `/autonomy/digest` and `/pricing/history`.
Both are `method="get"` filter forms posting to their own page, which is
correct and ordinary; the check had assumed every form is a POST. That was the
third time in one day that a checker written to find faults produced the fault
itself, so the method is read from the form now rather than presumed.

Behaviour 3 — check the checker — is not a step at the end. It is the reason
the count below can be believed.
"""

from __future__ import annotations

import os
import re
import tempfile

import pytest

# POST endpoints that no page renders a button for IN THE SEEDED DEMO STORE.
# Each needs state the demo does not create — an issued invoice, a payment to
# match, a job in flight — so their absence is a fact about the fixture, not a
# missing button.
#
# THE LIST WAS WRONG IN BOTH DIRECTIONS THE FIRST TIME IT RAN, and the two
# tests below caught it: `/comms` had no button and no reason, while three
# entries -- the delivery email and both workflow endpoints -- had grown
# buttons since and were carrying stale excuses. A registry nobody checks
# rots into an alibi.
#
# THE LIST IS THE POINT. Without it, "26 endpoints have no button" is
# indistinguishable from "26 endpoints are orphaned", and the honest version of
# that sentence is the one that says which and why. Anything that leaves this
# list has grown a button; anything that arrives has lost one.
# STRUCTURAL: never a form target whatever is in the store. A JSON API has no
# screen; a page whose own form posts back to itself renders no `action`. These
# do not move with the data, so BOTH directions are asserted — missing is a
# finding and newly-present is a stale excuse.
NOT_A_BUTTON = {
    "/api/withholding/estimate":  "JSON API, not a screen",
    "/api/withholding/read-paystub": "JSON API, not a screen",
    "/intake/new":                "posted by the intake form's own page",
    "/intake/plan":               "posted by the plan page's own form",
    "/withholding/add-job":       "the withholding screen builds these client-side",
    "/withholding/clear-jobs":    "same",
    "/withholding/from-client":   "same",
    "/withholding/from-file":     "same",
    "/withholding/from-paystub":  "same",
    "/withholding/paystub/layout": "same",
    "/withholding/remove-job":    "same",
    "/withholding/save-layout":   "same",
}

# DATA-DEPENDENT: renders only when the store holds the right rows — an issued
# invoice, a payment to match, a job in flight.
#
# THESE ARE NOT ASSERTED IN EITHER DIRECTION, and that is the honest shape.
# `STATE` is module-level, built once from the environment at import, so these
# tests crawl whatever store the rest of the suite has left behind. Run alone
# they saw a clean seeded store; run after 1,600 other tests they saw one those
# tests had filled in — and both registry checks failed on the difference.
#
# Asserting a set that moves with test order is how a suite grows a test that
# fails for a reason unrelated to its name. Split rather than pinned: the
# structural half above is checked strictly, and this half is documentation.
NEEDS_DATA = {
    "/clients/<client_id>/delivery-email": "needs a client with a delivery address",
    "/clients/<client_id>/discard":       "needs a client staged for import",
    "/clients/import/confirm":            "needs an import previewed first",
    "/comms":                             "its own form posts back to it, so it renders only when that form does",
    "/comms/decide":                      "needs a drafted comm",
    "/comms/outlook":                     "needs a drafted comm",
    "/engagements/<job_id>/email/outlook": "needs a job",
    "/engagements/<job_id>/tasks/<task_id>": "needs a job with tasks",
    "/intake/organizer/email":            "needs an organizer built",
    "/intake/run":                        "needs documents dropped for intake",
    "/invoices/<invoice_id>/issue":       "needs a draft invoice",
    "/invoices/<invoice_id>/paid":        "needs an issued invoice",
    "/payments/<payment_id>/match":       "needs an unmatched payment",
    "/sort/apply":                        "needs files sorted first",
    "/staging/<path:field_id>/<action>":  "needs a field still staged — earlier tests confirm or clear them, so this renders alone and not after a full run",
    "/today/restore":                     "needs something dismissed today",
    "/work/<job_id>/delivered":           "needs a job",
    "/workflows/<key>/edit":              "needs a workflow opened for editing",
    "/workflows/<key>/reset":             "needs an edited workflow",
}

EXPLAINED = {**NOT_A_BUTTON, **NEEDS_DATA}


@pytest.fixture(scope="module")
def app():
    os.environ["SATC_DATA_DIR"] = tempfile.mkdtemp(prefix="satc_buttons_")
    from satc.app.server import create_app
    return create_app()


@pytest.fixture(scope="module")
def crawl(app):
    """Every HTML page reachable by following links, and the forms on each.

    Returns (pages, forms) where forms is [(page, method, action)].
    """
    client = app.test_client()
    start = sorted({
        str(r.rule) for r in app.url_map.iter_rules()
        if "GET" in r.methods and "<" not in str(r.rule)
        and not str(r.rule).startswith(("/static", "/api"))
    })
    seen: set[str] = set()
    queue = list(start)
    forms: list[tuple[str, str, str]] = []

    while queue and len(seen) <= 150:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = client.get(url, follow_redirects=True)
        except Exception:                                  # noqa: BLE001
            continue
        if resp.status_code >= 400:
            continue
        if "text/html" not in resp.headers.get("Content-Type", ""):
            continue                                       # a file, not a page
        body = resp.get_data(as_text=True)
        for tag in re.findall(r"<form[^>]*>", body):
            method = (re.search(r'method="([^"]*)"', tag) or [None, "get"])[1].upper()
            action = (re.search(r'action="([^"]*)"', tag) or [None, url])[1]
            forms.append((url, method, action.split("?")[0] or url))
        for href in re.findall(r'href="(/[^"#?]*)"', body):
            if not href.startswith("/static") and href not in seen:
                queue.append(href)
    return sorted(seen), forms


# ── where every button goes ──────────────────────────────────────────────────

def test_the_crawl_reaches_more_than_the_parameterless_screens(crawl):
    """The denominator, asserted. If link-following breaks, every check below
    passes over a short list and reports success."""
    pages, forms = crawl
    assert len(pages) >= 40, f"only {len(pages)} pages reached; expected 46+"
    assert len(forms) >= 150, f"only {len(forms)} forms found; expected 200+"


def test_no_button_posts_somewhere_that_cannot_receive_it(app, crawl):
    """A DEAD BUTTON: rendered, pressable, and its target does not accept the
    method the form uses. The screen looks complete and one control does
    nothing.

    The method is read from the form. Presuming POST reported two `method="get"`
    filter forms as dead on the first run — the check's fault, not the app's.
    """
    _, forms = crawl
    adapter = app.url_map.bind("localhost")
    dead = []
    for page, method, action in forms:
        try:
            adapter.match(action, method=method)
        except Exception as exc:                           # noqa: BLE001
            dead.append(f"{page} → {action} [{method}] ({type(exc).__name__})")
    assert not dead, (
        f"{len(dead)} of {len(forms)} buttons go nowhere:\n  "
        + "\n  ".join(sorted(set(dead))))


def test_every_post_endpoint_is_either_reachable_or_explained(app, crawl):
    """No POST endpoint may be silently orphaned.

    Either a page renders a button for it, or it is in `UNREACHABLE_IN_DEMO`
    with the reason. An endpoint that quietly appears in neither is one nobody
    can press and nobody has noticed.
    """
    _, forms = crawl
    rendered = {a for _, m, a in forms if m == "POST"}
    posts = sorted({str(r.rule) for r in app.url_map.iter_rules()
                    if "POST" in r.methods})

    unexplained = []
    for rule in posts:
        pattern = "^" + re.sub(r"<[^>]+>", "[^/]+", rule) + "$"
        if any(re.match(pattern, a) for a in rendered):
            continue
        if rule in EXPLAINED:
            continue
        unexplained.append(rule)
    assert not unexplained, (
        f"{len(unexplained)} POST endpoint(s) have no button and no reason:\n  "
        + "\n  ".join(unexplained)
        + "\n\nAdd a button, or add it to UNREACHABLE_IN_DEMO saying why.")


def test_the_structural_list_has_not_gone_stale(app, crawl):
    """The other direction, which is the one that rots quietly.

    An endpoint listed as "never a button" that HAS grown one leaves a stale
    excuse in place and the next reader believes it. Only the STRUCTURAL half is
    checked: whether a data-dependent endpoint renders depends on what the store
    holds, which depends on what ran first, and asserting that would make this
    test fail for a reason that has nothing to do with its name.
    """
    _, forms = crawl
    rendered = {a for _, m, a in forms if m == "POST"}
    posts = {str(r.rule) for r in app.url_map.iter_rules() if "POST" in r.methods}

    gone = sorted(set(EXPLAINED) - posts)
    now_rendered = [
        rule for rule in NOT_A_BUTTON
        if rule in posts
        and any(re.match("^" + re.sub(r"<[^>]+>", "[^/]+", rule) + "$", a)
                for a in rendered)]
    assert not gone, f"listed here but no longer an endpoint at all: {gone}"
    assert not now_rendered, (
        f"listed as never-a-button and now rendering one: {now_rendered}")


# ── and what happens when they are pressed ───────────────────────────────────

def test_pressing_every_reachable_button_does_not_break_the_app(app, crawl):
    """PRESSED, not inspected. Each POST is sent with no fields — the form
    submitted empty, which is what a person does by accident.

    A 200, a redirect, or a 4xx refusal are all acceptable answers: the app may
    reasonably decline. **A 500 is not.** An unhandled exception on a button
    press is the app falling over in front of the preparer, and only pressing
    finds it.

    The store is a throwaway seeded copy, so a button that deletes something is
    free to delete it here.
    """
    pages, forms = crawl
    client = app.test_client()
    broke, pressed = [], 0
    for page, method, action in forms:
        if method != "POST":
            continue
        pressed += 1
        try:
            resp = client.post(action, data={}, follow_redirects=False)
        except Exception as exc:                           # noqa: BLE001
            broke.append(f"{page} → {action}: raised {type(exc).__name__}: {exc}")
            continue
        if resp.status_code >= 500:
            broke.append(f"{page} → {action}: HTTP {resp.status_code}")
    assert not broke, (
        f"{len(broke)} of {pressed} buttons broke the app when pressed:\n  "
        + "\n  ".join(sorted(set(broke))[:20]))
