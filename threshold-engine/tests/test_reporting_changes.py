"""Reporting changes (reporting_changes.py, config/reporting-changes.json):
the registry, its refusals, the note lines on the series a change touches,
Decide's chart marker and the book's Reporting changes tab.

The firm, 16 Oct 2026, on the commercial proposal's question 13: "Definitely
mark reporting changes." Every change is labelled on every series it
touches, in the quarter it took effect, a change spread over several
quarters included, the consumer book too.
"""
import copy
import json
import re
import zipfile
from pathlib import Path

import pytest
from openpyxl import load_workbook

from conftest import ROOT
from threshold_engine import book as BK
from threshold_engine import reporting_changes as RC
from threshold_engine.glossary import TERMS
from threshold_engine.peers import books as PB
from threshold_engine.peers import delinquency as D
from threshold_engine.series import read_notes
from threshold_engine.workbook import build

REGISTRY = ROOT / "config" / "reporting-changes.json"
CHANGES = RC.load(REGISTRY)
ALL_MEASURES = ["net charge-offs", "gross charge-offs", "30-89", "90+ accruing", "nonaccrual",
                "90+ incl. nonaccrual", "30+ incl. nonaccrual"]


def by_name(name):
    return next(c for c in CHANGES if c["name"] == name)


# ---- the registry in the repository -------------------------------------------------------------------

def test_the_registry_in_the_repository_loads_and_holds_the_consumer_changes():
    """Twelve changes, each from research-breaks.md or research-fdic.md
    (16 Oct 2026) and marked verified there. The ones touching each product
    are named here, consumer and commercial, so a change dropped or moved
    shows."""
    assert len(CHANGES) == 12
    touching = {c["name"]: (RC.when(c), c["products"]) for c in CHANGES if c["products"]}
    five = ["Credit card", "Mortgage", "Home equity", "Other consumer", "Auto"]
    six = list(PB.COMMERCIAL)
    real_estate = six[1:]
    splits = ["Owner-occupied nonfarm nonresidential", "Other nonfarm nonresidential"]
    assert touching == {
        "Construction, nonfarm and lease splits": ("2007Q1", splits),
        "Loans classified as trading": ("2008Q1", five + six),
        "Secured by real estate, clarified": ("2009Q1", six),
        "Securitizations back on the books (FAS 166 and 167)": ("2010Q1", ["Credit card", "Other consumer"]),
        "Construction loans after completion": ("2011Q1", real_estate),
        "Auto loans get their own line": ("2011Q1", ["Other consumer", "Auto"]),
        "Real estate breakdown for the whole bank": ("2013Q2", ["Mortgage", "Home equity"] + real_estate),
        "CECL: purchased credit-deteriorated loans": ("2020Q1", five + six),
        "COVID-19 deferrals not reported as past due": ("2020Q2", five + six),
        "NDFI and margin-loan revision": ("2024Q4 to 2025Q2", ["Other consumer", "C&I"]),
    }
    # 78 FR 30922: "the nine-category breakdown of loans secured by real estate for the
    # consolidated institution" - the 1-4 family lines (mortgage, home equity) are three of
    # the nine, so the change is on them too, not on the commercial items only.
    whole = by_name("Real estate breakdown for the whole bank")
    assert "nine-category" in whole["call_report_items"][0] and "1-4 family" in whole["call_report_items"][0]
    assert "1-4 family included" in whole["what_changed"]
    # Its own source says the 2010 NDFI line came out of other loans, not C&I.
    assert by_name("NDFI loans split out of other loans")["products"] == []
    # The nonfarm splits begin with the 2007 change, which their own note says.
    for p in splits:
        assert by_name("Construction, nonfarm and lease splits")["already_labelled"][p] == "first filed 2007Q1"
        assert "first filed 2007Q1" in PB.DEFINITIONS[p]
    ndfi = by_name("NDFI and margin-loan revision")
    assert "RC-C 6.d: other consumer loans" in ndfi["call_report_items"] and "RC-C 4: C&I" in ndfi["call_report_items"]
    assert ndfi["measures"] == ALL_MEASURES
    assert [s["url"] for s in ndfi["sources"]] == [
        "https://www.govinfo.gov/content/pkg/FR-2024-05-22/html/2024-11221.htm",
        "https://www.fdic.gov/analysis/bank-lending-nondepository-financial-institutions.pdf"]
    # Past due only: the deferral relief says nothing about nonaccrual.
    assert "nonaccrual" not in by_name("COVID-19 deferrals not reported as past due")["measures"]
    # The two the code already labelled are linked to its notes, not said twice.
    assert by_name("Securitizations back on the books (FAS 166 and 167)")["already_labelled"] == \
        {"Credit card": "Securitized cards"}
    assert PB.DEFINITIONS["Credit card"].startswith("Securitized cards: before 2010")
    assert by_name("Auto loans get their own line")["already_labelled"] == \
        {"Other consumer": "Auto was inside 6.d until 2011Q1"}
    for c in CHANGES:
        assert all(s["url"].startswith("https://") for s in c["sources"]), c["name"]
        assert "\n" not in c["what_changed"] and c["what_changed"].endswith("."), c["name"]
    assert "Left out:" in RC.what(REGISTRY)


