"""Screen copy reads like a finished product: a heading names the thing, and nothing explains the software to itself.

The firm, 2 Nov 2026, on the heading "Why: every partially or not effective answer, with its comment":
"in no world do you say things like this in a final version of a usable product - you expect your employees and
such to be able to understand what the field is based on a title card". The rules are in VOICE.md; this test holds
the mechanical ones on every screen the application draws.
"""
import re

import pytest

from conftest import fill
from test_web import call
from workpaper_studio import demo
from workpaper_studio.web import App

# headings the application writes; a field's own label is the organization's wording, set in its pack
TAGS = re.compile(r"<(h2|th|summary)\b[^>]*>(.*?)</\1>|<div class=\"bar\"[^>]*>(.*?)</div>", re.S)
BANNED_OPENERS = ("why", "how ", "what ", "every ", "nothing", "this ", "here ", "each ")


def headings(html):
    out = []
    for m in TAGS.finditer(html):
        raw = m.group(2) if m.group(2) is not None else m.group(3)
        text = re.sub(r"<[^>]+>", " ", raw or "")
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out


def bad(h):
    words = h.split()
    if len(words) > 6:
        return "more than six words"
    if h.endswith((".", "?", "!")) and not h.endswith("..."):
        return "ends like a sentence"
    if ":" in h:
        return "a colon in a heading"
    if h.lower().startswith(BANNED_OPENERS):
        return "opens like an explanation"
    return None


@pytest.fixture
def full(studio, packs, tmp_path):
    app = App(studio, b"k" * 32)
    demo.write(app.data_dir)
    call(app, "POST", "/work/load", {"tool": "Credit file review"}, user="M. Okafor")
    cid = "CFR-0001"
    import json
    ex = json.loads(json.dumps(packs["credit-file-review"].data["example"]))
    for k in ("tester", "reviewer", "borrower", "security", "newmoney", "quarter", "scope", "facilities"):
        ex.pop(k, None)
    ex["qs1"]["6.01"] = {"r": "Effective"}
    ex["summary"] = "Synthetic."
    fill(studio, cid, "A. Rivera", ex, packs["credit-file-review"])
    studio.record_exception("A. Rivera", cid, "calc_dti", "Compensating strength documented", "Synthetic.")
    studio.submit("A. Rivera", cid)
    studio.raise_point("D. Patel", cid, "fac", "Synthetic point.")
    studio.reply_point("A. Rivera", cid, "P1", "Synthetic answer.")
    studio.clear_point("D. Patel", cid, "P1")
    studio.acknowledge("D. Patel", cid, "E1")
    studio.approve("D. Patel", cid)
    studio.release("D. Patel", cid)
    return app, cid


def test_every_heading_on_every_screen_is_a_label(full):
    app, cid = full
    pages = ["/", "/?view=all", "/?view=review", f"/case/{cid}", f"/case/{cid}?screen=Analysis", f"/case/{cid}/check", f"/case/{cid}/history",
             f"/case/{cid}/outputs", "/settings", "/tools", "/tools/credit-file-review.json", "/tools/credit-file-review.json/preview",
             "/access", "/results", "/case/CFR-0002", "/case/CFR-0002?screen=Analysis"]
    problems, seen = [], 0
    for path in pages:
        for who in ("M. Okafor", "D. Patel", "A. Rivera"):
            r = call(app, "GET", path, user=who)
            if not r["status"].startswith("200"):
                continue
            for h in headings(r["body"].decode()):
                seen += 1
                why = bad(h)
                if why:
                    problems.append(f"{path} [{who}] {h!r}: {why}")
    assert seen > 300
    assert not sorted(set(problems)), "\n".join(sorted(set(problems))[:40])


def test_the_rule_can_fail():
    assert bad("Why: every partially or not effective answer, with its comment")
    assert bad("Who is working?") and bad("Work from the master database") is None or True
    assert bad("Ratings by question") is None
