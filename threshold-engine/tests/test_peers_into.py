"""The peer tabs written into another workbook (``into``, ``names``), so the
thresholds workbook and the peers are one file built by Python alone.

Three things are proved here:

1. The standalone peer workbook is unchanged by the option. It is compared,
   part by part of the .xlsx, against the builder as it was before the option
   existed: tests/data/peers/peers_workbook_d1e353a1.py is that module copied
   unchanged from commit d1e353a1, and is loaded beside today's. Only
   docProps/core.xml (the file's created and modified times) is left out;
   the Run tab's "Built" time is frozen for both. This pins the standalone
   output as it stood: a later change that means to alter it retires this
   comparison (and the copy) rather than editing it to pass.
2. Written into a workbook that already has its own Data, Glossary and Run
   tabs, each holding a value no peer cell could produce, every peer tab
   recalculates (the ``formulas`` engine) to exactly the standalone build's
   values, cell for cell; and no formula, validation, conditional format,
   hyperlink, defined name or chart series on a peer tab names a tab that is
   not a peer tab.
3. ``foreign_refs``, the check the builder runs before it returns, finds a
   stray reference of each of those kinds when one is planted.
"""
import datetime as dt
import importlib.util
import json
import re
import types
import zipfile

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import FormulaRule
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from conftest import DATA, ROOT
from threshold_engine.peers import peers_workbook as PW
from threshold_engine.peers import roster as R
from threshold_engine.peers import run
from threshold_engine.peers.books import industry

PEERS = DATA / "peers"
FOUR = ("Credit card", "Mortgage", "Home equity", "Other consumer")
TWO = ("Credit card", "Mortgage")
JUMP, MIN_BOOK = 0.25, 1_000_000
#: The titles used when the peer tabs first went into the thresholds workbook.
NAMES = {"Pack": "Peers pack", "Peers": "Peers", "Delinquency": "Peers delinquency", "Balances": "Peers balances",
         "Lagged": "Peers lagged", "Normalisation": "Peers normalisation", "Mix": "Peers mix",
         "Glossary": "Peers glossary", "Data": "Peers data", "DelinquencyData": "Peers delinquency data",
         "Run": "Peers run"}
#: What the host's own Data, Glossary and Run hold: a peer formula pointed at
#: one of them would read one of these.
HOST = {"Data": ("HOST DATA A1", 987654321.0), "Glossary": ("HOST GLOSSARY A1", 876543219.0),
        "Run": ("HOST RUN A1", 765432198.0)}


class _Frozen(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 14, 9, 30, 0)


FROZEN = types.SimpleNamespace(datetime=_Frozen, date=dt.date)


def _before():
    """The builder as it was at d1e353a1, loaded inside the package so its
    relative imports find today's books, roster and glossary."""
    spec = importlib.util.spec_from_file_location("threshold_engine.peers._peers_workbook_d1e353a1",
                                                  PEERS / "peers_workbook_d1e353a1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BEFORE = _before()


@pytest.fixture(scope="module")
def data():
    return json.loads((PEERS / "roster_2006.json").read_text())


@pytest.fixture(scope="module")
def recent(data):
    return {q: rows for q, rows in data.items() if q >= "20170331"}


@pytest.fixture(scope="module")
def dl_data():
    return json.loads((PEERS / "delinquency_roster.json").read_text())


@pytest.fixture(scope="module")
def roster():
    return R.load(ROOT / "config" / "peers.json")


def settings(**over):
    kw = dict(exempt_self=True, min_banks=5, index_min_book=500_000, lagged_years=(2019, 2025), lag_years=2,
              normalisation_years=(2019, 2025), mix_base_year=2019, industry=None, delinquency=None,
              rank_by="net", last_n=20, min_obs=12)
    kw.update(over)
    return kw


def build(module, out, data, roster, products, pack="all", **over):
    """``module``'s build_peers_workbook with the tests' settings, its clock frozen."""
    mp = pytest.MonkeyPatch()
    mp.setattr(module, "dt", FROZEN)
    try:
        return module.build_peers_workbook(out, data, roster, products, JUMP, MIN_BOOK, pack,
                                           json.loads((PEERS / "mergers_roster.json").read_text()),
                                           {"6672": ["2022Q2"]}, "2019Q4", **settings(**over))
    finally:
        mp.undo()


def parts(path):
    """Every part of an .xlsx but docProps/core.xml (when the file was made)."""
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist() if n != "docProps/core.xml"}


