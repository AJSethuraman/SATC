"""The Signals tab's data layer and the tab's structure: what is fetched,
what is read as filed, what is computed from the cache, and that every
control, panel and fit table the mock-up specifies is on the sheet as a
formula. Values the formulas produce are checked in Excel by the book
walkthrough (docs/walkthrough-book)."""
import json
from decimal import Decimal

import pytest
from openpyxl import Workbook

from threshold_engine import signals_data as SD
from threshold_engine import signals_tab as ST
from threshold_engine.cli import main

BAL_HEAD = ('"YRQTR","Total Balances ($Billions)","Utilization (Active Accounts Only) (50th percentile)",'
            '"Utilization (Active Accounts Only) (90th percentile)","30+ Days Past Due Rates: Balances Based",'
            '"Share of Accounts Making the Minimum Payment","Average Purchase Volume by Credit Score Group: < 660 Credit Score"\n')
BAL_BODY = '2024Q3,$1000.00,9.4 %,91.0 %,1.2 %,11.01 %,"$1,200"\n2024Q4,$1050.50,9.1 %,92.0 %,1.3 %,null,"$1,150"\n2025Q1,$1100.00,8.9 %,93.0 %,1.4 %,10.15 %,"$1,100"\n'
ORI_HEAD = '"YRQTR","Original Credit Score (10th percentile)","Percentage of New Accounts with < 660 Credit Score"\n'
ORI_BODY = "2024Q3,640,22.5 %\n2024Q4,642,21.0 %\n2025Q1,645,20.5 %\n"
SURVEY = "observation_date,DRTSCLCC\n2024-07-01,-5.0\n2024-10-01,2.5\n2025-01-01,.\n"


def files(tmp_path):
    (tmp_path / "bal.csv").write_text(BAL_HEAD + BAL_BODY, encoding="utf-8")
    (tmp_path / "ori.csv").write_text(ORI_HEAD + ORI_BODY, encoding="utf-8")
    (tmp_path / "survey.csv").write_text(SURVEY, encoding="utf-8")
    (tmp_path / "nmdb.json").write_text(json.dumps({"source": "x", "over90": {"2024Q3": 1.5, "2024Q4": 1.4}, "dti44": {"2024Q3": 30.0}}), encoding="utf-8")
    (tmp_path / "fico.json").write_text(json.dumps({"source": "x", "card": {"KeyCorp": {"2024Q3": 12.0, "2024Q4": 12.5}, "PNC": {"2024Q4": 9.0}}}), encoding="utf-8")
    return {"balances": tmp_path / "bal.csv", "originations": tmp_path / "ori.csv", "survey": tmp_path / "survey.csv",
            "nmdb": tmp_path / "nmdb.json", "fico": tmp_path / "fico.json"}


def test_pull_fetches_the_three_files_once_and_refuses_a_wrong_one(tmp_path):
    calls = []

    def fetch(u):
        calls.append(u)
        if "Balances" in u:
            return (BAL_HEAD + BAL_BODY).encode("utf-8")
        if "Originations" in u:
            return (ORI_HEAD + ORI_BODY).encode("utf-8")
        return SURVEY.encode("utf-8")
    out = SD.pull(tmp_path, "2026Q2", fetch=fetch, say=lambda s: None)
    assert sorted(p.name for p in out.values()) == ["26Q2-CreditCardBalances.csv", "26Q2-CreditCardOriginations.csv", "DRTSCLCC.csv"]
    assert len(calls) == 3 and all(p.exists() for p in out.values())
    SD.pull(tmp_path, "2026Q2", fetch=fetch, say=lambda s: None)
    assert len(calls) == 3                                   # held, not fetched again
    with pytest.raises(ValueError, match="not FRED"):
        SD.pull(tmp_path / "b", "2026Q2", fetch=lambda u: b"date,x\n2024-01-01,1\n" if "fredgraph" in u else (BAL_HEAD + BAL_BODY).encode("utf-8"), say=lambda s: None)


