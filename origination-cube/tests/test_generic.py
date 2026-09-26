"""The engine knows no column, no value and no number by name.

The firm, 25 Sep 2026: "it's confusing to me that you talk in terms of specific
datapoints because it worries me we are not working with a generic engine".
Every walkthrough has used one synthetic book (FICO, CHANNEL, ASSET_CLASS,
REV_DEBT, a planted FICO-under-620 / Broker pocket), so every number quoted
back came from it. This file runs the whole route on a different book: other
column names, another product, other sizes, a problem planted somewhere else,
and checks the workbook finds that problem and says nothing about the other
book.
"""

import csv
import math
import random
import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest
from openpyxl import load_workbook

from recalc import calculated_book, recalc

from origination_cube import book, confirm_tab, confirmatory, control, kgroups, meanings, synth
from test_book import PICK
from test_book_results import _set
from test_book_dates import _check, _columns, _control

# an auto book, not a card book: none of these names are in the synthetic extract
COLUMNS = ["AcctId", "BureauScore", "Dealer", "FinancedAmt", "ChargedOff", "NetLossDollars",
           "NetRevenueDollars", "Region", "PTI"]
DEALERS = ["North Motors", "Lakeside Auto", "Fleet Direct", "Metro Cars"]
REGIONS = ["Coast", "Valley", "Hills"]


#: The dated auto book (Goal 2 item 1): when each contract was signed, written the way a US dealer system writes it
#: (3/7/2023), and the business's income and sales, whose ratio carries cliffs of this book's own. Everything
#: differs from the first book's plant on purpose (canon S32, S18): the names, the edges, the size of each cliff,
#: the dates and their format, and how the cliff is planted. synth.add_ratio draws the ratio GIVEN the outcome;
#: this book draws the outcome given the ratio, multiplying each loan's odds of charging off.
DATED = ["ContractDate", "BizIncome", "BizSales"]
AUTO_BINS = [0.05, 0.2, 0.6, 1.5]
AUTO_REF = "0.20 - 0.59"
#: below 0.05, three times the odds of charging off; 1.50 and up, two and a half times; nothing between
CLIFFS = {0: 3.0, 4: 2.5}
FIRST_DAY, DAYS = date(2021, 7, 1), 1095               # contracts signed 1 Jul 2021 to 29 Jun 2024


def _group(ratio: float) -> int:
    k = 0
    while k < len(AUTO_BINS) and ratio >= AUTO_BINS[k]:
        k += 1
    return k


def _auto_book(d: Path, n: int = 7000, seed: int = 11, cliffs: dict | None = None) -> Path:
    """The planted problem: Fleet Direct in the Hills defaults about four times as
    often as the rest, at every score. The revenue column is profit after losses,
    as RANR is (OC-29, OC-35): what the loan paid, less the whole loss. It runs
    lower at low scores and is negative for most loans that charged off, so a
    comparison below zero is exercised too.

    `cliffs` (a dict of group -> odds multiple, possibly empty) adds the dated
    columns. The ratio, the date and the sales draw from their own stream, and
    each loan's charge-off still reads the same draw from the main one, so the
    book without cliffs ({}) is the book with them loan for loan, except the
    loans a cliff turned bad, and the undated book is the one every other test
    here has always used.

    The trap for a test that forgets its pockets: Fleet Direct's borrowers run
    a much lower income to sales than the other dealers', so the lowest group is
    full of the worst dealer's loans. Across the whole book, the lowest group
    goes bad more often even with no cliff planted. Inside a Dealer pocket the
    ratio has nothing to do with charging off, unless a cliff says so."""
    rnd = random.Random(seed)
    alt, alt_loss = random.Random(f"auto-dated-{seed}"), random.Random(f"auto-loss-{seed}")
    rows = []
    for i in range(n):
        score = int(min(820, max(540, rnd.gauss(690, 55))))
        dealer, region = rnd.choice(DEALERS), rnd.choice(REGIONS)
        amt = round(rnd.uniform(8_000, 45_000), 2)
        p = 0.02 + max(0, 700 - score) / 900
        if dealer == "Fleet Direct" and region == "Hills":
            p *= 4
        p = min(p, 0.9)
        extra = {}
        if cliffs is not None:
            ratio = math.exp(alt.gauss(-2.4 if dealer == "Fleet Direct" else -1.05, 1.3))
            sales = round(math.exp(alt.gauss(math.log(400_000), 0.6)))
            signed = FIRST_DAY + timedelta(days=alt.randrange(DAYS))
            odds = p / (1 - p) * cliffs.get(_group(ratio), 1.0)
            p = odds / (1 + odds)
            extra = {"ContractDate": f"{signed.month}/{signed.day}/{signed.year}", "BizIncome": round(ratio * sales),
                     "BizSales": sales}
        bad = rnd.random() < p
        # the undated book draws a loss only for a bad loan, from the main stream; a dated book draws one for every
        # loan from its own, so a cliff turning a loan bad moves no later loan's draws
        frac = alt_loss.uniform(0.3, 0.7) if cliffs is not None else rnd.uniform(0.3, 0.7) if bad else 0.0
        loss = round(amt * frac, 2) if bad else 0.0
        paid = amt * (0.04 + (score - 640) / 4000)          # contribution before losses
        rev = round(paid - loss, 2)                          # the whole loss comes out; it took out half until 26 Sep 2026
        rows.append({"AcctId": f"A{i:06d}", "BureauScore": score, "Dealer": dealer, "FinancedAmt": amt,
                     "ChargedOff": "Y" if bad else "N", "NetLossDollars": loss, "NetRevenueDollars": rev,
                     "Region": region, "PTI": round(rnd.uniform(0.04, 0.2), 3), **extra})
    d.mkdir(parents=True, exist_ok=True)
    out = d / "auto book.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS + (DATED if cliffs is not None else []))
        w.writeheader()
        w.writerows(rows)
    return out


