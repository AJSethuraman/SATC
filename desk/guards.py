"""Build-time checks on the record. They fail; they do not warn.

Each of these exists because review discipline is not a mechanism. A rule that
depends on somebody noticing a line in a diff holds until the first busy
afternoon, and then it holds nowhere and nobody knows when it stopped.

WHAT MAY BLOCK AND WHAT MAY ONLY ADVISE, which is the firm's own rule from the
tenet linter: what a machine can check EXACTLY may block; what it can only guess
at advises. Everything here is exact — a field is present or it is not, a source
permits storage or it does not — so everything here blocks.
"""
from __future__ import annotations

import re
from pathlib import Path

import positions
import record


class GuardFailure(AssertionError):
    """A record that broke one of its own rules. Never a warning."""


def no_positions_in_extracted(desk_dir: Path) -> None:
    """A judgement must never ride along inside an extraction diff.

    The two stores are read differently on purpose: a large extraction is
    skimmed, a single position is read. A position hidden in the first is one
    that got ratified by a glance.
    """
    extracted = Path(desk_dir) / "extracted"
    if not extracted.is_dir():
        return
    for f in sorted(extracted.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        for marker in positions.MARKERS:
            if re.search(rf"^\*\*{marker}:\*\*", text, re.M):
                raise GuardFailure(
                    f"{f.name} carries a '**{marker}:**' field. That makes it a "
                    f"position, and positions live in positions/ where their diff "
                    f"is actually read — not inside an extraction that is skimmed."
                )


def stored_text_is_permitted(desk: record.Desk) -> None:
    """Nothing is stored from a source that does not permit storing.

    `license_check` is the default and it stores nothing. A licence the firm
    holds may permit an internal copy, which is exactly why this is a fact
    recorded per source rather than one policy over all of them.
    """
    for p in desk.passages:
        src = desk.source(p.source_id)
        if src.may_store != "full_text":
            raise GuardFailure(
                f"passage {p.citation!r} stores text, but source {src.id} "
                f"({src.title}) is may_store={src.may_store!r}. Store the "
                f"citation and record the firm's position instead."
            )


def readable_sources_only_are_fetched(desk: record.Desk) -> None:
    """A `human_only` source must have no stored text at all.

    It is not a stricter fetch, it is the absence of one. FASB ASC is the worked
    example: its licence forbids the content reaching a model by any route, so
    no client rescues it and there is nothing legitimate to have cached.
    """
    for p in desk.passages:
        src = desk.source(p.source_id)
        if not src.readable:
            raise GuardFailure(
                f"passage {p.citation!r} holds text from {src.id} ({src.title}), "
                f"which is access={src.access!r}. The engine never reaches for it, "
                f"so this text cannot have arrived by a permitted route."
            )


def every_problem_has_authority(desk: record.Desk) -> None:
    """A problem whose citation the desk does not hold cannot be scored honestly.

    ASKED THROUGH THE ENGINE'S OWN LOOKUP, NOT BY SOURCE COVERAGE. This used to
    accept a `human_only` citation on the strength of its SOURCE being
    unreadable, which is not the same question: with no ratified position for
    that exact citation, `authority_for()` still returns None, so every attempt at
    that row graded `wrong_caught / authority_absent` and the denominator counted
    a problem nothing could ever answer. It failed in the other direction too --
    a readable citation-only source WITH a position was rejected here for having
    no stored passage, though the engine would have served it.

    Two ways of answering "does the desk hold this?" drift, and the guard was the
    one that was wrong. So it now asks exactly what `_check` asks.
    """
    for p in desk.problems:
        if desk.authority_for(p.citation) is None:
            raise GuardFailure(
                f"problem {p.id} cites {p.citation!r}, which resolves to no "
                f"authority this desk holds -- neither stored text nor a ratified "
                f"position. Every attempt at it would grade as authority_absent"
            )


ALL = (
    no_positions_in_extracted,
    stored_text_is_permitted,
    readable_sources_only_are_fetched,
    every_problem_has_authority,
)


def check(desk_dir: Path) -> record.Desk:
    """Run every guard over one desk. Raises on the first failure."""
    desk_dir = Path(desk_dir)
    no_positions_in_extracted(desk_dir)
    desk = record.load(desk_dir)
    for guard in ALL:
        if guard is no_positions_in_extracted:
            continue
        guard(desk)
    return desk