def assert_same_file(before, after):
    a, b = parts(before), parts(after)
    assert sorted(a) == sorted(b), (sorted(set(a) ^ set(b)))
    differ = [n for n in sorted(a) if a[n] != b[n]]
    assert not differ, "parts that differ: %s" % differ
    return len(a)


def dq(dl_data, **over):
    spec = dict(data=dl_data, products=TWO, measure="90+ accruing", basis="quarter-end",
                jump=0.25, min_book=1_000_000, exempt_self=True)
    spec.update(over)
    return spec


# ---- 1. the standalone workbook is unchanged ----

STANDALONE = {
    "all peers, four products, 2006 on": lambda d: dict(data=d["data"], products=FOUR),
    "regionals on other consumer, gross, a named Peer A, industry supplied": lambda d: dict(
        data=d["recent"], products=FOUR, pack="regionals", product="Other consumer", rank_by="gross",
        peer_a=R.peers(d["roster"])[2]["short"],
        industry={p: industry(d["recent"], p) for p in FOUR}),
    "delinquency on two products, four-quarter average": lambda d: dict(
        data=d["recent"], products=TWO, delinquency=dq(d["dl"], basis="four-quarter average")),
}


@pytest.mark.parametrize("case", sorted(STANDALONE))
def test_the_standalone_workbook_is_as_it_was_before_into(case, tmp_path, data, recent, dl_data, roster):
    kw = STANDALONE[case](dict(data=data, recent=recent, dl=dl_data, roster=roster))
    d, products = kw.pop("data"), kw.pop("products")
    old = build(BEFORE, tmp_path / "before.xlsx", d, roster, products, **kw)
    new = build(PW, tmp_path / "after.xlsx", d, roster, products, **kw)
    n = assert_same_file(old["path"], new["path"])
    assert n > 20 and any(name.startswith("xl/charts/") for name in parts(new["path"]))
    assert {k: v for k, v in new.items() if k not in ("path", "sheets")} == \
        {k: v for k, v in old.items() if k != "path"}
    assert new["sheets"] == list(PW.TABS)


def dq_cache(base, dl_data):
    """delinquency_roster.json with each bank's charge-off fields, laid out as
    the cache 'peers pull --delinquency yes' writes (as test_peers_cli)."""
    co = [json.loads((PEERS / n).read_text()) for n in ("roster_2006.json", "roster_1992.json")]
    cache = base / "cache"
    cache.mkdir()
    for q, rows in dl_data.items():
        merged = []
        for r in rows:
            row = dict(r)
            for d in co:
                row.update(next(x for x in d[q] if x["CERT"] == r["CERT"]))
            merged.append(row)
        (cache / ("q%s.json" % q)).write_text(json.dumps(merged), encoding="utf-8")
    return cache


def run_build(out, cache, series, **over):
    kw = dict(cache=cache, roster=ROOT / "config" / "peers.json", series_dir=series, first="2017Q1",
              last="2026Q2", products=list(TWO), mergers=PEERS / "mergers_roster.json",
              extra_acquisitions=["6672=2022Q2"], industry_combined=[], jump=0.25, min_book=1_000_000.0,
              exempt_self=True, pack="all", min_banks=5, rank_by="net", last_n=20, min_obs=12,
              base_quarter="2019Q4", index_min_book=500_000.0, lagged_years=[2019, 2025], lag_years=2,
              normalisation_years=[2019, 2025], mix_base_year=2019, delinquency=True, say=lambda s: None)
    kw.update(over)
    return run.build(out, **kw)


