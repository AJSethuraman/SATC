"""Tie a bank-quarter out to the FILED Call Report, not the FDIC's republication.

The rest of the tie-out runs *our workbook <-> the FDIC's public API <->
arithmetic*. That is a strong chain, and its trusted origin is still the FDIC
republishing what banks filed. This closes the first link: it fetches the XBRL
instance the bank itself submitted, from the FFIEC's own site, and compares the
raw lines the workbook landed against the raw lines the bank filed.

**XBRL** -- the filing in machine-readable form. Every line of the Call Report
as a code-and-value pair: `RCFD1407` in that file *is* schedule RC-N line 9
column B, with no PDF viewer in the way. It is better evidence than a
screenshot of a page.

FOUR THINGS LEARNED THE FIRST TIME THIS RAN, 4 SEPTEMBER 2026

1. **The filing is in dollars. The API and the workbook are in thousands.**
   `RCFD2170` reads 662,157,000,000 in the filing and 662,157,000 everywhere
   else. Divide by 1,000 and it ties to the dollar.

2. **A bank with foreign offices files consolidated lines under `RCFD`, not
   `RCON`.** Capital One files form 031. Its `RCON2122` (domestic loans) is
   449.65 bn; the consolidated `RCFD2122` is 457.43 bn, and the FDIC's
   `LNLSGR` is the consolidated figure. Bare codes are tried consolidated-first
   and every line **says which prefix it used**, so the reader knows which box
   on the form to look in.

3. **The provenance map's parentheticals are instructions, not decoration.**
   `RCON2200 (+RCFN2200 031)` means *add foreign-office deposits for an 031
   filer* -- and Capital One's deposits tie only with that 150,000 k$ added.
   `RCON1766 (031: RCFD1763+1764)` means *for an 031 filer the line is a
   different sum entirely*. The first version of this parser threw both away
   and reported two false differences against a map that had been right all
   along.

4. **Not every raw field is a dollar line, and not every dollar line is a
   balance.** Twelve "raw" fields are FDIC-computed ratios (`EQV` = 15, not
   15 bn) -- they are skipped by unit, never tied to a dollar line. And the
   charge-off flows (`NTCRCDQ`...) are quarterly in the API but year-to-date
   in the filing; they are skipped with that reason stated, because "not in
   filing" would be false and "differs" would be worse.

Network only when asked. Nothing here runs in the offline bar.
"""

from __future__ import annotations

import http.cookiejar
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

CDR = "https://cdr.ffiec.gov/Public/"
PAGE = CDR + "ViewFacsimileDirect.aspx?ds=call&idType=fdiccert&id={cert}&date={mmddyyyy}"

#: Filed values are dollars; the FDIC API and the workbook carry thousands.
DOLLARS_PER_UNIT = 1000

#: For a bare 4-character code: consolidated first (form 031, banks with
#: foreign offices), domestic as the fallback (forms 041/051). An 031 filer has
#: BOTH, and the FDIC's totals are the consolidated ones.
PREFIXES = ("RCFD", "RCON")

#: The unit label the FDIC field table gives a dollar balance.
DOLLAR_UNIT = "USD_thousands"


class FilingUnavailable(RuntimeError):
    """The FFIEC did not hand back an XBRL for this bank-quarter."""


def facsimile_page(cert: str, repdte_iso: str) -> str:
    y, m, d = repdte_iso[:10].split("-")
    return PAGE.format(cert=cert, mmddyyyy="%s%s%s" % (m, d, y))


