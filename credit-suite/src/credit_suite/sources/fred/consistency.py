"""S1, C3 and C5 -- the shipped artifact against its source of record.

**S1, the units defect.** ``series_seed.py`` carries a comment written the day
it was fixed::

    # MILLIONS, not billions: the Board prints 5,166,907.71 for June 2026

The shipped ``FRED_Credit_Risk_Dashboard.xlsm`` ``_config`` tab declares
``billions $`` for the same four G.19 series, beside a ``TOTALSL`` of
5,166,907.71 -- three orders of magnitude out, on the line a reader reads,
with the number itself correct, which is why nothing caught it. The source is
fixed. The artifact a person opens is not, and ``example-output/`` is in
``.gitignore``, so nothing in version control can tell you that.

The check compares the artifact to ``series_seed.py``, cell for cell.
Deliberately NOT "the workbook's declared units match the workbook's own
numbers" -- that is one file agreeing with itself, and it is one edit away
from being a mirror.

``layout.config_rows`` already DERIVES ``_config`` from the seed, so a freshly
built workbook passes by construction; the prevention is already in place and
this is the detector for the artifacts built before it. Point it at a shipped
workbook and it says whether that file is older than its source.

**C3, the vintage.** All 142 series in the shipped workbook carry one vintage.
Uniformity is the current state, so skew is new and means part of the workbook
did not refresh; a vintage that moved backwards means it refreshed from the
wrong place.

**C5, the date grid.** Strictly ordered, unique, stepping by the declared
cadence. 142 of 142 are regular today. Every transform downstream
(``zscore_8q``, ``yoy_pct``) silently gives a wrong answer on a broken grid,
which is what makes this worth a gate rather than a flag.

One thing it will not do is refuse an interior HOLE -- a gap that is a whole
number of steps. ``DRTSSP`` has 19 of them, the SLOOS does not ask every
question every quarter, and nothing in this repository records whether the
Board simply skipped those. That is UNKNOWN until somebody checks the release
history, not a build failure: a gate that refuses on it would be the false
alarm the design spends a page warning about.
"""

from __future__ import annotations

import re
from typing import Mapping, Optional, Sequence

from credit_suite.engine import consistency as K
from credit_suite.sources.fred import series_seed as SEED

#: The two Z.1 commercial-property series where our config, FRED and the Board
#: give three different answers on units, and the FRED tie-out could not
#: establish which is right. This check compares the artifact to the seed, so
#: it takes no position on either -- and a PASS here must not be read as
#: having confirmed the seed's answer for these two.
UNRESOLVED_UNITS = ("BOGZ1FL075035403Q", "BOGZ1FL075035503Q")

_VINTAGE = re.compile(r"vintage=(\d{4}-\d{2}-\d{2})")

# --------------------------------------------------------------------------
# S1 -- _config against the seed
# --------------------------------------------------------------------------

def _cell(value) -> str:
    return "" if value is None else str(value).strip()


def series_rows_of(rows: Sequence[Sequence]):
    """The ``[SERIES]`` block of a ``_config`` sheet: (header, {id: row}).

    Returns ``(None, {})`` when the sheet carries no such block -- an older
    build, or a tab that did not parse. That is UNKNOWN, not empty.
    """
    section = None
    header = None
    out = {}
    for raw in rows:
        cells = [_cell(c) for c in (raw or [])]
        first = cells[0] if cells else ""
        if first.startswith("[") and first.endswith("]"):
            section = first.strip("[]").strip().upper()
            continue
        if not first or section != "SERIES":
            continue
        # The header is captured once and NOT reset by the sections that
        # follow. It was, on the first draft, and the parser then handed back
        # a header of None over 142 correctly-parsed rows -- which the caller
        # would have reported as "no [SERIES] section", the honest answer to
        # the wrong question.
        if header is None:
            header = cells
            continue
        out[first] = cells
    return header, out