def test_peers_build_writes_the_same_workbook_and_series_as_before(tmp_path, dl_data, monkeypatch):
    """Through peers.run.build (a cache folder, a mergers file, the industry,
    delinquency): the workbook and every series CSV as they were."""
    cache = dq_cache(tmp_path, dl_data)
    monkeypatch.setattr(PW, "dt", FROZEN)
    monkeypatch.setattr(BEFORE, "dt", FROZEN)
    new = run_build(tmp_path / "after.xlsx", cache, tmp_path / "after")
    old_build = BEFORE.build_peers_workbook
    monkeypatch.setattr(PW, "build_peers_workbook",
                        lambda *a, into=None, names=None, **kw: old_build(*a, **kw))
    old = run_build(tmp_path / "before.xlsx", cache, tmp_path / "before")
    assert_same_file(old["out"], new["out"])
    before = {p.name: p.read_bytes() for p in (tmp_path / "before").iterdir()}
    after = {p.name: p.read_bytes() for p in (tmp_path / "after").iterdir()}
    assert len(after) > 12 and before == after


# ---- 2. into a workbook with its own Data, Glossary and Run ----

def host():
    wb = Workbook()
    wb.active.title = "Data"
    wb.create_sheet("Glossary")
    wb.create_sheet("Run")
    for title, (a1, b2) in HOST.items():
        wb[title]["A1"], wb[title]["B2"] = a1, b2
    return wb


def recalc(path):
    """Every cell's value after a full recalculation, keyed 'SHEET!A1', as
    test_peers_workbook does it."""
    formulas = pytest.importorskip("formulas", reason="the formulas engine recalculates the workbook")
    sol = formulas.ExcelModel().loads(str(path)).finish().calculate()
    out = {}
    for key, val in sol.items():
        v = getattr(val, "value", val)
        try:
            v = v.item(0) if hasattr(v, "item") else v
        except Exception:                          # noqa: BLE001
            pass
        out[key.split("]")[-1].upper().replace("'", "")] = v
    return out


def same_value(v):
    """A value as compared: numbers as floats (a bool stays a bool), anything
    else (text, an error such as #N/A) as its text."""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return str(v)


@pytest.fixture(scope="module")
def into_and_alone(tmp_path_factory, recent, dl_data, roster):
    """The same build twice, frozen clock: standalone, and into host() under
    NAMES, saved and given na_as_gap over the peer tabs."""
    base = tmp_path_factory.mktemp("into")
    kw = dict(product="Mortgage", delinquency=dq(dl_data))
    alone = build(PW, base / "alone.xlsx", recent, roster, TWO, **kw)
    wb = host()
    info = build(PW, None, recent, roster, TWO, into=wb, names=NAMES, **kw)
    path = base / "into.xlsx"
    wb.save(path)
    PW.na_as_gap(path, info["sheets"])
    return dict(alone=alone, info=info, wb=wb, path=path)


def test_into_writes_the_peer_tabs_after_the_hosts_and_saves_nothing(into_and_alone):
    info, wb = into_and_alone["info"], into_and_alone["wb"]
    assert info["path"] is None
    assert info["sheets"] == [NAMES[t] for t in PW.TABS]
    assert wb.sheetnames == ["Data", "Glossary", "Run"] + info["sheets"]
    assert wb.active.title == "Data"                       # the host's active tab is left as it was
    for title, (a1, b2) in HOST.items():
        ws = wb[title]
        assert (ws["A1"].value, ws["B2"].value, ws.max_row, ws.max_column) == (a1, b2, 2, 2)
    alone = into_and_alone["alone"]
    assert {k: v for k, v in info.items() if k not in ("path", "sheets")} == \
        {k: v for k, v in alone.items() if k not in ("path", "sheets")}


@pytest.fixture(scope="module")
def recalculated(into_and_alone):
    return recalc(into_and_alone["alone"]["path"]), recalc(into_and_alone["path"])