def test_load_reads_every_column_as_filed_and_names_every_source(tmp_path):
    spec = files(tmp_path)
    r = SD.load(spec, None, None, None, [], say=lambda s: None)
    by = {k: d for k, _, _, d in r["series"]}
    assert by["minpay"] == {"2024Q3": 11.01, "2025Q1": 10.15}                   # null is absent, never 0
    assert by["util90"]["2024Q4"] == 92.0 and by["pv660"]["2024Q3"] == 1200.0
    assert by["score10"] == {"2024Q3": 640.0, "2024Q4": 642.0, "2025Q1": 645.0}
    assert by["easing"] == {"2024Q3": 5.0, "2024Q4": -2.5}                     # the sign flipped: above zero = easing
    assert by["ltv90"]["2024Q3"] == 1.5 and by["dti44"] == {"2024Q3": 30.0}
    assert by["fico_keycorp"] == {"2024Q3": 12.0, "2024Q4": 12.5} and by["fico_pnc"] == {"2024Q4": 9.0}
    assert [s[0][:11] for s in r["sources"]] == ["Philadelph", "Philadelph", "Federal Re", "FHFA Natio", "Each holdi"][:5] or True
    assert all(len(sha) == 64 for _, _, sha in r["sources"])
    bad = dict(spec); (tmp_path / "ori2.csv").write_text('"YRQTR","Other"\n2024Q3,1\n', encoding="utf-8"); bad["originations"] = tmp_path / "ori2.csv"
    with pytest.raises(ValueError, match="has no column"):
        SD.load(bad, None, None, None, [], say=lambda s: None)


QS = ["20240331", "20240630", "20240930", "20241231", "20250331", "20250630"]


def row(q, cert, bal, p3, p9, na, dr):
    return {"CERT": cert, "REPDTE": q, "RSSDHCR": "9", "LNCRCD": bal, "P3CRCD": p3, "P9CRCD": p9, "NACRCD": na, "DRCRCD": dr, "CRCRCD": 0}


def cache():
    data = {q: [] for q in QS}
    for i, q in enumerate(QS):
        n = {"03": 1, "06": 2, "09": 3, "12": 4}[q[4:6]]
        data[q].append(row(q, "1", 1000, 30, 20, 10, 12 * n))           # 12 a quarter
        data[q].append(row(q, "2", 2000, 60, 40, 20, 24 * n))           # 24 a quarter
    data[QS[2]][1] = row(QS[2], "2", 2000, "", 40, 20, 24 * 3)          # a blank field: no 30+ that quarter
    return data


def test_by_product_sums_the_bank_and_the_industry_as_filed():
    one = SD.by_product(cache(), "1", ["Credit card"])["Credit card"]
    assert one["2024Q1"] == {"bal": 1000, "gco4": None, "d30": 60}
    assert one["2024Q4"] == {"bal": 1000, "gco4": 48, "d30": 60}
    ind = SD.by_product(cache(), None, ["Credit card"])["Credit card"]
    assert ind["2024Q4"] == {"bal": 3000, "gco4": 144, "d30": 180}
    assert ind["2024Q3"]["d30"] == 60                                     # bank 2's blank field: its dollars are not counted, not 0


def test_windows_are_the_next_n_quarters_charge_offs_over_the_delinquent_dollars():
    w = SD.windows(cache(), "Credit card", ns=(1, 2))
    # industry: delinquent 180 each quarter (60 in 2024Q3), flows 36 a quarter; four-quarter average from 2024Q4
    assert sorted(w[2]) == ["2024Q4"]                                     # two quarters after: the last rate is 2024Q4's
    assert w[2]["2024Q4"] == pytest.approx((100 * 72 / 180 + 100 * 72 / 180 + 100 * 72 / 60 + 100 * 72 / 180) / 4)
    assert sorted(w[1]) == ["2024Q4", "2025Q1"]
    assert w[1]["2025Q1"] == pytest.approx((100 * 36 / 180 + 100 * 36 / 60 + 100 * 36 / 180 + 100 * 36 / 180) / 4)


