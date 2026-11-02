"""The front door: the same rules hold when asked over HTTP, and nobody can sign in as somebody else."""
import json
import io
from urllib.parse import urlencode

import pytest

from workpaper_studio.web import App


@pytest.fixture
def app(studio):
    return App(studio, b"k" * 32)


def call(app, method, path, form=None, user=None, cookie=None):
    body = urlencode(form or {}).encode()
    path, _, qs = path.partition("?")
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": qs, "CONTENT_LENGTH": str(len(body)),
           "wsgi.input": io.BytesIO(body)}
    if user:
        env["HTTP_COOKIE"] = f"ws_user={app.sign(user)}"
    if cookie:
        env["HTTP_COOKIE"] = cookie
    out = {}

    def start(status, headers):
        out["status"], out["headers"] = status, dict(headers)
    out["body"] = b"".join(app(env, start))
    return out


def test_signed_out_goes_to_sign_in_and_a_forged_cookie_is_ignored(app):
    assert call(app, "GET", "/")["status"].startswith("303")
    forged = call(app, "GET", "/", cookie="ws_user=D.%20Patel%7Cdeadbeefdeadbeefdeadbeef")
    assert forged["status"].startswith("303") and "/signin" in forged["headers"]["Location"]


def test_reviewer_cannot_set_an_entry_over_http(app, studio):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    r = call(app, "POST", f"/api/case/{cid}/set", {"path": "f/stmt", "value": "100"}, user="D. Patel")
    assert r["status"].startswith("403")
    assert "Only a preparer" in json.loads(r["body"])["error"]
    assert studio.case(cid)["data"] == {}


def test_preparer_sets_an_entry_and_gets_the_recalculated_screen(app, studio):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    r = call(app, "POST", f"/api/case/{cid}/set", {"path": "f/stmt", "value": "$1,000.50"}, user="A. Rivera")
    assert r["status"].startswith("200")
    assert studio.case(cid)["data"]["stmt"] == 1000.5
    assert "1,000.50" in json.loads(r["body"])["main"]
    bad = call(app, "POST", f"/api/case/{cid}/set", {"path": "f/stmt", "value": "lots"}, user="A. Rivera")
    assert bad["status"].startswith("422") and "not a number" in json.loads(bad["body"])["error"]


def test_release_route_refuses_an_unapproved_case(app, studio):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    r = call(app, "POST", f"/case/{cid}/release", user="D. Patel")
    assert r["status"].startswith("303") and "release%20check%20is%20not%20clear" in r["headers"]["Location"]
    assert studio.case(cid)["status"] == "In progress"


def test_every_screen_renders(app, studio, packs):
    from conftest import fill
    cid = studio.new_case("A. Rivera", "Credit file review")
    fill(studio, cid, "A. Rivera", packs["credit-file-review"].data["example"], packs["credit-file-review"])
    for path in ["/", f"/case/{cid}", f"/case/{cid}?screen=Analysis", f"/case/{cid}/check", f"/case/{cid}/history",
                 f"/case/{cid}/outputs", "/settings", "/tools", "/tools/credit-file-review.json", f"/case/{cid}/draft/feed.json",
                 f"/case/{cid}/draft/feed.csv"]:
        r = call(app, "GET", path, user="A. Rivera")
        assert r["status"].startswith("200"), (path, r["status"])
    body = call(app, "GET", f"/case/{cid}?screen=Analysis", user="A. Rivera")["body"].decode()
    assert "51.3%" in body and "Above limit" in body
    assert packs["credit-file-review"].data["example"]["borrower"] not in call(app, "GET", f"/case/{cid}/draft/feed.json", user="A. Rivera")["body"].decode()


def test_a_broken_pack_is_shown_refused_not_hidden(app, studio):
    (studio.packs_dir / "broken.json").write_text('{"pack": {"name": "x", "version": "1"}, "org": {"name": "x"}, "tool": {"name": "x", "sections": []}}')
    body = call(app, "GET", "/tools", user="M. Okafor")["body"].decode()
    assert "Refused" in body and "broken.json" in body


def test_limit_history_speaks_the_screens_words(app, studio):
    call(app, "POST", "/settings", {"tool": "Credit file review", "calc": "calc_dti", "limit": "45"}, user="M. Okafor")
    body = call(app, "GET", "/settings", user="M. Okafor")["body"].decode()
    hist = body.split("<h2>Versions</h2>")[1]
    assert "Highest debt-to-income confirmed at 45%" in hist and "calc_dti" not in hist


def test_preparer_is_told_a_point_is_waiting(app, studio, packs):
    from conftest import fill
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    fill(studio, cid, "A. Rivera", dict(packs["bank-reconciliation"].data["example"], prep="A. Rivera"), packs["bank-reconciliation"])
    studio.submit("A. Rivera", cid)
    studio.raise_point("D. Patel", cid, "s2", "Why is item 4 still outstanding?")
    home = call(app, "GET", "/", user="A. Rivera")["body"].decode()
    assert "waiting for your answer" in home
    page = call(app, "GET", f"/case/{cid}", user="A. Rivera")["body"].decode()
    assert "Waiting for your answer" in page and "#point-P1" in page


def test_actions_confirm_what_they_did(app, studio, packs):
    from conftest import fill
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    fill(studio, cid, "A. Rivera", dict(packs["bank-reconciliation"].data["example"], prep="A. Rivera"), packs["bank-reconciliation"])
    r = call(app, "POST", f"/case/{cid}/submit", user="A. Rivera")
    assert "Sent%20for%20review" in r["headers"]["Location"]
    page = call(app, "GET", r["headers"]["Location"], user="A. Rivera")["body"].decode()
    assert 'class="flash good"' in page


def test_an_approver_can_see_a_tool_working_before_approving_it(app, studio):
    before = len(studio.case_ids())
    for screen in ("Workpaper", "Analysis"):
        r = call(app, "GET", f"/tools/credit-file-review.json/preview?screen={screen}", user="K. Owens")
        assert r["status"].startswith("200")
    body = r["body"].decode()
    assert "Nothing here is saved" in body and "51.3%" in body and "disabled" in body
    assert len(studio.case_ids()) == before
