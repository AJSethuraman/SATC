"""Match an arriving document to the intake request it satisfies.

The document pipeline classifies an incoming file into a label (e.g. "W-2",
"Schedule K-1 (1065)", "Prior-year 1040"). Intake opened ``Requested`` documents
whose type may be a specific form ("1095-A") or a BUNDLE described in prose
("Upload Forms W-2, 1099-INT, 1099-DIV, ..."). Naive substring matching is both
too loose (every "1099" collides) and too tight (a "W-2" never matches the
"Core income documents" bundle).

Instead we reduce each side to a set of FORM FAMILIES (via curated patterns),
matching when they intersect — so a received "W-2" satisfies any request whose
text mentions a W-2, and a "1099-INT" does not satisfy a request that only wants
1099-NEC. When several outstanding requests match, the MOST SPECIFIC one (fewest
families) wins, so a single 1099 closes a precise "brokerage 1099" request before
a broad income bundle.
"""

from __future__ import annotations

import re

# Canonical form family -> patterns that identify it (searched case-insensitively).
_FAMILY_PATTERNS: dict[str, list[str]] = {
    "W2":        [r"\bw-?2\b"],
    "1099INT":   [r"1099-?int", r"interest income"],
    "1099DIV":   [r"1099-?div", r"dividend"],
    "1099B":     [r"1099-?b\b", r"brokerage", r"consolidated 1099", r"realized gain", r"capital gain"],
    "1099G":     [r"1099-?g\b", r"unemployment", r"state refund"],
    "1099NEC":   [r"1099-?nec", r"nonemployee"],
    "1099K":     [r"1099-?k\b", r"payment platform", r"payment card"],
    "1099R":     [r"1099-?r\b", r"\b5498\b", r"1099-?sa", r"5498-?sa", r"retirement distribution", r"\bira\b", r"\bhsa\b"],
    "1095A":     [r"1095-?a", r"marketplace"],
    "1098T":     [r"1098-?t", r"tuition", r"education expense", r"scholarship"],
    "MORTGAGE":  [r"1098\b", r"mortgage interest"],
    "CLOSING":   [r"closing disclosure", r"closing statement", r"settlement statement", r"1099-?s\b", r"hud-?1"],
    "K1":        [r"\bk-?1\b", r"schedule k-?1", r"passthrough", r"pass-through"],
    "PRIOR":     [r"prior[- ]?year", r"prior 1040", r"carryforward"],
    "STATEMOVE": [r"move date", r"state-by-state", r"part-?year", r"nonresident"],
    "TRIALBAL":  [r"trial balance", r"general ledger", r"balance sheet", r"income statement", r"financial statement"],
    "MILEAGE":   [r"mileage"],
    "W9":        [r"\bw-?9\b", r"contractor"],
    "PAYROLL":   [r"payroll", r"\b941\b", r"\bw-?3\b", r"wage"],
    "INVENTORY": [r"inventory"],
    "ASSET":     [r"fixed asset", r"asset purchase", r"depreciation", r"placed-in-service", r"equipment"],
    "FOREIGN":   [r"foreign account", r"fbar", r"8938", r"foreign financial"],
    "ENGAGEMENT":[r"engagement letter"],
    "ORGANIZER": [r"organizer", r"intake questionnaire"],
    "EFILE_AUTH":[r"8879", r"e-file authoriz"],
}

_COMPILED = {fam: [re.compile(p, re.IGNORECASE) for p in pats] for fam, pats in _FAMILY_PATTERNS.items()}


# The classifier's label for a page carrying several forms. A document that is
# several forms satisfies no single request on its own: a consolidated brokerage
# 1099 answers "1099-INT" to a core-income bundle and the 1099-B nobody has yet
# is never asked for again. Measured 30 Aug 2026 -- $41,200 of proceeds, and the
# packet reported complete.
MULTI_PREFIX = "Several forms:"


def is_multi(received_label: str) -> bool:
    """True when this label names several forms rather than one."""
    return str(received_label).strip().startswith(MULTI_PREFIX)


def families(text: str) -> set[str]:
    """Reduce a label or request description to the form families it references."""
    blob = text or ""
    return {fam for fam, pats in _COMPILED.items() if any(p.search(blob) for p in pats)}


# How a family is named to the firm. The keys above are storage; these are what
# a note says out loud when a bundle is still waiting on something.
FAMILY_LABELS: dict[str, str] = {
    "W2": "W-2", "1099INT": "1099-INT", "1099DIV": "1099-DIV",
    "1099B": "1099-B / brokerage", "1099G": "1099-G", "1099NEC": "1099-NEC",
    "1099K": "1099-K", "1099R": "1099-R / retirement", "1095A": "1095-A",
    "1098T": "1098-T", "MORTGAGE": "1098 mortgage interest",
    "CLOSING": "closing statement", "K1": "Schedule K-1",
    "PRIOR": "prior-year return", "STATEMOVE": "state move details",
    "TRIALBAL": "trial balance", "MILEAGE": "mileage log", "W9": "W-9",
    "PAYROLL": "payroll reports", "INVENTORY": "inventory",
    "ASSET": "fixed asset detail", "FOREIGN": "foreign account details",
    "ENGAGEMENT": "engagement letter", "ORGANIZER": "organizer",
    "EFILE_AUTH": "signed 8879",
}


def name(family: str) -> str:
    """A family as the firm reads it."""
    return FAMILY_LABELS.get(family, family)


def names(fams) -> str:
    """A set of families as one readable list, in a stable order."""
    return ", ".join(sorted(name(f) for f in fams))


def is_bundle(*request_texts: str) -> bool:
    """True when a request names MORE THAN ONE form.

    THE BUG THIS EXISTS TO NAME. A request reading "Upload Forms 1099-INT,
    1099-DIV and brokerage statements" was closed by the first document that
    matched any of it: the 1099-DIV arrived, the request went Received, and the
    1099-INT that came next found no open request to satisfy. Found in a live
    run, 31 Aug 2026. It is the same shape as the consolidated-1099 bug the firm
    had already paid for -- the packet reads complete while a named form is
    still missing -- arriving from the other direction.
    """
    return len(families(" ".join(request_texts))) > 1


def outstanding(request_texts, arrived) -> set[str]:
    """Which of the families a request names have NOT arrived yet."""
    return families(" ".join(t for t in request_texts if t)) - set(arrived or ())


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def matches(received_label: str, *request_texts: str) -> bool:
    """True if a received document satisfies a request described by ``request_texts``.

    Family intersection first (handles bundles + form variants); falls back to a
    conservative exact normalized equality on the primary request text.
    """
    # REFUSED AT THE SEAM, not left to the caller. The label names several
    # forms, so it answers no single request: a page of DIV + INT + B is not
    # "the 1099-INT you asked for". Guarding here rather than only at the one
    # call site means a second caller cannot quietly reintroduce the bug -- and
    # the composite label DOES intersect these families, so without this it
    # would still match.
    if is_multi(received_label):
        return False
    received_families = families(received_label)
    requested_families: set[str] = set()
    for text in request_texts:
        requested_families |= families(text)
    if received_families and requested_families and (received_families & requested_families):
        return True
    primary = request_texts[0] if request_texts else ""
    return bool(received_label) and _normalize(received_label) == _normalize(primary)


def specificity(*request_texts: str) -> int:
    """How specific a request is (fewer families = more specific). Bundles rank high."""
    fams: set[str] = set()
    for text in request_texts:
        fams |= families(text)
    return len(fams) if fams else 99
