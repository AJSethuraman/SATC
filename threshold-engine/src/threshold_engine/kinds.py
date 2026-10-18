"""The kind of book: the words its reader sees, stated by the book, never guessed.

The firm, 17 Oct 2026, on the commercial book: *"names in this should be
changed to be more commercial ... product sounds consumer"*. So a book states
its ``kind``, and the kind decides the word a reader sees for what the
consumer book calls a product: **Product** for a consumer book, exactly as
before, and **Portfolio** for a commercial one ("C&I portfolio"). The kind is
required, as every key of a book is; a book that does not state it is
refused, by name. Nothing here reads a book's product names to decide what
kind of book it is.

A commercial book also shows its portfolios under commercial names: C&I,
Owner-occupied CRE, Investor CRE (non-owner-occupied), Multifamily,
Construction, Nonfarm nonresidential CRE for the parent total, and Loans to
nonbank financials (NDFI) wherever NDFI appears. The firm asked only for more
commercial names (the words above); these names were proposed by the session
that built the book (Claude) the same day, 17 Oct 2026, and the firm did not
object. The Call
Report's own name for each stays beside it on the Glossary, so a figure can
be traced to the filing (``CALL_REPORT``).

``reword`` is how a commercial book's workbook comes to say those words
everywhere: once every tab is written, each piece of text a reader sees (a
cell's text, the quoted text inside a formula, a dropdown's prompt, a chart's
title) has the word and the names put in. It never touches a formula's
references or a table's column names, and refuses a workbook in which one of
those would have to change.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

#: Each kind: the word for what consumer calls a product (the first part of
#: every series' name, ``parts[0]``); whether the Internal tab is built (the
#: internal import, docs/INTERNAL-IMPORT.md, is laid out for consumer
#: products); and the example the Glossary gives of that first part.
KINDS = {
    "consumer": {"word": "Product", "internal_tab": True, "example": "Credit card"},
    "commercial": {"word": "Portfolio", "internal_tab": False, "example": "C&I"},
}

#: A commercial book's portfolios, by the peers build's product name
#: (``peers.books.COMMERCIAL``). The firm asked only for more commercial
#: names ("names in this should be changed to be more commercial ... product
#: sounds consumer"); these names were proposed by the session that built the
#: book (Claude) the same day, 17 Oct 2026, and the firm did not object.
COMMERCIAL_NAMES = {
    "C&I": "C&I",
    "Nonfarm nonresidential": "Nonfarm nonresidential CRE",
    "Owner-occupied nonfarm nonresidential": "Owner-occupied CRE",
    "Other nonfarm nonresidential": "Investor CRE (non-owner-occupied)",
    "Multifamily": "Multifamily",
    "Construction": "Construction",
}
#: Where NDFI appears in a commercial book, it is shown as this.
NDFI = "Loans to nonbank financials (NDFI)"

#: The Call Report's own name for each portfolio, beside the name shown: the
#: RC-C item and the FDIC field the peers build reads, in the words of the
#: FDIC's definitions file (api.fdic.gov, the financials definitions, read 16
#: Oct 2026; docs/commercial-2026-10/research-fdic.md on main) or of the
#: FFIEC instructions (research-ffiec.md, quoting the 12-24 edition). The
#: RC-C item numbers are the ones ``peers.books.DEFINITIONS`` cites.
CALL_REPORT = (
    ("C&I", "Commercial and industrial loans", "RC-C item 4, whole bank (FDIC field LNCI)"),
    ("Nonfarm nonresidential CRE", "Loans secured by nonfarm nonresidential properties",
     "RC-C item 1.e, domestic offices (LNRENRES)"),
    ("Owner-occupied CRE", "Loans secured by owner-occupied nonfarm nonresidential properties",
     "RC-C item 1.e(1), domestic offices, from 2007Q1 (LNRENROW)"),
    ("Investor CRE (non-owner-occupied)", "Loans secured by other nonfarm nonresidential properties",
     "RC-C item 1.e(2), domestic offices, from 2007Q1 (LNRENROT)"),
    ("Multifamily", "Multifamily (5 or more) residential property loans secured by real estate",
     "Domestic offices (LNREMULT)"),
    ("Construction", "Construction and land development loans secured by real estate",
     "RC-C item 1.a, domestic offices (LNRECONS)"),
    (NDFI, "Loans to nondepository financial institutions",
     "RC-C item 9.a; a balance only in the FDIC data, with no charge-off line (RI-B has none)"),
)


def commercial_product(shown) -> Optional[str]:
    """The peers build's product for a commercial book's portfolio name
    (``COMMERCIAL_NAMES``), or for commercial names joined by " + ", a
    combined portfolio (``peers.books.members``: its parts' names joined the
    same way, as the consumer book names "Credit card + Other consumer");
    None for any other name, or a combination the build refuses (a whole
    with a part it holds)."""
    from .peers.books import JOIN, members
    if not isinstance(shown, str):
        return None
    back = {v: k for k, v in COMMERCIAL_NAMES.items()}
    names = shown.split(JOIN)
    if not all(n in back for n in names):
        return None
    product = JOIN.join(back[n] for n in names)
    try:
        members(product)
    except ValueError:
        return None
    return product


def kind_of(name) -> Optional[dict]:
    """The kind named, or None if ``name`` is not one of ``KINDS``."""
    return KINDS.get(name) if isinstance(name, str) else None


# ------------------------------------------------------------------ rewording

_WORDS = (("Products", "Portfolios"), ("products", "portfolios"), ("Product", "Portfolio"),
          ("product", "portfolio"))
_NAMES = sorted(((k, v) for k, v in COMMERCIAL_NAMES.items() if k != v), key=lambda kv: -len(kv[0]))
_PATTERN = re.compile("|".join(
    [r"\b%s\b(?!%s)" % (re.escape(k), re.escape(v[len(k):])) if v.startswith(k) else r"\b%s\b" % re.escape(k)
     for k, v in _NAMES]
    + [r"(?<!\()\bNDFI\b(?!\))"]
    + [r"\b%s\b" % w for w, _ in _WORDS]))
_TO = dict(_NAMES + [("NDFI", NDFI)] + list(_WORDS))
#: A quoted string inside a formula ("" is a quote inside one).
_LITERAL = re.compile(r'"(?:[^"]|"")*"')
#: Excel refuses a quoted string longer than this inside a formula.
LITERAL_MAX = 255


def commercial_text(text: str) -> str:
    """``text`` in a commercial book's words: the portfolio names, NDFI
    named in full, and portfolio for product."""
    return _PATTERN.sub(lambda m: _TO[m.group(0)], text)


def _formula(f: str) -> str:
    """A formula with only its quoted strings reworded. A string that grows
    past what Excel takes in one is split into pieces joined with &."""
    def one(m):
        inner = commercial_text(m.group(0)[1:-1])
        if len(inner) <= LITERAL_MAX:
            return '"%s"' % inner
        pieces, i = [], 0
        while i < len(inner):
            j = min(i + LITERAL_MAX, len(inner))
            # Never split a doubled quote, which is one character to Excel.
            while j < len(inner) and inner[i:j].count('"') % 2:
                j -= 1
            pieces.append(inner[i:j])
            i = j
        return "(%s)" % "&".join('"%s"' % p for p in pieces)
    return _LITERAL.sub(one, f)


def _chart_text(chart) -> int:
    """Reword a chart's title where it is written out, not referenced."""
    t = getattr(chart, "title", None)
    n = 0
    rich = getattr(getattr(t, "tx", None), "rich", None) if t is not None else None
    for p in (getattr(rich, "p", None) or []):
        for r in (getattr(p, "r", None) or []):
            if isinstance(r.t, str):
                new = commercial_text(r.t)
                if new != r.t:
                    r.t, n = new, n + 1
    return n