def test_quarters_counts_every_quarter_of_a_spread_change():
    assert RC.quarters("2024Q4", "2025Q2") == ["2024Q4", "2025Q1", "2025Q2"]
    assert RC.quarters("2010Q1", "2010Q1") == ["2010Q1"]


# ---- the refusals: by entry, by name, every problem at once ---------------------------------------------

def good():
    return {"_what": "A test registry.",
            "changes": [{"name": "A change", "first": "2024Q4", "last": "2025Q2", "products": ["Other consumer"],
                         "measures": ["net charge-offs"], "call_report_items": ["RC-C 6.d"],
                         "what_changed": "Something moved.",
                         "sources": [{"citation": "A notice", "url": "https://example.org/notice"}],
                         "already_labelled": {}}]}


def refused(raw, tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RC.RegistryError) as e:
        RC.load(p)
    return str(e.value)


def changed(**over):
    raw = good()
    for k, v in over.items():
        if v is KeyError:
            del raw["changes"][0][k]
        else:
            raw["changes"][0][k] = v
    return raw


@pytest.mark.parametrize("over, says", [
    (dict(first=KeyError), "change 1 (A change) is missing 'first' (every key is required; none has a default)"),
    (dict(already_labelled=KeyError), "is missing 'already_labelled'"),
    (dict(when="2024Q4"), "change 1 (A change) has 'when', which is not a key it takes"),
    (dict(first="2024-12-31"), "first must be a quarter written like 2024Q4, not '2024-12-31'"),
    (dict(last="2024Q3"), "last, 2024Q3, comes before first, 2024Q4"),
    (dict(products=["Cards"]), "products has 'Cards', not one of Credit card, Mortgage"),
    (dict(products=["Auto", "Auto"]), "products names one twice"),
    (dict(measures=["charge-offs"]), "measures has 'charge-offs', not one of net charge-offs"),
    (dict(measures=[]), "a change that touches a product names the measures it touches"),
    (dict(products=[], measures=[], call_report_items=[]), "it touches no product and no Call Report item"),
    (dict(products=[]), "a change that touches a product names the measures it touches, and one that touches none "
                        "names none"),
    (dict(what_changed=""), "what_changed must be one plain sentence on one line"),
    (dict(what_changed="Two\nlines."), "what_changed must be one plain sentence on one line"),
    (dict(what_changed="Two\rlines."), "what_changed must be one plain sentence on one line"),
    (dict(what_changed="Two\u2028lines."), "what_changed must be one plain sentence on one line"),
    (dict(name="A\nchange"), "name must be a short name on one line"),
    (dict(sources=[{"citation": "A\nnotice", "url": "https://example.org"}]), "citation must name the document, on one line"),
    (dict(sources=[{"citation": "A notice", "url": "http://example.org"}]), "change 1 (A change), source 1: url must be"),
    (dict(sources=[]), "sources must list at least one source"),
    (dict(sources=[{"citation": "A notice", "url": "example.org"}]), "change 1 (A change), source 1: url must be"),
    (dict(sources=[{"citation": "A notice"}]), "change 1 (A change), source 1 is missing 'url'"),
    (dict(already_labelled={"Credit card": "Securitized cards"}),
     "already_labelled names 'Credit card', which is not one of its products"),
    (dict(already_labelled={"Other consumer": "Auto left in 2019"}),
     "already_labelled for Other consumer quotes 'Auto left in 2019', but no definition note of Other consumer "
     "says it"),
])
def test_a_malformed_entry_is_refused_by_name(tmp_path, over, says):
    assert says in refused(changed(**over), tmp_path)