def _answer_as_a_person_would(b: Path) -> None:
    """Control from the same picks as every other test; Columns by meaning, as a
    person reads them, for the columns whose name gives nothing away."""
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        k = r[control.KEY_COL - 1].value
        if k in PICK:
            r[control.CHOOSE_COL - 1].value = PICK[k]
    for r in wb["Odd values"].iter_rows(min_row=5):
        if r[1].value and not r[4].value:
            r[4].value = "real"                     # revenue below zero is real here
    wb.save(b)
    cat = meanings.catalog()
    for col, code in {"AcctId": "key", "BureauScore": "fico", "Dealer": "category", "FinancedAmt": "booked",
                      "ChargedOff": "outcome", "NetLossDollars": "gco", "NetRevenueDollars": "ranr",
                      "Region": "category", "PTI": "dti"}.items():
        _set(b, col, book.C_MEANS, cat[code].label)
    _set(b, "ChargedOff", book.C_IS, "Y")
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)


def test_another_book_with_other_names_finds_its_own_problem(tmp_path):
    extract = _auto_book(tmp_path)
    out = book.set_up(extract)
    assert out.ok, out.lines
    _answer_as_a_person_would(out.book)
    ran = book.run(out.book)
    assert ran.ok, ran.lines
    wb = calculated_book(out.book)            # the flags are formulas over Control's lines (OC-40)

    # the grids are this book's columns
    grids = [c.value for c in wb["Grids"]["B"] if isinstance(c.value, str) and " x " in c.value]
    assert grids and all(re.match(r"(BureauScore|FinancedAmt|PTI) x (Dealer|Region)", g) for g in grids), grids

    # the planted pocket is found: Fleet Direct is the worst Dealer pocket for the outcome, in every
    # BureauScore band that was tested
    ws = wb["Where it bleeds"]
    rows = [[ws.cell(row=r, column=c).value for c in range(2, 20)] for r in range(5, ws.max_row + 1)]
    flagged = [x for x in rows if x[0] == "Outcome, share of loans" and x[3] == "Dealer" and x[16] == "worse"]
    assert flagged and {x[4] for x in flagged} == {"Fleet Direct"}, [(x[2], x[4], x[16]) for x in flagged]
    assert any(x[3] == "Region" and x[4] == "Hills" and x[16] == "worse" for x in rows)

    # nothing from the other book leaks in: no column, value, or pocket of the synthetic extract
    text = " ".join(str(c.value) for t in wb.sheetnames for row in wb[t].iter_rows() for c in row
                    if isinstance(c.value, str))
    # "FICO score" and "the FICO scale" stay: they're a meaning, chosen here for BureauScore, not a column.
    # Control's explanations used to carry the other book's pocket as their example ("Broker under 620
    # against the rest of under 620"); found by this test
    words = set(re.findall(r"[A-Za-z_]+", text.replace("FICO score", "").replace("FICO scale", "")))
    for name in synth.COLUMNS + synth.CHANNELS:
        assert name not in words, name
    assert "496 - 619" not in text and "under 620" not in text


