"""The FDIC identity set, and what a merger quarter is allowed to say.

Four identities the publisher's own numbers have to satisfy, and one verdict
about whether a quarter is comparable at all. Every threshold here was
measured on ``verified-data/bank-values.csv`` -- the audited deliverable, 12
banks x 16 quarters x 68 fields -- and the measurement is in the test beside
each one, with its denominator.

**What these prove, and what they do not.** They do not prove the FDIC agrees
with the filing; the tie-out did that once, by hand, against the banks' own
Call Reports. What they prove is that our parse landed a numerator, a
denominator and a ratio that belong to each other -- the exact fault class of
a column read into the wrong field, a label on the wrong series, or a unit off
by a thousand. That is worth building for, and for nothing more.

**Nothing here reconstructs a number across a merger.** The 670% chart was a
quarterly flow spanning a merger: arithmetically right, describing nothing.
The obvious next move is to repair it -- subtract the acquired bank's prior
year-to-date and carry on. Do not. Two mergers in this same twelve-bank panel
consolidate opposite ways, one where the survivor's year-to-date already
contains the acquired bank's and one where it does not, so there is no single
arithmetic that turns two year-to-dates into a quarter. This module marks the
period NOT COMPARABLE, names the acquired bank, and stops.

And where the merger record cannot be established the answer is UNKNOWN.
``read_mergers`` returns ``None`` for "nobody asked" and ``{}`` for "asked,
none found"; collapsing them is how the 670 got onto a chart.
"""

from __future__ import annotations

import dataclasses
from typing import Iterable, Mapping, Optional, Sequence

from credit_suite.engine import consistency as K

#: The seven published quarterly-flow fields. ``NTRENREQ`` is not among them:
#: the FDIC publishes no quarterly variant, so it is blank in all 192
#: bank-quarters and there is nothing to check.
FLOW_FIELDS = ("NTCRCDQ", "NTAUTOQ", "NTCONOTQ", "NTRERESQ", "NTRECONQ",
               "NTREMULQ", "NTCIQ")

#: I2 -- ratios the FDIC publishes alongside both of their components, as
#: (ratio, numerator, denominator). All four are served x100.
RATIO_IDENTITIES = (
    ("NCLNLSR", "NCLNLS", "LNLSGR"),
    ("LNATRESR", "LNATRES", "LNLSGR"),
    ("LNRESNCR", "LNATRES", "NCLNLS"),
    ("EQV", "EQ", "ASSET"),
)

#: Floating-point epsilon, not a rounding allowance. The FDIC serves these at
#: full double precision (``NCLNLSR = 1.0141164018559314`` for Goldman at
#: 2022-12-31), and the measured worst relative gap over 768 comparisons is
#: 5.3e-16. There is no near-miss population, so a wider tolerance would only
#: be a place for a real fault to hide.
RATIO_TOLERANCE = 1e-12

#: I3 -- the four renderings of the 1-4 family book. The nine loan-class
#: fields are NOT a partition: ``RERES`` CONTAINS ``RELOC``. Anyone who builds
#: "components sum to the total" without knowing that ships a check that fires
#: on half the panel, so the nesting is written down where they will be
#: standing.
NESTED_PREFIXES = ("LN", "P3", "P9", "NA")

#: I4 -- the eight classes that ARE disjoint: the nine minus ``RELOC``.
NONCURRENT_CLASSES = ("CRCD", "AUTO", "RERES", "CONOTH", "CI", "RECONS",
                      "RENRES", "REMULT")

Panel = Mapping[tuple, Mapping[str, Optional[float]]]


def _label(key) -> str:
    return " ".join(str(part) for part in key) if isinstance(key, tuple) \
        else str(key)


def _get(fields: Mapping[str, Optional[float]], name: str):
    value = fields.get(name)
    return value if isinstance(value, (int, float)) else None


# --------------------------------------------------------------------------
# I5 -- the netting identity
# --------------------------------------------------------------------------

