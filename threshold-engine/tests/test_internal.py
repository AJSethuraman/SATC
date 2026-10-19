"""internal: the import KeyBank's own figures come in through. Every figure
here is made up for the tests: no bank's books, and the Call Report cache is
a few invented rows in the shape fdic.pull writes. Each refusal is pinned by
the line it names; the rates are checked against hand-worked examples; the
reconciliation runs on a tiny synthetic cache."""
import json
from decimal import Decimal

import pytest

from conftest import ROOT
from threshold_engine import internal as I
from threshold_engine.cli import main
from threshold_engine.series import CORE_NOTES, read_csv, read_notes

KEY = "17534"
BANK = {"cert": KEY, "name": "Synthetic Bank, N.A. (made up)"}
COLS = ("quarter,product,segment,balance,gross_charge_offs,net_charge_offs,recoveries,"
        "dpd_30_plus,dpd_60_plus,dpd_90_plus")
NOTES = ["# entity: Synthetic Bancorp (made up for the tests)",
         "# as-of: balances at quarter-end; charge-offs for the quarter",
         "# basis: synthetic portfolio loans, $ thousands",
         "# source: invented in tests/test_internal.py"]
SEGS = {"All": "the synthetic product total",
        "Home equity lines": "synthetic revolving home equity lines",
        "Home equity loans": "synthetic closed-end home equity loans"}


def labels(first_year, first_q, n):
    out, y, q = [], first_year, first_q
    for _ in range(n):
        out.append("%dQ%d" % (y, q))
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def row(q, p="Credit card", s="All", bal="1000", g="12", net="10", rec="2", d30="40", d60="20", d90="10"):
    return ",".join([q, p, s, bal, g, net, rec, d30, d60, d90])


def card_rows(n=8):
    return [row(q) for q in labels(2024, 1, n)]


