"""The side analyses: lagged rates, normalisation, the organic balance index,
the mix factor and the balance trend. docs/PEERS-SPEC.md, "analyses.py", is
the contract.

Each is a pure function over ``data`` (``{REPDTE: [rows]}`` as ``fdic.pull``
returns it) or over the output of ``books``. Nothing is fetched, nothing is
written, and nothing is filled: a figure that cannot be worked out from what
was filed is None, never 0.

Calendar-year figures for one bank, as the earlier scripts worked them:

- net dollars = the Q4 year-to-date charge-offs less recoveries **as filed**
  (``DR`` - ``CR``), so a restated earlier quarter does not move them;
- the balance = the mean of that year's four quarter-end balances.

Both are None unless the bank filed all four quarters of the year. Amounts
stay in $ thousands, as filed.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Union

from .books import _by_cert, _fields, _follows, _num, filed_amount, label, not_filed, quarter_end

Certs = Union[str, int, Sequence[Union[str, int]]]


def _repdte(q: str) -> str:
    """A quarter in any form ``books.quarter_end`` takes -> 'YYYYMMDD'."""
    return quarter_end(q).replace("-", "")


def calendar_year(data: Dict[str, list], cert, product: str, year: int) -> dict:
    """``{year, net, gross, recoveries, balance}`` for one bank and calendar
    year. ``gross`` and ``recoveries`` are the Q4 year-to-date figures as
    filed and ``net`` is their difference; ``balance`` is the mean of the
    four quarter-end balances. All four are None unless the bank filed every
    quarter of the year, and, for a commercial product, filed every field of
    it (a blank is not filed, never 0: ``books.not_filed``)."""
    ln, dr, cr = _fields(product)
    _, snap = _by_cert(data)
    cert = str(cert)
    rows = [snap.get("%d%s" % (year, md), {}).get(cert)
            for md in ("0331", "0630", "0930", "1231")]
    if any(r is None or not_filed(r, product) for r in rows):
        return {"year": year, "net": None, "gross": None, "recoveries": None,
                "balance": None}
    q4 = rows[3]
    g, rc = _num(q4, dr), _num(q4, cr)
    return {"year": year, "net": g - rc, "gross": g, "recoveries": rc,
            "balance": sum(_num(r, ln) for r in rows) / 4}


def _cert_list(certs: Certs) -> List[str]:
    """Certificates as strings. A pack naming a bank twice (``1`` and ``'1'``
    are the same bank) is refused: its dollars would count twice."""
    if isinstance(certs, (str, int)):
        return [str(certs)]
    names = [str(c) for c in certs]
    twice = sorted({c for c in names if names.count(c) > 1})
    if twice:
        raise ValueError("certificate named twice in the pack: %s" % ", ".join(twice))
    return names


def lagged_rate(data: Dict[str, list], certs: Certs, product: str, year: int,
                lag_years: int) -> dict:
    """``100 x net(year) / balance(year - lag_years)``: what a year's losses
    cost against the book that made them, lent ``lag_years`` earlier.

    ``certs`` is one certificate or a list of them. A list is a pack total:
    the nets are summed and the balances are summed before dividing, so every
    dollar counts once, and a bank named twice is refused (ValueError).
    ``lag_years`` 0 is the plain calendar-year net rate; below 0 (a base year
    after the loss year) is refused.

    Returns ``{year, base_year, net, balance, rate}``; ``rate`` (and the sum
    it needs) is None when any bank named lacks either year in full, or the
    balance is not above 0. A pack total with a bank missing is refused, not
    worked out over the banks that remain."""
    if lag_years < 0:
        raise ValueError("lag_years must be 0 or more, not %r" % (lag_years,))
    names = _cert_list(certs)
    if not names:
        raise ValueError("lagged_rate needs at least one certificate")
    base = year - lag_years
    nets = [calendar_year(data, c, product, year)["net"] for c in names]
    bals = [calendar_year(data, c, product, base)["balance"] for c in names]
    net = None if any(n is None for n in nets) else sum(nets)
    bal = None if any(b is None for b in bals) else sum(bals)
    rate = 100 * net / bal if net is not None and bal is not None and bal > 0 else None
    return {"year": year, "base_year": base, "net": net, "balance": bal, "rate": rate}


def annual_means(series: Iterable[tuple]) -> Dict[int, Optional[float]]:
    """``{year: mean}`` of the quarterly values in ``(quarter, value)`` pairs.
    A year's mean is None unless all four of its quarters have a value: a
    year short of a quarter is not averaged over the quarters that remain.
    Quarters are counted as distinct quarter-ends, so '2019Q1' and
    '2019-03-31' are one quarter; a quarter given twice raises ValueError
    rather than one of its values being picked."""
    by_year: Dict[int, Dict[str, object]] = {}
    for q, v in series:
        end = quarter_end(q)
        year = by_year.setdefault(int(end[:4]), {})
        if end in year:
            raise ValueError("quarter %s is given twice" % label(_repdte(end)))
        year[end] = v
    return {y: (sum(vs.values()) / 4
                if len(vs) == 4 and all(v is not None for v in vs.values()) else None)
            for y, vs in sorted(by_year.items())}


def normalisation(series: Iterable[tuple], base_year: int, end_year: int) -> dict:
    """How far a TTM rate has moved between two years, on annual means.

    ``series`` is ``(quarter, value)`` pairs, quarter as ``YYYYQn`` or a date,
    e.g. ``[(r["quarter"], r["net_rate"]) for r in bank_book(...)]`` or the
    same from ``composite``. Each year's figure is the mean of its four
    quarterly TTM values (None unless all four exist). Returns ``{base_year,
    end_year, base, end, ratio}``, ``ratio`` = end / base, None when either is
    None or the base is not above 0: a ratio to a base of net recoveries flips
    its sign, so it would read the wrong way and is refused."""
    means = annual_means(series)
    b, e = means.get(base_year), means.get(end_year)
    ratio = e / b if b is not None and e is not None and b > 0 else None
    return {"base_year": base_year, "end_year": end_year, "base": b, "end": e,
            "ratio": ratio}


def balance_trend(data: Dict[str, list], cert, product: str) -> List[dict]:
    """Per quarter-end in the data: ``{quarter, date, balance, change,
    change_pct}``. ``change`` is the move from the quarter before ($000) and
    ``change_pct`` that move as % of the earlier balance; both None when
    either quarter has no filing (or, for a commercial product, a blank
    balance, which is not filed), the quarters are not consecutive, or (for
    the %) the earlier balance is 0."""
    ln, _, _ = _fields(product)
    qs, snap = _by_cert(data)
    cert = str(cert)
    out = []
    prev_q, prev_b = None, None
    for q in qs:
        r = snap[q].get(cert)
        b = filed_amount(r, ln) if r else None
        ch = pct = None
        if b is not None and prev_b is not None and _follows(prev_q, q):
            ch = b - prev_b
            pct = 100 * ch / prev_b if prev_b != 0 else None
        out.append({"quarter": label(q), "date": quarter_end(q), "balance": b,
                    "change": ch, "change_pct": pct})
        prev_q, prev_b = q, b
    return out


def organic_index(data: Dict[str, list], cert, product: str, base_quarter: str,
                  acquisitions: Iterable[str]) -> List[dict]:
    """The quarter-end balance as an index, base quarter = 100, two ways:

    - ``reported``: balance / base balance x 100;
    - ``organic``: chain-linked quarter-on-quarter growth, with the growth set
      to 1 (no change) in every acquisition quarter, so a book bought in does
      not count as growth. Before the base the chain runs backwards on the
      same rule.

    ``acquisitions`` are the bank's quarters of structural change, in any form
    ``books.quarter_end`` takes ('2022-06-30', '2022Q2', '20220630'): its
    classified acquisitions plus any declared extra, such as a nonbank
    purchase the FDIC record does not show. Which quarters count is the
    caller's judgement, so there is no default.

    Returns ``{quarter, date, balance, reported, organic, acquisition}`` per
    quarter-end in the data. A quarter with no filing breaks the chain: the
    organic index is None from it outward (away from the base). Raises
    ValueError when the base quarter has no filing or a balance of 0. An
    acquisition quarter carries the chain only from the quarter straight
    before it: a quarter absent from the data breaks the chain just as one the
    bank did not file does."""
    trend = balance_trend(data, cert, product)
    acq = {quarter_end(a) for a in acquisitions}
    base_date = quarter_end(base_quarter)
    pos = next((i for i, t in enumerate(trend) if t["date"] == base_date), None)
    if pos is None or not trend[pos]["balance"]:
        raise ValueError("cert %s has no %s balance at the base %s"
                         % (cert, product, label(_repdte(base_quarter))))
    base = trend[pos]["balance"]

    def growth(i):
        """Growth into quarter i from i-1, 1 in an acquisition quarter."""
        if trend[i]["date"] in acq:
            consecutive = i > 0 and _follows(_repdte(trend[i - 1]["date"]),
                                             _repdte(trend[i]["date"]))
            return 1.0 if consecutive else None
        ch = trend[i]["change_pct"]
        return None if ch is None else 1 + ch / 100

    organic: List[Optional[float]] = [None] * len(trend)
    organic[pos] = 100.0
    for i in range(pos + 1, len(trend)):
        g = growth(i)
        organic[i] = None if organic[i - 1] is None or g is None or trend[i]["balance"] is None \
            else organic[i - 1] * g
    for i in range(pos - 1, -1, -1):
        g = growth(i + 1)
        organic[i] = None if organic[i + 1] is None or not g or trend[i]["balance"] is None \
            else organic[i + 1] / g
    return [{"quarter": t["quarter"], "date": t["date"], "balance": t["balance"],
             "reported": None if t["balance"] is None else 100 * t["balance"] / base,
             "organic": organic[i], "acquisition": t["date"] in acq}
            for i, t in enumerate(trend)]


def mix_factor(bank_rate: Dict[int, float], industry_rate: Dict[int, float],
               bank_balance: Dict[int, float], base_year: int) -> List[dict]:
    """Per year, how much of a bank's move in loss rate is its own rather
    than the industry's, and how much its book grew:

    - ``bank_ratio`` = the bank's rate / its base-year rate;
    - ``industry_ratio`` = the industry's rate / its base-year rate;
    - ``own_factor`` = bank_ratio / industry_ratio: above 1, the bank moved
      worse than the industry; below 1, better. That reading holds only when
      every divisor is above 0, so a ratio over a base year (or an industry
      ratio) of 0 or below, e.g. a year of net recoveries, is None;
    - ``balance_factor`` = 1 / balance growth since the base year, the base
      balance / that year's balance: the pull of a growing book (new loans
      have not had time to charge off) or a shrinking one.

    Each input is ``{year: value}``. One row per year present in all three,
    in order; a ratio is None where its divisor is None or not above 0. Raises
    ValueError when the base year is missing from any input."""
    for name, d in (("bank_rate", bank_rate), ("industry_rate", industry_rate),
                    ("bank_balance", bank_balance)):
        if base_year not in d:
            raise ValueError("%s has no value for the base year %d" % (name, base_year))

    def ratio(a, b):
        """a / b, None unless both exist and b is above 0."""
        return a / b if a is not None and b is not None and b > 0 else None

    out = []
    for y in sorted(set(bank_rate) & set(industry_rate) & set(bank_balance)):
        br = ratio(bank_rate[y], bank_rate[base_year])
        ir = ratio(industry_rate[y], industry_rate[base_year])
        out.append({"year": y, "bank_ratio": br, "industry_ratio": ir,
                    "own_factor": ratio(br, ir),
                    "balance_factor": ratio(bank_balance[base_year], bank_balance[y])})
    return out