def netting_identity(panel: Panel) -> K.CheckResult:
    """``LNLSGR - LNATRES == LNLSNET``. Exact, 192 of 192, no exceptions.

    Cheap, and it pins three separately-landed fields to each other.
    """
    examined = 0
    failures = []
    for key, fields in panel.items():
        gross = _get(fields, "LNLSGR")
        reserve = _get(fields, "LNATRES")
        net = _get(fields, "LNLSNET")
        if gross is None or reserve is None or net is None:
            continue
        examined += 1
        if gross - reserve != net:
            failures.append(
                "%s: LNLSGR - LNATRES = %r but LNLSNET = %r"
                % (_label(key), gross - reserve, net))
    return K.decide("I5", examined, failures, unit="bank-quarters")


# --------------------------------------------------------------------------
# I2 -- the publisher's ratio against the publisher's own components
# --------------------------------------------------------------------------

def ratio_identity(panel: Panel) -> K.CheckResult:
    """Four ratios x every bank-quarter. 768 comparisons, zero exceptions."""
    examined = 0
    failures = []
    unknowns = []
    for key, fields in panel.items():
        for ratio, numerator, denominator in RATIO_IDENTITIES:
            got = _get(fields, ratio)
            num = _get(fields, numerator)
            den = _get(fields, denominator)
            if got is None or num is None or den is None:
                continue
            examined += 1
            if den == 0:
                unknowns.append(
                    "%s: %s has a zero denominator (%s), so %s cannot be "
                    "recomputed -- not divided, and not passed"
                    % (_label(key), ratio, denominator, ratio))
                continue
            want = num / den * 100.0
            gap = abs(want - got) / max(abs(got), abs(want), 1e-30)
            if gap > RATIO_TOLERANCE:
                failures.append(
                    "%s: %s = %r but %s/%s x100 = %r (relative gap %.3e)"
                    % (_label(key), ratio, got, numerator, denominator,
                       want, gap))
    return K.decide("I2", examined, failures, unknowns, unit="ratios")


# --------------------------------------------------------------------------
# I3 -- revolving 1-4 family nests inside total 1-4 family
# --------------------------------------------------------------------------

def nesting_identity(panel: Panel) -> K.CheckResult:
    """``xxRELOC <= xxRERES`` for LN, P3, P9 and NA."""
    examined = 0
    failures = []
    for key, fields in panel.items():
        for prefix in NESTED_PREFIXES:
            inner = _get(fields, prefix + "RELOC")
            outer = _get(fields, prefix + "RERES")
            if inner is None or outer is None:
                continue
            examined += 1
            if inner > outer:
                failures.append(
                    "%s: %sRELOC = %r exceeds %sRERES = %r -- the revolving "
                    "line is INSIDE the 1-4 family book, not beside it"
                    % (_label(key), prefix, inner, prefix, outer))
    return K.decide("I3", examined, failures, unit="nestings")


# --------------------------------------------------------------------------
# I4 -- the eight disjoint noncurrent classes do not exceed the total
# --------------------------------------------------------------------------

def noncurrent_classes(panel: Panel) -> K.CheckResult:
    """``sum over 8 disjoint classes (P9 + NA) <= NCLNLS``.

    Measured maximum exactly 1.0000 (Capital One, 2026-06-30 -- a bank whose
    whole noncurrent book is inside these eight), minimum 0.640. A bucket
    exceeding the total it is drawn from is a mapping error, not an unusual
    quarter.
    """
    examined = 0
    failures = []
    unknowns = []
    for key, fields in panel.items():
        total = _get(fields, "NCLNLS")
        parts = [(prefix + cls, _get(fields, prefix + cls))
                 for cls in NONCURRENT_CLASSES for prefix in ("P9", "NA")]
        absent = [name for name, value in parts if value is None]
        # The bank-quarter counts toward the denominator either way. Counting
        # only the ones that could be summed reported "-124 of 44" on the
        # first build it was pointed at -- an unsettled observation is still
        # an observation the check looked at.
        examined += 1
        if total is None or absent:
            missing = (["NCLNLS"] if total is None else []) + absent
            unknowns.append(
                "%s: cannot sum the eight noncurrent classes -- %s not landed"
                % (_label(key), ", ".join(missing[:4])))
            continue
        summed = sum(value for _, value in parts)
        if summed > total:
            failures.append(
                "%s: the eight noncurrent classes sum to %r against NCLNLS = "
                "%r (ratio %.4f)" % (_label(key), summed, total,
                                     summed / total if total else float("inf")))
    return K.decide("I4", examined, failures, unknowns, unit="bank-quarters")