def test_every_problem_is_listed_at_once_each_under_its_entry(tmp_path):
    raw = good()
    second = copy.deepcopy(raw["changes"][0])
    second.update(name="Another", first="2025Q5")
    third = copy.deepcopy(raw["changes"][0])           # the same name again
    raw["changes"] += [second, third]
    raw["changes"][0]["products"] = ["Boats"]
    msg = refused(raw, tmp_path)
    assert "change 1 (A change): products has 'Boats'" in msg
    assert "change 2 (Another): first must be a quarter written like 2024Q4, not '2025Q5'" in msg
    assert "change 3 (A change): the name is used twice" in msg


@pytest.mark.parametrize("raw, says", [
    ({"changes": []}, "r.json is missing '_what'"),
    ({"_what": "x", "changes": []}, "changes must list at least one change"),
    ({"_what": "x", "changes": [], "extra": 1}, "has 'extra', which is not a key it takes"),
    ({"_what": "", "changes": good()["changes"]}, "_what must say what the file is"),
])
def test_the_file_itself_is_checked(tmp_path, raw, says):
    assert says in refused(raw, tmp_path)


def test_a_missing_or_broken_file_is_refused(tmp_path):
    with pytest.raises(RC.RegistryError, match="does not exist"):
        RC.load(tmp_path / "nope.json")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(RC.RegistryError, match="bad.json is not valid JSON"):
        RC.load(tmp_path / "bad.json")
    with pytest.raises(RC.RegistryError, match="cannot be read"):
        RC.load(tmp_path)                                   # a folder, not a file
    (tmp_path / "latin.json").write_bytes(b'{"_what": "\xe9"}')
    with pytest.raises(RC.RegistryError, match="is not a UTF-8 text file"):
        RC.load(tmp_path / "latin.json")


# ---- the note lines on a series ----------------------------------------------------------------------

def test_an_affected_series_carries_the_change_and_an_unaffected_one_does_not():
    """Other consumer, net, 2020Q1 to 2026Q2: CECL and the NDFI revision,
    spread over its three quarters, each with its sources. Credit card over
    the same quarters: CECL only. Mortgage delinquency 30-89 from 2006Q1:
    trading, the 2013Q2 real estate breakdown (1-4 family is three of its
    nine categories), CECL and the deferrals; nonaccrual: the same without
    the deferrals."""
    oc = RC.note_lines(CHANGES, ["Other consumer"], "net charge-offs", "2020Q1", "2026Q2", [])
    assert oc == [
        "reporting-change: 2020Q1, CECL: purchased credit-deteriorated loans. %s Source: %s."
        % (by_name("CECL: purchased credit-deteriorated loans")["what_changed"],
           RC.cited(by_name("CECL: purchased credit-deteriorated loans"))),
        "reporting-change: 2024Q4 to 2025Q2, NDFI and margin-loan revision. %s Source: 89 FR 45046 (22 May 2024), "
        "section II.C.1: effective as of the December 31, 2024, report date, "
        "https://www.govinfo.gov/content/pkg/FR-2024-05-22/html/2024-11221.htm; FDIC, Banking Issues in Focus "
        "No. 1, Feb 2026, Bank Lending to Nondepository Financial Institutions (best efforts through 30 Jun 2025), "
        "https://www.fdic.gov/analysis/bank-lending-nondepository-financial-institutions.pdf."
        % by_name("NDFI and margin-loan revision")["what_changed"]]
    card = RC.note_lines(CHANGES, ["Credit card"], "net charge-offs", "2020Q1", "2026Q2", [])
    assert [ln.split(",")[0] for ln in card] == ["reporting-change: 2020Q1"]
    assert not any("NDFI" in ln for ln in card)
    assert [ln[:24] for ln in RC.note_lines(CHANGES, ["Mortgage"], "30-89", "2006Q1", "2026Q2", [])] == [
        "reporting-change: 2008Q1", "reporting-change: 2013Q2", "reporting-change: 2020Q1",
        "reporting-change: 2020Q2"]
    assert [ln[:24] for ln in RC.note_lines(CHANGES, ["Mortgage"], "nonaccrual", "2006Q1", "2026Q2", [])] == [
        "reporting-change: 2008Q1", "reporting-change: 2013Q2", "reporting-change: 2020Q1"]


