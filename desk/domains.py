"""Which body of authority governs a question, and what tier a publisher gets.

THE DEFECT THIS ANSWERS, 7 September 2026. The firm asked whether a lease goes on
the balance sheet. Every desk refused `authority_absent`; the searcher went out
and came back with four passages off irs.gov that TIED OUT -- re-fetched, matched
character for character, one occurrence each -- and proposed admitting them. All
four were about the tax question. The firm asked the book question. The firm:
*"you don't check the IRS website for coding tips"*.

Nothing could tell. A desk knew its subjects and its sources and never knew which
BODY OF AUTHORITY it spoke for, so a competent search in the wrong universe was
indistinguishable from a competent search in the right one.

TIER IS A PROPERTY OF THE PUBLISHER, NOT A FINDING ABOUT A SOURCE. That is the
whole reason this is one file rather than a line on every desk. The firm:
*"i'm trying to avoid a million desk creations which means i always don't want to
have to personally find every possible source"*. The body with authority over a
domain, publishing its own text, is primary; that body explaining itself is
secondary; everyone else is tertiary however good they are. Written once, applied
by the engine, so a host nobody has ever seen gets a tier without an interview.

IT REFUSES RATHER THAN DEFAULTS, twice over and for different reasons:

    a question matching no domain      -> `Verdict(None, ...)`, not a guess
    a host in no domain's list         -> TERTIARY, never silently primary

The first is the design principle this repository is built on. The second is the
safer direction of the same idea: an unknown publisher can help you FIND the
authority and can never be the authority.

WHAT IT DOES NOT DECIDE. Whether a source is readable, and whether its text may
be stored -- those are `access` and `may_store` on the source, and they are a
licence question. A licensed primary is still primary. The firm, the same day:
*"storage does not matter if we can search for it in the browser... if you are
allowed to store, all the better."*
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "DOMAINS.md"

PRIMARY, SECONDARY, TERTIARY = "primary", "secondary", "tertiary"


class DomainError(ValueError):
    """The map did not parse. Never a default -- a domain guessed from a
    half-read file is the failure this module exists to stop."""


@dataclass(frozen=True)
class Domain:
    name: str
    about: str
    body: str
    publishes: tuple
    explains: tuple
    fires_on: tuple

    def tier(self, host: str) -> str:
        """PUBLISHES IS CHECKED FIRST, and the order is load-bearing. A body
        that publishes both its regulations and its own plain-English guides
        lists one host in both places -- irs.gov is the worked example -- and
        checking `explains` first would demote the regulations to secondary."""
        if _hosts_match(host, self.publishes):
            return PRIMARY
        if _hosts_match(host, self.explains):
            return SECONDARY
        return TERTIARY


@dataclass(frozen=True)
class Verdict:
    """What a question was found to be about. `domain` is None where nothing
    fired, which is a refusal and not an absence of opinion."""

    domain: object = None
    matched: tuple = field(default_factory=tuple)
    also: tuple = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.domain is not None

    @property
    def straddles(self) -> bool:
        """More than one body of authority fired.

        NOT A TIE TO BREAK. `classify` orders by how many words fired, and that
        ordering is a weak signal doing a strong job: *"how do i know if a lease
        should be booked as an asset"* picks `us-gaap` 2-1, and a rewording that
        drops one word hands the same question to `federal-tax`, which would
        then answer the tax half of a book question -- the original defect
        wearing different clothes.

        A lease genuinely IS taxed and booked. The truthful response is two
        answers or a refusal, never one answer chosen by a word count, so this
        is surfaced for the caller to refuse on rather than resolved here.
        """
        return bool(self.domain is not None and self.also)

    @property
    def bodies(self) -> tuple:
        """Every domain that fired, best first. What a straddle has to answer."""
        return () if self.domain is None else (self.domain,) + tuple(self.also)


def _registered(host: str) -> str:
    host = (host or "").strip().lower()
    host = host.split("//")[-1].split("/")[0].split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _hosts_match(host: str, listed) -> bool:
    """A registered domain covers its subdomains: `fasb.org` covers
    `asc.fasb.org`. It must NOT cover `notfasb.org`, which a plain `endswith`
    would -- so the boundary is a dot."""
    host = _registered(host)
    return any(host == h or host.endswith("." + h) for h in listed)


def _words(text: str) -> tuple:
    return tuple(w for w in (p.strip().lower() for p in text.split(",")) if w)


_HEAD = re.compile(r"^## (?P<name>[a-z0-9][a-z0-9-]*) · (?P<about>.+)$")
_FIELD = "**{}:**"


def _field(block: str, label: str, *, required: bool = True) -> str:
    """A field runs to the next blank line, NOT to the end of its first line.

    THE BUG: `**Body:** the Financial Accounting Standards Board, through the
    Accounting\nStandards Codification` was read as ending at "the Accounting",
    and the refusal it printed named a body that does not exist. Silently, and
    only in prose a person reads -- the kind of truncation that never fails a
    test because nothing downstream compares it to anything.
    """
    lines = block.splitlines()
    head = _FIELD.format(label)
    for i, line in enumerate(lines):
        if line.strip().startswith(head):
            got = [line.strip()[len(head):].strip()]
            for nxt in lines[i + 1:]:
                if not nxt.strip() or nxt.strip().startswith("**"):
                    break
                got.append(nxt.strip())
            return " ".join(x for x in got if x)
    if required:
        raise DomainError(
            f"a domain entry has no {label!r} line. A field that was never "
            f"read and a field that was empty look identical downstream")
    return ""


def parse(text: str) -> tuple:
    out, seen = [], set()
    blocks = re.split(r"\n(?=## )", text)
    for block in blocks:
        head = _HEAD.match(block.splitlines()[0].strip()) if block.strip() else None
        if not head:
            continue
        name = head.group("name")
        if name in seen:
            raise DomainError(
                f"domain {name!r} is defined twice; which entry decides a "
                f"host's tier would be settled by file order")
        seen.add(name)
        publishes = _words(_field(block, "Publishes"))
        fires = _words(_field(block, "Fires on"))
        if not publishes:
            raise DomainError(
                f"domain {name!r} names no publisher, so nothing could ever be "
                f"primary in it and every source would read as tertiary")
        if not fires:
            raise DomainError(
                f"domain {name!r} fires on nothing, so no question can reach it")
        out.append(Domain(
            name=name, about=head.group("about").strip(),
            body=_field(block, "Body"),
            publishes=publishes,
            explains=_words(_field(block, "Explains itself at", required=False)),
            fires_on=fires))
    if not out:
        raise DomainError("no domains found; the map is what makes a tier mean "
                          "anything, and an empty one silently tiers nothing")
    return tuple(out)


def load(path=None) -> tuple:
    path = Path(path or MAP)
    if not path.is_file():
        raise DomainError(f"no domain map at {path}")
    return parse(path.read_text(encoding="utf-8"))


_WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")


def _hits(question: str, domain: Domain) -> tuple:
    """WHOLE WORDS AND WHOLE PHRASES, the same rule `SUBJECTS.md` matches on and
    for the same recorded reason: substring matching once made *"extension"*
    fire on *"extensive"*. A multi-word entry is matched as a phrase on the same
    normalised text, so `balance sheet` fires and `balance` alone does not."""
    words = _WORD.findall(question.lower())
    padded = " " + " ".join(words) + " "
    return tuple(t for t in domain.fires_on
                 if (t in words if " " not in t else f" {t} " in padded))


def classify(question: str, domains=None) -> Verdict:
    """Which domain a question is in, by what it fires on.

    THE MODEL DOES NOT GET A VOTE. This is a lookup over words the firm wrote
    down, which is what makes a wrong-domain answer a defect somebody can point
    at rather than a judgement call. `also` carries the runners-up: a question
    can straddle two bodies of authority -- a lease is taxed AND booked -- and
    hiding that would answer half of it confidently.
    """
    scored = []
    for d in (domains if domains is not None else load()):
        hit = _hits(question, d)
        if hit:
            scored.append((len(hit), d.name, d, hit))
    if not scored:
        return Verdict()
    scored.sort(key=lambda s: (-s[0], s[1]))
    return Verdict(domain=scored[0][2], matched=scored[0][3],
                   also=tuple(s[2] for s in scored[1:]))


def tier_for(url: str, domain) -> str:
    """The tier a publisher gets in a domain. TERTIARY where nothing matches --
    an unknown host helps you find the authority and is never the authority."""
    return domain.tier(_registered(url)) if domain else TERTIARY


def governs(url: str, domain) -> bool:
    """Is this host competent to ANSWER in this domain at all?

    The searcher's missing gate. irs.gov is tertiary in `us-gaap`: it can point
    at the right ASC paragraph and it cannot settle one.
    """
    return tier_for(url, domain) in (PRIMARY, SECONDARY)