def identity_set(panel: Panel) -> list:
    """I2, I3, I4 and I5 over one panel, each with its own denominator."""
    return [ratio_identity(panel), nesting_identity(panel),
            noncurrent_classes(panel), netting_identity(panel)]


# --------------------------------------------------------------------------
# I1, reframed -- comparability, never reconstruction
# --------------------------------------------------------------------------

#: The quarter is one bank's quarter and its flows mean what they say.
COMPARABLE = "COMPARABLE"
#: The quarter spans a whole-bank acquisition. A quarterly flow is the
#: year-to-date less the previous quarter's, so across a merger it mixes two
#: banks and is not a quarter of anything. NOT a number to be repaired.
NOT_COMPARABLE = "NOT_COMPARABLE"


@dataclasses.dataclass(frozen=True)
class Comparability:
    """Whether one bank-quarter's flows can be read as a quarter.

    There is deliberately nowhere here to put a repaired figure. The design
    this was built from worked one bank through as if the merger adjustment
    were well defined; it is not. Two mergers in this panel consolidate
    opposite ways -- one survivor's year-to-date already contains the acquired
    bank's prior year-to-date and the other's does not -- so no single
    arithmetic reconstructs the quarter. Adding a field for one should break a
    test and start a conversation.
    """

    verdict: str
    cert: str
    quarter: str
    reason: str
    acquired: tuple = ()


def _acquired_label(event: Mapping) -> str:
    name = str(event.get("out_name") or "").strip()
    cert = str(event.get("out_cert") or "").strip()
    if name and cert:
        return "%s (CERT %s)" % (name, cert)
    return name or ("CERT %s" % cert if cert else "an unnamed institution")


def flow_comparability(cert, quarter: str,
                       record: Optional[Mapping[str, Sequence[Mapping]]]
                       ) -> Comparability:
    """Is this bank-quarter's flow a quarter of anything?

    ``record`` is ``trend.read_mergers``'s shape: ``None`` when the run could
    not establish a merger record at all, ``{}`` when it asked and found none.
    They are not the same answer and this does not collapse them.
    """
    cert = str(cert)
    quarter = str(quarter)[:10]
    if record is None:
        return Comparability(
            verdict=K.UNKNOWN, cert=cert, quarter=quarter, acquired=(),
            reason=("merger status for CERT %s in the quarter ending %s could "
                    "not be established -- this run holds no merger record, "
                    "so whether these flows span a merger is not known. It is "
                    "not 'fine'." % (cert, quarter)))
    events = [event for event in (record.get(cert) or [])
              if str(event.get("quarter") or "")[:10] == quarter]
    if not events:
        return Comparability(
            verdict=COMPARABLE, cert=cert, quarter=quarter, acquired=(),
            reason=("the FDIC's own history records no whole-bank acquisition "
                    "for CERT %s in the quarter ending %s" % (cert, quarter)))
    who = "; ".join("%s, effective %s"
                    % (_acquired_label(event), event.get("effective") or "?")
                    for event in events)
    return Comparability(
        verdict=NOT_COMPARABLE, cert=cert, quarter=quarter,
        acquired=tuple(str(event.get("out_cert") or
                           event.get("out_name") or "").strip()
                       for event in events),
        reason=("the quarter ending %s for CERT %s spans a merger: %s. A "
                "quarterly flow is the year-to-date less the previous "
                "quarter's, so across a merger it mixes two banks and is not "
                "a quarter of anything. It is not reconstructed here: the two "
                "mergers in this panel consolidate opposite ways."
                % (quarter, cert, who)))


def comparability_check(keys: Iterable[tuple],
                        record: Optional[Mapping[str, Sequence[Mapping]]]
                        ) -> K.CheckResult:
    """Sweep every bank-quarter and report how many are readable as quarters.

    A period that is NOT COMPARABLE is not a failure -- the data is right and
    the publisher is right; it is the *period* that cannot be read. It lands
    in UNKNOWN, which is where "we cannot assert this" belongs.
    """
    keys = list(keys)
    unknowns = []
    for key in keys:
        cert, quarter = (key[0], key[1]) if isinstance(key, tuple) else (key, "")
        verdict = flow_comparability(cert, quarter, record)
        if verdict.verdict != COMPARABLE:
            unknowns.append(verdict.reason)
    return K.decide("I1", len(keys), (), unknowns, unit="bank-quarters")
