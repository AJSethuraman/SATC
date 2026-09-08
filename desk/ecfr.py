"""Read the eCFR through the door its publisher holds open.

THE FIRM, 8 September 2026, after #344 measured what an honest browser costs at
that publisher: *"I'm totally open to API pulls"* — with one condition, *"if
there is any cost to using it, it's not just public I'm not sure I want to use
it"* — and then, settling the shape: *"if we can use an API that's free and
verify the stuff coming out or whatever why not but either way, yeah we want
both."*

MEASURED BEFORE ANYTHING WAS BUILT ON IT, which is the condition they set:

    no key, no cost, no sign-up, HTTP 200 to a plain client with no browser
    user-agent — 8,824 bytes compressed, 33,940 characters of § 1.263(a)-2,
    the passage present and the section named

That is the whole of the case for this module. eCFR's own refusal page names
this API: *"programmatic access to these sites is limited to access to our
extensive developer APIs"*. A door somebody is holding open beats a door you are
merely allowed to walk past, so the user-agent in `browser.py` stays the fallback
for publishers offering nothing like this, and eCFR is read here.

IT IS A TRANSPORT AND NOT A SHORTCUT PAST VERIFICATION — *"and verify the stuff
coming out"*. What comes back goes through `proving.prove_passage` exactly as a
browser fetch does: the stored passage must be in it, the citation must be named
in it, and the landed host is compared. An API answering 200 is not evidence
that it answered about the right thing.

TWO THINGS THE PUBLISHER DOES THAT A NAIVE CLIENT GETS WRONG, both measured
rather than read:

    a date of TODAY answers 404.  The date must be one eCFR has an issue for,
    which it publishes as `up_to_date_as_of` per title. Asking for today is the
    obvious first implementation and it never works.

    a request that does not permit compression answers 406, with the body
    "This endpoint requires response compression."

WHAT IT COVERS AND WHAT IT DOES NOT. 21 of the 33 sources these desks cite are
eCFR. The rest are `uscode.house.gov` (4) and `irs.gov` publications and rulings
(8), and this module reaches neither — they keep the browser path. A reader
should not take "the API works" for "every source is reachable".

NOTHING HERE IS ON THE IMPORT PATH TO THE NETWORK. `urllib` is imported inside
the function that fetches, not at the top of the file, for the reason
`comparing.py` records: this suite replaces the socket layer, `http.client`
reaches `ssl`, and a module-level import made every test in an unrelated file
die inside `ssl.py`.
"""
from __future__ import annotations

import gzip
import re
from dataclasses import dataclass

#: The publisher this module speaks for, and nothing else.
HOST = "ecfr.gov"
API = "https://www.ecfr.gov/api/versioner/v1"

#: A CFR section number as eCFR's API wants it, and as this record writes it.
#: Measured against every prefix the seven desks actually cite -- `1.162-3`,
#: `1.263(a)-2`, `1.274-5T`, `1.280F-6`, `1.6050W-1` -- rather than invented.
_SECTION = re.compile(r"(\d+)\s*CFR\s*(\d+)\.(\d+[A-Z]*(?:\([a-z]\))?-\d+[A-Z]?)")

#: How long an answer about which date a title is current to stays good. Asked
#: once per title per process; eCFR moves it about once a day.
_DATES: dict = {}


class NotOnThisPublisher(ValueError):
    """This citation is not a CFR section. Say so; never guess a URL."""


@dataclass(frozen=True)
class Reply:
    """What `proving` reads off a transport. The same shape `browser` returns."""
    text: str
    url: str
    at: str = ""

    @property
    def body(self) -> bytes:
        return self.text.encode("utf-8")

    @property
    def nbytes(self) -> int:
        return len(self.body)


def parse(citation: str):
    """`(title, part, section)` for a CFR citation, or raise.

    A SUBPARAGRAPH IS NOT A SECTION. A desk cites `1.263(a)-2(d)(1)`; the API
    serves whole sections, so `(d)(1)` is dropped here and the paragraph is
    found by `proving` inside the text that comes back. The section's OWN
    parenthesis -- the `(a)` in `1.263(a)-2` -- is part of its number and stays.
    """
    found = _SECTION.search(citation or "")
    if not found:
        raise NotOnThisPublisher(
            f"{citation!r} is not a CFR section this API can serve. It reads "
            f"title 26 CFR sections; USC and IRS publications are somebody "
            f"else's door.")
    title, part, section = found.groups()
    return int(title), part, f"{part}.{section}"