def test_a_spread_change_touches_a_series_that_holds_any_of_its_quarters():
    def ndfi(first, last):
        return any("NDFI" in ln for ln in RC.note_lines(CHANGES, ["Other consumer"], "30-89", first, last, []))
    assert ndfi("2025Q2", "2026Q2") and ndfi("2010Q1", "2024Q4") and ndfi("2025Q1", "2025Q1")
    assert not ndfi("2010Q1", "2024Q3") and not ndfi("2025Q3", "2026Q2")


def test_a_change_its_products_own_note_describes_is_linked_not_said_twice():
    """Credit card before 2010: the series' own Securitized cards note says
    it, so the reporting change points to that note; without the note, the
    change is said in full."""
    note = [PB.DEFINITIONS["Credit card"]]
    linked = RC.note_lines(CHANGES, ["Credit card"], "gross charge-offs", "2006Q1", "2010Q4", note)
    fas = [ln for ln in linked if "FAS 166" in ln]
    assert fas == ['reporting-change: 2010Q1, Securitizations back on the books (FAS 166 and 167). The note above '
                   'that says "Securitized cards" describes this change. Source: FDIC Quarterly Banking Profile, '
                   'first quarter 2010, https://www.fdic.gov/analysis/quarterly-banking-profile/qbp/2010mar/qbp.pdf.']
    full = [ln for ln in RC.note_lines(CHANGES, ["Credit card"], "gross charge-offs", "2006Q1", "2010Q4", [])
            if "FAS 166" in ln]
    assert by_name("Securitizations back on the books (FAS 166 and 167)")["what_changed"] in full[0]
    # Other consumer carries the auto split in its own note: linked; Auto has no such note: in full.
    oc = [ln for ln in RC.note_lines(CHANGES, ["Other consumer"], "nonaccrual", "2006Q1", "2026Q2",
                                     [D.DEFINITIONS["Other consumer"]]) if "Auto loans" in ln]
    assert 'The note above that says "Auto was inside 6.d until 2011Q1" describes this change.' in oc[0]
    auto = [ln for ln in RC.note_lines(CHANGES, ["Auto"], "nonaccrual", "2011Q1", "2026Q2", []) if "Auto loans" in ln]
    assert by_name("Auto loans get their own line")["what_changed"] in auto[0]


def test_the_quarters_are_read_back_from_a_files_notes(tmp_path):
    lines = RC.note_lines(CHANGES, ["Other consumer"], "net charge-offs", "2006Q1", "2026Q2", [])
    p = tmp_path / "s.csv"
    p.write_text("".join("# %s\n" % ln for ln in ["measure: x"] + lines) + "date,value\n2020-03-31,1\n",
                 encoding="utf-8")
    notes = read_notes(p)
    assert [k for k, _ in notes].count("reporting-change") == len(lines) == 5
    assert RC.quarters_in_notes(notes) == {"2008Q1", "2010Q1", "2011Q1", "2020Q1", "2024Q4", "2025Q1", "2025Q2"}
    with pytest.raises(ValueError, match="must begin with the quarter it took effect"):
        RC.quarters_in_notes([("reporting-change", "sometime in 2024, a change")])