# --------------------------------------------------------------------------
# Goal 2, item 1: the cliffs planted in this book too, found and confirmed by a "Test from a pre-spec" run.
# The first book's goal test (test_confirm_test.py) can only show the code agreeing with its own fixture; this
# book was planted differently and read by the same route, and a copy with no cliff must NOT be confirmed.

AUTO_SPEC = f"""\
# The auto book's pre-spec, written for this test the way the example in docs/ is written.
prespec: 1
written: 2026-09-26
column: IncomeToSales
bins: {AUTO_BINS}
reference: "{AUTO_REF}"
strata: [BureauScore, Dealer]
confidence: 0.95
holdout: {{from: 2023-07-01, to: 2024-06-29}}
development: {{from: 2021-07-01, to: 2023-06-30}}
"""


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false",
                    *args], cwd=repo, check=True, capture_output=True)


def _dated_route(folder: Path, cliffs: dict, n: int = 12000):
    """The auto book, dated, through Set up and Run as a person would take it: Columns answered by meaning,
    the contract date marked Origination date, income ÷ sales made on Control, and "Test from a pre-spec" naming
    a pre-spec committed beside the workbook. Returns the extract, the workbook, the Run and the test itself."""
    extract = _auto_book(folder, n=n, cliffs=cliffs)
    b = book.set_up(extract).book
    _answer_as_a_person_would(b)
    cat = meanings.catalog()
    _set(b, "ContractDate", book.C_MEANS, cat["origination_date"].label)
    for c in ("BizIncome", "BizSales"):
        _set(b, c, book.C_MEANS, cat["amount"].label)
    _control(b, run_kind="Finding and testing a new variable", new_variable_step="Test from a pre-spec",
             **{"derived|1": ("IncomeToSales", "BizIncome", "BizSales")})
    book.set_up(extract)
    for c in ("FinancedAmt", "PTI", "BizIncome", "BizSales", "IncomeToSales"):
        _columns(b, c, C_CUT="No")
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    ws = wb[control.SHEET]
    ws.cell(row=control.row_of(ws, control.PRESPEC_KEY), column=control.CHOOSE_COL).value = "auto prespec.yaml"
    wb.save(b)
    (folder / "auto prespec.yaml").write_text(AUTO_SPEC, encoding="utf-8")
    _git(folder, "init", "-q")
    _git(folder, "add", "auto prespec.yaml")
    _git(folder, "commit", "-q", "-m", "pre-spec")
    seen = {}
    real = confirmatory.state

    def spy(*a, **k):
        seen["st"] = real(*a, **k)
        return seen["st"]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(confirmatory, "state", spy)
        ran = book.run(b)
    assert ran.ok, ran.lines
    return {"x": extract, "b": b, "ran": ran, "t": seen["st"].test}


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed on this machine")


@pytest.fixture(scope="module")
def auto_routes(tmp_path_factory):
    out = {}
    for name, cliffs in (("planted", CLIFFS), ("clean", {})):
        folder = tmp_path_factory.mktemp(f"auto-{name}")
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GIT_CEILING_DIRECTORIES", str(folder))
            mp.setenv("CUBE_MEMORY", str(folder / "memory.yaml"))
            out[name] = _dated_route(folder, cliffs)
    return out