def fetch_xbrl(cert: str, repdte_iso: str, timeout: float = 180.0) -> bytes:
    """Press the 'Download XBRL' button the way the page does.

    It is an ASP.NET postback: GET the page for its session cookie and
    `__VIEWSTATE`, then POST the button to the form's *action* URL -- which is
    a different page from the one you are looking at. Posting to the page URL
    returns the page, politely, with no file. That cost an hour.
    """
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page_url = facsimile_page(cert, repdte_iso)
    opener.addheaders = [("User-Agent", "credit-suite tie-out"), ("Referer", page_url)]
    html = opener.open(page_url, timeout=timeout).read().decode("utf-8", "replace")

    def hidden(name: str) -> str:
        found = re.search(r'name="%s"[^>]*value="([^"]*)"' % re.escape(name), html)
        return found.group(1) if found else ""

    action = re.search(r'<form[^>]*action="([^"]+)"', html)
    button = re.search(r'name="([^"]+)"[^>]*value="Download XBRL"', html)
    if not (action and button and hidden("__VIEWSTATE")):
        raise FilingUnavailable(
            "cert %s %s: the facsimile page did not offer an XBRL download "
            "(no filing for that quarter, or the page changed shape)" % (cert, repdte_iso))
    form = {"__EVENTTARGET": "", "__EVENTARGUMENT": "",
            "__VIEWSTATE": hidden("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": hidden("__VIEWSTATEGENERATOR"),
            button.group(1): "Download XBRL"}
    request = urllib.request.Request(
        CDR + action.group(1).replace("&amp;", "&"),
        data=urllib.parse.urlencode(form).encode(), method="POST")
    response = opener.open(request, timeout=timeout)
    body = response.read()
    if b"<xbrl" not in body[:4000].lower():
        raise FilingUnavailable(
            "cert %s %s: the download came back as %s, not XBRL"
            % (cert, repdte_iso, response.headers.get("Content-Type", "?")))
    return body


_FACT = re.compile(r'<[A-Za-z]+:(R[CI][A-Z]{2}[A-Z0-9]{4})\b[^>]*contextRef="([^"]+)"[^>]*>([^<]*)<')


def parse_facts(xbrl: bytes, repdte_iso: str) -> Dict[str, int]:
    """Every numeric fact for the period context, keyed by its full code.

    The instance carries a context per period; the one whose id ends in the
    report date is the one that matters. If none does, every context is
    accepted rather than nothing -- a filing with one context and an unusual
    id should still tie.
    """
    text = xbrl.decode("utf-8", "replace")
    contexts = set(re.findall(r'<(?:xbrli:)?context id="([^"]+)"', text))
    wanted = {c for c in contexts if c.endswith(repdte_iso[:10])} or contexts
    out: Dict[str, int] = {}
    for code, context, raw in _FACT.findall(text):
        if context not in wanted:
            continue
        raw = raw.strip()
        if re.fullmatch(r"-?\d+", raw):
            out[code] = int(raw)
    return out


# --------------------------------------------------------------------------
# the provenance map's MDRM column, as an expression
# --------------------------------------------------------------------------

#: One term: sign, the 4-character line, and an explicit prefix when the map
#: named one (RCFN, RIAD...). A bare term is resolved through PREFIXES.
Term = Tuple[int, str, Optional[str]]

_TERM = re.compile(r"([+-]?)\s*(RC[A-Z]{2}|RI[A-Z]{2})?([A-Z]?\d{3,4})")


@dataclass
class Expression:
    """What the map says a field is made of.

    ``primary`` is the plain expression. ``alternative`` is the "(031: ...)"
    form, tried first and used only if every one of its terms resolves.
    ``optional`` are the "(+RCFNxxxx 031)" additions, included when present
    and silently absent when the bank has no such line.
    """
    primary: List[Term]
    alternative: List[Term] = field(default_factory=list)
    optional: List[Term] = field(default_factory=list)
    #: "(domestic)" in the map: resolve RCON before RCFD for this line,
    #: because the FDIC publishes it for domestic offices only.
    domestic: bool = False


def _terms(text: str) -> Optional[List[Term]]:
    text = text.replace(" ", "")
    if not text or any(c in text for c in "x*,/"):
        return None
    out: List[Term] = []
    consumed = ""
    for sign, prefix, token in _TERM.findall(text):
        # The map writes RCON by convention and RCFD for the 031 variant. Those
        # two are exactly what PREFIXES resolves, consolidated-first -- so they
        # are the DEFAULT, not an instruction. Treating "RCON2122" as a fixed
        # prefix sent Capital One's loans to the domestic line and reported a
        # 7.78 bn difference against a filing that tied. Only a prefix outside
        # that pair (RCFN foreign offices, RIAD income statement) is explicit.
        explicit = prefix if prefix and prefix not in PREFIXES else None
        out.append((-1 if sign == "-" else 1, token, explicit))
        consumed += sign + (prefix or "") + token
    if not out or consumed.lstrip("+") != text.lstrip("+"):
        return None
    return out


def parse_mdrm(expr: str) -> Optional[Expression]:
    """'RCON2200 (+RCFN2200 031)' -> primary [2200], optional [RCFN2200].
    'RCON1766 (031: RCFD1763+1764)' -> primary [1766], alternative [1763, 1764].
    'RCON2170 (RCFD2170 031)' -> primary [2170] (the alt is the same line).
    Returns None for anything that is not a line expression: a ratio, prose,
    a slash, a formula."""
    if not expr:
        return None
    domestic = "(domestic)" in expr
    expr = expr.replace("(domestic)", "").strip()
    head, _, rest = expr.partition("(")
    primary = _terms(head.strip())
    if primary is None:
        return None
    alternative: List[Term] = []
    optional: List[Term] = []
    for paren in re.findall(r"\(([^)]*)\)", "(" + rest if rest else ""):
        body = paren.replace("031", "").strip(" :")
        if paren.strip().startswith("031:"):
            alt = _terms(body)
            if alt:
                alternative = alt
        elif body.startswith("+"):
            opt = _terms(body)
            if opt:
                optional.extend(opt)
        # "(RCFD2170 031)" -- the same 4 characters under the consolidated
        # prefix, which PREFIXES already tries first. Nothing to add.
    return Expression(primary, alternative, optional, domestic)


def _resolve(facts: Dict[str, int], term: Term,
             domestic: bool = False) -> Optional[Tuple[int, str]]:
    """A bare term is tried consolidated-first, or domestic-first when the map
    pins the line to domestic offices with "(domestic)"."""
    sign, token, prefix = term
    order = tuple(reversed(PREFIXES)) if domestic else PREFIXES
    for candidate in ((prefix,) if prefix else order):
        code = candidate + token
        if code in facts:
            return sign * facts[code], ("-" if sign < 0 else "+") + code
    return None


def filed_value(facts: Dict[str, int], expression: Expression
                ) -> Tuple[Optional[int], str]:
    """Evaluate the map's expression against the filing, in thousands.

    Every required term must resolve or the result is None -- a partial sum is
    a wrong number that looks like a right one. The alternative form wins when
    it resolves completely; optional terms are added when present.
    """
    for terms in ((expression.alternative, True), (expression.primary, False)):
        candidates, is_alt = terms
        if not candidates:
            continue
        resolved = [_resolve(facts, t, expression.domestic) for t in candidates]
        if any(r is None for r in resolved):
            if is_alt:
                continue
            return None, ""
        total = sum(v for v, _ in resolved)
        used = [c for _, c in resolved]
        for opt in expression.optional:
            got = _resolve(facts, opt, expression.domestic)
            if got:
                total += got[0]
                used.append(got[1])
        return total // DOLLARS_PER_UNIT, "".join(used).lstrip("+")
    return None, ""


# --------------------------------------------------------------------------
# the comparison
# --------------------------------------------------------------------------

@dataclass
class Line:
    field: str
    expression: str
    filed_thousands: Optional[int]
    used: str                      # e.g. "RCFD1407+RCFD1403", or "" when absent
    landed_thousands: Optional[float]
    note: str = ""                 # set when the line was skipped, and why

    @property
    def verdict(self) -> str:
        if self.note:
            return "SKIPPED: " + self.note
        if self.filed_thousands is None:
            return "NOT IN FILING"
        if self.landed_thousands is None:
            return "NOT LANDED"
        if abs(self.filed_thousands - self.landed_thousands) < 0.5:
            return "TIES"
        return "DIFFERS by {:+,}".format(int(self.landed_thousands - self.filed_thousands))


def _is_flow(fieldname: str) -> bool:
    """Charge-off / recovery flows: `NT...Q`. Quarterly in the API, year-to-date
    in the filing (schedule RI-B), so a line-for-line tie is not the right test."""
    return fieldname.startswith("NT") and fieldname.endswith("Q")


def tie(facts: Dict[str, int], landed: Dict[str, Optional[float]],
        expressions: Dict[str, str],
        units: Optional[Dict[str, str]] = None) -> List[Line]:
    """One Line per field that has a line expression, in the order given.

    ``units`` (the FDIC field table's) keeps ratios out: a percent tied to a
    dollar line is not a discrepancy, it is a category error, and it is
    reported as skipped rather than as a difference of fifteen billion.
    """
    rows: List[Line] = []
    for fieldname, expr in expressions.items():
        expression = parse_mdrm(expr)
        if expression is None:
            continue
        if units is not None and units.get(fieldname, DOLLAR_UNIT) != DOLLAR_UNIT:
            rows.append(Line(fieldname, expr, None, "", landed.get(fieldname),
                             note="a ratio (%s), not a dollar line; recomputed "
                                  "in the arithmetic leg instead" % units[fieldname]))
            continue
        if _is_flow(fieldname):
            rows.append(Line(fieldname, expr, None, "", landed.get(fieldname),
                             note="a quarterly flow; the filing carries year-to-date"))
            continue
        filed, used = filed_value(facts, expression)
        rows.append(Line(fieldname, expr, filed, used, landed.get(fieldname)))
    return rows
