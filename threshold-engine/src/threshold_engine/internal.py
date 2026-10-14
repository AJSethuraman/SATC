"""The internal import: the one file KeyBank's own figures come in through,
run on site only. docs/INTERNAL-IMPORT.md is the layout. Nothing internal is
ever written to the repository; the tests use made-up figures.

The file, one row per ``quarter, product, segment``, amounts in $ thousands::

    # entity: whose books these are
    # as-of: when each figure is measured
    # basis: what the figures cover
    # source: the internal system or report
    # segment-All: what the product total holds
    # segment-Home equity lines: what that segment holds
    quarter,product,segment,balance,gross_charge_offs,net_charge_offs,recoveries,dpd_30_plus,dpd_60_plus,dpd_90_plus
    2024Q3,Credit card,All,925000,21000,18000,3000,30000,20000,9000

``check(path)`` lists every problem at once, each naming its line; an empty
list means the file passes. ``read(path)`` returns the file as an
``Internal``, or raises ``Refused`` carrying the same list. The rules:

- the four notes ``entity``, ``as-of``, ``basis`` and ``source``, and one
  ``segment-NAME`` note for every segment the rows use, each answered (not
  empty, no ``[STATE:``). A segment with no note is "not stated", which is a
  problem; a segment note with no rows is a problem too (a misspelt name).
  Any other ``#`` line is refused, so nothing can travel in one;
- the columns ``quarter``, ``product``, ``segment``, ``balance``,
  ``dpd_30_plus``, ``dpd_60_plus``, ``dpd_90_plus``, and at least two of
  ``gross_charge_offs``, ``net_charge_offs`` and ``recoveries``;
- ``quarter`` written ``YYYYQn``; ``product`` one of ``PRODUCTS``;
  ``segment`` not empty (``All`` for the product total; home equity gives
  ``Home equity lines`` and ``Home equity loans`` separately);
- every required cell filled with a plain finite number; a balance, a
  past-due amount, gross charge-offs and recoveries are not below 0 (net
  charge-offs can be, when recoveries exceed them);
- each row gives at least two of gross, net and recoveries, and the third is
  worked out (gross less recoveries is net). When all three are given they
  must agree exactly, as written: no tolerance is assumed;
- past due is cumulative: 0 <= 90+ <= 60+ <= 30+ <= balance;
- no ``quarter, product, segment`` twice, and each ``product, segment`` runs
  over consecutive quarters with none missing (a gap is refused, never
  filled in). Rows may come in any order;
- a further column is carried through, never compared with public data. Its
  cells hold numbers or nothing, and a column whose name reads as an
  identifier (account, borrower, customer, name, id, SSN, ...) is refused:
  the file holds totals by segment, never anything about an account or a
  person;
- no byte-order mark, UTF-8, and lines split exactly where ``templates.py``
  splits them.

**Named exclusions are a separate file**, not a second section. Its shape
differs (``quarter, product, segment, measure, name, amount``), so a second
header inside the internal file would be one more thing the column rule has
to let through; its amounts come from public filings (the 10-K, the Call
Report) rather than internal systems, and change on their own timetable; and
the command line takes it as its own ``--exclusions``, so it can be checked,
fingerprinted and replaced by itself. An exclusion is what the internal
figures leave out "because they were not credit related" (the firm): the
filed figure, less the exclusions, is set against the internal one. Two are
known from the public tie-out, education loans in discontinued operations and
residential mortgages held for sale; their amounts are never assumed. Each
exclusion names the internal ``segment`` it belongs to and the ``measure``
(``balance``, ``gross_charge_offs`` or ``net_charge_offs``) it adjusts,
because home equity's two segments meet different public lines and a balance
taken out says nothing about the charge-offs on it. A negative amount is
something the internal figure holds and the filing does not.

``series(internal, product, segment, measure)`` gives the ``(quarter,
value)`` pairs ``books.write_series`` writes, by the public method: net and
gross charge-off rates over four quarters (``100 x`` four quarters' flows
over the mean of their four quarter-end balances) and the 30+, 60+ and 90+
rates at quarter-end and as the mean of four quarter-end rates. A quarter
with no four consecutive quarters behind it has no value.

``reconcile(internal, filed, exclusions, tolerance, bank=...)`` sets, per
quarter and comparison (``COMPARISONS``), the filed Call Report figure less
the named exclusions against the internal one, for balance, gross and net
charge-offs, and says whether the unexplained remainder is within
``tolerance``, a share of the internal figure that is required and has no
default. Delinquency is not reconciled: the buckets differ (``DELINQUENCY``
states the nearest public measure).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .peers import books
from .peers.books import label, parts, quarter_end, raw_fields
from .templates import PLACEHOLDER, _LINES

#: The products a row may name: the tool's five (``books.PRODUCTS``).
PRODUCTS = tuple(books.PRODUCTS)
ALL = "All"

FLOWS = ("gross_charge_offs", "net_charge_offs", "recoveries")
DPD = ("dpd_30_plus", "dpd_60_plus", "dpd_90_plus")
REQUIRED = ("quarter", "product", "segment", "balance") + DPD
COLUMNS = ("quarter", "product", "segment", "balance") + FLOWS + DPD

#: The notes the file must answer, ``(key, question)``.
NOTES = (
    ("entity", "whose books these are, e.g. KeyCorp consolidated, as in the 10-K"),
    ("as-of", "when each figure is measured, e.g. balances at quarter-end, charge-offs for the quarter"),
    ("basis", "what the figures cover, e.g. portfolio loans of continuing operations, in $ thousands"),
    ("source", "the internal system or report, by name"),
)
SEGMENT = "segment-"
SEGMENT_QUESTION = "what this segment holds, in the bank's words"
#: The segments the template asks about: the product total, and home
#: equity's two (docs/INTERNAL-IMPORT.md).
TEMPLATE_SEGMENTS = (ALL, "Home equity lines", "Home equity loans")

#: Words that make a further column's name read as an identifier.
IDENTIFIER_WORDS = {"account", "accounts", "acct", "borrower", "customer", "client", "obligor",
                    "member", "name", "id", "ssn", "tin", "ein", "taxid", "dob", "birth",
                    "address", "phone", "email", "zip"}

EXCLUSION_COLUMNS = ("quarter", "product", "segment", "measure", "name", "amount")
EXCLUSION_NOTES = (("source", "where each amount comes from, e.g. the 10-K note and page"),)
EXCLUSION_MEASURES = ("balance", "gross_charge_offs", "net_charge_offs")

_YQ = re.compile(r"^(\d{4})Q([1-4])$")
_NOTE = re.compile(r"^#\s*([A-Za-z][A-Za-z0-9-]*)\s*:(.*)$")
_SEGMENT_NOTE = re.compile(r"^#\s*segment-([^:]*?)\s*:(.*)$", re.IGNORECASE)


class Refused(ValueError):
    """A file that does not pass; ``problems`` lists every reason."""

    def __init__(self, path, problems: Sequence[str]):
        self.path = str(path)
        self.problems = list(problems)
        super().__init__("%s does not pass; %d problem%s:\n%s" % (
            path, len(self.problems), "" if len(self.problems) == 1 else "s",
            "\n".join("  - " + p for p in self.problems)))


@dataclass(frozen=True)
class Row:
    """One quarter of one product and segment. Amounts are as written, in $
    thousands. ``worked_out`` names the charge-off column that was not given
    and was worked out from the other two, or is None."""
    line: int
    quarter: str
    product: str
    segment: str
    balance: Decimal
    gross_charge_offs: Decimal
    net_charge_offs: Decimal
    recoveries: Decimal
    worked_out: Optional[str]
    dpd_30_plus: Decimal
    dpd_60_plus: Decimal
    dpd_90_plus: Decimal
    extra: Tuple[Tuple[str, Optional[Decimal]], ...]


@dataclass(frozen=True)
class Internal:
    """A file that passed ``check``: its notes, what each segment holds, the
    further columns carried through, and the rows, oldest first within each
    product and segment."""
    path: str
    notes: Dict[str, str]
    segments: Dict[str, str]
    extra_columns: Tuple[str, ...]
    rows: Tuple[Row, ...]

    def keys(self) -> List[Tuple[str, str]]:
        """Every ``(product, segment)`` in the file, products in ``PRODUCTS``
        order, segments as first met."""
        seen: List[Tuple[str, str]] = []
        for p in PRODUCTS:
            for r in self.rows:
                if r.product == p and (p, r.segment) not in seen:
                    seen.append((p, r.segment))
        return seen

    def rows_for(self, product: str, segment: str) -> List[Row]:
        return [r for r in self.rows if r.product == product and r.segment == segment]


@dataclass(frozen=True)
class Exclusion:
    line: int
    quarter: str
    product: str
    segment: str
    measure: str
    name: str
    amount: Decimal


@dataclass(frozen=True)
class Exclusions:
    path: str
    notes: Dict[str, str]
    rows: Tuple[Exclusion, ...]


# ---------------------------------------------------------------- reading

def qindex(quarter: str) -> int:
    """'2024Q3' -> a number that rises by one each quarter."""
    return int(quarter[:4]) * 4 + int(quarter[5]) - 1


def _quarter_label(i: int) -> str:
    return "%dQ%d" % (i // 4, i % 4 + 1)


def _amount(text: str):
    """A plain finite number as written (``Decimal``), None when blank, or a
    problem string."""
    t = (text or "").strip()
    if not t:
        return None
    try:
        d = Decimal(t)
    except InvalidOperation:
        return "%r is not a number; write it plainly, with no thousands separator or $ sign" % text
    if not d.is_finite():
        return "%r is not a finite number" % text
    return d


def _show(d: Decimal) -> str:
    return format(d, "f")


def _read_table(path, allow_segments: bool):
    """The file split into notes and CSV rows, with the problems found on the
    way: ``(notes {key: (line, text)}, segment notes {name: (line, text)},
    rows [(line, fields)], problems)``. ``rows[0]`` is the header."""
    raw = Path(path).read_bytes()
    problems: List[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("the file starts with a byte-order mark (Excel's 'CSV UTF-8'); save it as "
                        "plain CSV or from a text editor")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {}, {}, None, problems + ["the file is not UTF-8 text"]
    lines = _LINES.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    notes: Dict[str, Tuple[int, str]] = {}
    segs: Dict[str, Tuple[int, str]] = {}
    body = []
    for n, line in enumerate(lines, start=1):
        if not line.startswith("#"):
            body.append((n, line))
            continue
        m = _SEGMENT_NOTE.match(line) if allow_segments else None
        if m:
            name = m.group(1).strip()
            if not name:
                problems.append("line %d: a segment note needs the segment's name, "
                                "'# segment-NAME: what it holds'" % n)
            elif name in segs:
                problems.append("line %d: segment '%s' is described twice (first on line %d)"
                                % (n, name, segs[name][0]))
            else:
                segs[name] = (n, m.group(2).strip())
            continue
        m = _NOTE.match(line)
        if not m:
            problems.append("line %d: a '#' line must be a note, '# key: answer'; anything else is "
                            "refused, so nothing about an account or a person can travel in one" % n)
            continue
        k = m.group(1).lower()
        if k in notes:
            problems.append("line %d: note '%s' is given twice (first on line %d)" % (n, k, notes[k][0]))
            continue
        notes[k] = (n, m.group(2).strip())
    rows, reader, used = [], csv.reader(l + "\n" for _, l in body), 0
    for r in reader:
        start, used = body[used][0], reader.line_num
        if r:
            rows.append((start, r))
    return notes, segs, rows, problems


def _check_notes(notes, asked, problems, more=()) -> Dict[str, str]:
    """Refuse a note not asked for; report one missing, empty or still a
    placeholder. Returns the answers. ``more`` names other notes the file
    takes, for the message."""
    allowed = {k for k, _ in asked}
    for k, (n, _) in sorted(notes.items(), key=lambda kv: kv[1][0]):
        if k not in allowed:
            problems.append("line %d: note '%s' is not one this file takes (%s); a '#' line holds only "
                            "these, so nothing about an account or a person can travel in one"
                            % (n, k, ", ".join(sorted(allowed) + list(more))))
    out = {}
    for k, q in asked:
        if k not in notes:
            problems.append("note '%s' is not stated: add '# %s: %s'" % (k, k, q))
        elif PLACEHOLDER in notes[k][1]:
            problems.append("line %d: note '%s' still holds its placeholder; answer it: %s"
                            % (notes[k][0], k, q))
        elif not notes[k][1]:
            problems.append("line %d: note '%s' is empty; answer it: %s" % (notes[k][0], k, q))
        else:
            out[k] = notes[k][1]
    return out


def _identifier(column: str) -> bool:
    words = [w for w in re.split(r"[^a-z0-9]+", column.lower()) if w]
    return any(w in IDENTIFIER_WORDS for w in words)


def _parse(path):
    """``(Internal or None, problems)``."""
    notes, segs, rows, problems = _read_table(path, allow_segments=True)
    if rows is None:
        return None, problems
    if not rows:
        return None, problems + ["no header: the first line after the notes must name the columns: %s"
                                 % ",".join(COLUMNS)]
    answers = _check_notes(notes, NOTES, problems, more=("segment-NAME",))

    hline, header = rows[0]
    names = [h.strip() for h in header]
    missing = [c for c in REQUIRED if c not in names]
    flows = [c for c in FLOWS if c in names]
    if missing:
        problems.append("line %d: the header has no %s column%s; the layout is %s"
                        % (hline, ", ".join(missing), "" if len(missing) == 1 else "s", ",".join(COLUMNS)))
    if len(flows) < 2:
        problems.append("line %d: the header gives %s; give at least two of gross_charge_offs, "
                        "net_charge_offs and recoveries, and the third is worked out"
                        % (hline, " and ".join(flows) if flows else "none of the charge-off columns"))
    seen_cols, extra = set(), []
    for h in names:
        if h in seen_cols:
            problems.append("line %d: column '%s' appears twice" % (hline, h))
            continue
        seen_cols.add(h)
        if h in COLUMNS:
            continue
        if not h:
            problems.append("line %d: a column has no name (a trailing comma?)" % hline)
        elif _identifier(h):
            problems.append("line %d: column '%s' is refused: its name reads as something that "
                            "identifies an account or a person, and this file holds totals by segment "
                            "only" % (hline, h))
        else:
            extra.append(h)
    if missing or len(flows) < 2:
        return None, problems
    at = {h: names.index(h) for h in seen_cols if h}

    out_rows: List[Row] = []
    first_line: Dict[Tuple[str, str, str], int] = {}
    runs: Dict[Tuple[str, str], List[Tuple[int, str, int]]] = {}
    seg_lines: Dict[str, int] = {}
    unreadable = 0
    for n, r in rows[1:]:
        if len(r) != len(header):
            problems.append("line %d: %d field%s, but the header names %d columns"
                            % (n, len(r), "" if len(r) == 1 else "s", len(header)))
            unreadable += 1
            continue
        cell = {h: r[i] for h, i in at.items()}
        bad = len(problems)
        q = cell["quarter"].strip()
        if not _YQ.match(q):
            problems.append("line %d: quarter %r is not written YYYYQn, e.g. 2024Q3" % (n, cell["quarter"]))
        p = cell["product"].strip()
        if p not in PRODUCTS:
            problems.append("line %d: product %r is not one of %s" % (n, cell["product"], ", ".join(PRODUCTS)))
        s = cell["segment"].strip()
        if not s:
            problems.append("line %d: segment is blank; write %s for the product total" % (n, ALL))
        elif ":" in s:
            problems.append("line %d: segment %r holds a colon, which its '# segment-' note cannot carry"
                            % (n, s))
        else:
            seg_lines.setdefault(s, n)

        vals: Dict[str, Optional[Decimal]] = {}
        invalid = set()
        for c in ("balance",) + DPD + tuple(flows):
            v = _amount(cell[c])
            if isinstance(v, str):
                problems.append("line %d: %s %s" % (n, c, v))
                invalid.add(c)
                v = None
            elif v is None and c not in FLOWS:
                problems.append("line %d: %s is blank; every row needs it" % (n, c))
            elif v is not None and v < 0 and c != "net_charge_offs":
                problems.append("line %d: %s is %s, below 0" % (n, c, _show(v)))
                invalid.add(c)
                v = None
            vals[c] = v
        given = [c for c in flows if vals.get(c) is not None]
        g, net, rec = (vals.get(c) for c in FLOWS)
        worked = None
        if invalid & set(FLOWS):
            pass                # the bad cell is reported; nothing is worked out from it
        elif len(given) < 2:
            problems.append("line %d: gives %s; give at least two of gross_charge_offs, "
                            "net_charge_offs and recoveries, and the third is worked out"
                            % (n, " and ".join(given) if given else "no charge-offs"))
        elif len(given) == 3:
            if g - rec != net:
                problems.append("line %d: gross_charge_offs %s less recoveries %s is %s, but "
                                "net_charge_offs is %s; the three must agree (gross less recoveries "
                                "is net), or give only two and the third is worked out"
                                % (n, _show(g), _show(rec), _show(g - rec), _show(net)))
        else:
            worked = next(c for c in FLOWS if c not in given)
            if worked == "gross_charge_offs":
                g = net + rec
            elif worked == "recoveries":
                rec = g - net
            else:
                net = g - rec
            v = g if worked == "gross_charge_offs" else rec if worked == "recoveries" else None
            if v is not None and v < 0:
                problems.append("line %d: %s worked out from the other two is %s, below 0; check "
                                "the two given" % (n, worked, _show(v)))

        d30, d60, d90, bal = vals["dpd_30_plus"], vals["dpd_60_plus"], vals["dpd_90_plus"], vals["balance"]
        if None not in (d30, d60, d90):
            if d60 > d30:
                problems.append("line %d: dpd_60_plus %s is more than dpd_30_plus %s; past due is "
                                "cumulative (30+ includes 60+, 60+ includes 90+)" % (n, _show(d60), _show(d30)))
            if d90 > d60:
                problems.append("line %d: dpd_90_plus %s is more than dpd_60_plus %s; past due is "
                                "cumulative (30+ includes 60+, 60+ includes 90+)" % (n, _show(d90), _show(d60)))
            if bal is not None and d30 > bal:
                problems.append("line %d: dpd_30_plus %s is more than the balance %s"
                                % (n, _show(d30), _show(bal)))

        carried = []
        for c in extra:
            v = _amount(cell[c])
            if isinstance(v, str):
                problems.append("line %d: further column %s: %s; a further column holds numbers or "
                                "nothing, so nothing about an account or a person travels in it"
                                % (n, c, v))
                v = None
            carried.append((c, v))

        if _YQ.match(q) and p in PRODUCTS and s and ":" not in s:
            key = (q, p, s)
            if key in first_line:
                problems.append("line %d: %s, %s, %s is repeated (first on line %d)"
                                % (n, q, p, s, first_line[key]))
                continue
            first_line[key] = n
            runs.setdefault((p, s), []).append((qindex(q), q, n))
        if len(problems) == bad:
            out_rows.append(Row(n, q, p, s, bal, g, net, rec, worked, d30, d60, d90, tuple(carried)))

    if len(rows) == 1:
        problems.append("no rows: the file has a header and nothing under it")
    for (p, s), run in runs.items():
        run.sort()
        for (a, qa, _), (b, qb, nb) in zip(run, run[1:]):
            if b != a + 1:
                problems.append("line %d: %s / %s: %s follows %s; the quarters between are missing, "
                                "and a gap is refused, not filled in" % (nb, p, s, qb, qa))

    seg_answers = {}
    for name, n in sorted(seg_lines.items(), key=lambda kv: kv[1]):
        if name not in segs:
            problems.append("segment '%s' (first on line %d) is not stated: add '# %s%s: %s'"
                            % (name, n, SEGMENT, name, SEGMENT_QUESTION))
        elif PLACEHOLDER in segs[name][1]:
            problems.append("line %d: note 'segment-%s' still holds its placeholder; answer it: %s"
                            % (segs[name][0], name, SEGMENT_QUESTION))
        elif not segs[name][1]:
            problems.append("line %d: note 'segment-%s' is empty; answer it: %s"
                            % (segs[name][0], name, SEGMENT_QUESTION))
        else:
            seg_answers[name] = segs[name][1]
    for name, (n, _) in sorted(segs.items(), key=lambda kv: kv[1][0]):
        # A row that could not be read may hold the segment; it is reported.
        if name not in seg_lines and not unreadable:
            problems.append("line %d: segment '%s' is described but no row holds it; remove the note, "
                            "or check the name matches the rows exactly" % (n, name))
    if problems:
        return None, problems
    ordered = tuple(sorted(out_rows, key=lambda r: (PRODUCTS.index(r.product), r.segment, qindex(r.quarter))))
    return Internal(str(path), answers, seg_answers, tuple(extra), ordered), []


def check(path) -> List[str]:
    """Every problem with the internal file at ``path``, at once; empty means
    it passes. A file that cannot be read raises its ``OSError``."""
    return _parse(path)[1]


def read(path) -> Internal:
    """The internal file at ``path``; ``Refused`` (a ``ValueError``) with
    every problem when it does not pass."""
    internal, problems = _parse(path)
    if problems:
        raise Refused(path, problems)
    return internal


def _parse_exclusions(path):
    notes, _, rows, problems = _read_table(path, allow_segments=False)
    if rows is None:
        return None, problems
    if not rows:
        return None, problems + ["no header: the first line after the notes must be exactly %s"
                                 % ",".join(EXCLUSION_COLUMNS)]
    answers = _check_notes(notes, EXCLUSION_NOTES, problems)
    hline, header = rows[0]
    if [h.strip() for h in header] != list(EXCLUSION_COLUMNS):
        problems.append("line %d: the header must be exactly %s; found %r"
                        % (hline, ",".join(EXCLUSION_COLUMNS), ",".join(header)))
        return None, problems
    out, first = [], {}
    for n, r in rows[1:]:
        if len(r) != len(EXCLUSION_COLUMNS):
            problems.append("line %d: %d field%s; an exclusion has %d: %s"
                            % (n, len(r), "" if len(r) == 1 else "s", len(EXCLUSION_COLUMNS),
                               ",".join(EXCLUSION_COLUMNS)))
            continue
        q, p, s, m, name, amt = (x.strip() for x in r)
        bad = len(problems)
        if not _YQ.match(q):
            problems.append("line %d: quarter %r is not written YYYYQn, e.g. 2024Q3" % (n, r[0]))
        if p not in PRODUCTS:
            problems.append("line %d: product %r is not one of %s" % (n, r[1], ", ".join(PRODUCTS)))
        if not s:
            problems.append("line %d: segment is blank; write %s for the product total" % (n, ALL))
        if m not in EXCLUSION_MEASURES:
            problems.append("line %d: measure %r is not one of %s" % (n, r[3], ", ".join(EXCLUSION_MEASURES)))
        if not name:
            problems.append("line %d: name is blank; say what is left out" % n)
        v = _amount(amt)
        if v is None:
            problems.append("line %d: amount is blank; an exclusion's amount is stated, never assumed" % n)
        elif isinstance(v, str):
            problems.append("line %d: amount %s" % (n, v))
        if len(problems) > bad:
            continue
        key = (q, p, s, m, name)
        if key in first:
            problems.append("line %d: %s, %s, %s, %s, %r is repeated (first on line %d)"
                            % (n, q, p, s, m, name, first[key]))
            continue
        first[key] = n
        out.append(Exclusion(n, q, p, s, m, name, v))
    if problems:
        return None, problems
    return Exclusions(str(path), answers, tuple(out)), []


def check_exclusions(path) -> List[str]:
    """Every problem with the exclusions file at ``path``; empty means it
    passes. A header and no rows passes: it states nothing is left out."""
    return _parse_exclusions(path)[1]


def read_exclusions(path) -> Exclusions:
    ex, problems = _parse_exclusions(path)
    if problems:
        raise Refused(path, problems)
    return ex


# ---------------------------------------------------------------- template

def exclusions_path(out) -> Path:
    """``OUT.csv`` -> ``OUT.exclusions.csv`` beside it."""
    out = Path(out)
    return out.with_name(out.stem + ".exclusions.csv")


def write_template(out) -> Tuple[Path, Path]:
    """The empty internal file at ``out`` (a ``.csv``) and the empty
    exclusions file beside it; return both paths. Every note holds
    ``[STATE: question]``, so ``check`` refuses both until each is answered.
    Neither is written over (``ValueError``): a filled file would be lost."""
    out = Path(out)
    if out.suffix.lower() != ".csv":
        raise ValueError("the internal file is a CSV: name it OUT.csv, not %s" % out.name)
    ex = exclusions_path(out)
    for p in (out, ex):
        if p.exists():
            raise ValueError("%s already exists; it is not written over, so a filled file cannot be "
                             "lost. Choose another name or move it." % p)
    lines = ["# %s: %s %s]" % (k, PLACEHOLDER, q) for k, q in NOTES]
    lines += ["# %s%s: %s %s]" % (SEGMENT, s, PLACEHOLDER, SEGMENT_QUESTION) for s in TEMPLATE_SEGMENTS]
    lines.append(",".join(COLUMNS))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ex.write_text("\n".join(["# %s: %s %s]" % (k, PLACEHOLDER, q) for k, q in EXCLUSION_NOTES]
                            + [",".join(EXCLUSION_COLUMNS)]) + "\n", encoding="utf-8")
    return out, ex


# ---------------------------------------------------------------- series

@dataclass(frozen=True)
class Measure:
    key: str
    title: str
    numerator: str
    denominator: str
    basis: str


_AVG_BAL = "the mean of the four quarter-end balances"
MEASURES = {m.key: m for m in (
    Measure("net-charge-off-rate", "Net charge-off rate, trailing four quarters, %",
            "net charge-offs, the four quarters summed (gross less recoveries)", _AVG_BAL,
            "trailing four quarters"),
    Measure("gross-charge-off-rate", "Gross charge-off rate, trailing four quarters, %",
            "gross charge-offs, the four quarters summed", _AVG_BAL, "trailing four quarters"),
) + tuple(
    Measure("dpd-%s-plus-%s" % (d, b), "%s+ days past due, %s, %%" % (d, words),
            "balances %s or more days past due at quarter-end (dpd_%s_plus)" % (d, d),
            den, words)
    for d in ("30", "60", "90")
    for b, words, den in (
        ("quarter-end", "quarter-end", "the balance at the same quarter-end"),
        ("four-quarter-average", "four-quarter average",
         "each quarter's own quarter-end balance; the four quarter-end rates are averaged")))}

WHY_WINDOW = "fewer than four consecutive quarters to measure over"
WHY_NO_BALANCE = "no balance to divide by (0)"
WHY_RATE_MISSING = "a quarter-end rate in the window has no value (%s)"


def _measure(key: str) -> Measure:
    if key not in MEASURES:
        raise ValueError("measure must be one of %s, not %r" % (", ".join(MEASURES), key))
    return MEASURES[key]


def _series(internal: Internal, product: str, segment: str, measure: str):
    """``[(quarter, value or None, why or None)]``."""
    m = _measure(measure)
    rows = internal.rows_for(product, segment)
    if not rows:
        raise ValueError("the file has no rows for %s / %s; it holds %s" % (
            product, segment, "; ".join("%s / %s" % k for k in internal.keys())))
    idx = [qindex(r.quarter) for r in rows]
    four = [i >= 3 and idx[i] - idx[i - 3] == 3 for i in range(len(rows))]
    out = []
    if m.key.endswith("charge-off-rate"):
        attr = "net_charge_offs" if m.key.startswith("net") else "gross_charge_offs"
        for i, r in enumerate(rows):
            if not four[i]:
                out.append((r.quarter, None, WHY_WINDOW))
                continue
            win = rows[i - 3:i + 1]
            avg = sum(float(w.balance) for w in win) / 4
            if avg <= 0:
                out.append((r.quarter, None, WHY_NO_BALANCE))
                continue
            out.append((r.quarter, 100 * sum(float(getattr(w, attr)) for w in win) / avg, None))
        return out
    attr = "dpd_%s_plus" % m.key.split("-")[1]
    rates = [100 * float(getattr(r, attr)) / float(r.balance) if r.balance > 0 else None for r in rows]
    if m.basis == "quarter-end":
        return [(r.quarter, v, None if v is not None else WHY_NO_BALANCE) for r, v in zip(rows, rates)]
    for i, r in enumerate(rows):
        if not four[i]:
            out.append((r.quarter, None, WHY_WINDOW))
            continue
        gone = [rows[k].quarter for k in range(i - 3, i + 1) if rates[k] is None]
        if gone:
            out.append((r.quarter, None, WHY_RATE_MISSING % ", ".join(gone)))
        else:
            out.append((r.quarter, sum(rates[i - 3:i + 1]) / 4, None))
    return out


def series(internal: Internal, product: str, segment: str, measure: str) -> List[Tuple[str, Optional[float]]]:
    """``(quarter, value)`` pairs, oldest first, the shape
    ``books.write_series`` takes; None where there is no value. ``measure``
    is a key of ``MEASURES``."""
    return [(q, v) for q, v, _ in _series(internal, product, segment, measure)]


def series_notes(internal: Internal, product: str, segment: str, measure: str) -> List[str]:
    """The ``#`` lines for one series file: the measure, numerator,
    denominator and basis (the method, which this module applies), then the
    file's own as-of, source, entity and what the segment holds, copied as
    written."""
    m = _measure(measure)
    n = internal.notes
    return ["measure: %s. %s, segment %s, internal" % (m.title, product, segment),
            "numerator: %s" % m.numerator,
            "denominator: %s" % m.denominator,
            "basis: %s. The file's own basis: %s" % (m.basis, n["basis"]),
            "as-of: %s" % n["as-of"],
            "source: %s" % n["source"],
            "entity: %s" % n["entity"],
            "population: %s" % internal.segments[segment],
            "Written by 'internal series' from %s. Internal data: run on site, never committed."
            % Path(internal.path).name]


def series_file_name(product: str, segment: str, measure: str) -> str:
    from .peers.run import slug
    return "internal_%s_%s_%s.csv" % (slug(product), slug(segment), measure)


def write_all_series(internal: Internal, out_dir) -> List[dict]:
    """Every product, segment and measure as a ``date,value`` CSV in
    ``out_dir``. A series is written from its latest unbroken run (the
    workbook refuses a gap); what is left out, and why, is in its notes. A
    series with no value at all is not written. Returns ``[{path, written,
    quarters, left_out}]``."""
    from .peers.run import series_note, unbroken_tail
    out_dir = Path(out_dir)
    made = []
    for product, segment in internal.keys():
        for key in MEASURES:
            full = _series(internal, product, segment, key)
            tail, before, after = unbroken_tail([(q, v) for q, v, _ in full])
            path = out_dir / series_file_name(product, segment, key)
            note = series_notes(internal, product, segment, key)
            why: Dict[str, List[str]] = {}
            for q, v, w in full:
                if v is None:
                    why.setdefault(w, []).append(q)
            if why:
                note.append("No value: " + "; ".join("%s (%s)" % (", ".join(qs), w) for w, qs in why.items()))
            if tail:
                books.write_series(tail, path, series_note(note, tail, before, after))
            made.append({"path": path, "written": bool(tail), "quarters": len(tail),
                         "left_out": before + after})
    return made


# ---------------------------------------------------------------- reconcile

@dataclass(frozen=True)
class Comparison:
    """One internal figure (the sum of ``internal``'s product-segment rows)
    against one public one. Field names joined by '+' are summed
    (``books.parts``)."""
    name: str
    internal: Tuple[Tuple[str, str], ...]
    balance: str
    gross: str
    recoveries: str
    items: str


#: The public match for each internal figure (docs/INTERNAL-IMPORT.md). The
#: charge-off and recovery lines are RI-B's for the same loans as the RC-C
#: balance line.
COMPARISONS = (
    Comparison("Credit card", (("Credit card", ALL),), "LNCRCD", "DRCRCD", "CRCRCD",
               "RC-C 6.a; RI-B 5.a"),
    Comparison("Mortgage", (("Mortgage", ALL),), "LNRERSFM", "DRRERSFM", "CRRERSFM",
               "RC-C 1.c.(2)(a); RI-B 1.c.(2)(a)"),
    Comparison("Home equity lines", (("Home equity", "Home equity lines"),), "LNRELOC", "DRRELOC",
               "CRRELOC", "RC-C 1.c.(1); RI-B 1.c.(1)"),
    Comparison("Mortgage and home equity loans", (("Mortgage", ALL), ("Home equity", "Home equity loans")),
               "LNRERSFM+LNRERSF2", "DRRERSFM+DRRERSF2", "CRRERSFM+CRRERSF2",
               "RC-C 1.c.(2)(a) + (b); RI-B 1.c.(2)(a) + (b)"),
    Comparison("Other consumer", (("Other consumer", ALL),), "LNCONRP+LNAUTO+LNCONOTH",
               "DRAUTO+DRCONOTH", "CRAUTO+CRCONOTH", "RC-C 6.b + 6.c + 6.d; RI-B 5.b + 5.c"),
    Comparison("Auto", (("Auto", ALL),), "LNAUTO", "DRAUTO", "CRAUTO", "RC-C 6.c; RI-B 5.b"),
)

#: Every filed field ``reconcile`` reads; ``internal pull`` fetches these.
FIELDS = raw_fields(f for c in COMPARISONS for f in (c.balance, c.gross, c.recoveries))

COMPARED = ("balance", "gross_charge_offs", "net_charge_offs")

#: The nearest public measure to each internal past-due bucket. Stated, never
#: reconciled for equality: the buckets differ.
DELINQUENCY = (
    "Delinquency is not reconciled: the internal file counts days past due, cumulative; the Call Report "
    "(RC-N) files 30-89 days, 90+ days still accruing, and nonaccrual, some of which is not late at all.",
    "Nearest public measure to internal 30+: 30-89 + 90+ accruing + nonaccrual ('30+ incl. nonaccrual'). "
    "To internal 90+: 90+ accruing + nonaccrual ('90+ incl. nonaccrual'). The gap is nonaccrual loans that "
    "are current. Internal 60+ has no public counterpart.",
    "The public fields are peers/delinquency.py's FIELDS (P3, P9, NA per product); for internal other "
    "consumer, which holds direct auto, the nearest is other consumer plus auto (RC-N 5.b + 5.c).",
)

YES, NO, NOT_MEASURED = "yes", "no", "not measured"
RECONCILE_COLUMNS = ("quarter", "comparison", "measure", "public_fields", "filed", "excluded",
                     "excluded_names", "filed_less_excluded", "internal", "remainder", "remainder_share",
                     "within_tolerance", "why")


def _tolerance(tolerance) -> Decimal:
    """The stated tolerance as a ``Decimal``; refused when missing, not a
    number, not finite or below 0."""
    if tolerance is None or isinstance(tolerance, bool):
        raise ValueError("tolerance is required: the share of the internal figure an unexplained "
                         "remainder may be and still count as within, e.g. 0.01. It has no default")
    try:
        t = Decimal(str(tolerance).strip())
    except InvalidOperation:
        raise ValueError("tolerance must be a number, e.g. 0.01, not %r" % (tolerance,)) from None
    if not t.is_finite() or t < 0:
        raise ValueError("tolerance must be a finite number of at least 0, e.g. 0.01, not %r" % (tolerance,))
    return t


def _prev_repdte(repdte: str) -> str:
    i = qindex(label(repdte)) - 1
    return quarter_end(_quarter_label(i)).replace("-", "")


def _filed_amount(filed, present, cert, repdte, field):
    """``(Decimal, None)`` or ``(None, why)`` for one filed field at one
    quarter-end; a '+' name is the sum of its parts, and one part not filed
    makes the sum not filed."""
    q = label(repdte)
    if repdte not in filed:
        return None, "%s is not in the cache" % q
    row = filed[repdte].get(cert)
    if row is None:
        return None, "certificate %s has no row for %s in the cache" % (cert, q)
    total = Decimal(0)
    for f in parts(field):
        if f not in present[repdte]:
            return None, ("the cache for %s was pulled without %s; 'internal pull' fetches every field "
                          "reconcile reads, into its own cache folder" % (q, f))
        v = row.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            return None, "%s is blank for %s (not filed)" % (f, q)
        try:
            d = Decimal(str(v).strip())
        except InvalidOperation:
            d = Decimal("NaN")
        if not d.is_finite():
            raise ValueError("certificate %s, %s: %s is %r, not a number" % (cert, q, f, v))
        total += d
    return total, None


def _filed_flow(filed, present, cert, repdte, field):
    """The quarter's flow from year-to-date filings: Q1 is its own year to
    date, a later quarter its year to date less the quarter before's, or the
    year to date itself where it restarted under a new parent
    (``books.restarted``: push-down accounting, as the public series read it).
    A repeated year to date after an absorption under common control has
    already been taken off by ``reconcile``."""
    now, why = _filed_amount(filed, present, cert, repdte, field)
    if now is None or repdte[4:6] == "03":
        return now, why
    before = _prev_repdte(repdte)
    if before not in filed:
        return None, ("the quarter before, %s, is not in the cache, so the year to date cannot be "
                      "turned into the quarter's" % label(before))
    prev, why = _filed_amount(filed, present, cert, before, field)
    if prev is None:
        return None, why
    a, b = books._parent(filed[repdte][cert]), books._parent(filed[before][cert])
    if a and b and a != b and now < prev:
        return now, None
    return now - prev, None


def _key(product, segment):
    return "%s / %s" % (product, segment)


def _check_exclusions_against(internal: Internal, exclusions: Exclusions) -> None:
    """Refuse an exclusion nothing would use: its product and segment is in
    no comparison, or the internal file has no row for it that quarter."""
    compared = {ps for c in COMPARISONS for ps in c.internal}
    have = {(r.quarter, r.product, r.segment) for r in internal.rows}
    problems = []
    for e in exclusions.rows:
        if (e.product, e.segment) not in compared:
            problems.append("line %d: %s is not compared with a public line, so nothing would take "
                            "this exclusion; the comparisons take %s"
                            % (e.line, _key(e.product, e.segment),
                               "; ".join(_key(*ps) for ps in sorted(compared))))
        elif (e.quarter, e.product, e.segment) not in have:
            problems.append("line %d: the internal file has no row for %s, %s, so nothing would take "
                            "this exclusion" % (e.line, e.quarter, _key(e.product, e.segment)))
    if problems:
        raise Refused(exclusions.path, problems)


def reconcile(internal: Internal, filed: Dict[str, list], exclusions: Exclusions, tolerance, *,
              bank: dict, absorptions: Sequence[dict]) -> List[dict]:
    """Per comparison, quarter and measure (balance, gross and net
    charge-offs), the filed figure less the named exclusions against the
    internal one: ``{quarter, comparison, measure, public_fields, filed,
    excluded, excluded_names, filed_less_excluded, internal, remainder,
    remainder_share, within_tolerance, why}``.

    ``filed`` is ``{REPDTE: rows}`` as ``fdic.pull`` returns it; ``bank`` is
    the roster's entry for the filer (``cert`` and ``name``). The remainder is
    filed less excluded less internal, and its share is the remainder over the
    internal figure. ``within_tolerance`` is ``yes`` when the share is at most
    ``tolerance`` (required, no default; an internal figure of 0 is within only
    when the remainder is 0), ``no`` when it is not, and ``not measured``, with
    the reason in ``why``, when either side is not stated. Every quarter the
    file holds for a comparison is a row; nothing is skipped silently."""
    tol = _tolerance(tolerance)
    cert = str(bank["cert"])
    _check_exclusions_against(internal, exclusions)
    for q in filed:
        if not (isinstance(q, str) and len(q) == 8 and q.isdigit() and q[4:] in ("0331", "0630", "0930", "1231")):
            raise ValueError("filed must be keyed by YYYYMMDD quarter-ends, as fdic.pull returns it, not %r" % (q,))
    # The filing's charge-offs as the public series count them: where the
    # bank absorbed another under the same parent, the absorbed bank's year
    # to date, which the survivor's filing repeats, is taken off
    # (books.repeated_ytd; KeyBank and First Niagara, 2016Q4, is one).
    ytd = [f for c in COMPARISONS for f in parts(c.gross) + parts(c.recoveries)]
    filed = books.without_repeats(filed, books.repeated_ytd_fields(filed, absorptions, list(dict.fromkeys(ytd))))
    present = {q: {k for r in rows for k in r} for q, rows in filed.items()}
    snap = {q: {str(r.get("CERT")): r for r in rows} for q, rows in filed.items()}
    idx = {(r.quarter, r.product, r.segment): r for r in internal.rows}
    excl: Dict[tuple, List[Exclusion]] = {}
    for e in exclusions.rows:
        excl.setdefault((e.quarter, e.product, e.segment, e.measure), []).append(e)

    out = []
    for c in COMPARISONS:
        quarters = sorted({r.quarter for r in internal.rows if (r.product, r.segment) in c.internal},
                          key=qindex)
        for q in quarters:
            repdte = quarter_end(q).replace("-", "")
            mine = [idx.get((q,) + ps) for ps in c.internal]
            absent = [_key(*ps) for ps, r in zip(c.internal, mine) if r is None]
            for m in COMPARED:
                if m == "balance":
                    fields = c.balance
                    pub, why = _filed_amount(snap, present, cert, repdte, c.balance)
                else:
                    g, why = _filed_flow(snap, present, cert, repdte, c.gross)
                    pub = g
                    fields = c.gross
                    if m == "net_charge_offs":
                        fields = "(%s) - (%s)" % (c.gross, c.recoveries)
                        if g is not None:
                            rc, why = _filed_flow(snap, present, cert, repdte, c.recoveries)
                            pub = None if rc is None else g - rc
                taken = [e for ps in c.internal for e in excl.get((q,) + ps + (m,), [])]
                ex = sum((e.amount for e in taken), Decimal(0))
                inside = None if absent else sum((getattr(r, m) for r in mine), Decimal(0))
                row = {"quarter": q, "comparison": c.name, "measure": m, "public_fields": fields,
                       "filed": pub, "excluded": ex if taken else None,
                       "excluded_names": "; ".join("%s (%s)" % (e.name, _key(e.product, e.segment))
                                                   for e in taken),
                       "filed_less_excluded": None if pub is None else pub - ex,
                       "internal": inside, "remainder": None, "remainder_share": None,
                       "within_tolerance": NOT_MEASURED, "why": ""}
                if absent:
                    row["why"] = "the internal file has no row for %s in %s" % (" or ".join(absent), q)
                elif pub is None:
                    row["why"] = "filed figure not stated: " + why
                else:
                    rem = pub - ex - inside
                    row["remainder"] = rem
                    if inside == 0:
                        row["within_tolerance"] = YES if rem == 0 else NO
                        if rem != 0:
                            row["why"] = "the internal figure is 0, so the remainder has no share"
                    else:
                        share = rem / inside
                        row["remainder_share"] = share
                        row["within_tolerance"] = YES if abs(share) <= tol else NO
                out.append(row)
    return out


def reconcile_notes(internal: Internal, exclusions: Exclusions, bank: dict, tolerance,
                    source: str) -> List[str]:
    """The ``#`` lines for the reconciliation file: which two entities, the
    tolerance, how charge-offs are read, each comparison (and any not made,
    with why), the exclusions' source, and the nearest public delinquency
    measures."""
    tol = _tolerance(tolerance)
    have = set(internal.keys())
    lines = [
        "Reconciliation of the internal file %s against the Call Report, written by 'internal reconcile'. "
        "Internal data: run on site, never committed." % Path(internal.path).name,
        "Compared: %s (the internal file's entity) against %s, FDIC certificate %s (the Call Report "
        "filer). They are different entities: part of any remainder can be the difference between them."
        % (internal.notes["entity"], bank["name"], bank["cert"]),
        "Remainder = filed, less the named exclusions, less the internal figure; its share is the "
        "remainder over the internal figure. Within tolerance when the share is at most %s, the "
        "tolerance stated on the command line (there is no default). Amounts in $ thousands."
        % format(tol, "f"),
        "Charge-offs: the Call Report files them year to date, so a quarter is its year to date less the "
        "quarter before's (Q1 is its own), counted as the public series count them: where the bank "
        "absorbed another under the same parent, the absorbed bank's year to date, which the filing "
        "repeats, is taken off (from absorptions.json beside the cache); a year to date that restarted "
        "under a new parent is the quarter's own.",
        source,
    ]
    for c in COMPARISONS:
        gone = [_key(*ps) for ps in c.internal if ps not in have]
        what = " plus ".join(_key(*ps) for ps in c.internal)
        if gone:
            lines.append("Not compared: %s (internal %s against %s), because the file has no rows for %s."
                         % (c.name, what, c.items, " or ".join(gone)))
        else:
            lines.append("%s: internal %s against %s (%s; charge-offs %s, recoveries %s)."
                         % (c.name, what, c.items, c.balance, c.gross, c.recoveries))
    if exclusions.rows:
        lines.append("Exclusions: %d named, from %s. Source: %s"
                     % (len(exclusions.rows), Path(exclusions.path).name, exclusions.notes["source"]))
    else:
        lines.append("Exclusions: none named (%s has no rows)." % Path(exclusions.path).name)
    return lines + list(DELINQUENCY)


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def write_reconciliation(rows: Sequence[dict], notes: Sequence[str], path) -> Path:
    """The reconciliation as a CSV: the notes as ``#`` lines, then one row
    per comparison, quarter and measure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        for item in notes:
            for line in str(item).splitlines():
                fh.write("# %s\n" % line)
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(RECONCILE_COLUMNS)
        for r in rows:
            row = []
            for k in RECONCILE_COLUMNS:
                v = r[k]
                if k == "remainder_share" and v is not None:
                    row.append("%.6g" % float(v))
                else:
                    row.append(_cell(v))
            w.writerow(row)
    return path


def quarters_to_read(internal: Internal) -> Tuple[List[str], List[str]]:
    """``(needed, wanted)`` as REPDTEs: every quarter the file holds, and the
    quarter before each that is not a Q1 and not itself held (the year to
    date is differenced against it; read when cached, stated when not)."""
    held = sorted({qindex(r.quarter) for r in internal.rows})
    needed = [quarter_end(_quarter_label(i)).replace("-", "") for i in held]
    wanted = []
    for i in held:
        if i % 4 and (i - 1) not in held:
            wanted.append(quarter_end(_quarter_label(i - 1)).replace("-", ""))
    return needed, wanted


def read_filed(internal: Internal, cache) -> Dict[str, list]:
    """The cached Call Report quarters ``reconcile`` reads, through
    ``fdic.pull`` with a downloader that refuses, so nothing is fetched. A
    quarter the file holds that is not cached is refused, naming it; a quarter
    before one, wanted only to difference the year to date, is read when
    cached and otherwise left out (the rows that need it say so)."""
    from .peers import fdic

    def no_fetch(url):
        raise ValueError("reconcile reads the cache only and never fetches")
    cache = Path(cache)
    needed, wanted = quarters_to_read(internal)
    missing = [q for q in needed if not (cache / ("q%s.json" % q)).exists()]
    if missing:
        raise ValueError("%s has no %d of the %d quarters the internal file holds (first missing %s): run "
                         "'internal pull' for them first; reconcile never fetches"
                         % (cache, len(missing), len(needed), label(missing[0])))
    have = needed + [q for q in wanted if (cache / ("q%s.json" % q)).exists()]
    return fdic.pull(sorted(have), [], cache, fetch=no_fetch)


def pull(cache, first: str, last: str, fetch=None) -> Dict[str, list]:
    """Fetch every field ``reconcile`` reads (``FIELDS`` and each filer's
    parent) for every filer, ``first`` to ``last`` (``YYYYQn``), into
    ``cache``; quarters already there are read, not fetched. Then the FDIC's
    record of who absorbed whom since the start of ``first``'s year, into
    ``cache/absorptions.json``, which ``reconcile`` reads. Public data only.
    Use a cache folder of its own: a peers cache was pulled with other fields
    and is refused by name."""
    import json
    from .peers import fdic
    data = fdic.pull(fdic.quarter_ends(first, last), FIELDS + [books.PARENT], cache, fetch=fetch)
    rows = fdic.history("%s-01-01" % first[:4], fetch=fetch)
    (Path(cache) / ABSORPTIONS).write_text(json.dumps(fdic.absorptions(rows), indent=1), encoding="utf-8")
    return data


#: Who absorbed whom, beside the cache 'internal pull' fills.
ABSORPTIONS = "absorptions.json"


def read_absorptions(cache) -> List[dict]:
    """``cache/absorptions.json``, as 'internal pull' writes it; refused, by
    name, when it is not there."""
    from .peers.run import load_absorptions
    path = Path(cache) / ABSORPTIONS
    if not path.exists():
        raise ValueError("%s is not there: reconcile needs the FDIC's record of who absorbed whom, so a "
                         "repeated year to date is not counted twice. Run 'internal pull' again" % path)
    return load_absorptions(path)