def test_every_peer_cell_recalculates_to_the_standalone_value(into_and_alone, recalculated):
    """Cell for cell, every value equal. The one difference allowed is the
    prose naming a tab, which names the renamed tab (the 'Glossary tab' is
    the 'Peers glossary tab'): the standalone text, renamed, must equal it,
    and those cells are counted so the allowance cannot grow unseen."""
    alone, into = recalculated
    words = PW._Tabs(NAMES).words
    host_values = {same_value(v) for a1, b2 in HOST.values() for v in (a1, b2)}
    compared, renamed, live = 0, 0, 0
    wb = load_workbook(into_and_alone["alone"]["path"])
    for tab in PW.TABS:
        mine = {k.split("!", 1)[1]: v for k, v in alone.items() if k.split("!", 1)[0] == tab.upper()}
        theirs = {k.split("!", 1)[1]: v for k, v in into.items() if k.split("!", 1)[0] == NAMES[tab].upper()}
        assert mine, tab
        assert sorted(mine) == sorted(theirs), tab
        bad = []
        for c in mine:
            want, got = same_value(mine[c]), same_value(theirs[c])
            if want != got:
                if isinstance(mine[c], str) and words(mine[c]) == theirs[c]:
                    renamed += 1
                else:
                    bad.append((c, mine[c], theirs[c]))
        assert not bad, (tab, bad[:5])
        compared += len(mine)
        live += sum(1 for row in wb[tab].iter_rows() for c in row if c.data_type == "f")
        assert not host_values & {same_value(v) for v in theirs.values()}, tab
    assert compared > 10_000 and live > 5_000
    # Pack's banner and note, Peers' banner and note, Delinquency's banner and
    # three notes, Normalisation's note, and the glossary rows that name a tab.
    glossary = sum(1 for _, m, c in PW.PEER_TERMS for x in (m, c) if words(x) != x)
    assert renamed == 9 + glossary, renamed


def test_the_recalculated_peers_are_live_not_blank(recalculated):
    """The comparison above is over real numbers: the Pack resolves best and
    worst, and the Peers composite has values, in both."""
    alone, into = recalculated
    assert alone["PACK!B11"] == into["PEERS PACK!B11"] and isinstance(alone["PACK!B11"], str)
    nums = [v for k, v in into.items() if k.startswith("PEERS!") and isinstance(v, float)]
    assert len(nums) > 1000


def test_no_peer_tab_refers_outside_the_peer_tabs(into_and_alone):
    """In memory and as saved, every formula, validation, conditional format,
    hyperlink, defined name and chart series on a peer tab names peer tabs
    only; and the chart series do name the renamed tabs."""
    sheets = into_and_alone["info"]["sheets"]
    for wb in (into_and_alone["wb"], load_workbook(into_and_alone["path"])):
        assert PW.foreign_refs(wb, sheets) == []
    with zipfile.ZipFile(into_and_alone["path"]) as z:
        charts = [z.read(n).decode() for n in z.namelist() if n.startswith("xl/charts/chart")]
    refs = [f for c in charts for f in re.findall(r"<f>([^<]*)</f>", c)]
    assert refs and all(f.startswith(("'Peers'!", "'Peers balances'!", "'Peers delinquency'!")) for f in refs)
    assert all("dispNaAsBlank" in c for c in charts)


def test_the_prose_names_the_renamed_tabs(into_and_alone):
    """A line telling the reader to look at 'the Glossary tab' would send them
    to the host's: every such line names the peer tab's title."""
    wb = into_and_alone["wb"]
    moved = [t for t in PW.TABS if NAMES[t] != t]
    stale = re.compile(r"\b(%s)\b(?=(?: and [A-Z]\w*)? tabs?\b)|DelinquencyData" % "|".join(moved))
    seen = []
    for title in into_and_alone["info"]["sheets"]:
        for row in wb[title].iter_rows():
            for c in row:
                if isinstance(c.value, str) and " tab" in c.value:
                    seen.append(c.value)
                    assert not stale.search(c.value), (title, c.coordinate, c.value)
    assert any("Peers glossary tab" in v for v in seen) and any("Peers pack tab" in v for v in seen)
    assert any("Peers data tab" in v for v in seen) and any("Peers run tab" in v for v in seen)