def current_date(title: int, opener=None) -> str:
    """The date this title is current to, from eCFR itself.

    ASKED RATHER THAN ASSUMED, and that is not caution for its own sake: a URL
    built with TODAY'S date answers 404. Measured 8 September 2026 --
    `2026-09-08` 404, `2026-09-03` 200 -- and today is the date every first
    implementation reaches for.
    """
    if title in _DATES:
        return _DATES[title]
    raw = _get(f"{API}/titles.json", opener=opener)
    import json

    for row in json.loads(raw).get("titles", []):
        if row.get("number") == title:
            when = str(row.get("up_to_date_as_of") or "").strip()
            if not when:
                raise NotOnThisPublisher(
                    f"eCFR lists title {title} and does not say what date it is "
                    f"current to; nothing here will guess one.")
            _DATES[title] = when
            return when
    raise NotOnThisPublisher(f"eCFR does not list title {title}")


def url_for(citation: str, date: str) -> str:
    title, part, section = parse(citation)
    return (f"{API}/full/{date}/title-{title}.xml"
            f"?part={part}&section={section}")


def _get(url: str, opener=None) -> str:
    """One request. Compression is REQUIRED, not an optimisation.

    Without an `Accept-Encoding` that permits it the endpoint answers 406 with
    the body "This endpoint requires response compression." Measured; it is not
    in the shape of an error anybody expects from a document endpoint.
    """
    if opener is not None:
        return opener(url)
    # INSIDE THE FUNCTION. See this module's header: `http.client` reaches
    # `ssl`, and this suite replaces the socket layer.
    import urllib.request

    req = urllib.request.Request(url, headers={
        "Accept-Encoding": "gzip",
        # WHO IS ASKING, SAID PLAINLY. There is no reason to be anything else
        # here: this is the route the publisher asked automated clients to use,
        # so the honest identification is also the one that works.
        "User-Agent": "satc-desk (accounting record verification)",
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


_TAGS = re.compile(r"<[^>]+>")
_DROP = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)

#: TAGS THAT SIT INSIDE A SENTENCE AND MUST LEAVE NO SPACE BEHIND. eCFR sets
#: run-in headings in italics, so the real markup reads
#:
#:     <P>(a) <I>In general</I>—(1) <I>Non-incidental materials…</I> Except as…
#:
#: Replacing every tag with a space turns `In general—(1)` into
#: `In general —(1)`, and the stored passage then fails to match by ONE
#: CHARACTER. Three of nineteen sources came back DIFFERS on the first live run
#: because of exactly this — which, taken at face value, would have been
#: reported as three regulations having moved and would have told a preparer to
#: retire them. It is the #344 defect in a new costume: a fault of OURS
#: presented as a finding about the publisher.
#:
#: Read off the real document rather than guessed: the tags eCFR actually uses
#: in title 26 are P, I, E, HEAD, HED, PSPACE, EXAMPLE and DIV8. Only the
#: emphasis pair is inline.
_INLINE = ("I", "E", "B", "SU", "SUP", "SUB")
_INLINE_TAG = re.compile(r"</?(?:%s)\b[^>]*>" % "|".join(_INLINE), re.I)


def as_text(xml: str) -> str:
    """The section's words, with the markup taken out and nothing else done.

    NO NORMALISATION HERE. `comparing` owns what a marked omission means and how
    whitespace folds; a second copy of that in this module is the kind of drift
    `proving`'s own header warns about. What this does own is the difference
    between a tag that separates words and one that does not — see `_INLINE`.
    """
    body = _DROP.sub(" ", xml or "")
    return " ".join(_TAGS.sub(" ", _INLINE_TAG.sub("", body)).split())


def fetch(citation: str, *, opener=None) -> Reply:
    """The section this citation names, as text, with the URL that served it."""
    title, _part, _section = parse(citation)
    url = url_for(citation, current_date(title, opener=opener))
    return Reply(text=as_text(_get(url, opener=opener)), url=url)


def serves(source_or_url) -> bool:
    """Whether this publisher is the one this module speaks for."""
    url = getattr(source_or_url, "url", source_or_url) or ""
    import urllib.parse

    host = (urllib.parse.urlsplit(str(url)).hostname or "").lower()
    return host == HOST or host.endswith("." + HOST)


def for_proving(*, opener=None):
    """A transport in the shape `proving.prove_passage` wants.

    THE SAME SIGNATURE `browser.for_proving` RETURNS, so a caller chooses a door
    rather than a code path — and neither module learns about the other.
    """
    def go(source, citation=""):
        return fetch(citation or getattr(source, "citation_prefix", ""),
                     opener=opener)
    return go
