"""The adversarial pass of 19 September 2026, taken into the suite.

A second model was handed the built pack with one job — break it — and could
write only tests (canon skill `adversarial`). It formed 35 hypotheses, tried
all 35, and 16 went red against the code at a2c67ba; the other 19 are listed
as clean in BACKLOG.md section 6c. Every red test is here. Fifteen were bugs
against the PRD or the README and were fixed; the sixteenth (moving a live
knob) was arguable, and its expectation is restated below to what the firm
would want: never a false count. Each docstring describes the behaviour as it
was found; the code now does what the test asserts.

Three tests recalculate a workbook with the `formulas` engine (about twelve
seconds each); the rest are fast.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

from analysis_pack import ladder, stats, synth                      # noqa: E402
from analysis_pack.cli import main                                  # noqa: E402
from analysis_pack.config import Config, load_config                # noqa: E402
from analysis_pack.ingest import inspect_columns, read_table        # noqa: E402
from analysis_pack.population import add_months, build_population   # noqa: E402
from analysis_pack.workbook import build_pack                       # noqa: E402

ASOF = date(2026, 6, 30)
RUN = date(2026, 9, 18)
ORIG = add_months(ASOF, -30)          # comfortably seasoned at a 24-month window

COLUMNS = ["loan_id", "origination_date", "field_a", "field_b", "amount", "category_1",
           "category_2", "code_1", "outcome_date", "flag_1", "measure_a", "measure_b"]


# --------------------------------------------------------------------------
# Fixtures: a question file the tool wrote itself, plus books built by hand
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def question_file(tmp_path_factory) -> Path:
    """The synthetic question file, straight from `pack synth`. Only the
    loans change from test to test; the question never does."""
    d = tmp_path_factory.mktemp("question")
    synth.generate(d, seed=20260918, loans=50, mode="effect")
    return d / "config.yaml"


def loan(i: int, *, ratio: float = 3.0, event: bool = False, amount: str = "120000",
         category_1: str = "north", category_2: str = "kind_1", measure_a: str = "1.0",
         origination: date = ORIG, field_b: str = "1000") -> dict:
    return {"loan_id": "L%05d" % i, "origination_date": origination.isoformat(),
            "field_a": "%.6f" % (ratio * float(field_b)), "field_b": field_b,
            "amount": amount, "category_1": category_1, "category_2": category_2,
            "code_1": "111111",
            "outcome_date": add_months(origination, 12).isoformat() if event else "",
            "flag_1": "1" if event else "0", "measure_a": measure_a, "measure_b": "2.0"}


def write_book(where: Path, rows: list[dict], name: str = "loans.csv") -> Path:
    p = where / name
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


def build(question_file: Path, data_path: Path, cfg: Config | None = None):
    cfg = cfg or load_config(question_file)
    table = read_table(data_path)
    pop = build_population(cfg, table.rows, ASOF)
    blob, data, checks = build_pack(cfg, pop, table, RUN)
    return cfg, pop, table, blob, data, checks


def recalculated(blob: bytes, **kw):
    from recalc import Recalc
    return Recalc(blob, **kw)


def check_verdicts(rec) -> list[tuple[int, str]]:
    return [(r, v) for r, v in sorted(rec.column("_check", "G").items()) if r >= 2]


# --------------------------------------------------------------------------
# 1. The gradient headline
# --------------------------------------------------------------------------

def test_an_empty_bucket_must_not_hide_a_fall_in_the_rate(question_file, tmp_path):
    """PRD 5.13: "A monotonicity read over buckets with n > 0: monotonic
    increasing, monotonic decreasing, or not monotonic on point estimates."

    Here four of the five buckets hold 200 loans each and the rates over them
    run 5%, 20%, 1%, 2% -- a twenty-fold fall in the middle. The fifth bucket
    (1 - 2) holds no loans at all. The read must be `not monotonic`, because
    the rates over the buckets with n > 0 do not rise.

    The code compares only ADJACENT pairs where both buckets hold loans, so the
    empty bucket breaks the chain and the fall from 20% to 1% is never looked
    at. The pack reports `monotonic increasing` and the cover publishes
    "Gradient: yes. As the ratio rises, the event rate rises at every step."
    """
    rows, i = [], 0
    for ratio, n, events in ((0.25, 200, 10), (0.75, 200, 40), (3.0, 200, 2), (7.0, 200, 4)):
        for k in range(n):
            i += 1
            rows.append(loan(i, ratio=ratio, event=k < events))
    p = write_book(tmp_path, rows)
    cfg, pop, _, _, data, _ = build(question_file, p)
    g = data.per_outcome[0][1]
    rates = [r.rate for r in g.rows if r.cube.n > 0]
    assert rates == pytest.approx([0.05, 0.20, 0.01, 0.02]), rates
    assert g.word == "not monotonic", (g.word, rates, g.diffs)


def test_a_book_with_no_events_must_not_report_a_rising_gradient(question_file, tmp_path):
    """README, on the cover tab: "the answer in three lines". PRD 5.17.

    When the outcome never happens, every bucket rate is exactly zero. Nothing
    rises anywhere, so the cover must not tell the reader that the rate rises
    at every step -- the wording file already carries a variant for "there is
    no gradient to read", and canon behaviour 6 says a case the pack cannot
    answer gets its own answer rather than being folded into `yes`.

    As it stands, all-zero rates make every adjacent difference 0.0, which
    passes the `no negative differences` test, so the word is `monotonic
    increasing` and the cover reads "Gradient: yes. As the ratio rises, the
    event rate rises at every step." on a book with zero events. Checked on a
    1,500-loan zero-event book: it recalculates to "1374 of 1374 formula checks
    agree", so nothing anywhere in the pack contradicts the sentence.
    """
    rows = [loan(i, ratio=0.25 + 0.5 * (i % 6), event=False) for i in range(1, 601)]
    p = write_book(tmp_path, rows)
    cfg, pop, _, _, data, _ = build(question_file, p)
    facts, g = data.per_outcome[0]
    assert facts.events == 0 and facts.seasoned == 600
    assert g.word != "monotonic increasing", (g.word, [r.rate for r in g.rows])


# --------------------------------------------------------------------------
# 2. Blanks in a grouping column
# --------------------------------------------------------------------------

def test_a_blank_in_a_decomposition_dimension_keeps_the_packs_own_check_green(question_file, tmp_path):
    """PRD 5.26: "The test suite recalculates every fixture with the `formulas`
    engine and fails on any MISMATCH." PRD 8: "the recalculated cover reads
    `N of N formula checks agree`."

    Step 5's "share of all flagged events" is worked out two ways that only
    agree when no loan has a blank in the dimension. Python divides the level's
    flagged events by the flagged events in the WHOLE seasoned book; the Excel
    formula divides by the sum of the rows PRINTED ON THE TAB, and loans with a
    blank value are printed nowhere. Here 100 of the 200 flagged loans have a
    blank `category_1` and carry 30 of the 50 flagged events: Python's twin
    says 0.4 and the sheet says 1.0.

    Built and recalculated, this pack's cover reads "619 of 620 formula checks
    agree". A pack the tool built without a murmur reports itself as wrong.
    """
    rows = []
    for k in range(100):
        rows.append(loan(len(rows) + 1, ratio=3.0, event=k < 20, category_1="north"))
    for k in range(100):
        rows.append(loan(len(rows) + 1, ratio=3.0, event=k < 30, category_1=""))
    for k in range(100):
        rows.append(loan(len(rows) + 1, ratio=0.3, event=k < 5, category_1="north"))
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(question_file, p)
    rec = recalculated(blob)
    bad = [(r, v) for r, v in check_verdicts(rec) if v != "OK"]
    detail = [(rec.value("_check", "A%d" % r), rec.value("_check", "B%d" % r),
               rec.value("_check", "D%d" % r), rec.value("_check", "E%d" % r)) for r, _ in bad]
    assert not bad, (rec.find_text("Cover", "formula checks agree"), detail)


def test_a_blank_grouping_value_gets_its_own_level_rather_than_vanishing(question_file, tmp_path):
    """PRD 6.8: "Blank category -> level `(blank)`, always last."

    Steps 4 and 5 build their levels from the values they find and silently
    drop every loan whose value is blank. On this book a third of the seasoned
    loans have no `category_1` and no `category_2`; the capture tab counts them
    as blank, and then they leave the analysis with no row, no count and no
    sentence saying how many left. A reader of step 5 cannot tell whether the
    tab covers the book or two thirds of it.
    """
    rows = []
    for k in range(300):
        blank = k % 3 == 0
        rows.append(loan(k + 1, ratio=3.0 if k % 2 else 0.3, event=k % 7 == 0,
                         category_1="" if blank else "north",
                         category_2="" if blank else "kind_1"))
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(question_file, p)
    dropped = [l for l in pop.seasoned if l.rule_value is not None and l.values.get("category_1") is None]
    assert len(dropped) == 100
    dec = next(d for d in data.decompositions if d.dimension == "category_1")
    strat = next(s for s in data.strata if s.confounder == "category_2")
    assert "(blank)" in [r.label for r in dec.rows], [r.label for r in dec.rows]
    assert "(blank)" in [b.label for b in strat.bands], [b.label for b in strat.bands]


def test_the_crude_odds_ratio_labelled_whole_population_is_the_whole_population(question_file, tmp_path):
    """The row the pack writes on `4_Stratified` says, in its own words,
    "Crude odds ratio, whole population -- ratio, lower, upper". PRD 5.14 asks
    for "the crude odds ratio beside the pooled one" so a reader can see how
    much of the effect the confounder explains.

    The number under that label is worked out from the bands only, so every
    loan with a blank in THAT confounder is silently missing from it -- and the
    figure therefore changes from block to block on the same tab, under the
    same label, for reasons that have nothing to do with the confounder.

    On this book the crude odds ratio over the whole population is 6.42. The
    `size_band` and `category_2` blocks print 6.42. The `amount_band` block
    prints 2.11, because half the loans have no `amount`, and its one-word
    verdict flips from `survives` to `no crude effect` -- which the cover then
    publishes as the answer.
    """
    rows = []
    for k in range(200):
        rows.append(loan(len(rows) + 1, ratio=3.0, event=k < 20, amount="120000"))
    for k in range(200):
        rows.append(loan(len(rows) + 1, ratio=0.3, event=k < 10, amount="120000"))
    for k in range(200):
        rows.append(loan(len(rows) + 1, ratio=3.0, event=k < 60, amount=""))
    for k in range(200):
        rows.append(loan(len(rows) + 1, ratio=0.3, event=k < 5, amount=""))
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(question_file, p)

    seasoned_both = [l for l in pop.seasoned if l.rule_value is not None]
    a = sum(1 for l in seasoned_both if l.fires and l.events["o1"])
    b = sum(1 for l in seasoned_both if l.fires and not l.events["o1"])
    c = sum(1 for l in seasoned_both if not l.fires and l.events["o1"])
    d = sum(1 for l in seasoned_both if not l.fires and not l.events["o1"])
    truth = stats.crude_odds_ratio(a, b, c, d, stats.z_for_confidence(cfg.confidence))[0]
    assert truth == pytest.approx(6.4167, abs=1e-3)

    printed = {"%s.%s" % (st.confounder, st.scheme): st.crude[0] for st in data.strata}
    off = {k: v for k, v in printed.items() if v is None or abs(v - truth) > 1e-6}
    assert not off, (off, truth, {k: v for k, v in printed.items()})


# --------------------------------------------------------------------------
# 3. Blanks in the outcome
# --------------------------------------------------------------------------

def test_a_blank_snapshot_measure_is_counted_and_not_silently_a_non_event(question_file, tmp_path):
    """PRD 6.4, on the snapshot outcome: "a blank measure is non-event and is
    counted as blank on `1_Capture`." PRD 5.5 (user story 5): blanks are "a
    finding, not dirt", counted on the capture tab.

    Nothing counts them. A loan with no balance at the as-of date is recorded
    as "did not go bad" and appears nowhere -- not on `1_Capture`, not in
    `_cube`, not on `_provenance`, not in the method note. On this book a third
    of the seasoned loans have no measure; the headline rate is worked out over
    all of them, so it understates the rate among the loans that actually had
    one, and no number in the workbook lets a reader notice.
    """
    text = question_file.read_text(encoding="utf-8").replace(
        "outcome:\n  label: event\n  date_field: outcome_date\n",
        "outcome: {label: drawn, measure: {kind: ratio, field_a: measure_a, field_b: measure_b},"
        " op: '>=', value: 0.5, basis: snapshot_at_asof}\n")
    snap_cfg_path = tmp_path / "snapshot.yaml"
    snap_cfg_path.write_text(text, encoding="utf-8")

    rows = [loan(i, ratio=3.0 if i % 2 else 0.3, measure_a="" if i % 3 == 0 else "1.8")
            for i in range(1, 301)]
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(snap_cfg_path, p)
    blank_measure = [l for l in pop.seasoned if l.measure is None]
    assert len(blank_measure) == 100
    assert not any(l.events["o1"] for l in blank_measure)

    wb = load_workbook(io.BytesIO(blob))
    named = []
    for sheet in ("1_Capture", "_cube"):
        for row in wb[sheet].iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and ("measure_a" in cell.value or "measure_b" in cell.value):
                    named.append((sheet, cell.coordinate, cell.value))
    assert named, ("neither 1_Capture nor _cube mentions the measure at all, so the %d seasoned "
                   "loans with no measure at the as-of date are counted nowhere"
                   % len(blank_measure))


def test_each_outcomes_block_sits_under_its_own_event_count(question_file, tmp_path):
    """PRD 5.22: "Every results tab repeats the file name, hash, seasoned
    count, event count, generator version and run date in its header band."
    PRD 5.9 lets a measure outcome carry `edges`, which gives one outcome per
    edge -- "every step is shown once per band edge".

    With more than one outcome there is no single event count, and steps 4 and
    5 print the FIRST outcome's on every block. On this book the three outcomes
    carry 800, 800 and 0 events; `4_Stratified` heads all nine blocks with
    "800 events", so the reader looking at the `drawn >= 0.8` block -- which
    has none -- reads 800. Step 3 gets this right: its section band states each
    outcome's own count. Steps 4 and 5 do not.
    """
    text = question_file.read_text(encoding="utf-8").replace(
        "outcome:\n  label: event\n  date_field: outcome_date\n",
        "outcome: {label: drawn, measure: {kind: ratio, field_a: measure_a, field_b: measure_b},"
        " edges: [0.2, 0.5, 0.8], basis: snapshot_at_asof}\n")
    edges_cfg = tmp_path / "edges.yaml"
    edges_cfg.write_text(text, encoding="utf-8")
    rows = [loan(i, ratio=0.4 + 0.2 * (i % 20), measure_a="1.0") for i in range(1, 201)]
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(edges_cfg, p)
    expected = {facts.events for facts, _ in data.per_outcome}
    assert expected == {200, 0}, expected

    import re
    wb = load_workbook(io.BytesIO(blob))
    stated = set()
    for row in wb["4_Stratified"].iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                for m in re.finditer(r"(\d[\d,]*) events", cell.value):
                    stated.add(int(m.group(1).replace(",", "")))
    assert stated == expected, stated


# --------------------------------------------------------------------------
# 4. Sentences that state a number the counts do not support
# --------------------------------------------------------------------------

def test_step_seven_states_no_share_when_no_loan_carries_both_fields(question_file, tmp_path):
    """DESIGN-PRINCIPLES: never invent a value; refuse rather than default.
    PRD 5.17: step 7 reports "the share of seasoned loans with both fields
    present where the rule fires".

    On a book whose loans are all younger than the window there are no seasoned
    loans, so there is no share. The cell on `7_Control` gets this right and
    prints nothing. The sentence printed two rows below it, and repeated on the
    cover, reads "In 0.0% of the 0 seasoned loans where both field_a and
    field_b are present, field_a / field_b > 1." The share is written as
    `share or 0.0` -- a missing number replaced with zero, which reads as
    "checked, and it never happens".
    """
    young = add_months(ASOF, -3)
    rows = [loan(i, ratio=3.0, origination=young) for i in range(1, 21)]
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(question_file, p)
    assert len(pop.seasoned) == 0 and data.control.both.n == 0 and data.control.share is None

    wb = load_workbook(io.BytesIO(blob))
    sentences = [str(c.value) for row in wb["7_Control"].iter_rows() for c in row
                 if isinstance(c.value, str) and ("seasoned loans where both" in c.value
                                                  or "No seasoned loan carries both" in c.value)]
    assert sentences, "step 7 printed no share sentence at all"
    assert not any("%" in s for s in sentences), sentences
    assert any("cannot be read" in s for s in sentences), sentences


def test_one_bad_value_is_refused_once_not_twice(question_file, tmp_path, capsys):
    """PRD 6.3: on a hygiene failure the tool must "write the CSV, print counts
    per reason and the file path". Canon behaviour 2: report the denominator,
    and a count that is not a count is worse than no count.

    A column used both as a rule field and as a confounder is checked twice and
    reported twice. One unparseable value, in one column, on one loan, is
    written to `hygiene-<name>.csv` as two identical rows and announced as
    "2 x non-numeric". The guard against this exists for fields carrying a
    `plausible` range and was not extended to the rule fields.
    """
    rows = [loan(i, ratio=3.0) for i in range(1, 21)]
    rows[0]["field_b"] = "not a number"
    p = write_book(tmp_path, rows)
    rc = main(["build", str(question_file), "--data", str(p), "--asof", ASOF.isoformat(),
               "-o", str(tmp_path / "pack.xlsx")])
    captured = capsys.readouterr()
    assert rc == 2
    status = json.loads(captured.out)
    refusals = list(csv.DictReader((tmp_path / ("hygiene-%s.csv" % load_config(question_file).name)).read_text().splitlines()))
    assert len(refusals) == 1, refusals
    assert status["counts"] == {"non-numeric": 1}, status["counts"]


# --------------------------------------------------------------------------
# 5. The front door: inspect, list, suggest
# --------------------------------------------------------------------------

def test_inspect_reports_the_date_pattern_of_a_column_the_build_reads_as_dates(question_file, tmp_path):
    """PRD 5.5: "`pack inspect DATA` prints, per column: inferred type
    (integer, decimal, date-like, text, mixed), null share, distinct count,
    five sample values, and the date pattern that parses the most date-like
    values." README: "Look at an extract first."

    A date column written the way a mainframe writes it -- 20210315 -- is all
    digits, so `inspect` calls it an `integer` and prints no date line for it.
    The build then detects `%Y%m%d` and reads the same column as dates. The one
    command the reviewer is told to run first tells them nothing about the one
    thing the build is about to decide on their behalf.
    """
    rows = [dict(loan(i), origination_date="2021%02d15" % ((i % 12) + 1)) for i in range(1, 31)]
    p = write_book(tmp_path, rows)
    table = read_table(p)
    entry = {e["column"]: e for e in inspect_columns(table)}["origination_date"]

    cfg = load_config(question_file)
    plain = Config(**{**cfg.__dict__, "date_format": None})
    pop = build_population(plain, table.rows, ASOF)
    assert pop.date_formats["origination_date"] == "%Y%m%d"
    assert entry.get("dates"), entry


def test_inspect_survives_an_extract_with_a_header_and_no_rows(tmp_path):
    """PRD 6.16: "Exit codes: 0 OK - 1 error - 2 refused". The CLI catches
    OSError and ValueError and turns them into exit 1.

    An extract with a header and no rows -- what a filter that matched nothing
    produces -- makes `inspect` raise TypeError out of the command, past the
    handler, as a traceback. It is the "nothing to look at" case, and the tool
    has no answer for it.
    """
    p = tmp_path / "empty.csv"
    p.write_text("loan_id,origination_date,field_a\n", encoding="utf-8")
    assert main(["inspect", str(p)]) in (0, 1)


def test_pack_list_exists(tmp_path, question_file):
    """PRD 6.16 sets out the command line and includes
    `pack list [DIR]  # configs and their validity`; PRD 3 repeats it --
    "Config is YAML; `pack list` / `pack validate` are the only front door."

    There is no `list` subcommand. argparse rejects it and exits 2, which is
    the code the tool reserves for "refused", so a script cannot even tell a
    missing command from a refused question file.
    """
    try:
        rc = main(["list", str(question_file.parent)])
    except SystemExit as exc:                      # argparse: "invalid choice: 'list'"
        pytest.fail("pack list is set out in PRD 6.16 and does not exist "
                    "(argparse exited %r, the code the tool reserves for `refused`)" % exc.code)
    assert rc == 0


def test_suggest_answers_field_on_demand_for_any_numeric_column(question_file, tmp_path, capsys):
    """PRD 6.6: "For each confounder with a numeric field (and for `--field
    COL` on demand)". README: "Ask for band cut points before writing them."

    `--field` only works for a column that already happens to be a confounder
    or a control, because those are the only values the population keeps per
    loan. Ask for bands on `field_a` -- the rule's own field, the column a
    reviewer is most likely to want banded -- and the command prints "no
    seasoned loan carries a numeric value in `field_a`", emits
    `{"ok": true, "suggestions": []}` and exits 0. A green nothing.
    """
    rows = [loan(i, ratio=0.5 + 0.1 * (i % 40), event=i % 9 == 0) for i in range(1, 401)]
    p = write_book(tmp_path, rows)
    rc = main(["suggest", str(question_file), "--data", str(p), "--asof", ASOF.isoformat(),
               "--field", "field_a"])
    status = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert status["suggestions"], status


def test_suggest_refuses_a_text_column_rather_than_crashing(question_file, tmp_path):
    """PRD 6.6 offers band cut points for a numeric field. Asking for them on a
    text column is a mistake a reviewer will make, and the tool's whole habit
    is to refuse with the line to fix rather than to fall over: PRD 6.16 allows
    exit 0, 1 or 2 and nothing else.

    `pack suggest --field category_1` raises TypeError ("can't multiply
    sequence by non-int of type 'float'") from inside the percentile helper,
    out through the command, as a traceback.
    """
    rows = [loan(i, ratio=0.5 + 0.1 * (i % 40), event=i % 9 == 0) for i in range(1, 201)]
    p = write_book(tmp_path, rows)
    assert main(["suggest", str(question_file), "--data", str(p), "--asof", ASOF.isoformat(),
                 "--field", "category_1"]) == 2


# --------------------------------------------------------------------------
# 6. The live knobs and the empty block
# --------------------------------------------------------------------------

def test_moving_the_interval_method_knob_never_shows_a_false_check_count(question_file, tmp_path):
    """PRD 5.18 (user story 18): "As the reader, I want to change the
    confidence level or switch Wilson to Clopper-Pearson on one tab and watch
    every interval and the step-4 word recompute." PRD 5.21: the cover shows
    `N of N formula checks agree`, for "a reader with no Python".

    As found: doing the first broke the second. The `_check` tab's Python
    column is frozen at the settings the pack was BUILT with, so a reader who
    switched the method watched the cover change to "529 of 620 formula checks
    agree" and concluded the pack was broken. Nothing warned them.

    The finding asked for the check to stay green. It cannot: the Python
    column is a snapshot at the built settings and there is no Python at the
    desk to recompute it. What the firm would want instead is never to read a
    false count, so the restated expectation is: with a knob moved, the cover
    says the knobs moved and shows no count at all; with the knobs at the
    built settings, it reads N of N.
    """
    rows = [loan(i, ratio=0.4 + 0.2 * (i % 30), event=i % 11 == 0) for i in range(1, 401)]
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(question_file, p)
    wb = load_workbook(io.BytesIO(blob))
    ref = wb.defined_names["METHOD"].attr_text
    sheet, cell = ref.split("!")[0], ref.split("!")[1].replace("$", "")

    rec = recalculated(blob, inputs={(sheet, cell): "Clopper-Pearson"})
    assert rec.find_text("Cover", "formula checks agree") == []
    moved = rec.find_text("Cover", "live knobs have been moved")
    assert len(moved) == 1 and "Wilson" in moved[0] and "95%" in moved[0], moved

    at_built = recalculated(blob)
    line = at_built.find_text("Cover", "formula checks agree")
    assert len(line) == 1 and line[0].startswith(f"{len(checks)} of {len(checks)} "), line


def test_a_confounder_with_no_seasoned_levels_writes_no_backwards_range(question_file, tmp_path):
    """PRD 5.26: "The test suite recalculates every fixture with the `formulas`
    engine and fails on any MISMATCH." PRD 7 names that engine as the seam-1
    instrument.

    When a categorical confounder has no seasoned levels -- here because no
    loan is old enough yet -- step 4 still writes its block, and writes the
    crude-odds-ratio formulas over a range that runs backwards: `SUM(C106:C105)`
    across a band list with nothing in it. The engine the project verifies with
    returns `#NULL!` for nine cells, including the cover's own "Survives or
    collapses" answer line, and the cover reads "533 of 542 formula checks
    agree".

    Stated plainly, because the instrument matters here: LibreOffice 24.2
    renders the same workbook with no error cells (it normalises the backwards
    range), and `tools/render.py` would not catch it either -- its error list
    has no `#NULL!` in it. So this is not a number a reader sees wrong. It is a
    workbook that the project's own stated verification cannot recalculate, and
    a cell range written backwards that no builder should emit.
    """
    young = add_months(ASOF, -3)
    rows = [loan(i, ratio=3.0 if i % 2 else 0.3, origination=young) for i in range(1, 21)]
    p = write_book(tmp_path, rows)
    cfg, pop, table, blob, data, checks = build(question_file, p)
    empty = [st for st in data.strata if not st.bands]
    assert empty, "expected a confounder block with no bands"

    rec = recalculated(blob)
    bad = [(r, v) for r, v in check_verdicts(rec) if v != "OK"]
    detail = [(rec.value("_check", "A%d" % r), rec.value("_check", "B%d" % r)) for r, _ in bad]
    assert not bad, (rec.find_text("Cover", "formula checks agree"), detail)