# ---- the peers build: refused without a registry, before anything is read -------------------------------

STATED = dict(cache="c", roster="r", series_dir="s", first="2020Q1", last="2021Q4", products=["Credit card"],
              mergers="m", absorptions="a", extra_acquisitions=[], industry_combined=[], jump=0.25,
              acquisition_share=0.05, min_book=0, exempt_self=True, pro_forma=False, pack="all", min_banks=5,
              rank_by="net", last_n=4, min_obs=2, base_quarter="2020Q4", index_min_book=0, lagged_years=[2020],
              lag_years=1, normalisation_years=[2020, 2021], mix_base_year=2020, delinquency=False)


def test_the_peers_build_refuses_without_a_good_registry(tmp_path):
    from threshold_engine.peers import run
    with pytest.raises(TypeError, match="reporting_changes"):
        run.build("p.xlsx", say=lambda line: None, **STATED)
    with pytest.raises(ValueError, match="--reporting-changes must name the registry"):
        run.build("p.xlsx", reporting_changes=None, say=lambda line: None, **STATED)
    with pytest.raises(ValueError, match="--reporting-changes: the reporting changes file .* does not exist"):
        run.build("p.xlsx", reporting_changes=tmp_path / "nope.json", say=lambda line: None, **STATED)
    p = tmp_path / "r.json"
    p.write_text(json.dumps(changed(last="2024Q3")), encoding="utf-8")
    with pytest.raises(ValueError, match=r"--reporting-changes: change 1 \(A change\): last, 2024Q3"):
        run.build("p.xlsx", reporting_changes=p, say=lambda line: None, **STATED)
    assert not Path("p.xlsx").exists()


# ---- Decide: the chart marks the quarters, Sources shows the lines --------------------------------------

from test_decide import LABELS, PAIRS, SER, SETTINGS, decide_spec, typed  # noqa: E402


def with_notes(folder, notes):
    """SER's files copied into ``folder``, ``notes[label]`` lines added before the data."""
    out = []
    for lbl, path in SER:
        dst = folder / path.name
        extra = "".join("# %s\n" % ln for ln in notes.get(lbl, []))
        dst.write_text(extra + path.read_text(encoding="utf-8"), encoding="utf-8")
        out.append((lbl, dst))
    return out


NOTES = {
    # Card net: CECL (2020Q1) in full, and the FAS 166 and 167 link (2010Q1).
    "Card - Net - Industry": RC.note_lines(CHANGES, ["Credit card"], "net charge-offs", "2009Q1", "2026Q2",
                                           [PB.DEFINITIONS["Credit card"]]),
    # Card gross (an other consumer file in the test data): the NDFI revision, three quarters.
    "Card - Gross - Industry": RC.note_lines(CHANGES, ["Other consumer"], "gross charge-offs", "2023Q1",
                                             "2026Q2", []),
}


@pytest.fixture(scope="module")
def marked(tmp_path_factory):
    d = tmp_path_factory.mktemp("changes")
    ser = with_notes(d, NOTES)
    info = build(d / "decide.xlsx", ser, decide=decide_spec(), **SETTINGS)
    return d, info


def test_sources_shows_each_reporting_change_line(marked):
    d, info = marked
    """Round 3: each file's row on Sources names the quarters its reporting
    changes took effect (the table under Reporting changes says what each
    is), and the lines themselves are not repeated."""
    ws = load_workbook(info["path"])["Sources"]
    h = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 5).value == "File")
    col = [ws.cell(h, c).value for c in range(1, 12)].index("Reporting changes") + 1
    by_file = {ws.cell(r, 5).value: ws.cell(r, col).value for r in range(h + 1, h + 1 + len(SER))}
    files = dict(SER)                                    # the fixture's copies keep the file names
    for lbl, notes in NOTES.items():
        want = RC.whens_in_notes([("reporting-change", ln[len("reporting-change: "):]) for ln in notes])
        assert by_file[files[lbl].name] == " · ".join(want)
    assert by_file[files["Card - Net - Industry"].name] == "2010Q1 · 2020Q1"
    assert by_file[files["Card - Gross - Industry"].name] == "2024Q4 to 2025Q2"
    text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    assert "reporting-change:" not in text
    assert "Reporting change" in {t for t, _, _ in TERMS}


