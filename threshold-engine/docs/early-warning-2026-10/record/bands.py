"""Read FICO band members into score ranges, and a bank-quarter's facts into
balances per (class, band). No band edge is assumed: each band's top is the
next band's bottom, so 'under X' is exact for every X a bank publishes."""
import re
from collections import defaultdict

UNSCORED = re.compile(r"(?i)(NoFICO|NoScore|NotAvailable|Datanotavailable|OtherInternal|ClassifiablyManaged|"
                      r"DelinquencyManaged|NoFico|NotRequired)")
TOTAL = "FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss"
OLD_TOTALS = ("FinancingReceivableRecordedInvestment", "LoansAndLeasesReceivableGrossCarryingAmount",
              "NotesReceivableGross", "LoansReceivableGrossCarryingAmount", "LoansAndLeasesReceivableNetOfDeferredIncome")


def band_lo(member: str):
    """The lowest score a band member covers: None for 'under X' bands, a
    number for the rest, 'unscored' for no score. Raises on a name not read."""
    m = member.split(":")[-1].replace("Member", "")
    if UNSCORED.search(m):
        return "unscored"
    n = [int(x) for x in re.findall(r"\d{3}", m)]
    if not n:
        raise ValueError("no score in %r" % member)
    low = m.lower()
    if re.search(r"lessthan|below|lessthanorequalto", low):
        return None
    if re.search(r"greaterthanorequalto|equaltoorgreaterthan|andabove|above", low):
        return n[0]
    if "greaterthan" in low:
        return n[0] + 1
    return n[0]                             # 'AToB', 'A-B', 'BetweenAAndB'


def fico_dim(dims):
    """The dimension holding the score band: its member names a score range or
    no score. A member that only says FICO is the metric used ('Using FICO
    credit metric', PNC) is not a band."""
    for k, v in dims.items():
        if "FICO" in (v or "").upper() or "CREDITSCORE" in (k or "").upper():
            try:
                band_lo(v)
            except ValueError:
                continue
            return k
    return None


def balances(facts):
    """{class: {band member: amount}} for a bank-quarter's FICO facts. A class
    is the non-FICO members joined. Per (class, band) the total concept is used
    where filed, else the vintage and revolving columns summed."""
    g = defaultdict(lambda: defaultdict(dict))
    for concept, v, dims in facts:
        fd = fico_dim(dims)
        if fd is None:
            continue
        cls = " / ".join(dims[k].split(":")[-1].replace("Member", "") for k in sorted(dims) if k != fd)
        g[cls][dims[fd]][concept] = v
    out = {}
    for cls, bands in g.items():
        row = {}
        for b, cs in bands.items():
            if TOTAL in cs:
                row[b] = cs[TOTAL]
            elif any(c in cs for c in OLD_TOTALS):
                row[b] = next(cs[c] for c in OLD_TOTALS if c in cs)
            else:
                vs = [x for c, x in cs.items() if ("Originated" in c or c.endswith("Revolving")
                                                  or c.endswith("RevolvingConvertedToTermLoan")) and "Writeoff" not in c
                      and "WriteOff" not in c]
                if vs:
                    row[b] = sum(vs)
        if row:
            out[cls] = row
    return out


def cumulative(row):
    """(scored total, unscored, [(edge, share under edge)]) from {band: amount}."""
    scored = {}
    unscored = 0.0
    for b, v in row.items():
        lo = band_lo(b)
        if lo == "unscored":
            unscored += v
        else:
            scored[b] = (lo, v)
    total = sum(v for _, v in scored.values())
    if not total:
        return 0.0, unscored, []
    order = sorted(((lo, v, b) for b, (lo, v) in scored.items()), key=lambda t: -1 if t[0] is None else t[0])
    edges, run = [], 0.0
    for i, (lo, v, b) in enumerate(order[:-1]):
        run += v
        nums = [int(x) for x in re.findall(r"\d{3}", b.split(":")[-1])]
        top = nums[1] + 1 if lo is not None and len(nums) >= 2 else None     # 'AToB' covers up to B
        nxt = order[i + 1][0]
        edges.append((min(x for x in (top, nxt) if x is not None), run / total))
    return total, unscored, edges


def under(edges, cut=660):
    """(low, high) bounds on the share under ``cut``: equal where an edge is
    exactly ``cut``; otherwise the nearest published edges below and above."""
    exact = [s for e, s in edges if e == cut]
    if exact:
        return exact[0], exact[0]
    below = [s for e, s in edges if e < cut]
    above = [s for e, s in edges if e > cut]
    return (below[-1] if below else 0.0), (above[0] if above else 1.0)