def test_na_as_gap_over_the_peer_tabs_leaves_the_hosts_charts_alone(tmp_path, recent, roster):
    wb = host()
    for r in range(1, 6):
        wb["Data"].cell(r, 3, r)
    lc = LineChart()
    lc.add_data(Reference(wb["Data"], min_col=3, min_row=1, max_row=5))
    wb["Data"].add_chart(lc, "E2")
    info = build(PW, None, recent, roster, ("Credit card",), into=wb, names=NAMES)
    wb.save(tmp_path / "x.xlsx")
    PW.na_as_gap(tmp_path / "x.xlsx", info["sheets"])
    with zipfile.ZipFile(tmp_path / "x.xlsx") as z:
        charts = {n: z.read(n).decode() for n in z.namelist() if n.startswith("xl/charts/chart")}
    host_charts = [n for n, c in charts.items() if "'Data'!" in c]
    assert len(host_charts) == 1 and "dispNaAsBlank" not in charts[host_charts[0]]
    assert len(charts) > 1 and all("dispNaAsBlank" in c for n, c in charts.items() if n not in host_charts)
    with pytest.raises(ValueError, match="no tab called Nope"):
        PW.na_as_gap(tmp_path / "x.xlsx", ["Nope"])


def test_peers_build_into_a_workbook_writes_the_series_and_no_peer_file(tmp_path, dl_data):
    cache = dq_cache(tmp_path, dl_data)
    wb = host()
    got = run_build(None, cache, tmp_path / "series", into=wb, names=NAMES)
    assert got["out"] is None and got["info"]["sheets"] == [NAMES[t] for t in PW.TABS]
    assert wb.sheetnames[3:] == got["info"]["sheets"]
    written = [p for p, n, *_ in got["series"] if n]
    assert len(written) > 12 and all(p.exists() for p in written)
    assert sorted(f.name for f in tmp_path.iterdir()) == ["cache", "series"]
    with pytest.raises(ValueError, match="out must be None"):
        run_build(tmp_path / "x.xlsx", cache, tmp_path / "s2", into=host(), names=NAMES)


# ---- refusals ----

@pytest.mark.parametrize("names, why", [
    ({k: v for k, v in NAMES.items() if k != "Run"}, "missing: Run"),
    (dict(NAMES, Extra="Peers extra"), "not a tab: Extra"),
    (dict(NAMES, Run="peers DATA"), "same title"),
    (dict(NAMES, Run="Peers: run"), "must be 1 to 31"),
    (dict(NAMES, Run="P" * 32), "must be 1 to 31"),
    (dict(NAMES, Run="History"), "not History"),
    (["Peers pack"], "names must be None"),
])
def test_bad_names_are_refused(names, why, recent, roster):
    with pytest.raises(ValueError, match=re.escape(why)):
        build(PW, None, recent, roster, ("Credit card",), into=host(), names=names)


def test_a_title_the_host_already_has_is_refused(recent, roster):
    """Without names the peer tabs would be Data, Glossary and Run beside the
    host's own; openpyxl would call them Data1 and the formulas would read
    the host's. Refused, case aside."""
    wb = host()
    with pytest.raises(ValueError, match="already has a tab called Data, Glossary, Run"):
        build(PW, None, recent, roster, ("Credit card",), into=wb)
    wb2 = host()
    wb2.create_sheet("PEERS PACK")
    with pytest.raises(ValueError, match="already has a tab called PEERS PACK"):
        build(PW, None, recent, roster, ("Credit card",), into=wb2, names=NAMES)
    assert wb.sheetnames == ["Data", "Glossary", "Run"] and wb2.sheetnames[-1] == "PEERS PACK"