def test_decide_marks_the_quarters_on_the_row_shown(marked, tmp_path):
    """The flags are per row of the table, from its sources' notes; the marker
    is the top of the zones in a flagged quarter within the window, #N/A
    otherwise. Last 48 quarters (as built): 2020Q1 on Card, net, and not
    2010Q1, which is outside the window; every quarter: both. Card, gross:
    2024Q4, 2025Q1 and 2025Q2. Mortgage: none."""
    d, info = marked
    h = info["decide"]["helpers"]
    wb = load_workbook(info["path"])
    ws, data = wb["Decide"], wb["Data"]
    quarters = [data.cell(r, 1).value for r in range(2, data.max_row + 1) if data.cell(r, 1).value]
    flagged = {}
    for i, pr in enumerate(PAIRS):
        c_ = h["chg%d" % i]
        assert ws["%s1" % c_].value == "Reporting change took effect: %s - %s" % pr
        flagged[pr] = [q for k, q in enumerate(quarters) if ws["%s%d" % (c_, 2 + k)].value == 1]
    assert flagged == {("Card", "Net"): ["2010Q1", "2020Q1"], ("Mortgage", "Net"): [],
                       ("Card", "Gross"): ["2024Q4", "2025Q1", "2025Q2"]}

    def drawn(vals):
        top = vals["DECIDE!%s3" % h["ft"]]
        got = {}
        for k, q in enumerate(quarters):
            v = vals.get("DECIDE!%s%d" % (h["chg"], 2 + k))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert v == top, q
                got[q] = v
        return sorted(got)

    window = "Decide!M%d" % info["decide"]["layout"]["window"]
    assert drawn(typed(info["path"], tmp_path / "a.xlsx", {}, show=[("Card", "Net")], info=info)) == ["2020Q1"]
    assert drawn(typed(info["path"], tmp_path / "b.xlsx", {window: "Every quarter"}, show=[("Card", "Net")],
                       info=info)) == ["2010Q1", "2020Q1"]
    assert drawn(typed(info["path"], tmp_path / "c.xlsx", {}, show=[("Card", "Gross")], info=info)) == \
        ["2024Q4", "2025Q1", "2025Q2"]
    assert drawn(typed(info["path"], tmp_path / "d.xlsx", {}, show=[("Mortgage", "Net")], info=info)) == []
    assert drawn(typed(info["path"], tmp_path / "e.xlsx", {}, show=[("Card", "Net"), ("Card", "Gross")],
                       info=info)) == []                                         # two rows shown: nothing drawn


def test_decides_chart_draws_the_marker_as_a_diamond_and_says_so(marked):
    d, info = marked
    with zipfile.ZipFile(info["path"]) as z:
        xml = next(z.read(n).decode() for n in z.namelist()
                   if re.match(r"xl/charts/chart\d+\.xml$", n) and "Decide!dq_" in z.read(n).decode())
    ser = next(s for s in re.findall(r"<ser>.*?</ser>", xml) if "Decide!dq_change" in s)
    assert "<v>Reporting change</v>" in ser and '<symbol val="diamond" /><size val="7" />' in ser
    assert "<a:ln><a:noFill" in ser
    ws = load_workbook(info["path"])["Decide"]
    note = ws.cell(info["decide"]["layout"]["notes"] + 1, 2).value
    assert "A diamond along the top marks a quarter in which a reporting change took effect" in note


def test_without_reporting_change_notes_decide_marks_nothing(tmp_path):
    info = build(tmp_path / "plain.xlsx", SER, decide=decide_spec(), **SETTINGS)
    h = info["decide"]["helpers"]
    ws = load_workbook(info["path"])["Decide"]
    assert all(ws["%s%d" % (h["chg%d" % i], r)].value is None for i in range(len(PAIRS)) for r in range(2, 180))
    assert "diamond" not in ws.cell(info["decide"]["layout"]["notes"] + 1, 2).value