def _auto_by_hand(x, lo: date, hi: date):
    """Contracts signed lo to hi (both ends in), as (group, bad), read from the csv with no help from the cube."""
    out = []
    with open(x, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m, d, y = (int(v) for v in r["ContractDate"].split("/"))
            if lo <= date(y, m, d) <= hi and r["BizSales"] not in ("", "0"):
                out.append((_group(float(r["BizIncome"]) / float(r["BizSales"])), int(r["ChargedOff"] == "Y")))
    return out


@needs_git
def test_the_second_books_cliffs_are_found_on_development_and_confirmed_on_the_holdout(auto_routes):
    """The goal's sentence, on a book the cube's own fixture had no hand in: other names, other edges, a US date
    format, another reference group, and the cliffs planted on the outcome rather than the ratio."""
    t = auto_routes["planted"]["t"]
    assert t.problem is None and t.method == kgroups.CONDITIONAL
    assert t.column == "IncomeToSales" and t.groups[t.ref] == AUTO_REF and t.strata == ("BureauScore", "Dealer")
    for side in (t.development, t.holdout):
        a, f = side.association, side.fit
        assert a.p_general < 0.05 and f.p_block < 0.05 and f.settled, side.name
        for k, planted in CLIFFS.items():
            lo, hi = f.interval(k, 1.96)
            assert f.odds[k] > 1 and f.p[k] < 0.05 and lo < planted < hi, (side.name, k, f.odds[k], lo, hi)
    # on the holdout, where the finding counts, no group between the cliffs reads significant
    assert all(t.holdout.fit.p[k] > 0.05 for k in (1, 3))


@needs_git
def test_the_second_books_ranges_hold_the_loans_counted_by_hand(auto_routes):
    """Development and holdout, read from US-style dates in the csv by hand: every contract in its range, none in
    both, and the group counts the test used."""
    r = auto_routes["planted"]
    t = r["t"]
    for side, lo, hi in ((t.development, date(2021, 7, 1), date(2023, 6, 30)),
                         (t.holdout, date(2023, 7, 1), date(2024, 6, 29))):
        mine = _auto_by_hand(r["x"], lo, hi)
        assert side.n == len(mine) > 0
        assert side.loans == [sum(1 for g, _ in mine if g == k) for k in range(len(AUTO_BINS) + 1)]
        assert side.bad == [sum(y for g, y in mine if g == k) for k in range(len(AUTO_BINS) + 1)]
    assert t.development.n + t.holdout.n == 12000 and not t.left_out
    chk = _check(r["b"])
    assert chk["Differs from the pre-spec"] == "nowhere: this run used what it says"


@needs_git
def test_the_second_book_with_no_cliff_is_not_confirmed(auto_routes):
    """The guard, on the clean case: the same loans with no cliff planted. The trap is still there (the worst
    dealer's loans crowd the lowest group, so across the whole book that group does go bad more often), and
    with the pockets held fixed nothing is found on either range."""
    r = auto_routes["clean"]
    t = r["t"]
    assert t.problem is None
    # the trap is real: counted by hand, with no pockets, the lowest group goes bad well above the reference
    mine = _auto_by_hand(r["x"], date(2023, 7, 1), date(2024, 6, 29))
    rate = [sum(y for g, y in mine if g == k) / sum(1 for g, _ in mine if g == k) for k in (0, 2)]
    assert rate[0] > 1.4 * rate[1], rate
    for side in (t.development, t.holdout):
        a, f = side.association, side.fit
        assert a.p_general >= 0.05 and f.p_block >= 0.05, (side.name, a.p_general, f.p_block)
        assert all(f.p[k] >= 0.05 for k in range(len(AUTO_BINS) + 1) if k != t.ref), (side.name, f.p)


@needs_git
def test_the_second_books_tab_confirms_the_planted_cliffs_and_not_the_clean_book(auto_routes, tmp_path):
    """What the analyst reads, calculated: the planted book's holdout line names both cliffs; the clean book's
    says no group differs."""
    said = {}
    for name in ("planted", "clean"):
        ws = recalc(auto_routes[name]["b"], tmp_path / name)[confirm_tab.SHEET]
        texts = [str(c.value) for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
        assert not [s for s in texts if s.startswith("#") or "Err:" in s]
        said[name] = next(s for s in texts if s.startswith("On the holdout,") and "pockets held fixed" in s)
    t = auto_routes["planted"]["t"]
    for k in CLIFFS:
        assert f"{t.groups[k]} goes bad " in said["planted"], said["planted"]
    assert said["clean"] == (f"On the holdout, no group differs from {AUTO_REF} at 95% sure, with the pockets held "
                             f"fixed."), said["clean"]
