"""A real headless browser — and the honest statement of what this file proves.

WHAT THIS FILE DOES NOT PROVE, said first because it is the important half.
`conftest.py` replaces the socket layer for every test in this suite, autouse,
with a test showing that guard itself can fail. A real browser needs a real
socket. **So the one thing `browser.py` exists to do is the one thing CI can
never exercise**, and nothing below should be read as evidence that a publisher
serves a real browser the real document.

That class was named by the desk on 8 September 2026, after running this suite
on the firm's Windows machine for the first time and finding six failures CI had
never seen:

    "A CONTROL WHOSE OUTCOME IS DECIDED BY THE ENVIRONMENT RATHER THAN BY THE
     CODE. Mutation cannot catch these, and that is precisely why they survive
     -- you are mutating the code, and the code is not what is deciding."

WHAT THIS FILE DOES PROVE is the shape: the argv is what it claims, the landed
URL is read back rather than assumed, the three failures are told apart, and an
unreachable origin RAISES rather than handing back an empty body that would read
as "the publisher no longer carries this". Every one of those is decided by the
code and every one is worth pinning.

THE LIVE RUN IS #344 — on the Forge, through a real browser, against a real
publisher, recorded verbatim including if it fails. Until that exists this
module is unproven against anything but a fixture, and this docstring is the
place that says so rather than a README nobody opens.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import browser                                              # noqa: E402
import fetch                                                # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402

REAL = "https://www.ecfr.gov/current/title-26/section-1.263(a)-2"


def _source(url=REAL):
    return record.Source(
        id="S1", title="eCFR", tier="primary", access="headless_browser",
        may_store="full_text", checked="2026-09-08", citation_prefix="26 CFR ",
        url=url)


class _Done:
    """What `subprocess.run` hands back. The only thing a test needs to make."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _reply(dom, *, code=0, err="", url=REAL):
    """`browser._read` on a canned run — THE REAL FUNCTION, not a copy of it.

    A second implementation in this file would drift from the one that ships,
    and every test below would go on passing while the shipped code changed
    underneath. That failure is recorded more than once in this repository.
    """
    return browser._read(_Done(dom, err, code), url)


# ── the file's own claim about itself ───────────────────────────────────────

def test_this_file_says_out_loud_that_ci_does_not_run_a_browser():
    """The acceptance criterion, asserted rather than trusted to a docstring
    somebody later trims."""
    text = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert "the one thing CI can never exercise" in text
    assert "#344" in text, "the issue that DOES prove it must be named"


def test_no_test_in_this_suite_launches_a_browser():
    """Every call below injects `run`. A test that forgot would launch a real
    process on whatever machine the suite runs on, and would pass on the one
    machine that has a browser installed."""
    text = pathlib.Path(__file__).read_text(encoding="utf-8")
    for line in text.splitlines():
        if "browser.transport(" in line and "run=" not in text[
                text.index(line):text.index(line) + 400]:
            raise AssertionError(f"a transport call with no injected run: {line}")


# ── the command it builds ───────────────────────────────────────────────────

def test_it_is_a_transport_and_not_a_session():
    """`signed_in_browser` is a different rung of `record.ACCESS` and a
    different permission. Nothing here may climb to it by accident, so the
    absence of a profile is asserted rather than assumed."""
    argv = browser.command(REAL, "/usr/bin/chromium")
    assert "--headless=new" in argv
    assert "--incognito" in argv and "--disable-extensions" in argv
    assert argv[-1] == REAL, "the url must be the last argument"
    assert not any(a.startswith("--user-data-dir=") for a in argv), (
        "no profile unless one is asked for")
    assert not any("profile" in a.lower() and "user-data" not in a
                   for a in argv)


def test_a_profile_is_a_throwaway_directory_when_there_is_one():
    argv = browser.command(REAL, "/usr/bin/chromium", user_data_dir="/tmp/x")
    assert "--user-data-dir=/tmp/x" in argv


def test_an_empty_url_is_refused_rather_than_launched():
    with pytest.raises(ValueError):
        browser.command("  ", "/usr/bin/chromium")


# ── finding a browser, and saying so when there is none ────────────────────

def test_the_lookup_happens_at_call_time_and_not_at_import():
    """Every test in this suite imports this module. A module-level lookup
    would make importing it a statement about the machine.

    IT PARSES RATHER THAN SCANS. The first version searched the source text for
    `shutil.which` outside `find` and went red on the COMMENT next to the
    Windows paths explaining what `which` does not do — the same defect the
    offline guard had, which scanned `judging.py`'s prose about not fetching.
    A guard that reads English is a guard that fires on documentation.
    """
    import ast
    tree = ast.parse((HERE / "browser.py").read_text(encoding="utf-8"))
    at_import = [n for n in tree.body
                 if not isinstance(n, (ast.FunctionDef, ast.ClassDef,
                                       ast.Import, ast.ImportFrom))]
    for node in at_import:
        for call in (c for c in ast.walk(node) if isinstance(c, ast.Call)):
            name = ast.dump(call.func)
            assert "which" not in name and "isfile" not in name, (
                f"a browser lookup runs at import: {ast.dump(call)[:120]}")


def test_a_machine_with_no_browser_is_told_what_to_do():
    with pytest.raises(browser.NoBrowser) as e:
        # EMPTYING `PATH` IS NOT ENOUGH and that is worth knowing: the list
        # holds ABSOLUTE paths, so a machine with `/opt/pw-browsers/chromium`
        # still has a browser. The first version of this test set only PATH,
        # found one, and passed for the wrong reason.
        browser.find(env={"PATH": "/nonexistent"}, candidates=())
    said = str(e.value)
    assert browser.ENV_VAR in said
    assert "no fallback" in said, (
        "the firm asked for a REAL browser; a fallback would be the false "
        "statement they refused, so its absence has to be stated")