def write(tmp_path, rows, notes=None, segs=None, cols=COLS, name="internal.csv"):
    """The file: notes, a segment note for each used segment (or ``segs``),
    the header, the rows. Line numbers: notes, then segments, then header."""
    path = tmp_path / name
    used = []
    for r in rows:
        parts = r.split(",")
        if len(parts) > 2 and parts[2] and parts[2] not in used:
            used.append(parts[2])
    seg_lines = (["# segment-%s: %s" % (s, SEGS.get(s, "synthetic")) for s in used]
                 if segs is None else segs)
    lines = (NOTES if notes is None else notes) + seg_lines + [cols] + list(rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def first_row_line(notes=4, segs=1):
    """The line number of the first data row in ``write``'s layout."""
    return notes + segs + 2


# ---------------------------------------------------------------- a good file

def test_a_good_file_passes(tmp_path):
    rows = card_rows() + [row(q, "Home equity", "Home equity lines", "300", "1", "1", "0", "6", "3", "1")
                          for q in labels(2024, 1, 8)]
    path = write(tmp_path, rows)
    assert I.check(path) == []
    got = I.read(path)
    assert got.keys() == [("Credit card", "All"), ("Home equity", "Home equity lines")]
    assert got.notes["entity"] == "Synthetic Bancorp (made up for the tests)"
    assert got.segments["Home equity lines"] == "synthetic revolving home equity lines"
    assert len(got.rows_for("Credit card", "All")) == 8


def test_rows_may_come_in_any_order(tmp_path):
    path = write(tmp_path, list(reversed(card_rows())))
    assert I.check(path) == []
    assert [r.quarter for r in I.read(path).rows] == labels(2024, 1, 8)


def test_read_refuses_with_every_problem(tmp_path):
    path = write(tmp_path, [row("2024Q1", bal="x"), row("2024Q2", p="Cards")])
    with pytest.raises(I.Refused) as exc:
        I.read(path)
    assert len(exc.value.problems) == 2


# ---------------------------------------------------------------- charge-offs: two of three

@pytest.mark.parametrize("given,blank,expect", [
    (("gross", "net"), "rec", ("12", "10", "2")),
    (("net", "rec"), "gross", ("12", "10", "2")),
    (("gross", "rec"), "net", ("12", "10", "2")),
])
def test_the_third_charge_off_figure_is_worked_out(tmp_path, given, blank, expect):
    vals = {"gross": "12", "net": "10", "rec": "2"}
    vals[blank] = ""
    path = write(tmp_path, [row(q, g=vals["gross"], net=vals["net"], rec=vals["rec"])
                            for q in labels(2024, 1, 4)])
    assert I.check(path) == []
    r = I.read(path).rows[0]
    assert (r.gross_charge_offs, r.net_charge_offs, r.recoveries) == tuple(Decimal(x) for x in expect)
    assert r.worked_out == {"gross": "gross_charge_offs", "net": "net_charge_offs", "rec": "recoveries"}[blank]


def test_a_file_with_only_two_charge_off_columns_passes(tmp_path):
    cols = "quarter,product,segment,balance,gross_charge_offs,recoveries,dpd_30_plus,dpd_60_plus,dpd_90_plus"
    path = write(tmp_path, ["2024Q1,Credit card,All,1000,12,2,40,20,10"], cols=cols)
    assert I.check(path) == []
    assert I.read(path).rows[0].net_charge_offs == Decimal("10")


def test_three_that_agree_exactly_as_written_pass(tmp_path):
    # 1.1 - 0.2 is not 0.9 in floating point; as written, it is.
    path = write(tmp_path, [row("2024Q1", g="1.1", net="0.9", rec="0.2")])
    assert I.check(path) == []


def test_net_charge_offs_may_be_negative(tmp_path):
    path = write(tmp_path, [row("2024Q1", g="1", net="-2", rec="3")])
    assert I.check(path) == []


# ---------------------------------------------------------------- refusals, each naming its line

L = first_row_line()


@pytest.mark.parametrize("bad,expect", [
    (row("2024-03-31"), "line %d: quarter '2024-03-31' is not written YYYYQn" % L),
    (row("2024Q1", p="Cards"), "line %d: product 'Cards' is not one of Credit card, Mortgage" % L),
    (row("2024Q1", bal=""), "line %d: balance is blank; every row needs it" % L),
    (row("2024Q1", bal='"1,000"'), "line %d: balance '1,000' is not a number" % L),
    (row("2024Q1", bal="nan"), "line %d: balance 'nan' is not a finite number" % L),
    (row("2024Q1", bal="-5"), "line %d: balance is -5, below 0" % L),
    (row("2024Q1", g="-1", net="", rec="2"), "line %d: gross_charge_offs is -1, below 0" % L),
    (row("2024Q1", d30=""), "line %d: dpd_30_plus is blank" % L),
    (row("2024Q1", g="", rec=""), "line %d: gives net_charge_offs; give at least two of" % L),
    (row("2024Q1", g="", net="", rec=""), "line %d: gives no charge-offs" % L),
    (row("2024Q1", g="12", net="9", rec="2"),
     "line %d: gross_charge_offs 12 less recoveries 2 is 10, but net_charge_offs is 9" % L),
    (row("2024Q1", g="5", net="10", rec=""),
     "line %d: recoveries worked out from the other two is -5, below 0" % L),
    (row("2024Q1", d30="20", d60="30", d90="10"),
     "line %d: dpd_60_plus 30 is more than dpd_30_plus 20; past due is cumulative" % L),
    (row("2024Q1", d30="40", d60="20", d90="25"),
     "line %d: dpd_90_plus 25 is more than dpd_60_plus 20" % L),
    (row("2024Q1", bal="30", d30="40", d60="20", d90="10"),
     "line %d: dpd_30_plus 40 is more than the balance 30" % L),
    (row("2024Q1") + ",7", "line %d: 11 fields, but the header names 10 columns" % L),
])
def test_each_row_refusal_names_its_line(tmp_path, bad, expect):
    problems = I.check(write(tmp_path, [bad]))
    assert any(p.startswith(expect) for p in problems), problems


def test_a_blank_segment_is_refused(tmp_path):
    problems = I.check(write(tmp_path, [row("2024Q1", s="")], segs=[]))
    assert problems == ["line %d: segment is blank; write All for the product total" % (L - 1)]


def test_a_repeat_is_refused_naming_both_lines(tmp_path):
    problems = I.check(write(tmp_path, [row("2024Q1"), row("2024Q2"), row("2024Q1")]))
    assert problems == ["line %d: 2024Q1, Credit card, All is repeated (first on line %d)" % (L + 2, L)]


def test_a_gap_is_refused_not_filled_in(tmp_path):
    problems = I.check(write(tmp_path, [row("2024Q1"), row("2024Q2"), row("2024Q4")]))
    assert problems == ["line %d: Credit card / All: 2024Q4 follows 2024Q2; the quarters between are "
                        "missing, and a gap is refused, not filled in" % (L + 2)]


def test_quarters_run_per_product_and_segment(tmp_path):
    # Card 2024Q1-Q2 and auto 2024Q4 is no gap: each series is consecutive.
    path = write(tmp_path, [row("2024Q1"), row("2024Q2"), row("2024Q4", p="Auto")])
    assert I.check(path) == []


@pytest.mark.parametrize("notes,expect", [
    (NOTES[1:], "note 'entity' is not stated: add '# entity: whose books these are"),
    (["# entity: [STATE: whose books]"] + NOTES[1:], "line 1: note 'entity' still holds its placeholder"),
    (["# entity:"] + NOTES[1:], "line 1: note 'entity' is empty"),
    (NOTES + ["# prepared-by: someone"], "line 5: note 'prepared-by' is not one this file takes"),
    (NOTES + ["# 123 Main St, account 99"], "line 5: a '#' line must be a note"),
    (NOTES + [NOTES[0]], "line 5: note 'entity' is given twice (first on line 1)"),
])
def test_each_note_refusal(tmp_path, notes, expect):
    problems = I.check(write(tmp_path, card_rows(1), notes=notes))
    assert any(p.startswith(expect) for p in problems), problems


def test_a_segment_with_no_note_is_not_stated(tmp_path):
    problems = I.check(write(tmp_path, card_rows(1), segs=[]))
    assert problems == ["segment 'All' (first on line 6) is not stated: add '# segment-All: what this "
                        "segment holds, in the bank's words'"]


def test_a_segment_note_with_no_rows_is_refused(tmp_path):
    segs = ["# segment-All: total", "# segment-Direct autos: misspelt"]
    problems = I.check(write(tmp_path, card_rows(1), segs=segs))
    assert problems == ["line 6: segment 'Direct autos' is described but no row holds it; remove the "
                        "note, or check the name matches the rows exactly"]


def test_a_segment_note_still_a_placeholder_is_refused(tmp_path):
    problems = I.check(write(tmp_path, card_rows(1), segs=["# segment-All: [STATE: what]"]))
    assert problems[0].startswith("line 5: note 'segment-All' still holds its placeholder")


@pytest.mark.parametrize("cols,expect", [
    (COLS.replace(",balance", ""), "line 6: the header has no balance column"),
    (COLS.replace(",net_charge_offs,recoveries", ""),
     "line 6: the header gives gross_charge_offs; give at least two of"),
    (COLS + ",account_number", "line 6: column 'account_number' is refused: its name reads as"),
    (COLS + ",Borrower Name", "line 6: column 'Borrower Name' is refused"),
    (COLS + ",", "line 6: a column has no name (a trailing comma?)"),
    (COLS + ",balance", "line 6: column 'balance' appears twice"),
])
def test_each_header_refusal(tmp_path, cols, expect):
    rows = [row("2024Q1") + ("," if cols.count(",") > COLS.count(",") else "")]
    problems = I.check(write(tmp_path, rows, cols=cols))
    assert any(p.startswith(expect) for p in problems), problems


def test_a_further_column_holds_numbers_and_is_carried_through(tmp_path):
    path = write(tmp_path, [row("2024Q1") + ",55", row("2024Q2") + ","], cols=COLS + ",first_lien_share")
    assert I.check(path) == []
    got = I.read(path)
    assert got.extra_columns == ("first_lien_share",)
    assert got.rows[0].extra == (("first_lien_share", Decimal("55")),)
    assert got.rows[1].extra == (("first_lien_share", None),)


def test_text_in_a_further_column_is_refused(tmp_path):
    problems = I.check(write(tmp_path, [row("2024Q1") + ",Jane Doe"], cols=COLS + ",detail"))
    assert problems[0].startswith("line 7: further column detail: 'Jane Doe' is not a number")


def test_a_byte_order_mark_is_refused(tmp_path):
    path = write(tmp_path, card_rows(1))
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert I.check(path)[0].startswith("the file starts with a byte-order mark")


def test_not_utf8_is_refused(tmp_path):
    path = tmp_path / "x.csv"
    path.write_bytes(b"\xff\xfe" + COLS.encode())
    assert I.check(path) == ["the file is not UTF-8 text"]


def test_no_rows_is_refused(tmp_path):
    assert "no rows: the file has a header and nothing under it" in I.check(write(tmp_path, []))


def test_a_vertical_tab_does_not_split_a_line(tmp_path):
    # templates.py's line rule: only CR, LF and CRLF end a line.
    path = write(tmp_path, card_rows(1))
    text = path.read_text(encoding="utf-8").replace("# entity: Synthetic", "# entity: Synthetic\x0b")
    path.write_text(text, encoding="utf-8")
    assert I.check(path) == []


# ---------------------------------------------------------------- template

def test_the_template_is_written_and_refused_until_filled(tmp_path):
    out, ex = I.write_template(tmp_path / "keybank.csv")
    assert ex.name == "keybank.exclusions.csv"
    text = out.read_text(encoding="utf-8").splitlines()
    assert text[-1] == COLS
    assert all("[STATE:" in line for line in text[:-1])
    assert "# segment-Home equity lines: [STATE: what this segment holds, in the bank's words]" in text
    problems = I.check(out)
    assert sum("still holds its placeholder" in p for p in problems) == 4
    assert "no rows: the file has a header and nothing under it" in problems
    assert I.check_exclusions(ex)[0].startswith("line 1: note 'source' still holds its placeholder")
    with pytest.raises(ValueError, match="already exists"):
        I.write_template(tmp_path / "keybank.csv")
    with pytest.raises(ValueError, match="name it OUT.csv"):
        I.write_template(tmp_path / "keybank.txt")


# ---------------------------------------------------------------- series

def ttm_file(tmp_path):
    bal = ["1000", "1100", "1200", "1300", "1400"]
    net = ["2", "3", "4", "5", "6"]
    rows = [row(q, bal=b, g=str(int(n) + 1), net=n, rec="", d30=str(int(b) // 25), d60="0", d90="0")
            for q, b, n in zip(labels(2024, 1, 5), bal, net)]
    return I.read(write(tmp_path, rows))


def test_the_ttm_rate_equals_a_hand_worked_example(tmp_path):
    got = I.series(ttm_file(tmp_path), "Credit card", "All", "net-charge-off-rate")
    # 2024Q4: (2+3+4+5) / mean(1000, 1100, 1200, 1300) = 14 / 1150 = 1.2173913...%
    assert got[3] == ("2024Q4", pytest.approx(100 * 14 / 1150))
    # 2025Q1: (3+4+5+6) / mean(1100..1400) = 18 / 1250
    assert got[4] == ("2025Q1", pytest.approx(100 * 18 / 1250))
    gross = I.series(ttm_file(tmp_path), "Credit card", "All", "gross-charge-off-rate")
    assert gross[3][1] == pytest.approx(100 * (3 + 4 + 5 + 6) / 1150)


def test_a_window_short_of_four_quarters_has_no_value(tmp_path):
    got = I.series(ttm_file(tmp_path), "Credit card", "All", "net-charge-off-rate")
    assert [v for _, v in got[:3]] == [None, None, None]


def test_delinquency_rates_on_both_bases(tmp_path):
    rows = [row(q, bal="1000", d30=str(d), d60=str(d // 2), d90="0")
            for q, d in zip(labels(2024, 1, 5), (10, 20, 30, 40, 50))]
    internal = I.read(write(tmp_path, rows))
    qe = I.series(internal, "Credit card", "All", "dpd-30-plus-quarter-end")
    assert [v for _, v in qe] == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0])
    avg = I.series(internal, "Credit card", "All", "dpd-30-plus-four-quarter-average")
    assert [v for _, v in avg[:3]] == [None] * 3
    assert avg[3][1] == pytest.approx(2.5) and avg[4][1] == pytest.approx(3.5)
    sixty = I.series(internal, "Credit card", "All", "dpd-60-plus-quarter-end")
    assert sixty[0][1] == pytest.approx(0.5)


def test_series_refuses_an_unknown_measure_or_segment(tmp_path):
    internal = ttm_file(tmp_path)
    with pytest.raises(ValueError, match="measure must be one of"):
        I.series(internal, "Credit card", "All", "net")
    with pytest.raises(ValueError, match="no rows for Mortgage / All"):
        I.series(internal, "Mortgage", "All", "net-charge-off-rate")


def test_written_series_carry_the_file_s_own_notes(tmp_path):
    internal = ttm_file(tmp_path)
    made = I.write_all_series(internal, tmp_path / "out")
    assert len(made) == len(I.MEASURES) and all(m["written"] for m in made)
    path = tmp_path / "out" / "internal_credit-card_all_net-charge-off-rate.csv"
    pts = read_csv(path)
    assert [p.date for p in pts] == ["2024-12-31", "2025-03-31"]
    notes = dict(read_notes(path))
    assert set(CORE_NOTES) <= set(notes)
    assert notes["as-of"] == "balances at quarter-end; charge-offs for the quarter"
    assert notes["source"] == "invented in tests/test_internal.py"
    assert notes["entity"] == "Synthetic Bancorp (made up for the tests)"
    assert notes["basis"].startswith("trailing four quarters. The file's own basis: synthetic portfolio")
    assert notes["denominator"] == "the mean of the four quarter-end balances"
    text = path.read_text(encoding="utf-8")
    assert "2024Q1, 2024Q2, 2024Q3 (fewer than four consecutive quarters to measure over)" in text


def test_a_written_series_builds_through_the_workbook(tmp_path):
    """A made-up cycle of 24 quarters: the TTM file is an ordinary series."""
    import math
    from threshold_engine.workbook import build
    qs = labels(2015, 1, 24)
    rows = [row(q, bal="1000", g=str(10 + round(8 * math.sin(i / 3.0))), net="", rec="2")
            for i, q in enumerate(qs)]
    I.write_all_series(I.read(write(tmp_path, rows)), tmp_path / "out")
    p = tmp_path / "out" / "internal_credit-card_all_net-charge-off-rate.csv"
    info = build(tmp_path / "w.xlsx", [("Card", p)], "Net charge-off rate", "%", "higher_is_worse",
                 "quarterly", 1, True, 0.5, 1.0, 2.5, "worse", (10,), (50, 75, 90, 95), 4, 12)
    assert info["quarters"] == 21 and (tmp_path / "w.xlsx").exists()


# ---------------------------------------------------------------- reconcile

Q1, Q2 = "20250331", "20250630"

# KeyBank's synthetic filing; charge-offs and recoveries year to date.
FILED = {
    Q1: dict(LNCRCD=1000, DRCRCD=10, CRCRCD=2, LNRERSFM=5000, DRRERSFM=4, CRRERSFM=1,
             LNRELOC=300, DRRELOC=1, CRRELOC=0, LNRERSF2=50, DRRERSF2=0, CRRERSF2=0,
             LNCONRP=20, LNAUTO=80, LNCONOTH=400, DRAUTO=1, DRCONOTH=5, CRAUTO=0, CRCONOTH=1),
    Q2: dict(LNCRCD=1010, DRCRCD=25, CRCRCD=5, LNRERSFM=5000, DRRERSFM=6, CRRERSFM=1,
             LNRELOC=300, DRRELOC=2, CRRELOC=0, LNRERSF2=50, DRRERSF2=0, CRRERSF2=0,
             LNCONRP=20, LNAUTO=80, LNCONOTH=400, DRAUTO=2, DRCONOTH=10, CRAUTO=0, CRCONOTH=2),
}

# (quarter, product, segment, balance, gross, recoveries), quarterly.
INTERNAL = [
    ("2025Q1", "Credit card", "All", 1000, 10, 2), ("2025Q2", "Credit card", "All", 1010, 15, 3),
    ("2025Q1", "Mortgage", "All", 4900, 4, 1), ("2025Q2", "Mortgage", "All", 4800, 2, 0),
    ("2025Q1", "Home equity", "Home equity lines", 300, 1, 0),
    ("2025Q2", "Home equity", "Home equity lines", 300, 1, 0),
    ("2025Q1", "Home equity", "Home equity loans", 50, 0, 0),
    ("2025Q2", "Home equity", "Home equity loans", 50, 0, 0),
    ("2025Q1", "Other consumer", "All", 480, 6, 1), ("2025Q2", "Other consumer", "All", 480, 6, 1),
    ("2025Q1", "Auto", "All", 80, 1, 0), ("2025Q2", "Auto", "All", 80, 1, 0),
]

EXCLUSIONS = [
    "# source: made up for the tests",
    ",".join(I.EXCLUSION_COLUMNS),
    "2025Q1,Mortgage,All,balance,Residential mortgages held for sale,100",
    "2025Q2,Mortgage,All,balance,Residential mortgages held for sale,100",
    "2025Q1,Other consumer,All,balance,Education loans in discontinued operations,20",
    "2025Q2,Other consumer,All,balance,Education loans in discontinued operations,20",
]


def internal_file(tmp_path, data=INTERNAL):
    rows = [",".join([q, p, s, str(b), str(g), "", str(r), "4", "2", "1"]) for q, p, s, b, g, r in data]
    return write(tmp_path, rows)


def cache(tmp_path, drop=(), quarters=(Q1, Q2)):
    d = tmp_path / "cache"
    d.mkdir(exist_ok=True)
    for q in quarters:
        mine = {k: v for k, v in FILED[q].items() if k not in drop}
        other = {k: 7 for k in mine}
        rows = [dict(CERT=int(KEY), REPDTE=q, **mine), dict(CERT=628, REPDTE=q, **other)]
        (d / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    (d / "absorptions.json").write_text('{"since": "2025-01-01", "absorptions": []}', encoding="utf-8")
    return d


def exclusions_file(tmp_path, lines=EXCLUSIONS):
    p = tmp_path / "exclusions.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def run(tmp_path, tolerance=0.01, drop=(), quarters=(Q1, Q2), ex_lines=EXCLUSIONS):
    internal = I.read(internal_file(tmp_path))
    filed = I.read_filed(internal, cache(tmp_path, drop, quarters))
    ex = I.read_exclusions(exclusions_file(tmp_path, ex_lines))
    return {(r["quarter"], r["comparison"], r["measure"]): r
            for r in I.reconcile(internal, filed, ex, tolerance, bank=BANK, absorptions=[])}


def test_reconcile_exclusions_explain_a_gap_and_an_unexplained_one_is_flagged(tmp_path):
    got = run(tmp_path)
    m1 = got[("2025Q1", "Mortgage", "balance")]
    assert (m1["filed"], m1["excluded"], m1["internal"], m1["remainder"]) == (5000, 100, 4900, 0)
    assert m1["within_tolerance"] == "yes"
    assert m1["excluded_names"] == "Residential mortgages held for sale (Mortgage / All)"
    m2 = got[("2025Q2", "Mortgage", "balance")]
    assert m2["remainder"] == 100 and m2["within_tolerance"] == "no"
    assert float(m2["remainder_share"]) == pytest.approx(100 / 4800)
    oc = got[("2025Q1", "Other consumer", "balance")]
    assert (oc["filed"], oc["remainder"], oc["within_tolerance"]) == (500, 0, "yes")


def test_without_the_exclusions_the_gaps_are_unexplained(tmp_path):
    got = run(tmp_path, ex_lines=EXCLUSIONS[:2])
    assert got[("2025Q1", "Mortgage", "balance")]["within_tolerance"] == "no"
    assert got[("2025Q1", "Other consumer", "balance")]["remainder"] == 20


def test_the_tolerance_decides_within(tmp_path):
    assert run(tmp_path, tolerance=0.03)[("2025Q2", "Mortgage", "balance")]["within_tolerance"] == "yes"


def test_charge_offs_are_differenced_from_year_to_date(tmp_path):
    got = run(tmp_path)
    card = got[("2025Q2", "Credit card", "gross_charge_offs")]
    assert (card["filed"], card["internal"], card["within_tolerance"]) == (15, 15, "yes")
    net = got[("2025Q2", "Credit card", "net_charge_offs")]
    assert (net["filed"], net["internal"], net["remainder"]) == (12, 12, 0)
    assert got[("2025Q1", "Credit card", "gross_charge_offs")]["filed"] == 10   # Q1 is its own
    oc = got[("2025Q2", "Other consumer", "gross_charge_offs")]
    assert oc["filed"] == (2 + 10) - (1 + 5) and oc["public_fields"] == "DRAUTO+DRCONOTH"


def test_home_equity_loans_and_mortgage_meet_the_two_lien_lines_together(tmp_path):
    got = run(tmp_path)
    both = got[("2025Q1", "Mortgage and home equity loans", "balance")]
    assert (both["filed"], both["excluded"], both["internal"], both["remainder"]) == (5050, 100, 4950, 0)
    assert got[("2025Q1", "Home equity lines", "balance")]["remainder"] == 0


def test_a_field_the_cache_was_pulled_without_is_not_measured(tmp_path):
    got = run(tmp_path, drop=("LNRERSF2", "DRRERSF2", "CRRERSF2"))
    r = got[("2025Q1", "Mortgage and home equity loans", "balance")]
    assert r["within_tolerance"] == "not measured"
    assert "pulled without LNRERSF2" in r["why"] and "'internal pull'" in r["why"]
    assert got[("2025Q1", "Mortgage", "balance")]["within_tolerance"] == "yes"


def test_a_quarter_before_the_cache_is_not_measured_not_guessed(tmp_path):
    # The file starts in 2025Q2 here; 2025Q1 is not cached, so Q2's year to
    # date cannot be differenced.
    data = [d for d in INTERNAL if d[0] == "2025Q2"]
    internal = I.read(internal_file(tmp_path, data))
    filed = I.read_filed(internal, cache(tmp_path, quarters=(Q2,)))
    ex = I.read_exclusions(exclusions_file(tmp_path, EXCLUSIONS[:2]))
    rows = I.reconcile(internal, filed, ex, 0.01, bank=BANK, absorptions=[])
    card = next(r for r in rows if r["comparison"] == "Credit card" and r["measure"] == "gross_charge_offs")
    assert card["within_tolerance"] == "not measured"
    assert "the quarter before, 2025Q1, is not in the cache" in card["why"]


def test_a_quarter_the_file_holds_must_be_cached(tmp_path):
    internal = I.read(internal_file(tmp_path))
    with pytest.raises(ValueError, match="first missing 2025Q2.*never fetches"):
        I.read_filed(internal, cache(tmp_path, quarters=(Q1,)))


def test_a_missing_internal_half_is_stated(tmp_path):
    data = [d for d in INTERNAL if not (d[2] == "Home equity loans" and d[0] == "2025Q2")]
    internal = I.read(internal_file(tmp_path, data))
    filed = I.read_filed(internal, cache(tmp_path))
    ex = I.read_exclusions(exclusions_file(tmp_path))
    rows = I.reconcile(internal, filed, ex, 0.01, bank=BANK, absorptions=[])
    r = next(r for r in rows if r["quarter"] == "2025Q2" and r["comparison"] ==
             "Mortgage and home equity loans" and r["measure"] == "balance")
    assert r["within_tolerance"] == "not measured"
    assert r["why"] == "the internal file has no row for Home equity / Home equity loans in 2025Q2"


def test_an_internal_figure_of_zero_is_within_only_at_no_remainder(tmp_path):
    data = [d if d[:2] != ("2025Q1", "Auto") else ("2025Q1", "Auto", "All", 80, 0, 0) for d in INTERNAL]
    internal = I.read(internal_file(tmp_path, data))
    filed = I.read_filed(internal, cache(tmp_path))
    ex = I.read_exclusions(exclusions_file(tmp_path))
    rows = {(r["quarter"], r["comparison"], r["measure"]): r
            for r in I.reconcile(internal, filed, ex, 0.01, bank=BANK, absorptions=[])}
    r = rows[("2025Q1", "Auto", "gross_charge_offs")]
    assert (r["filed"], r["internal"], r["remainder"], r["remainder_share"]) == (1, 0, 1, None)
    assert r["within_tolerance"] == "no"
    assert r["why"] == "the internal figure is 0, so the remainder has no share"
    hel = rows[("2025Q1", "Mortgage and home equity loans", "net_charge_offs")]
    assert hel["internal"] == 3 and hel["within_tolerance"] == "yes"


@pytest.mark.parametrize("tolerance,match", [
    (None, "tolerance is required"),
    (float("nan"), "finite number"),
    (-0.01, "at least 0"),
    ("a lot", "must be a number"),
    (True, "tolerance is required"),
])
def test_reconcile_refuses_without_a_stated_tolerance(tmp_path, tolerance, match):
    with pytest.raises(ValueError, match=match):
        run(tmp_path, tolerance=tolerance)


def test_an_exclusion_nothing_would_take_is_refused(tmp_path):
    lines = EXCLUSIONS[:2] + ["2025Q1,Other consumer,Direct auto,balance,Something,5",
                              "2024Q4,Mortgage,All,balance,Held for sale,5"]
    with pytest.raises(I.Refused) as exc:
        run(tmp_path, ex_lines=lines)
    assert exc.value.problems[0].startswith("line 3: Other consumer / Direct auto is not compared")
    assert exc.value.problems[1] == ("line 4: the internal file has no row for 2024Q4, Mortgage / All, "
                                     "so nothing would take this exclusion")


@pytest.mark.parametrize("bad,expect", [
    ("2025Q1,Mortgage,All,balance,Held for sale,", "line 3: amount is blank"),
    ("2025Q1,Mortgage,All,balances,Held for sale,5", "line 3: measure 'balances' is not one of"),
    ("2025Q1,Mortgage,All,balance,,5", "line 3: name is blank"),
    ("2025-03-31,Mortgage,All,balance,Held for sale,5", "line 3: quarter '2025-03-31' is not written"),
    ("2025Q1,Mortgage,All,balance,Held for sale,5,extra", "line 3: 7 fields"),
])
def test_each_exclusions_refusal(tmp_path, bad, expect):
    problems = I.check_exclusions(exclusions_file(tmp_path, EXCLUSIONS[:2] + [bad]))
    assert any(p.startswith(expect) for p in problems), problems


def test_an_exclusion_given_twice_is_refused(tmp_path):
    problems = I.check_exclusions(exclusions_file(tmp_path, EXCLUSIONS + [EXCLUSIONS[2]]))
    assert problems == ["line 7: 2025Q1, Mortgage, All, balance, 'Residential mortgages held for sale' "
                        "is repeated (first on line 3)"]


def test_exclusions_with_no_rows_state_there_are_none(tmp_path):
    assert I.check_exclusions(exclusions_file(tmp_path, EXCLUSIONS[:2])) == []


def test_the_notes_name_both_entities_and_the_delinquency_match(tmp_path):
    internal = I.read(internal_file(tmp_path))
    ex = I.read_exclusions(exclusions_file(tmp_path))
    notes = "\n".join(I.reconcile_notes(internal, ex, BANK, 0.01, "Source: test"))
    assert ("Compared: Synthetic Bancorp (made up for the tests) (the internal file's entity) against "
            "Synthetic Bank, N.A. (made up), FDIC certificate 17534") in notes
    assert "Internal 60+ has no public counterpart" in notes
    assert "Within tolerance when the share is at most 0.01" in notes


def test_a_comparison_the_file_cannot_make_is_named(tmp_path):
    internal = I.read(internal_file(tmp_path, [d for d in INTERNAL if d[1] == "Credit card"]))
    ex = I.read_exclusions(exclusions_file(tmp_path, EXCLUSIONS[:2]))
    notes = I.reconcile_notes(internal, ex, BANK, 0.01, "Source: test")
    assert ("Not compared: Auto (internal Auto / All against RC-C 6.c; RI-B 5.b), because the file has "
            "no rows for Auto / All.") in notes


def test_pull_fetches_only_the_reconcile_fields(tmp_path):
    asked = []

    def fake(url):
        asked.append(url)
        if "/history" in url:
            return {"meta": {"total": 0}, "data": []}
        return {"meta": {"total": 1}, "data": [{"data": dict(CERT=int(KEY), REPDTE="20250331",
                                                             RSSDHCR="1", **FILED[Q1])}]}
    got = I.pull(tmp_path / "c", "2025Q1", "2025Q1", fetch=fake)
    assert list(got) == [Q1]
    assert "LNRERSF2" in asked[0] and "LNCONRP" in asked[0] and "RSSDHCR" in asked[0]
    assert any("/history" in u and "2025-01-01" in u for u in asked)
    assert I.read_absorptions(tmp_path / "c", "2025Q1") == []
    # Question 22: the record states its start, the pull's first year
    assert json.loads((tmp_path / "c" / "absorptions.json").read_text())["since"] == "2025-01-01"


def test_reconcile_refuses_without_the_absorption_record(tmp_path):
    d = cache(tmp_path)
    (d / "absorptions.json").unlink()
    with pytest.raises(ValueError, match="absorptions.json is not there.*internal pull"):
        I.read_absorptions(d, "2025Q1")


def _card_gross_q2(tmp_path, filed, links, measure="gross_charge_offs"):
    data = [x for x in INTERNAL if x[1] == "Credit card"]
    internal = I.read(internal_file(tmp_path, data))
    ex = I.read_exclusions(exclusions_file(tmp_path, EXCLUSIONS[:2]))
    rows = I.reconcile(internal, filed, ex, 0.01, bank=BANK, absorptions=links)
    return next(r for r in rows if r["comparison"] == "Credit card" and r["quarter"] == "2025Q2"
                and r["measure"] == measure)


def test_a_repeated_year_to_date_is_taken_off_the_filing_as_the_public_series_do(tmp_path):
    """KeyBank absorbs bank 999 under the same parent in 2025Q2; 999 filed a
    Q1 year to date of 4, which KeyBank's Q2 year to date repeats (25 + 4)."""
    filed = {Q1: [dict(CERT=int(KEY), REPDTE=Q1, RSSDHCR="1", **FILED[Q1]),
                  dict(CERT=999, REPDTE=Q1, RSSDHCR="1", **dict(FILED[Q1], DRCRCD=4, CRCRCD=1))],
             Q2: [dict(CERT=int(KEY), REPDTE=Q2, RSSDHCR="1", **dict(FILED[Q2], DRCRCD=29, CRCRCD=6))]}
    link = [{"acquirer": KEY, "absorbed": "999", "quarter": "2025-06-30"}]
    assert float(_card_gross_q2(tmp_path, filed, [])["filed"]) == 19
    assert float(_card_gross_q2(tmp_path, filed, link)["filed"]) == 15
    # recoveries too: net is (29 - 4 - 10) - (6 - 1 - 2) = 12, not 15 or 11
    assert float(_card_gross_q2(tmp_path, filed, link, "net_charge_offs")["filed"]) == 12


def test_a_year_to_date_restarted_under_a_new_parent_is_the_quarters(tmp_path):
    filed = {Q1: [dict(CERT=int(KEY), REPDTE=Q1, RSSDHCR="1", **FILED[Q1])],
             Q2: [dict(CERT=int(KEY), REPDTE=Q2, RSSDHCR="2", **dict(FILED[Q2], DRCRCD=8))]}
    assert float(_card_gross_q2(tmp_path, filed, [])["filed"]) == 8
    filed[Q2][0]["RSSDHCR"] = "1"
    assert float(_card_gross_q2(tmp_path, filed, [])["filed"]) == -2


# ---------------------------------------------------------------- the command line

def test_cli_check_ok_and_refused(tmp_path, capsys):
    good = internal_file(tmp_path)
    ex = exclusions_file(tmp_path)
    assert main(["internal", "check", str(good), "--exclusions", str(ex)]) == 0
    out = capsys.readouterr().out
    assert "OK: %s passes: 12 rows, 2025Q1 to 2025Q2" % good in out
    assert "net_charge_offs on 12 rows" in out
    bad = write(tmp_path, [row("2024Q1", bal="x"), row("2024Q3")], name="bad.csv")
    badex = exclusions_file(tmp_path, EXCLUSIONS[:2] + ["2025Q1,Mortgage,All,balance,X,"])
    assert main(["internal", "check", str(bad), "--exclusions", str(badex)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED: %s does not pass as an internal file; 2 problems:" % bad in err
    assert "line 7: balance 'x' is not a number" in err
    assert "REFUSED: %s does not pass as an exclusions file; 1 problem:" % badex in err


def test_cli_template_then_series(tmp_path, capsys):
    assert main(["internal", "template", str(tmp_path / "t.csv")]) == 0
    assert (tmp_path / "t.exclusions.csv").exists()
    assert main(["internal", "template", str(tmp_path / "t.csv")]) == 2
    assert "already exists" in capsys.readouterr().err
    path = write(tmp_path, card_rows(3))
    assert main(["internal", "series", str(path), "--out-dir", str(tmp_path / "s")]) == 0
    out = capsys.readouterr().out
    assert "Wrote 3 of 8 series" in out
    assert "Not written: internal_credit-card_all_net-charge-off-rate.csv has no value." in out


def test_cli_reconcile(tmp_path, capsys):
    good = internal_file(tmp_path)
    d = cache(tmp_path)
    ex = exclusions_file(tmp_path)
    out = tmp_path / "rec.csv"
    roster = str(ROOT / "config" / "peers.json")
    args = ["internal", "reconcile", str(good), "--cache", str(d), "--roster", roster,
            "--exclusions", str(ex), "--out", str(out)]
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert "--tolerance" in capsys.readouterr().err
    assert main(args + ["--tolerance", "0.01"]) == 0
    said = capsys.readouterr().out
    assert "outside 2" in said and "outside: 2025Q2 Mortgage balance, remainder 100" in said
    assert "outside: 2025Q2 Mortgage and home equity loans balance, remainder 100" in said
    text = out.read_text(encoding="utf-8")
    assert "against KeyBank NA, FDIC certificate 17534" in text
    header = [ln for ln in text.splitlines() if not ln.startswith("#")][0]
    assert header == ",".join(I.RECONCILE_COLUMNS)
    (d / ("q%s.json" % Q2)).unlink()
    assert main(args + ["--tolerance", "0.01"]) == 2
    assert "first missing 2025Q2" in capsys.readouterr().err



def test_segments_whose_files_would_share_a_name_are_refused(tmp_path):
    """'Prime' and 'PRIME' would both write internal_credit-card_prime_*.csv
    (review, 14 Oct 2026: one segment's series were lost)."""
    rows = [",".join([q, "Credit card", seg, "100", "1", "", "0", "4", "2", "1"])
            for seg in ("Prime", "PRIME") for q in ("2025Q1", "2025Q2")]
    problems = I.check(write(tmp_path, rows))
    assert any("segments 'Prime' and 'PRIME' of Credit card differ only in case or punctuation" in x
               for x in problems), problems


def test_pull_records_absorptions_for_every_cached_quarter(tmp_path):
    asked = []

    def fake(url):
        asked.append(url)
        if "/history" in url:
            return {"meta": {"total": 0}, "data": []}
        return {"meta": {"total": 1}, "data": [{"data": dict(CERT=int(KEY), REPDTE="20250630",
                                                             RSSDHCR="1", **FILED[Q2])}]}
    c = tmp_path / "c"
    c.mkdir()
    (c / "q20160331.json").write_text(json.dumps([dict(CERT=int(KEY), REPDTE="20160331", RSSDHCR="1",
                                                       **FILED[Q1])]), encoding="utf-8")
    I.pull(c, "2025Q2", "2025Q2", fetch=fake)
    assert any("/history" in u and "2016-01-01" in u for u in asked)



def test_each_series_states_the_books_path(tmp_path):
    """A shrinking book can raise a rate with no more loss (home equity
    loans, "just discontinued"): the path is stated, no run-off line drawn."""
    qs = labels(2022, 1, 12)
    rows = [(q, "Home equity", "Home equity loans", 1000 - 50 * i, 2, 0) for i, q in enumerate(qs)]
    internal = I.read(internal_file(tmp_path, rows))
    line = I.book_path(internal, "Home equity", "Home equity loans")
    # windows end 2022Q4..2024Q4; first average (1000+950+900+850)/4 = 925, last (600+550+500+450)/4 = 525
    assert line.startswith("Book: four-quarter average balance 925 ($000) at 2022Q4, 525 at 2024Q4 (-43.2%)")
    assert "fell in 8 of the 8 quarters since" in line
    I.write_all_series(internal, tmp_path / "s")
    text = (tmp_path / "s" / I.series_file_name("Home equity", "Home equity loans", "net-charge-off-rate")).read_text()
    assert "# Book: four-quarter average balance 925" in text
    short = I.read(internal_file(tmp_path, rows[:8]))
    assert "fewer than nine" in I.book_path(short, "Home equity", "Home equity loans")
