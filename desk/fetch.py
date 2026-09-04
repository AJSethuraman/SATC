"""How a source is reached — declared, never discovered by failing.

THE TRAP THIS AVOIDS, and it is the whole reason `access` is a field. If a FAILED
fetch were what reached for a heavier client, then a site refusing automated
access would be the thing that triggered one. That is retry-on-denial: a ladder
that climbs hardest against exactly the sites that have told you not to. So the
method is read off the source, and the engine goes straight there.

FAILURES ARE HANDLED BY CAUSE, NOT BY CLIMBING.

  denied by our own policy   the egress proxy refused the domain
                             -> source_blocked_by_us. the allow-list is the fix.
  denied by the source       its origin refused this client (403, bot management)
                             -> source_refuses_us. the allow-list is NOT the fix.
  empty                      JS-rendered; the fetch got a shell
                             -> a headless browser. escalates RENDERING, not
                                authority. never engages a signed-in profile.
  transient                  timeout, 5xx, reset -> retry the SAME method, once.

THE FIRST TWO WERE ONE REASON, AND COLLAPSING THEM PRODUCED A REAL DEFECT. A
re-test found `asc.fasb.org` reachable and returning a Cloudflare 403 from FASB's
own origin, while the escalation table offered exactly one remedy: grant the
domain. The domain was already granted. A desk would have emitted that reason
forever and sent a person to change a setting that was already correct.

Telling them apart is mechanical, which is what makes it the engine's job rather
than a judgement: our block arrives as a structured refusal from the proxy naming
the domain; theirs arrives as an ordinary HTTP response carrying that origin's
own headers.

NOTHING HERE RUNS IN THE TEST SUITE. The transport is injected, and the suite's
socket layer raises. Verification reads stored text; this module is for building
the record, not for grading against it.
"""
from __future__ import annotations

from dataclasses import dataclass

from record import Source


class NotFetchable(Exception):
    """This source is not reached by any client. Carries the reason and the fix."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class Response:
    """What a transport hands back. Deliberately small."""
    status: int = 0
    body: str = ""
    headers: tuple[tuple[str, str], ...] = ()
    egress_blocked: bool = False        # the proxy refused, not the origin

    def header(self, name: str) -> str:
        return next((v for k, v in self.headers if k.lower() == name.lower()), "")


#: Headers that identify a refusal as coming from the SOURCE's own edge rather
#: than from our egress policy. Presence of any one is enough: the proxy's
#: refusal is structured and carries none of them.
ORIGIN_MARKERS = ("cf-ray", "x-amz-cf-id", "x-akamai-request-id", "x-served-by")

TRANSIENT = (408, 425, 429, 500, 502, 503, 504)


def classify(source: Source, resp: Response) -> str:
    """Name the failure by its cause. Returns "" when there is nothing wrong."""
    if resp.egress_blocked:
        return "source_blocked_by_us"
    if resp.status in TRANSIENT:
        return "transient"
    if resp.status in (401, 403, 407, 451) or resp.status == 429:
        return "source_refuses_us"
    if 400 <= resp.status:
        return "source_refuses_us"
    if not resp.body.strip():
        return "empty"
    return ""


def fetch(source: Source, transport) -> str:
    """Reach a source by the method it declares, and only that method.

    `transport` is any callable taking (source, access) and returning a Response.
    Injected rather than imported so the suite never opens a socket and so the
    signed-in-browser path can be supplied by the machine that actually holds
    the profile.
    """
    if not source.readable:
        raise NotFetchable(
            "human_only",
            f"{source.title} is access={source.access!r}: the engine never "
            f"reaches for it. Cite the reference and answer from positions/, "
            f"or escalate.",
        )

    resp = transport(source, source.access)
    reason = classify(source, resp)

    if reason == "transient":
        # Retry the SAME method, once. Never a different client — a different
        # client is a different permission, and this failure is neither.
        resp = transport(source, source.access)
        reason = classify(source, resp)
        if reason == "transient":
            raise NotFetchable(
                "source_refuses_us",
                f"{source.title} failed twice with {resp.status}; a second "
                f"failure is real, not a flake",
            )

    if reason == "source_blocked_by_us":
        raise NotFetchable(
            "source_blocked_by_us",
            f"our own egress policy refused {source.url or source.title}. Add "
            f"the domain to the environment's allowed-domains list.",
        )

    if reason == "source_refuses_us":
        raise NotFetchable(
            "source_refuses_us",
            f"{source.title} refused this client with {resp.status}"
            f"{' from its own edge' if any(resp.header(h) for h in ORIGIN_MARKERS) else ''}. "
            f"The allow-list is NOT the fix. Change this source's access, have a "
            f"person open it, or accept that it is not automatable.",
        )

    if reason == "empty":
        raise NotFetchable(
            "empty",
            f"{source.title} returned nothing usable — likely rendered by "
            f"script. Set access to headless_browser: that escalates rendering, "
            f"not authority, and needs no sign-in.",
        )

    return resp.body
