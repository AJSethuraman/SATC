"""Compute every figure in the comparability tie-out, and its verdict.

    python collect.py --sources SRC --cache CACHE --series SERIES \
        --roster ../../../../config/peers.json --engine ../../../../src --out ../figures.json

SRC     what fetch_sources.py downloaded (filings, API responses, 10-K, QBP)
CACHE   the tool's own cache, written by `threshold-engine peers pull`
SERIES  the tool's own series CSVs, written by `threshold-engine peers build`
ENGINE  threshold-engine/src, so the peer median uses the tool's bank_book

Every comparison is written as a figure: what it is, the 'ours' value and
where it was read, the 'source' value and where it was read, the difference,
the tolerance allowed and why, and the verdict read off those numbers.
Verdicts: TIED, DIFFERS, COULD NOT. Nothing is written ahead of its numbers.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import sources as S  # noqa: E402

FIG = []


def fig(gap, what, ours, ours_from, src, src_from, units, tol=0, tol_why="exact", note=None,
        verdict=None, diff=None):
    """Record one comparison. The verdict is computed from the two numbers
    unless one side does not exist (COULD NOT), when it must be given with its
    obstacle in ``note``."""
    if verdict is None:
        diff = ours - src
        verdict = "TIED" if abs(diff) <= tol + 1e-9 else "DIFFERS"
    FIG.append(dict(id="G%d-%02d" % (gap, 1 + sum(1 for f in FIG if f["gap"] == gap)), gap=gap,
                    what=what, ours=ours, ours_from=ours_from, source=src, source_from=src_from,
                    units=units, diff=diff, tolerance=tol, tolerance_why=tol_why,
                    verdict=verdict, note=note))
    return FIG[-1]


def main():
    ap = argparse.ArgumentParser()
    for a in ("--sources", "--cache", "--series", "--roster", "--engine", "--out"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    src, out = Path(a.sources), {}
    sys.path.insert(0, a.engine)
    from threshold_engine.peers import books  # the tool's own code, unchanged

    roster = json.load(open(a.roster, encoding="utf-8"))["banks"]
    short = {b["cert"]: b["short"] for b in roster}
    peers = [b["cert"] for b in roster if b["group"] == "peer"]
    data = S.cache(a.cache)
    q26 = data["20260630"]
    F26 = {c: S.filing(src, c, "06302026") for c in short}
    gty, _ = S.api_by_cert(src / "fdic-2026q2-guaranteed.json")
    api_rows, api_meta = S.api_rows(src / "fdic-2026q2-guaranteed.json")
    qbp = S.qbp_blocks(src / "qbp-2026q2-time-series.xlsx",
                       {"Credit Cards", "Home Equity Lines of Credit",
                        "Closed-End First Lien 1-4 Family Residential Mortgages",
                        'Rebooked "GNMA Loans"', "Other Loans to Individuals", "Auto Loans"})
    CALL = "KeyBank Call Report (FFIEC 031) 30 Jun 2026"

    # ==================================================================== GAP 1
    kb = F26["17534"]
    for code, field, label in (("K037", "P9GTYPAR", "RC-N 11 col B, wholly or partially guaranteed, 90+ accruing"),
                               ("K040", "P9GTY", "RC-N 11.a col B, guaranteed portion (excl. rebooked GNMA), 90+"),
                               ("K043", "P9GTYGNM", "RC-N 11.b col B, rebooked GNMA loans, 90+")):
        v, full = S.line(kb, code)
        fig(1, "KeyBank " + label, gty["17534"][field], "FDIC API %s (the tool does not pull this field)" % field,
            v, "%s, %s (XBRL; same value on report page 45)" % (CALL, full), "$000")
    v, full = S.line(kb, "C237")
    fig(1, "KeyBank first-lien mortgage 90+ accruing, RC-N 1.c.(2)(a) col B", q26["17534"]["P9RERSFM"],
        "tool cache q20260630.json, P9RERSFM", v, "%s, %s" % (CALL, full), "$000")
    for c in peers:
        f = F26[c]
        v, full = S.line(f, "K043")
        fig(1, "%s rebooked GNMA 90+ (RC-N 11.b col B)" % short[c], gty[c]["P9GTYGNM"], "FDIC API P9GTYGNM",
            v, "Call Report 30 Jun 2026, %s" % full, "$000")
        v, full = S.line(f, "C237")
        fig(1, "%s first-lien mortgage 90+ accruing" % short[c], q26[c]["P9RERSFM"], "tool cache, P9RERSFM",
            v, "Call Report 30 Jun 2026, %s" % full, "$000")
    ind_gnma = sum(r.get("P9GTYGNM") or 0 for r in api_rows)
    qg = qbp['Rebooked "GNMA Loans"']
    fig(1, "Industry rebooked GNMA loans 90+ days past due, 2026Q2", ind_gnma / 1000,
        "FDIC API P9GTYGNM summed over %d filers ($000 / 1,000)" % len(api_rows),
        qg["rows"]["90 days or more past due"]["2026Q2"],
        "FDIC QBP time series, sheet Loan Performance, block 'Rebooked GNMA Loans' (row %d), 2026Q2" % (qg["excel_row"] + 2),
        "$m", tol=0.0005, tol_why="the spreadsheet states $m to three decimals")
    k10 = S.htm_text(src / "keycorp-10k-2025.htm")
    q10 = S.htm_text(src / "keycorp-10q-2026q2.htm")
    pat = r"Includes balances of \$ ?(\d+) million in Commercial mortgage and \$ ?(\d+) million i ?n Real estate - residential mortgage associated with loans sold to GNMA"
    import re
    g10k = [tuple(map(int, m.groups())) for m in re.finditer(pat, k10)]
    g10q = [tuple(map(int, m.groups())) for m in re.finditer(pat, q10)]
    kbd, _ = S.line(S.filing(src, "17534", "12312025"), "K043")
    fig(1, "KeyBank rebooked GNMA 90+ at 31 Dec 2025: filing against KeyCorp 10-K", kbd / 1000,
        "KeyBank Call Report 31 Dec 2025, RCFDK043 ($000 / 1,000)", sum(g10k[0]),
        "KeyCorp 10-K 2025, Note 4 aging table footnote (c): $%d m commercial mortgage + $%d m residential" % g10k[0],
        "$m", tol=1.0, tol_why="two figures each rounded to $1m")
    kbj, _ = S.line(kb, "K043")
    fig(1, "KeyBank rebooked GNMA 90+ at 30 Jun 2026: filing against KeyCorp 10-Q", kbj / 1000,
        "KeyBank Call Report 30 Jun 2026, RCFDK043 ($000 / 1,000)", sum(g10q[0]),
        "KeyCorp 10-Q Q2 2026, Note 4 aging table footnote (c): $%d m commercial mortgage + $%d m residential" % g10q[0],
        "$m", tol=1.0, tol_why="two figures each rounded to $1m",
        note="Not explained here. Item 11.b counts GNMA loans 'repurchased or eligible for repurchase'; the 10-Q footnote counts loans 'where Key has the right but not the obligation to repurchase'. Loans already bought back would be in the first and not the second. That is a reading of the two definitions, not a reconciliation.")
    size1 = []
    for b in roster:
        f = F26[b["cert"]]
        g = lambda k: S.line(f, k)[0] or 0
        size1.append(dict(bank=b["short"], first_90=g("C237"), first_30=g("C236"), first_na=g("C229"),
                          gty_90=g("K037"), gnma_90=g("K043"), part_90=g("K040"), gnma_30=g("K042"),
                          other_90=g("K217")))
    hist = {q: (qg["rows"]["90 days or more past due"][q],
                qbp["Closed-End First Lien 1-4 Family Residential Mortgages"]["rows"]["90 days or more past due"][q])
            for q in ("2010Q4", "2012Q4", "2014Q4", "2016Q4", "2018Q4", "2020Q4", "2022Q4", "2024Q4", "2026Q2")}
    out["gap1"] = dict(banks=size1, industry_gnma_90=ind_gnma, industry_first_90=sum(r.get("P9RERSFM") or 0 for r in api_rows),
                       industry_first_na=sum(r.get("NARERSFM") or 0 for r in api_rows),
                       industry_hist=hist, keycorp_10q_gnma=g10q[0], keycorp_10k_gnma=g10k[0],
                       api_index=api_meta.get("index"))

    # ==================================================================== GAP 2
    for c in short:
        f = F26[c]
        for code, field, lab in (("B577", "NACRCD", "card nonaccrual (RC-N 5.a col C)"),
                                 ("B576", "P9CRCD", "card 90+ accruing (RC-N 5.a col B)")):
            v, full = S.line(f, code)
            fig(2, "%s %s" % (short[c], lab), q26[c][field], "tool cache q20260630.json, %s" % field,
                v, "Call Report 30 Jun 2026, %s" % full, "$000")
    for c in ("57957", "3511"):
        f = S.filing(src, c, "12312015")
        for code, field, lab in (("B577", "NACRCD", "card nonaccrual"), ("B576", "P9CRCD", "card 90+ accruing")):
            v, full = S.line(f, code)
            fig(2, "%s %s, 31 Dec 2015" % (short[c], lab), data["20151231"][c][field],
                "tool cache q20151231.json, %s" % field, v, "Call Report 31 Dec 2015, %s" % full, "$000")
    size2, hist2 = [], []
    qs = sorted(data)
    for b in roster:
        c = b["cert"]
        r = q26[c]
        size2.append(dict(bank=b["short"], bal=r["LNCRCD"], na=r["NACRCD"], p9=r["P9CRCD"], p3=r["P3CRCD"]))
        filed = na = p9 = p9zero = 0
        first_na = None
        for q in qs:
            x = data[q].get(c)
            if not x or not x.get("LNCRCD"):
                continue
            filed += 1
            if x.get("NACRCD"):
                na += 1
                first_na = first_na or q
            if x.get("P9CRCD"):
                p9 += 1
            else:
                p9zero += 1
        hist2.append(dict(bank=b["short"], quarters=filed, na_quarters=na, p9_zero_quarters=p9zero))
    share = {}
    for q in ("20090630", "20140630", "20190630", "20260630"):
        rows = data[q].values()
        N = sum(x.get("NACRCD") or 0 for x in rows)
        P = sum(x.get("P9CRCD") or 0 for x in rows)
        L = sum(x.get("LNCRCD") or 0 for x in rows)
        share[q] = dict(na_pct=100 * N / L, p9_pct=100 * P / L, na_share=100 * N / (N + P))
    out["gap2"] = dict(banks=size2, history=hist2, industry=share, first_quarter=qs[0], last_quarter=qs[-1])

    # ==================================================================== GAP 3
    qc = qbp["Credit Cards"]
    for d, L in (("20091231", "2009Q4"), ("20100331", "2010Q1")):
        s = sum((x.get("LNCRCD") or 0) for x in data[d].values())
        fig(3, "Industry credit card balances, %s" % L, s / 1000, "tool cache q%s.json, LNCRCD summed ($000 / 1,000)" % d,
            qc["rows"]["Total outstanding"][L], "FDIC QBP time series, Credit Cards, Total outstanding, %s" % L,
            "$m", tol=0.0005, tol_why="the spreadsheet states $m to three decimals")
    rev = {}
    for d in ("2009q4", "2010q1"):
        rows, _ = S.api_rows(src / ("fdic-%s-revolving.json" % d))
        rev[d] = sum((x.get("LNCRCD") or 0) + (x.get("LNCONRP") or 0) for x in rows if x.get("BKCLASS") in ("N", "NM", "SM"))
    h8 = S.htm_text(src / "fed-h8-2010-04-16.html")
    m = S.find(h8, r"consumer loans, credit cards and other revolving plans, \$([\d.]+) \(instead of \$([\d.]+)\)", "H.8")
    fig(3, "Commercial banks' cards and other revolving plans: change 2009Q4 to 2010Q1 against the amount consolidated",
        (rev["2010q1"] - rev["2009q4"]) / 1e6, "FDIC API, BKCLASS N/NM/SM, LNCRCD + LNCONRP, 2010Q1 less 2009Q4 ($000 / 1e6)",
        float(m.group(1)), "Federal Reserve H.8, 16 Apr 2010, Notes on the Data (revised figure)", "$bn",
        tol=0, tol_why="different basis: see note",
        note="Not the same quantity. The H.8 counts only what was consolidated, in the week ending 31 Mar 2010; the quarter's change also nets off that quarter's charge-offs (card net charge-offs alone were $18.7bn, QBP) and paydowns. The two agree in scale, not to the dollar.")
    four = {"23360", "33318", "23702", "33954"}
    grp = {}
    for name, sel in (("four", lambda c: c in four), ("rest", lambda c: c not in four)):
        rowsq = {}
        for d in ("20091231", "20100331"):
            b_ = n_ = 0
            for c, x in data[d].items():
                if not sel(c):
                    continue
                if d.endswith("0331"):
                    fl = (x.get("DRCRCD") or 0) - (x.get("CRCRCD") or 0)
                else:
                    p = data["20090930"].get(c)
                    if p is None:
                        continue
                    fl = ((x.get("DRCRCD") or 0) - (x.get("CRCRCD") or 0)) - ((p.get("DRCRCD") or 0) - (p.get("CRCRCD") or 0))
                n_ += fl
                b_ += x.get("LNCRCD") or 0
            rowsq[d] = dict(bal=b_, nco=n_, rate=400 * n_ / b_)
        grp[name] = rowsq
    r4, rr = grp["four"]["20100331"]["rate"], grp["rest"]["20100331"]["rate"]
    w0 = (grp["four"]["20091231"]["bal"], grp["rest"]["20091231"]["bal"])
    w1 = (grp["four"]["20100331"]["bal"], grp["rest"]["20100331"]["bal"])
    mix0 = (w0[0] * r4 + w0[1] * rr) / sum(w0)
    mix1 = (w1[0] * r4 + w1[1] * rr) / sum(w1)
    moves = []
    for b in roster:
        a0 = (data["20091231"].get(b["cert"]) or {}).get("LNCRCD")
        a1 = (data["20100331"].get(b["cert"]) or {}).get("LNCRCD")
        moves.append(dict(bank=b["short"], q4=a0, q1=a1))
    rise = {c: ((data["20100331"].get(c) or {}).get("LNCRCD") or 0) - ((data["20091231"].get(c) or {}).get("LNCRCD") or 0)
            for c in set(data["20100331"]) | set(data["20091231"])}
    four_share = sum(rise[c] for c in four) / sum(rise.values())
    ind_s = S.series(Path(a.series) / "credit-card_industry_net.csv")
    out["gap3"] = dict(four_share=four_share, groups=grp, mix_before=mix0, mix_after=mix1, mix_effect=mix1 - mix0, moves=moves,
                       h8=float(m.group(1)), rev_change=rev["2010q1"] - rev["2009q4"],
                       qbp=dict((q, dict(bal=qc["rows"]["Total outstanding"][q], nco=qc["rows"]["Net charge-offs"][q],
                                         rate=qc["rows"]["Net charge-off rate"][q]))
                                for q in ("2009Q3", "2009Q4", "2010Q1", "2010Q2", "2010Q3", "2010Q4")),
                       tool_ttm={q: ind_s.get(q) for q in ("2009Q3", "2009Q4", "2010Q1", "2010Q2", "2010Q3", "2010Q4", "2011Q1")})

    # ==================================================================== GAP 4
    pdf_va = "FDIC QBP 2026 Q2, Table V-A, All Insured Institutions, June 30, 2026"
    q2, q1, q0 = data["20260630"], data["20260331"], data["20251231"]
    tot = lambda d, f: sum((x.get(f) or 0) for x in d.values())
    L = tot(q2, "LNCRCD")
    asset_rows, _ = S.api_rows(src / "fdic-2026q2-asset.json")
    fig(4, "Industry credit card loans outstanding", L / 1e6, "tool cache q20260630.json, LNCRCD summed ($000 / 1e6)",
        1189.6, pdf_va + ", Loans outstanding, Credit card loans", "$bn", tol=0.05, tol_why="Table V-A states $bn to one decimal")
    ytd = tot(q2, "DRCRCD") - tot(q2, "CRCRCD")
    avg3 = (tot(q0, "LNCRCD") + tot(q1, "LNCRCD") + L) / 3
    fig(4, "Industry card net charge-offs, YTD annualised, over the QBP's average (Dec, Mar, Jun quarter-ends)",
        200 * ytd / avg3, "tool cache: (DRCRCD - CRCRCD) summed, x2, over the mean of three quarter-end sums",
        4.00, pdf_va + ", Percent of Loans Charged-Off (net, YTD), Credit card loans", "%", tol=0.005,
        tol_why="Table V-A states two decimals; average as the QBP's notes define it")
    for lab, num, qv in (("30-89 days past due", ["P3CRCD"], 1.37), ("noncurrent (90+ and nonaccrual)", ["P9CRCD", "NACRCD"], 1.44),
                         ("past due and nonaccrual (30+)", ["P3CRCD", "P9CRCD", "NACRCD"], 2.81)):
        fig(4, "Industry card loans %s, %% of loans" % lab, 100 * sum(tot(q2, f) for f in num) / L,
            "tool cache: %s summed over LNCRCD summed" % " + ".join(num), qv, pdf_va + ", Credit card loans",
            "%", tol=0.005, tol_why="two decimals")
    fig(4, "Industry home equity lines outstanding", tot(q2, "LNRELOC") / 1e6, "tool cache, LNRELOC summed",
        307.5, pdf_va + ", Loans outstanding, Home equity loans", "$bn", tol=0.05, tol_why="one decimal")
    o14 = tot(q2, "LNRERSFM") + sum(x.get("LNRERSF2") or 0 for x in asset_rows)
    fig(4, "Industry closed-end 1-4 family (first + junior liens) outstanding", o14 / 1e6,
        "tool cache LNRERSFM + FDIC API LNRERSF2, summed", 2648.8, pdf_va + ", Other 1-4 family residential",
        "$bn", tol=0.05, tol_why="one decimal")
    oli = tot(q2, "LNAUTO") + tot(q2, "LNCONOTH") + sum(x.get("LNCONRP") or 0 for x in asset_rows)
    fig(4, "Industry other loans to individuals (auto + other consumer + other revolving)", oli / 1e6,
        "tool cache LNAUTO + LNCONOTH + FDIC API LNCONRP, summed", 905.4, pdf_va + ", Other loans to individuals",
        "$bn", tol=0.05, tol_why="one decimal")
    qkeys = sorted(qc["rows"]["Net charge-offs"])
    blocks = {"credit-card": qbp["Credit Cards"], "mortgage": qbp["Closed-End First Lien 1-4 Family Residential Mortgages"],
              "home-equity": qbp["Home Equity Lines of Credit"], "auto": qbp["Auto Loans"]}

    def qbp_ttm(blk, at):
        i = qkeys.index(at)
        w = qkeys[i - 3:i + 1]
        vals = [(blk["rows"]["Net charge-offs"][x], blk["rows"]["Total outstanding"][x]) for x in w]
        if not all(isinstance(n, (int, float)) and isinstance(b, (int, float)) for n, b in vals):
            return None
        return 100 * sum(n for n, _ in vals) / (sum(b for _, b in vals) / 4)
    hist4 = {}
    for slug, blk in blocks.items():
        ind = S.series(Path(a.series) / ("%s_industry_net.csv" % slug))
        fig(4, "Tool's industry TTM net charge-off rate, %s, 2026Q2" % slug, ind["2026Q2"],
            "tool series %s_industry_net.csv, 2026-06-30" % slug, qbp_ttm(blk, "2026Q2"),
            "built from the QBP time series alone: 4 quarters of Net charge-offs / mean of 4 Total outstanding", "%",
            tol=0.001, tol_why="the QBP states $m to three decimals")
        cmp_ = {q: (v, qbp_ttm(blk, q)) for q, v in ind.items() if qbp_ttm(blk, q) is not None}
        off = {q: v for q, v in cmp_.items() if abs(v[0] - v[1]) >= 0.01}
        hist4[slug] = dict(n=len(cmp_), off=off)
        worst = max(cmp_.items(), key=lambda kv: abs(kv[1][0] - kv[1][1]))
        fig(4, "Tool's industry TTM net rate, %s, every quarter %s to %s (largest gap shown)" % (slug, min(cmp_), max(cmp_)),
            worst[1][0], "tool series %s_industry_net.csv, %s" % (slug, worst[0]), worst[1][1],
            "QBP-built TTM, %s; %d of %d quarters differ by 0.01 pts or more" % (worst[0], len(off), len(cmp_)),
            "%", tol=0.01, tol_why="0.01 pts, the precision a threshold is set at")
    Fk = {d: S.filing(src, "17534", d) for d in ("06302025", "09302025", "12312025", "03312026", "06302026")}
    g = Fk["06302026"]["RIADB514"] + Fk["12312025"]["RIADB514"] - Fk["06302025"]["RIADB514"]
    r_ = Fk["06302026"]["RIADB515"] + Fk["12312025"]["RIADB515"] - Fk["06302025"]["RIADB515"]
    bals = [S.line(Fk[d], "B538")[0] for d in ("09302025", "12312025", "03312026", "06302026")]
    kbs = S.series(Path(a.series) / "credit-card_keybank_net.csv")
    fig(4, "KeyBank card TTM net charge-off rate, 2026Q2 (a per-bank rate, the median's input)", kbs["2026Q2"],
        "tool series credit-card_keybank_net.csv, 2026-06-30",
        100 * (g - r_) / (sum(bals) / 4),
        "five KeyBank Call Reports: RI-B 5.a YTD (Jun26 + Dec25 - Jun25), over RC-C 6.a at Sep25, Dec25, Mar26, Jun26",
        "%", tol=1e-6, tol_why="same arithmetic, filed inputs")
    fig(4, "Peer median of TTM net charge-off rates (any product)", None, "computed here with the tool's bank_book",
        None, "none", "%", verdict="COULD NOT",
        note="No one publishes a median of this 15-bank roster, so there is nothing independent to tie it to. Attacked once: each input rate is a per-bank TTM rate, and one of them (KeyBank card, above) was rebuilt from five filings and ties. The median of rates that tie is arithmetic on them; it is shown, not tied.")
    gap4 = {}
    for prod, slug in (("Credit card", "credit-card"), ("Mortgage", "mortgage"), ("Home equity", "home-equity"),
                       ("Other consumer", "other-consumer"), ("Auto", "auto")):
        bk = {c: books.bank_book(data_list(data), c, prod, 0.25, 1000000) for c in peers}
        med = {}
        for c, rows in bk.items():
            for r in rows:
                if r["kept"]:
                    med.setdefault(r["quarter"], []).append(r["net_rate"])
        meds = {q: (statistics.median(v), len(v)) for q, v in med.items() if len(v) >= 5}
        ind = S.series(Path(a.series) / ("%s_industry_net.csv" % slug))
        pack = S.series(Path(a.series) / ("%s_pack-composite_net.csv" % slug))
        kbn = S.series(Path(a.series) / ("%s_keybank_net.csv" % slug))
        common = [q for q in sorted(meds) if q in ind]
        diffs = [ind[q] - meds[q][0] for q in common]
        ratios = [ind[q] / meds[q][0] for q in common if meds[q][0] > 0]
        rows = {q: dict(ind=ind.get(q), med=meds[q][0], n=meds[q][1], pack=pack.get(q), kb=kbn.get(q))
                for q in ("2009Q4", "2010Q4", "2014Q4", "2019Q4", "2021Q4", "2024Q4", "2026Q2") if q in meds and q in ind}
        gap4[prod] = dict(first=common[0], last=common[-1], n=len(common), mean=statistics.mean(diffs),
                          min=min(diffs), max=max(diffs), ratio_median=statistics.median(ratios),
                          ratio_min=min(ratios), ratio_max=max(ratios), rows=rows)
    out["gap4"] = dict(products=gap4, qbp_hist={k: dict(n=v["n"], off=v["off"]) for k, v in hist4.items()},
                       qbp_count=4238, api_count=len(asset_rows))

    # ==================================================================== GAP 5
    snap = data
    ordered = sorted(snap)

    def ind_flow(i, field):
        """The tool's industry() rule: Q1 as filed; later quarters, each bank
        present in both quarters, year-to-date less the quarter before."""
        d = ordered[i]
        cur = snap[d]
        if d[4:6] == "03":
            return sum((x.get(field) or 0) for x in cur.values())
        prev = snap[ordered[i - 1]]
        return sum(((cur[c].get(field) or 0) - (prev[c].get(field) or 0)) for c in cur if c in prev)
    inst, _ = S.api_by_cert(src / "fdic-institutions-card-charters.json")
    events = [("20061231", ["27595", "26211"]), ("20100630", ["58496"]), ("20110930", ["23360"]),
              ("20141231", ["33318"]), ("20190630", ["23702"]), ("20221231", ["33954"])]
    ev_out = []
    for d, gone in events:
        i = ordered.index(d)
        L_ = "%sQ%d" % (d[:4], (int(d[4:6]) - 1) // 3 + 1)
        tool = ind_flow(i, "DRCRCD") / 1000
        q_ = qc["rows"]["Total charge-offs"][L_]
        absorbed = sum((snap[ordered[i - 1]][c].get("DRCRCD") or 0) for c in gone) / 1000
        fig(5, "Industry card gross charge-offs in %s: the tool's quarterly flow against the QBP" % L_, tool,
            "tool cache, by industry()'s rule (each bank's YTD less its previous quarter's)", q_,
            "FDIC QBP time series, Credit Cards, Total charge-offs, %s" % L_, "$m", tol=1.0, tol_why="$1m",
            note="Difference %.1f; the absorbed charter(s) %s filed year-to-date card charge-offs of %.1f at their last report." % (
                tool - q_, ", ".join("%s (%s)" % (inst.get(c, {}).get("NAME", c), c) for c in gone), absorbed))
        ev_out.append(dict(q=L_, tool=tool, qbp=q_, absorbed=absorbed,
                           names=[inst.get(c, {}).get("NAME", c) for c in gone]))
    c_jun, c_sep, csd = S.filing(src, "7213", "06302011"), S.filing(src, "7213", "09302011"), S.filing(src, "23360", "06302011")
    tool_c = (snap["20110930"]["7213"]["DRCRCD"] - snap["20110630"]["7213"]["DRCRCD"])
    fig(5, "Citibank NA card charge-offs, 2011Q3, as the tool differences them", tool_c,
        "tool cache: q20110930 DRCRCD - q20110630 DRCRCD, cert 7213",
        c_sep["RIADB514"] - c_jun["RIADB514"], "Citibank NA Call Reports: RI-B 5.a RIADB514, 30 Sep 2011 less 30 Jun 2011",
        "$000", note="The tool reads the filings faithfully. The filed September YTD (%s) includes Citibank (South Dakota)'s first-half charge-offs (%s, its last filing), because a merger under common control reports income 'as though the entities had combined at the beginning of the year' (Call Report glossary, Business Combinations)." % (
            format(c_sep["RIADB514"], ","), format(csd["RIADB514"], ",")))
    fig(5, "Citibank (South Dakota) card charge-offs YTD at its last filing, 30 Jun 2011", snap["20110630"]["23360"]["DRCRCD"],
        "tool cache q20110630.json, cert 23360, DRCRCD", csd["RIADB514"], "Citibank (South Dakota) Call Report 30 Jun 2011, RIADB514", "$000")
    wbook = books.bank_book(data_list(data), "3511", "Credit card", 0.25, 1000000)
    wcs_q1 = (data["20100331"]["58496"]["DRCRCD"] or 0) - (data["20100331"]["58496"]["CRCRCD"] or 0)
    wells = []
    for r in wbook:
        if r["quarter"] in ("2010Q2", "2010Q3", "2010Q4", "2011Q1") and r["kept"]:
            wells.append(dict(q=r["quarter"], net=r["net_rate"], without=100 * ((r["gross"] - r["recoveries"]) - wcs_q1) / r["avg_balance"]))
    acq = acquisitions(src, snap, short)
    out["gap5"] = dict(wells=wells, wcs_q1=wcs_q1, events=ev_out, acquisitions=acq, qbp_hist={k: dict(n=v["n"], off=v["off"]) for k, v in hist4.items()},
                       citi=dict(jun=c_jun["RIADB514"], sep=c_sep["RIADB514"], csd=csd["RIADB514"]))

    # ==================================================================== GAP 6
    fd = S.filing(src, "17534", "12312025")
    kc = data["20251231"]["17534"]
    for field, code, lab in (("LNCRCD", "B538", "card, RC-C 6.a"), ("LNCONOTH", "K207", "other consumer, RC-C 6.d"),
                             ("LNAUTO", "K137", "auto, RC-C 6.c"), ("LNRERSFM", "5367", "first liens, RC-C 1.c.(2)(a)"),
                             ("LNRELOC", "1797", "home equity lines, RC-C 1.c.(1)")):
        v, full = S.line(fd, code)
        fig(6, "KeyBank %s, 31 Dec 2025" % lab, kc[field], "tool cache q20251231.json, %s" % field, v,
            "KeyBank Call Report 31 Dec 2025, %s" % full, "$000")
    k9 = S.find(k10, r"Figure 9\. Composition of Loans .{0,900}?Total consumer loans [\d,]+ [\d.]+ [\d,]+", "10-K Figure 9").group(0)
    q8 = S.find(q10, r"Figure 8\. Composition of Loans at June 30, 2026 .{0,900}?Total consumer loans [\d,]+ [\d.]+ [\d,]+", "10-Q Figure 8").group(0)

    def amt(seg, label):
        return S.num(S.find(seg, re.escape(label) + r" \$? ?([\d,]+) ", label).group(1))
    k32 = S.find(k10, r"Figure 32\. Summary of Loan and Lease Loss Experience from Continuing Operations .{0,2200}?Net loan charge-offs \(\d+\) \(\d+\)", "10-K Figure 32").group(0)
    q29 = S.find(q10, r"Figure 29\. Summary of Loan and Lease Loss Experience from Continuing Operations .{0,2200}?Net loan charge-offs \(\d+\) \(\d+\) \(\d+\) \(\d+\)", "10-Q Figure 29").group(0)

    def flows(seg, label, col, ncols):
        """(charged off, recovered) for one loan type; col picks the column."""
        co = seg[seg.index("Loans charged off"):seg.index("Recoveries")]
        rc = seg[seg.index("Recoveries"):]
        pat = re.escape(label) + "".join(r" \$? ?(\(?[\d,]+\)?|—)" for _ in range(ncols))
        return S.num(S.find(co, pat, label).group(col + 1)), S.num(S.find(rc, pat, label).group(col + 1))
    disc_k = int(S.find(k10, r"\(c\) Total loans exclude loans of \$ ?(\d+) million at December 31, 2025", "10-K disc").group(1))
    hfs_k = int(S.find(k10, r"residential mortgage loans held for sale at fair value of \$ ?(\d+) million at December 31, 2025", "10-K HFS").group(1))
    disc_q = int(S.find(q10, r"\(b\) Total loans exclude loans of \$ ?(\d+) million at June 30, 2026", "10-Q disc").group(1))
    hfs_q = int(S.find(q10, r"residential mortgage loans held for sale at fair value of \$ ?(\d+) million at June 30, 2026", "10-Q HFS").group(1))
    dk = S.find(k10, r"Discontinued operations — education lending business: Loans charged off \$ ?(\d+) \$ ?(\d+) Recoveries (\d+) (\d+)", "10-K disc NCO")
    dq = S.find(q10, r"Discontinued operations — education lending business: Loans charged off \$ ?(\S+) \$ ?(\S+) \$ ?(\S+) \$ ?(\S+) Recoveries (\S+) (\S+) (\S+) (\S+)", "10-Q disc NCO")
    disc_nco_k = (int(dk.group(1)), int(dk.group(3)))
    disc_nco_q = (S.num(dq.group(3)), S.num(dq.group(7)))
    ent = {}
    for when, seg, lossseg, col, ncols, F, disc, hfs, dnco in (
            ("31 Dec 2025", k9, k32, 0, 2, fd, disc_k, hfs_k, disc_nco_k),
            ("30 Jun 2026", q8, q29, 2, 4, kb, disc_q, hfs_q, disc_nco_q)):
        g = lambda k: S.line(F, k)[0]
        doc = "KeyCorp 10-K 2025" if when.endswith("2025") else "KeyCorp 10-Q Q2 2026"
        cards, oc = amt(seg, "Credit cards"), amt(seg, "Other consumer loans")
        resi, he = amt(seg, "Real estate — residential mortgage"), amt(seg, "Home equity loans")
        fig(6, "Credit card balances, %s" % when, g("B538") / 1000, "KeyBank Call Report, RC-C 6.a ($000 / 1,000)", cards,
            "%s, Composition of Loans, Credit cards ($m)" % doc, "$m", tol=0.5, tol_why="$m rounding")
        fig(6, "Other consumer balances, %s, with the discontinued education loans added back" % when,
            (g("B539") + g("K137") + g("K207")) / 1000, "KeyBank Call Report, RC-C 6.b + 6.c + 6.d", oc + disc,
            "%s: Other consumer loans %d + education loans in discontinued assets %d ($m)" % (doc, oc, disc),
            "$m", tol=1.0, tol_why="two figures each rounded to $1m")
        fig(6, "Residential mortgage + home equity, %s, with mortgage loans held for sale added" % when,
            (g("1797") + g("5367") + g("5368")) / 1000, "KeyBank Call Report, RC-C 1.c.(1) + 1.c.(2)(a) + 1.c.(2)(b)",
            resi + he + hfs, "%s: residential mortgage %d + home equity %d + residential held for sale %d ($m)" % (doc, resi, he, hfs),
            "$m", tol=1.5, tol_why="three figures each rounded to $1m")
        fig(6, "Home equity, %s: KeyCorp's class against the Call Report's home equity lines" % when, g("1797") / 1000,
            "KeyBank Call Report, RC-C 1.c.(1) revolving lines only", he, "%s, Home equity loans" % doc, "$m",
            tol=0.5, tol_why="$m rounding", note="A definition gap, not an error: KeyCorp's home equity includes closed-end home equity loans, which the Call Report files under 1.c.(2) with residential mortgages.")
        lab_rib = "RI-B YTD" if when.endswith("2026") else "RI-B, full year"
        for lab, codes, mine in (("credit cards", (("RIADB514", "RIADB515"),), ["Credit cards"]),
                                 ("other consumer incl. discontinued education", (("RIADK129", "RIADK133"), ("RIADK205", "RIADK206")), ["Other consumer loans"]),
                                 ("residential mortgage + home equity", (("RIAD5411", "RIAD5412"), ("RIADC234", "RIADC217"), ("RIADC235", "RIADC218")),
                                  ["Real estate — residential mortgage", "Home equity loans"])):
            co = sum(F[x] for x, _ in codes) / 1000
            rc = sum(F[y] for _, y in codes) / 1000
            kco = sum(flows(lossseg, m_, col, ncols)[0] for m_ in mine)
            krc = sum(flows(lossseg, m_, col, ncols)[1] for m_ in mine)
            if "discontinued" in lab:
                kco += dnco[0]
                krc += dnco[1]
            t = 0.5 * len(mine) + (0.5 if "discontinued" in lab else 0)
            fig(6, "Charge-offs, %s, %s" % (lab, when), co, "KeyBank Call Report, %s %s" % (lab_rib, "+".join(x for x, _ in codes)),
                kco, "%s, Summary of Loan and Lease Loss Experience, loans charged off" % doc, "$m", tol=t, tol_why="$1m rounding per figure")
            fig(6, "Recoveries, %s, %s" % (lab, when), rc, "KeyBank Call Report, %s %s" % (lab_rib, "+".join(y for _, y in codes)),
                krc, "%s, same table, recoveries" % doc, "$m", tol=t, tol_why="$1m rounding per figure")
        ent[when] = dict(cards=cards, oc=oc, disc=disc, resi=resi, he=he, hfs=hfs, heloc=g("1797"), first=g("5367"),
                         junior=g("5368"), b539=g("B539"), k137=g("K137"), k207=g("K207"), b538=g("B538"))
    out["gap6"] = ent

    # ==================================================================== GAP 7
    for d, lab in (("06302026", "30 Jun 2026"), ("06302021", "30 Jun 2021"), ("09302021", "30 Sep 2021")):
        f = F26["17534"] if d == "06302026" else S.filing(src, "17534", d)
        v, full = S.line(f, "K137")
        fig(7, "KeyBank auto loans, RC-C 6.c, %s" % lab, data[d[4:] + d[:4]]["17534"]["LNAUTO"],
            "tool cache q%s.json, LNAUTO" % (d[4:] + d[:4]), v, "KeyBank Call Report %s, %s" % (lab, full), "$000")
    for c in peers:
        v, full = S.line(F26[c], "K137")
        fig(7, "%s auto loans, RC-C 6.c" % short[c], q26[c]["LNAUTO"], "tool cache, LNAUTO", v,
            "Call Report 30 Jun 2026, %s" % full, "$000")
    fig(7, "Where KeyBank's direct auto book is filed, beyond RC-C 6.c", None, "public filings", None, "none", "$000",
        verdict="COULD NOT",
        note="KeyCorp's 10-K and 10-Q never state a direct auto balance (searched for automobile, auto, direct, indirect, marine, recreational): the nearest is 'consumer loans have collateral that includes residential real estate, automobiles, boats, and RVs'. The internal figure is not used here, by rule. What public data does settle: RC-C 6.c must hold all direct and indirect consumer loans to buy a car (62,212); consumer auto leases are 10.a (0); boats, RVs, motorcycles and cash loans against a car already owned are 6.d.")
    fig(7, "Consumer leases in the tool's data (RC-C 10.a)", None, "FDIC API: no field for RC-C 10.a", None,
        "filed on RC-C 10.a for every bank (read below)", "$000", verdict="COULD NOT",
        note="The FDIC API publishes total leases (LS) but no consumer-lease line, so the tool cannot carry 10.a. Attacked once: the field dictionary (risview_properties.yaml, 2,378 fields) was searched for lease, individual, consumer and personal; nothing maps to RCFDF162. The filings are read directly instead.")
    leases = []
    for b in roster:
        f = F26[b["cert"]]
        g = lambda k: S.line(f, k)[0] or 0
        leases.append(dict(bank=b["short"], auto=g("K137"), leases=g("F162"), lease_co=f.get("RIADF185", 0),
                           lease_rec=f.get("RIADF187", 0), auto_co=f.get("RIADK129", 0), auto_rec=f.get("RIADK133", 0)))
    kbh, _ = S.api_rows(src / "fdic-keybank-consumer-2015-2026.json")
    abs21 = S.filing(src, "17534", "09302021")
    out["gap7"] = dict(leases=leases, keybank_history=[dict(q=r["REPDTE"], auto=r["LNAUTO"], other=r["LNCONOTH"],
                                                            rev=r["LNCONRP"], con=r["LNCON"]) for r in kbh],
                       abs_auto_2021q3=abs21["RCFDB846"], abs_auto_2021q2=S.filing(src, "17534", "06302021").get("RCFDB846", 0),
                       senior_notes=dict(dec24=303, dec25=74, jun26=16))

    # ==================================================================== roster
    counts = {}
    for f_ in FIG:
        counts[f_["verdict"]] = counts.get(f_["verdict"], 0) + 1
    out["figures"] = FIG
    out["counts"] = counts
    Path(a.out).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    card = {q: [qc["rows"]["Net charge-offs"][q], qc["rows"]["Total outstanding"][q]] for q in qkeys}
    (Path(a.out).parent / "qbp-card.json").write_text(json.dumps({"card": card}), encoding="utf-8")
    print("figures: %d  %s" % (len(FIG), counts))
    for f_ in FIG:
        if f_["verdict"] != "TIED":
            print("  %s %-9s %s" % (f_["id"], f_["verdict"], f_["what"]))
    return 0


def data_list(data):
    """books.bank_book wants {REPDTE: [rows]}; the cache reader keys rows by cert."""
    return {q: list(rows.values()) for q, rows in data.items()}


def acquisitions(src, snap, short):
    """Every whole-bank acquisition by a roster bank since Oct 2005 (FDIC
    history, the tool's own allowlist of codes), product by product: the
    acquired bank's book at its last filing against the acquirer's book the
    quarter before, and whether the 25% jump rule fires in the quarter."""
    ACQ = {211, 215, 216, 217, 221, 222, 223, 224}
    P = {"Credit card": "LNCRCD", "Mortgage": "LNRERSFM", "Home equity": "LNRELOC",
         "Other consumer": "LNCONOTH", "Auto": "LNAUTO"}
    rows, _ = S.api_rows(Path(src) / "fdic-history-roster.json")
    qs = sorted(snap)

    def qend(d):
        y, m = int(d[:4]), int(d[5:7])
        em = ((m - 1) // 3) * 3 + 3
        return "%04d%02d%02d" % (y, em, {3: 31, 6: 30, 9: 30, 12: 31}[em])
    out, events, nofile = [], 0, []
    for h in rows:
        if int(h["CHANGECODE"]) not in ACQ:
            continue
        events += 1
        acq, oc, q = str(h["ACQ_CERT"]), str(h["OUT_CERT"]), qend(h["EFFDATE"][:10])
        if q not in qs:
            continue
        i = qs.index(q)
        prev = next((qs[j] for j in range(i - 1, -1, -1) if oc in snap[qs[j]]), None)
        if prev is None:
            nofile.append(oc)
            continue
        for prod, f in P.items():
            ob = snap[prev][oc].get(f) or 0
            ab = (snap[qs[i - 1]].get(acq) or {}).get(f) or 0
            az = (snap[q].get(acq) or {}).get(f) or 0
            if ob <= 0 or (ab == 0 and az == 0):
                continue
            jump = (az / ab - 1) if ab else None
            caught = (ab == 0 and az > 0) or (jump is not None and abs(jump) > 0.25)
            material = (ab >= 1000000 and ob / ab >= 0.05) or (ab < 1000000 and ob >= 1000000)
            out.append(dict(acquirer=short[acq], out_cert=oc, code=int(h["CHANGECODE"]), quarter=q, product=prod,
                            acquired=ob, before=ab, after=az, share=(ob / ab if ab else None), jump=jump,
                            caught=caught, material=material))
    names = {}
    for fn in sorted(Path(src).glob("fdic-institutions-acquired-*.json")):
        for x in json.loads(fn.read_text("utf-8"))["data"]:
            names[str(x["data"]["CERT"])] = x["data"]["NAME"]
    for r in out:
        r["out_name"] = names.get(r["out_cert"], r["out_cert"])
    return dict(events=events, no_filing=nofile, rows=out)


if __name__ == "__main__":
    sys.exit(main())