def config_matches_seed(rows: Sequence[Sequence]) -> K.CheckResult:
    """S1 -- every ``_config`` cell equals what ``series_seed.py`` says.

    The denominator is cells, not rows: a row-level comparison would report
    "142 of 142 series present" over a units column that had been rewritten.
    """
    header, found = series_rows_of(rows)
    if header is None:
        return K.undetermined(
            "S1", "the _config sheet carries no [SERIES] section, so the "
                  "artifact could not be compared with series_seed.py at all",
            unit="cells")

    seed = {row["series_id"]: row for row in SEED.all_series()}
    columns = SEED.HEADER
    ids = sorted(set(seed) | set(found))
    examined = len(ids) * len(columns)
    failures = []

    if header != list(columns):
        failures.append(
            "the [SERIES] header is %r; series_seed.HEADER is %r"
            % (header, list(columns)))

    index = {name: i for i, name in enumerate(header)}
    for series_id in ids:
        if series_id not in found:
            failures.append("%s: in series_seed.py, absent from the artifact"
                            % series_id)
            continue
        if series_id not in seed:
            failures.append("%s: in the artifact, absent from series_seed.py"
                            % series_id)
            continue
        cells = found[series_id]
        for column in columns:
            want = _cell(seed[series_id][column])
            position = index.get(column)
            got = cells[position] if position is not None \
                and position < len(cells) else None
            if got is None:
                failures.append("%s.%s: the artifact has no such column"
                                % (series_id, column))
            elif got != want:
                failures.append("%s.%s: artifact %r, series_seed.py %r"
                                % (series_id, column, got, want))
    return K.decide("S1", examined, failures, unit="cells")


# --------------------------------------------------------------------------
# C3 -- the vintage moves forward, and moves together
# --------------------------------------------------------------------------

def vintage_of(meta: Optional[str]) -> Optional[str]:
    """The vintage out of a raw block's meta string, or None if it has none.

    Reads what ``runner.block_meta`` writes rather than being a second parser
    of the same string.
    """
    if not meta:
        return None
    match = _VINTAGE.search(str(meta))
    return match.group(1) if match else None


def vintage_check(current: Mapping[str, Optional[str]],
                  previous: Optional[Mapping[str, Optional[str]]]
                  ) -> K.CheckResult:
    """C3 -- one vintage across the run, and never earlier than the last one.

    ``previous=None`` is the first run against a fresh workbook: the forward
    leg cannot be established, so it says so and ships.
    """
    examined = len(current)
    failures = []
    unknowns = []

    missing = sorted(sid for sid, value in current.items() if not value)
    if missing:
        unknowns.append(
            "%d series carry no vintage at all (%s) -- the block was written "
            "without one, so 'did it refresh' cannot be answered for them"
            % (len(missing), ", ".join(missing[:8])))

    stamps = {}
    for sid, value in current.items():
        if value:
            stamps.setdefault(value, []).append(sid)
    if len(stamps) > 1:
        detail = "; ".join(
            "%s: %s" % (stamp, ", ".join(sorted(ids)[:4]))
            for stamp, ids in sorted(stamps.items()))
        failures.append(
            "the run carries %d different vintages, so part of the workbook "
            "did not refresh -- %s" % (len(stamps), detail))

    unsettled = None
    if previous is None:
        unknowns.append(
            "no previous run was recorded, so whether the vintage moved "
            "forward could not be established for any of the %d series -- "
            "shipped, and said" % examined)
        # One sentence, every series unsettled. Reporting it as 1 of 142 would
        # claim 141 series had been checked against a previous run that does
        # not exist.
        unsettled = examined
    else:
        for sid, value in sorted(current.items()):
            was = previous.get(sid)
            if value and was and value < was:
                failures.append(
                    "%s: vintage moved backwards, %s then %s -- the block "
                    "refreshed from an older release" % (sid, was, value))

    return K.decide("C3", examined, failures, unknowns, unit="series",
                    unknown=unsettled)


# --------------------------------------------------------------------------
# C5 -- the date grid is regular
# --------------------------------------------------------------------------
#
# The check itself lives in ``engine.consistency``: it is arithmetic on dates
# and a declared cadence, with nothing FRED-specific in it, and the FRED
# runner has to be able to import it. The runner deliberately does NOT import
# ``series_seed`` -- the dictionary in the workbook is the contract and the
# runner just reads it -- and this module does, for S1. Re-exported here so a
# reader looking for FRED's checks finds all three in one place.
date_grid = K.date_grid
date_grid_all = K.date_grid_all