def test_an_env_var_pointing_nowhere_says_so_rather_than_falling_back():
    """SILENTLY IGNORING IT WOULD BE THE WORST OUTCOME: the operator believes
    they chose a browser and something else was used."""
    with pytest.raises(browser.NoBrowser) as e:
        browser.find(env={browser.ENV_VAR: "/nope/not/here"})
    assert "/nope/not/here" in str(e.value)


def test_the_env_var_wins_over_the_usual_places():
    assert browser.find(env={browser.ENV_VAR: sys.executable}) == sys.executable


# ── what comes back ─────────────────────────────────────────────────────────

def test_a_page_comes_back_as_the_existing_response_shape():
    """Nothing else in the system learns a new shape."""
    resp = _reply("<html><body>the regulation</body></html>", code=0, err="")
    assert isinstance(resp, fetch.Response)
    assert resp.status == 200
    assert "the regulation" in resp.body
    assert resp.header("x-satc-transport") == "headless-browser"
    assert not resp.egress_blocked


def test_the_landed_url_is_read_from_the_page_and_not_assumed():
    """THE FIELD THE WHOLE TRANSPORT EXISTS FOR. ecfr.gov bounces a plain
    client to an interstitial that returns HTTP 200 with a full page of
    unrelated text; without the landed URL nothing can tell that from the
    publisher having rewritten the page, and `proving` withdraws the answer."""
    dom = ('<html><head><link rel="canonical" '
           'href="https://unblock.federalregister.gov/blocked">'
           '</head><body>you have been blocked</body></html>')
    resp = _reply(dom)
    assert resp.url == "https://unblock.federalregister.gov/blocked"


def test_and_proving_then_calls_that_a_bounce_rather_than_a_moved_rule():
    """The two halves together, because either alone proves nothing: the
    transport reports where it landed AND the guard acts on it."""
    dom = ('<html><head><link rel="canonical" '
           'href="https://unblock.federalregister.gov/blocked"></head>'
           '<body>nothing like the regulation</body></html>')
    proof = proving.prove_passage(
        "26 CFR 1.263(a)-2", "a taxpayer must capitalize amounts paid",
        _source(), lambda s, c: browser.as_text(_reply(dom)))
    assert proof.verdict == proving.COULD_NOT, (
        "a bounce read as DIFFERS withdraws every primary citation we hold")
    assert "landed on" in proof.note


def test_a_page_that_does_not_say_where_it_is_reports_what_we_asked_for():
    """Honest rather than clever: we cannot tell, so we do not claim to. The
    cost is that `proving`'s landed-host check compares a host with itself and
    is silent, which is a real limit of `--dump-dom` and is why #344 exists."""
    resp = _reply("<html><body>a page</body></html>", code=0, err="")
    assert resp.url == REAL


# ── the three failures, told apart ─────────────────────────────────────────

def test_an_unreachable_origin_raises_rather_than_returning_nothing():
    """AN EMPTY BODY WOULD READ AS 'THE TEXT IS GONE'. `proving` compares our
    passage against what came back; nothing against an empty document is
    DIFFERS, which `ask.answer` turns into `authority_has_moved` — a claim
    about the PUBLISHER made out of a failure that was ours."""
    with pytest.raises(ConnectionError):
        _reply("", code=1, err="ERR_NAME_NOT_RESOLVED")


def test_an_empty_document_raises_too():
    with pytest.raises(ConnectionError) as e:
        _reply("   \n  ", code=0, err="")
    assert "no heavier client" in str(e.value)


def test_our_own_egress_is_told_apart_from_the_origin_refusing():
    """The distinction that produced a real defect: collapsing them sent a
    person to grant a domain that was already granted."""
    resp = _reply("", code=1, err="net::ERR_TUNNEL_CONNECTION_FAILED at proxy")
    assert resp.egress_blocked
    assert fetch.classify(_source(), resp) == "source_blocked_by_us"


def test_the_origin_refusing_is_not_reported_as_our_egress():
    with pytest.raises(ConnectionError):
        _reply("", code=1, err="net::ERR_CONNECTION_REFUSED")


def test_a_slow_publisher_is_transient_and_is_retried_by_the_same_method(
        monkeypatch):
    """`TimeoutError` is in `fetch.TRANSIENT_ERRORS`, so `fetch.fetch` retries
    the SAME client once — never a heavier one. A different client is a
    different permission and a timeout is not a reason to take one."""
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="chromium", timeout=browser.TIMEOUT)

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(TimeoutError):
        browser._launch(["/x"])
    assert TimeoutError in fetch.TRANSIENT_ERRORS, (
        "a timeout that is not in this tuple is escalated instead of retried")


def test_a_browser_that_will_not_launch_says_which_one(monkeypatch):
    def boom(*a, **k):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(browser.NoBrowser) as e:
        browser._launch(["/usr/bin/chromium"])
    assert "/usr/bin/chromium" in str(e.value)


# ── the adapter into `proving` ─────────────────────────────────────────────

def test_the_two_transport_shapes_are_bridged_rather_than_merged():
    """`fetch.fetch` passes (source, access); `proving` passes (source,
    citation) and reads `.text`. Neither learns about the other."""
    dom = "<html><body>a taxpayer must capitalize amounts paid</body></html>"
    go = browser.for_proving(binary="/x", run=lambda argv, url: _reply(dom))
    reply = go(_source(), "26 CFR 1.263(a)-2")
    assert "capitalize" in reply.text
    assert reply.url == REAL and reply.nbytes == len(dom.encode("utf-8"))
