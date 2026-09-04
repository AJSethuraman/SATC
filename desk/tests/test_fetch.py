"""Reaching a source: declared, never discovered by failing.

The first two reasons here were one reason once, and collapsing them produced a
real defect — a single prescribed fix ("grant the domain") met by a case where
the domain was already granted. A desk would have emitted that forever and sent
a person to change a setting that was already correct.
"""
from __future__ import annotations

import pytest

import fetch
import record

BASE = ("## S1 · A source\n\n"
        "**Tier:** primary · **Access:** {access} · "
        "**May store:** full_text · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** X\n\n**Url:** https://example.test/a\n")


def src(access="public_fetch"):
    return record.parse_sources(BASE.format(access=access))[0]


def transport(*responses):
    """A recording transport. Never opens a socket — the suite's guard forbids it."""
    seen = []
    it = iter(responses)

    def _t(source, access):
        seen.append(access)
        return next(it)

    _t.seen = seen
    return _t


# ── the method comes off the source, and only that method is used ────────────

def test_the_declared_method_is_the_one_used(monkeypatch):
    t = transport(fetch.Response(200, "text"))
    assert fetch.fetch(src("headless_browser"), t) == "text"
    assert t.seen == ["headless_browser"], "the engine must not try others"


def test_a_human_only_source_is_never_reached_at_all():
    """Assert no request is ATTEMPTED, not that its result was discarded."""
    t = transport()          # any call raises StopIteration
    with pytest.raises(fetch.NotFetchable) as e:
        fetch.fetch(src("human_only"), t)
    assert e.value.reason == "human_only"
    assert t.seen == [], "human_only is the absence of a fetch, not a stricter one"
    assert "positions/" in e.value.detail, "the refusal must name the next step"


# ── our block and their refusal are different, and the fixes differ ──────────

def test_our_own_egress_block_names_the_allow_list():
    t = transport(fetch.Response(egress_blocked=True))
    with pytest.raises(fetch.NotFetchable) as e:
        fetch.fetch(src(), t)
    assert e.value.reason == "source_blocked_by_us"
    assert "allowed-domains" in e.value.detail


def test_the_sources_own_refusal_says_the_allow_list_is_not_the_fix():
    """The defect this split exists to prevent: prescribing a remedy that
    cannot resolve the case, to somebody who will act on it."""
    t = transport(fetch.Response(403, "blocked", (("server", "cloudflare"),
                                                  ("cf-ray", "abc123"))))
    with pytest.raises(fetch.NotFetchable) as e:
        fetch.fetch(src(), t)
    assert e.value.reason == "source_refuses_us"
    assert "NOT the fix" in e.value.detail
    assert "own edge" in e.value.detail, "origin headers should be recognised"


def test_the_two_reasons_are_not_interchangeable():
    blocked = fetch.classify(src(), fetch.Response(egress_blocked=True))
    refused = fetch.classify(src(), fetch.Response(403, "x"))
    assert blocked == "source_blocked_by_us"
    assert refused == "source_refuses_us"
    assert blocked != refused


# ── transient retries the same method, once ──────────────────────────────────

def test_a_transient_failure_retries_the_same_method_once():
    t = transport(fetch.Response(503, ""), fetch.Response(200, "text"))
    assert fetch.fetch(src(), t) == "text"
    assert t.seen == ["public_fetch", "public_fetch"], (
        "a retry must use the same method — a different client is a different "
        "permission, and this failure is neither"
    )


def test_a_second_transient_failure_is_real_not_a_flake():
    t = transport(fetch.Response(503, ""), fetch.Response(503, ""))
    with pytest.raises(fetch.NotFetchable) as e:
        fetch.fetch(src(), t)
    assert e.value.reason == "source_refuses_us"
    assert len(t.seen) == 2, "at most one retry, ever"


# ── an empty render is a rendering problem, not a permission problem ─────────

def test_an_empty_body_points_at_the_browser_that_needs_no_sign_in():
    t = transport(fetch.Response(200, "   "))
    with pytest.raises(fetch.NotFetchable) as e:
        fetch.fetch(src(), t)
    assert "headless_browser" in e.value.detail
    assert "rendering" in e.value.detail
    assert "signed_in" not in e.value.detail, (
        "solving a rendering problem must never reach for an identity"
    )
