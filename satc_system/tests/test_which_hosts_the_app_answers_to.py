"""The app answers to an allowlist of hosts, and nothing else.

**THIS CONTROL HAD NO TESTS.** `server.py` carries two numbered hardening
guards — H2, which refuses a Host header the app does not answer to, and H3,
which refuses a state-changing request a browser marks cross-origin. Neither had
a single test anywhere in the suite. They were edited on 5 October 2026 to let
the app be reached over the firm's tailnet, which is exactly the wrong moment to
be editing something nothing measures.

**WHAT H2 IS FOR,** because it reads like paranoia until you know: a page the
preparer happens to visit can point its own domain at this machine, and the
browser will then send requests to `http://evil.example/clients` that arrive
here looking local. That is **DNS rebinding**. The defence is to check the name
in the Host header against a list, not to check where the packet came from — the
packet really did come from the preparer's own browser.

So the change had to stay an **allowlist**. `SATC_ALLOWED_HOSTS` adds names;
it does not switch the check off. An attacker's domain is still not on the list.

**WHY IT WAS CHANGED AT ALL.** The firm, 5 October 2026:

    "we are setting up bookkeeping to work through tailscale and i can view it
     on the same network, this is a control i'm comfortable with. leaving my
     environment is not conducive to it leaving only the forge"

The screens behind this hold real client names and there is no login on any of
them, so the network is the whole control. That is the firm's decision to make
and it is recorded rather than inferred. What these tests guarantee is that the
decision stayed as narrow as it was described.
"""
from __future__ import annotations

import pytest

from satc.app import server


@pytest.fixture
def client_for():
    """An app built with a given SATC_ALLOWED_HOSTS, and its test client.

    The allowlist is read when the app is BUILT, so each case rebuilds it. A
    fixture that read the variable per-request would pass while the real app,
    which reads it once at startup, behaved differently.
    """
    def build(allowed: str | None, monkeypatch):
        if allowed is None:
            monkeypatch.delenv("SATC_ALLOWED_HOSTS", raising=False)
        else:
            monkeypatch.setenv("SATC_ALLOWED_HOSTS", allowed)
        app = server.create_app()
        app.config.update(TESTING=True)
        return app.test_client()
    return build


# ── the default: nothing changed for a machine that sets nothing ─────────────

@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "127.0.0.1:5050"])
def test_loopback_is_answered_by_default(client_for, monkeypatch, host):
    c = client_for(None, monkeypatch)
    assert c.get("/", headers={"Host": host}).status_code != 400


@pytest.mark.parametrize("host", [
    "100.125.166.122",            # this machine's own tailnet address
    "satc-forge",                 # its tailnet name
    "192.168.68.103",             # its address on the local network
    "evil.example",
    "satcllp.com",
])
def test_everything_else_is_refused_by_default(client_for, monkeypatch, host):
    """THE SHIPPED BEHAVIOUR. A machine that sets nothing is unreachable from
    any other device, including over the firm's own tailnet."""
    c = client_for(None, monkeypatch)
    r = c.get("/", headers={"Host": host})
    assert r.status_code == 400
    assert b"Bad Host" in r.data


# ── the opt-in, and how far it opens ────────────────────────────────────────

def test_a_named_host_is_answered(client_for, monkeypatch):
    c = client_for("100.125.166.122,satc-forge", monkeypatch)
    for host in ("100.125.166.122", "satc-forge", "100.125.166.122:5050"):
        assert c.get("/", headers={"Host": host}).status_code != 400, host


def test_naming_one_host_does_not_admit_the_others(client_for, monkeypatch):
    """THE WHOLE POINT. Opening the tailnet address must not open every name.

    If this ever passes a hostname it was not given, the rebinding defence is
    gone and the change became a bypass rather than an allowlist.
    """
    c = client_for("100.125.166.122", monkeypatch)
    for host in ("evil.example", "satc-forge", "192.168.68.103", "satcllp.com"):
        r = c.get("/", headers={"Host": host})
        assert r.status_code == 400, f"{host} was admitted by naming another host"


def test_loopback_still_works_when_other_hosts_are_named(client_for, monkeypatch):
    """The preparer sitting at the Forge must not be locked out by opening it up."""
    c = client_for("100.125.166.122", monkeypatch)
    assert c.get("/", headers={"Host": "127.0.0.1:5050"}).status_code != 400


@pytest.mark.parametrize("spelling", [
    "SATC-FORGE", "  satc-forge  ", "satc-forge,", ",satc-forge",
])
def test_the_list_is_read_forgivingly(client_for, monkeypatch, spelling):
    """Case and stray whitespace in an environment variable are a typo, not a
    security decision. A hostname is case-insensitive by definition."""
    c = client_for(spelling, monkeypatch)
    assert c.get("/", headers={"Host": "satc-forge"}).status_code != 400


def test_an_empty_setting_is_the_same_as_not_setting_it(client_for, monkeypatch):
    """Otherwise a blank variable in a launcher script silently opens the app."""
    c = client_for("", monkeypatch)
    assert c.get("/", headers={"Host": "satc-forge"}).status_code == 400


# ── H3, the cross-origin guard, must survive the change ─────────────────────

def test_a_foreign_origin_is_still_refused_on_a_write(client_for, monkeypatch):
    """H3. Widening the host list must not widen what may POST here."""
    c = client_for("satc-forge", monkeypatch)
    r = c.post("/api/withholding/estimate",
               headers={"Host": "satc-forge", "Origin": "http://evil.example"},
               json={})
    assert r.status_code == 403
    assert b"Cross-origin" in r.data


def test_the_allowed_host_may_post_to_itself(client_for, monkeypatch):
    """The other half: once the tailnet name is admitted, a page served FROM it
    has to be able to submit a form back to it, or the app is read-only on
    every device except the Forge."""
    c = client_for("satc-forge", monkeypatch)
    r = c.post("/api/withholding/estimate",
               headers={"Host": "satc-forge", "Origin": "http://satc-forge:5050"},
               json={})
    assert r.status_code != 403


def test_a_request_with_no_origin_is_still_allowed(client_for, monkeypatch):
    """Local tools and the JSON API send no Origin at all. H3's comment says so
    and nothing checked it."""
    c = client_for(None, monkeypatch)
    r = c.post("/api/withholding/estimate", headers={"Host": "127.0.0.1"}, json={})
    assert r.status_code != 403


# ── the denominator ─────────────────────────────────────────────────────────

def test_the_allowlist_function_always_contains_loopback():
    """Whatever the environment says, the Forge itself is never locked out."""
    import os
    for setting in ("", "satc-forge", "a,b,c"):
        os.environ["SATC_ALLOWED_HOSTS"] = setting
        try:
            assert "127.0.0.1" in server.allowed_hosts()
            assert "localhost" in server.allowed_hosts()
        finally:
            del os.environ["SATC_ALLOWED_HOSTS"]


def test_the_guard_can_actually_refuse():
    """The control on every test above. If `/` answered 400 for its own
    reasons, every refusal here would pass while proving nothing."""
    import os
    os.environ.pop("SATC_ALLOWED_HOSTS", None)
    app = server.create_app()
    app.config.update(TESTING=True)
    c = app.test_client()
    good = c.get("/", headers={"Host": "127.0.0.1"})
    bad = c.get("/", headers={"Host": "evil.example"})
    assert good.status_code != 400, "the page does not load even from loopback"
    assert bad.status_code == 400
    assert good.status_code != bad.status_code