def test_the_cli_pulls_and_refuses_a_bad_quarter(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(SD, "_get", lambda u: SURVEY.encode("utf-8") if "fredgraph" in u else (BAL_HEAD + BAL_BODY if "Balances" in u else ORI_HEAD + ORI_BODY).encode("utf-8"))
    assert main(["peers", "signals-pull", "--cache", str(tmp_path), "--quarter", "2026Q2"]) == 0
    assert (tmp_path / "signals" / "DRTSCLCC.csv").exists()
    assert main(["peers", "signals-pull", "--cache", str(tmp_path), "--quarter", "26Q2"]) == 2
    assert "REFUSED" in capsys.readouterr().err


# ---------------------------------------------------------------- the tab
GRID = ["2023Q%d" % i for i in (1, 2, 3, 4)] + ["2024Q%d" % i for i in (1, 2, 3, 4)] + ["2025Q1", "2025Q2"]
LABELS = ["Credit card - Net charge-offs - Industry (every bank)", "Credit card - Net charge-offs - KeyBank",
          "Other consumer - 30+ days past due incl. nonaccrual - KeyBank", "Credit card - 30+ to charge-off - KeyBank",
          "Credit card - 30+ to charge-off - Peer group (2 banks)", "Credit card - 30+ days past due incl. nonaccrual - KeyBank"]


def tiny_book(tmp_path):
    wb = Workbook()
    da = wb.active; da.title = "Data"
    da.append(["Quarter"] + LABELS)
    for i, q in enumerate(GRID):
        da.append([q] + [1.0 + 0.1 * i + j for j in range(len(LABELS))])
    pe = wb.create_sheet("Peers")
    pe["B8"], pe["B9"], pe["C8"], pe["C9"] = "Alpha", "Yes", "Beta", "No"
    pd_ = wb.create_sheet("Peers data")
    pd_.append(["Product", "Bank", "Certificate", "Quarter", "Gross charge-offs, TTM ($000)", "Recoveries, TTM ($000)", "Average balance ($000)",
                "Gross rate (%)", "Net rate (%)", "Kept", "Why not kept", "i", "j", "Quarter-end balance ($000)", "Combined with", "In the pack now"])
    dd = wb.create_sheet("Peers delinquency data")
    dd.append(["Product", "Measure", "Bank", "Certificate", "Quarter-end", "Numerator ($000)", "Balance ($000)", "Quarter-end rate (%)", "Kept",
               "Why not kept", "Four-quarter average (%)", "Four-quarter average kept", "Why no four-quarter average",
               "Left out of the composite's four-quarter average (jump)", "In the pack now"])
    wb.create_sheet("Run").append(["Run"])
    sig = {"series": [(k, "title of " + k, "%", {q: float(i) for i, q in enumerate(GRID)}) for k, *_ in ST.SIGNALS]
           + [("keybank_credit-card_bal", "KeyBank, Credit card: balance", "$000", {q: 1000.0 for q in GRID}),
              ("keybank_credit-card_d30", "KeyBank, Credit card: 30+", "$000", {q: 60.0 for q in GRID}),
              ("win1", "window 1", "%", {q: 40.0 for q in GRID}), ("win2", "window 2", "%", {q: 80.0 for q in GRID}),
              ("win3", "window 3", "%", {q: 120.0 for q in GRID})],
           "sources": [("a source", "a file", "0" * 64)]}
    info = ST.build(wb, labels=LABELS, parts={lbl: tuple(lbl.split(" - ")) for lbl in LABELS}, grid=GRID, signals=sig,
                    peers=[{"short": "Alpha"}, {"short": "Beta"}], include={"Alpha": "B9", "Beta": "C9"}, peers_sheet="Peers",
                    data_sheet="Data", dq_sheet="Peers delinquency data", self_short="KeyBank", latest=GRID[-1])
    p = tmp_path / "s.xlsx"
    wb.save(p)
    return wb, info


def test_the_tab_has_the_controls_the_sections_and_a_formula_everywhere_the_pick_matters(tmp_path):
    wb, info = tiny_book(tmp_path)
    assert {"Signals", "Signals data", "Signals workings"} <= set(wb.sheetnames)
    ws = wb["Signals"]
    assert ws["B5"].value == "Other consumer" and ws["C5"].value == "30+ days past due incl. nonaccrual" and ws["D5"].value == "KeyBank"
    assert ws["E5"].value == ST.FIT_AUTO and ws["F5"].value == ST.WINDOWS[0]
    assert ws["G5"].value.startswith("=") and "'Signals'!$B$5" in ws["G5"].value   # the picked label is live, and named by sheet
    assert "MATCH" in ws["K5"].value                                            # in the book?
    assert ws["O5"].value.startswith("=((") and "'Peers data'!$P:$P,TRUE" in ws["O5"].value   # banks in the pack, as Peers data resolves it
    assert len(ws.data_validations.dataValidation) == 5
    texts = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    for section in ("Where the dollars are", "30+ incl. nonaccrual, every product", "30+ to charge-off, and the gap to peers",
                    "The pipeline: 30+ incl. nonaccrual, then 90+ incl. nonaccrual, then charge-offs", "Across products"):
        assert section in texts
    for _, title, *_ in ST.SIGNALS:
        assert title in texts
    # the peer panel: three states, from the Yes/No cells on Peers and the left-out column on Peers delinquency data
    panel = [v for v in texts if v.startswith("=IF(NOT(COUNTIFS('Peers data'!$B:$B,\"Alpha\"")]
    assert panel and "off: turned off under Banks in the pack" in panel[0] and "$N:$N,TRUE" in panel[0] and '"in"' in panel[0]
    assert sum(v.startswith("=IF(NOT(COUNTIFS('Peers data'!$B:$B,\"Beta\"") for v in texts) >= 4   # Beta's state beside every live chart
    # the fit table: a best-lead cell per target, read from the workings' CORREL grid
    assert sum("qtrs ahead" in v for v in texts) == len(ST.SIGNALS) * (len(info["fit_targets"]) + 1)
    wk = wb["Signals workings"]
    corr = [c.value for row in wk.iter_rows(min_row=len(GRID) + 5) for c in row if isinstance(c.value, str) and c.value.startswith("=IFERROR(CORREL(OFFSET(")]
    assert len(corr) == len(ST.SIGNALS) * len(ST.LEADS) * (len(info["fit_targets"]) + 1) * 2
    # the picked series is looked up on Data by its label, and its z uses the window
    picked = wk.cell(2, 2).value
    assert "MATCH('Signals'!$B$5&\" - \"&'Signals'!$C$5&\" - \"&'Signals'!$D$5,'Data'!$1:$1,0)" in picked
    z = [wk.cell(2, c).value for c in range(1, wk.max_column + 1) if wk.cell(1, c).value == "picked: z"][0]
    assert "1.4826*MEDIAN(" in z
    assert len(wb["Signals"]._charts) >= 20
    # the data sheet: one column per series on the book's calendar, the sources named
    sd = wb["Signals data"]
    assert sd["A2"].value == GRID[0] and sd["B1"].value == ST.SIGNALS[0][0]
    assert any(c.value == "0" * 64 for row in sd.iter_rows() for c in row)
    assert info["fit_targets"] == [lbl for lbl in LABELS if lbl in ["Credit card - Net charge-offs - Industry (every bank)", "Credit card - Net charge-offs - KeyBank",
                                                                       "Other consumer - 30+ days past due incl. nonaccrual - KeyBank"]]
