"""The tie-out must report where it ARRIVED, not where it aimed.

`proving.prove` compares the landing host against the source's before it
compares any text, so a bot-filter bounce comes back COULD_NOT rather than
`authority_has_moved` — **but only if the transport says where it landed**.

`tools/tieout.py` did not. `_get` returned bare bytes and `live_text` filled
`Fetched.url` with the URL it had ASKED for, so every proof looked like it had
reached the publisher. The guard could not fire on the one tool that needs it,
which made 0.9.5's fix true in the tests and inert in production.

Found reading the shipped transport after the desktop reported the bounce.
"""
import pathlib
import re

import pytest

# IMPORTED AT MODULE SCOPE, AND IT HAS TO BE. `conftest.no_network` replaces
# `socket.socket` with a function for every test, and `ssl` subclasses
# `socket.socket` at import — so importing anything that reaches `urllib.request`
# from INSIDE a test dies with "argument 'code' must be code, not str", which
# looks nothing like the network guard that caused it. Import here, patch there.
from tools import tieout                                          # noqa: E402

TIEOUT = (pathlib.Path(__file__).resolve().parents[1] / "tools" / "tieout.py")
SOURCE = TIEOUT.read_text(encoding="utf-8")


def _tieout():
    return tieout


def _source(url):
    """A minimal readable source. `record.Source` requires the whole contract."""
    import record
    return record.Source(id="S1", title="a publication", tier="secondary",
                         access="public_fetch", may_store=True,
                         checked="2026-09-07", citation_prefix="X", url=url)


class _Reply:
    """What `urlopen` hands back, including the URL it settled on."""

    def __init__(self, body, landed):
        self._body, self._landed = body, landed
        self.headers = {}

    def read(self):
        return self._body

    def geturl(self):
        return self._landed

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_the_transport_returns_the_landing_url(monkeypatch):
    mod = _tieout()
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=0: _Reply(
                            b"<p>blocked</p>", "https://unblock.federalregister.gov/"))
    body, landed = mod._get("https://www.ecfr.gov/current/title-26/section-1.263(a)-2")
    assert body == b"<p>blocked</p>"
    assert landed == "https://unblock.federalregister.gov/"


def test_live_text_carries_the_landing_url_and_not_the_one_it_asked_for(monkeypatch):
    """THE DEFECT ITSELF. `Fetched.url` was the requested URL, always — which is
    a claim to have reached the publisher, made without checking."""
    mod = _tieout()
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=0: _Reply(
                            b"<p>You have been blocked</p>",
                            "https://unblock.federalregister.gov/"))
    got = mod.live_text(_source("https://www.irs.gov/publications/p583"))
    assert got.url == "https://unblock.federalregister.gov/", (
        "the tie-out still reports the URL it asked for, so a bounce is "
        "invisible to `proving.prove` and reads as the publisher rewriting")


def test_an_unredirected_fetch_still_reports_its_own_url(monkeypatch):
    """THE CONTROL. Most fetches land where they aimed and must say so."""
    mod = _tieout()
    here = "https://www.irs.gov/publications/p583"
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=0: _Reply(b"<p>the text</p>", here))
    assert mod.live_text(_source(here)).url == here


def test_no_caller_of_the_transport_treats_it_as_bare_bytes():
    """A tuple return breaks silently at a caller that indexes bytes. Every
    `_fetch`/`_get` result must be unpacked or subscripted, never used whole."""
    bad = []
    for n, line in enumerate(SOURCE.splitlines(), 1):
        # A SINGLE BARE NAME on the left. `raw, landed = _fetch(url)` unpacks
        # the tuple and is correct; `raw = _fetch(url)` treats it as bytes and
        # is the defect. The first version of this guard flagged both.
        if re.search(r"^\s*[A-Za-z_][A-Za-z_0-9]*\s*=\s*_(?:fetch|get)\(", line):
            bad.append(f"tools/tieout.py:{n}: {line.strip()}")
    assert not bad, (
        "a caller takes the transport's whole return as if it were bytes: "
        + "; ".join(bad))


def test_the_shipped_user_agent_is_still_the_one_that_gets_bounced():
    """PINNED SO THE DECISION IS NOT MADE BY ACCIDENT.

    ecfr.gov refuses this UA and every other non-browser one. The fix is a
    decision about how the firm represents itself to a publisher — recorded in
    `docs/DECISIONS-2026-09-08-ELEVENTH.md` with a recommendation to use a REAL
    headless browser rather than claim to be one — and it is the firm's, not a
    session's. If this test fails, somebody changed it: check that they were
    asked."""
    assert 'UA = "satc-desk-tieout' in SOURCE, (
        "the tie-out's user agent changed. That is a decision about what this "
        "desk tells a publisher it is, and it belongs to the firm — see "
        "docs/DECISIONS-2026-09-08-ELEVENTH.md")