def reword(wb) -> Dict[str, int]:
    """Put a commercial book's words into every piece of text in ``wb`` a
    reader sees, and return how many were changed, by tab. Refused
    (ValueError) if a table's column or a defined name holds one of the words,
    since formulas refer to those by name and would break."""
    for ws in wb.worksheets:
        for t in ws.tables.values():
            for col in t.tableColumns:
                if commercial_text(col.name) != col.name:
                    raise ValueError("the table %s on %s has a column named %r; a commercial book names its "
                                     "first part Portfolio, so no table column should say that"
                                     % (t.name, ws.title, col.name))
    for name in list(getattr(wb.defined_names, "keys", lambda: [])()):
        if commercial_text(name) != name:
            raise ValueError("the defined name %r holds a word a commercial book changes" % name)
    changed: Dict[str, int] = {}
    for ws in wb.worksheets:
        n = 0
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if not isinstance(v, str):
                    continue
                new = _formula(v) if v.startswith("=") else commercial_text(v)
                if new != v:
                    c.value, n = new, n + 1
        for dv in ws.data_validations.dataValidation:
            for attr in ("prompt", "promptTitle", "error", "errorTitle"):
                v = getattr(dv, attr)
                if isinstance(v, str) and commercial_text(v) != v:
                    setattr(dv, attr, commercial_text(v))
                    n += 1
        for ch in getattr(ws, "_charts", []):
            n += _chart_text(ch)
        if n:
            changed[ws.title] = n
    return changed