def test_a_malformed_reporting_change_note_is_refused(tmp_path):
    ser = with_notes(tmp_path, {LABELS[0]: ["reporting-change: in 2024 something moved"]})
    with pytest.raises(ValueError, match="must begin with the quarter it took effect"):
        build(tmp_path / "x.xlsx", ser, decide=decide_spec(), **SETTINGS)


# ---- the book: its key, and the Reporting changes tab -------------------------------------------------------

from test_book import write_book  # noqa: E402


def test_the_book_names_the_registry_and_a_peers_build_must(tmp_path):
    p = write_book(tmp_path)
    raw = json.loads(p.read_text())
    del raw["reporting_changes"]
    p.write_text(json.dumps(raw))
    with pytest.raises(BK.BookError, match="missing 'reporting_changes'"):
        BK.load(p)
    p = write_book(tmp_path, peers={k: "x" for k in BK.PEERS_KEYS})
    with pytest.raises(BK.BookError, match="reporting_changes: the peers build reads the Call Report"):
        BK.load(p)
    (tmp_path / "r.json").write_text(json.dumps(changed(products=["Boats"])), encoding="utf-8")
    with pytest.raises(BK.BookError, match=r"reporting_changes: change 1 \(A change\): products has 'Boats'"):
        BK.load(write_book(tmp_path, reporting_changes="r.json"))
    bk = BK.load(write_book(tmp_path, reporting_changes=str(REGISTRY)))
    assert bk["changes"] == CHANGES and bk["reporting_changes"] == REGISTRY


def test_the_public_book_names_the_repositorys_registry():
    bk = BK.load(ROOT / "books" / "consumer-public.json")
    assert bk["reporting_changes"].resolve() == REGISTRY.resolve() and len(bk["changes"]) == 12


def test_the_book_writes_the_reporting_changes_on_sources(tmp_path):
    """The book folds the changes into Sources as its last section: one row per
    change, as the registry states it, under headings each with a Glossary
    entry; the registry's own words (what it leaves out) above; no tab of its own."""
    from threshold_engine import reference_tabs as RT
    out = tmp_path / "book.xlsx"
    BK.build(write_book(tmp_path, reporting_changes=str(REGISTRY)), out, say=lambda *_: None)
    wb = load_workbook(out)
    assert RC.TAB not in wb.sheetnames
    ws = wb["Sources"]
    r = next(x for x in range(1, ws.max_row + 1) if str(ws.cell(x, 2).value or "").startswith("Reporting changes ·"))
    assert ws.cell(r + 1, 2).value == RC.what(REGISTRY)
    h = r + 2
    heads = [ws.cell(h, c).value for c in range(2, 14) if ws.cell(h, c).value]
    assert heads == list(RT.RC_HEAD)
    terms = {t for t, _, _ in TERMS}
    assert {"Reporting change"} <= terms
    col = {v: c for c in range(2, 14) for v in [ws.cell(h, c).value] if v}
    rows = [x for x in range(h + 1, ws.max_row + 1) if ws.cell(x, 2).value]
    assert [ws.cell(x, 2).value for x in rows] == [c["name"] for c in CHANGES]
    nd = rows[[c["name"] for c in CHANGES].index("NDFI and margin-loan revision")]
    assert [ws.cell(nd, col[k]).value for k in RT.RC_HEAD[1:4]] == [
        "2024Q4 to 2025Q2", "Other consumer, C&I", ", ".join(ALL_MEASURES)]
    tdr = rows[[c["name"] for c in CHANGES].index("Troubled debt restructuring captions replaced")]
    assert [ws.cell(tdr, col[k]).value for k in RT.RC_HEAD[2:4]] == ["None of the products", "None"]


def test_a_book_without_a_registry_has_no_tab(tmp_path):
    out = tmp_path / "book.xlsx"
    BK.build(write_book(tmp_path), out, say=lambda *_: None)
    assert RC.TAB not in load_workbook(out).sheetnames
