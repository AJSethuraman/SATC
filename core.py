#!/usr/bin/env python3
"""Shared primitives used across tools.

This is the suite's small, dependency-free core: a single home for the handful of
helpers that several tools need (HTML escaping, money parsing/formatting, and the
per-client file-ownership check). Keeping them here -- public, documented, and
tested in one place -- means tools depend on a stable contract instead of reaching
into each other's private helpers, so a fix happens once.

Standard library only; intentionally imports nothing from the rest of the suite.
"""

from __future__ import annotations


def escape_html(value: object, quote: bool = False) -> str:
    """Escape a value for safe insertion into HTML text (templates are trusted)."""

    text = (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return text.replace('"', "&quot;") if quote else text


def parse_money(value: object) -> float:
    """Parse a money-ish value ("$1,234.56", "1234.56", 1234.56) to a float, else 0.0."""

    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def format_money(value: float) -> str:
    """Format a number as a 2-decimal amount with thousands separators."""

    return f"{value:,.2f}"


def longer_slugs(slug: str, all_slugs) -> list[str]:
    """Other client slugs that have ``slug`` as a strict prefix (e.g. Jo_Sample_Jr)."""

    prefix = f"{slug}_"
    return [other for other in all_slugs if other != slug and other.startswith(prefix)]


def file_belongs_to_other_client(name: str, longer: list[str]) -> bool:
    """True if a per-client output file actually belongs to a longer (more specific) slug.

    Output files are named ``<slug>_...`` (optionally prefixed with ``Signed_``). When
    one client's slug is a prefix of another's, a plain ``<slug>_*`` match would wrongly
    pull in the longer client's files; this excludes them.
    """

    core = name[len("Signed_"):] if name.startswith("Signed_") else name
    return any(core.startswith(f"{other}_") for other in longer)