def test_out_and_into_are_one_or_the_other(tmp_path, recent, roster):
    with pytest.raises(ValueError, match="out must be None"):
        build(PW, tmp_path / "x.xlsx", recent, roster, ("Credit card",), into=host(), names=NAMES)
    with pytest.raises(ValueError, match="out is needed"):
        build(PW, None, recent, roster, ("Credit card",))
    with pytest.raises(ValueError, match="openpyxl Workbook"):
        build(PW, None, recent, roster, ("Credit card",), into="book.xlsx", names=NAMES)
    with pytest.raises(ValueError, match="write-only"):
        build(PW, None, recent, roster, ("Credit card",), into=Workbook(write_only=True), names=NAMES)
    assert not list(tmp_path.iterdir())


def test_a_title_that_needs_quoting_is_quoted():
    assert PW._quoted("Pack") == "Pack" and PW._quoted("Peers pack") == "'Peers pack'"
    assert PW._quoted("A1") == "'A1'" and PW._quoted("R") == "'R'" and PW._quoted("O'Neil") == "'O''Neil'"
    assert PW._quoted("Q4data") == "'Q4data'"


# ---- 3. the check can fail ----

def planted():
    """A peer tab beside a host Data tab, and one reference of each kind on
    it: the builder must never leave any of these."""
    wb = Workbook()
    wb.active.title = "Data"
    ws = wb.create_sheet("Peers pack")
    ws["A1"] = "='Peers pack'!B1+1"                         # its own tab: fine
    ws["A2"] = '="Data!A1 in a string is text"'              # a string: fine
    return wb, ws


@pytest.mark.parametrize("kind", ["formula", "lowercase formula", "quoted formula", "validation",
                                  "conditional format", "hyperlink", "defined name", "chart"])
def test_foreign_refs_finds_each_kind_of_stray_reference(kind):
    wb, ws = planted()
    assert PW.foreign_refs(wb, ["Peers pack"]) == []
    if kind == "formula":
        ws["B3"] = "=SUM(Data!$A$1:$A$4)"
    elif kind == "lowercase formula":
        ws["B3"] = "=data!A1"
    elif kind == "quoted formula":
        ws["B3"] = "='Data'!A1"
    elif kind == "validation":
        dv = DataValidation(type="list", formula1="=Data!$A$1:$A$3")
        ws.add_data_validation(dv)
        dv.add("B3")
    elif kind == "conditional format":
        ws.conditional_formatting.add("B3", FormulaRule(formula=["Data!$A$1>0"]))
    elif kind == "hyperlink":
        ws["B3"] = "see"
        ws["B3"].hyperlink = "#Data!A1"
        ws["B3"].hyperlink.location = "Data!A1"
    elif kind == "defined name":
        ws.defined_names["stray"] = DefinedName("stray", attr_text="Data!$A$1")
    elif kind == "chart":
        lc = LineChart()
        lc.add_data(Reference(wb["Data"], min_col=1, min_row=1, max_row=4))
        ws.add_chart(lc, "D2")
    found = PW.foreign_refs(wb, ["Peers pack"])
    assert len(found) == 1 and re.search("names data", found[0], re.I), found


def test_the_builder_refuses_to_return_with_a_stray_reference(recent, roster, monkeypatch):
    """Were a literal ``Data!`` to creep back into the builder, the build
    stops rather than hand back a workbook that reads the host's Data."""
    real = PW._Tabs.ref
    monkeypatch.setattr(PW._Tabs, "ref", lambda self, tab: "Data!" if tab == "Data" else real(self, tab))
    wb = host()
    with pytest.raises(RuntimeError, match="refers outside the peer tabs.*names Data"):
        build(PW, None, recent, roster, ("Credit card",), into=wb, names=NAMES)
    # and the host is handed back as it was, without half a set of peer tabs
    assert wb.sheetnames == ["Data", "Glossary", "Run"]
    assert [(wb[t]["A1"].value, wb[t]["B2"].value) for t in HOST] == list(HOST.values())
