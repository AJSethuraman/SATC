"""focus.html: only the early-warning thread, built from build.py's data and charts."""
import json, re, sys
from pathlib import Path

D = HERE = Path(__file__).parent
sys.argv = [sys.argv[0], "peers.json"]
src = (D / "build.py").read_text(encoding="utf-8").split("# ---------- page ----------")[0]
g = {"__file__": str(D / "build.py")}
exec(compile(src, "build.py", "exec"), g)
globals().update({k: v for k, v in g.items() if not k.startswith("__")})

# ---------- card strain on the existing book ----------
def _ph_bal(col):
    return _philly("26Q2-CreditCardBalances.csv", col)


MINPAY = _ph_bal("Share of Accounts Making the Minimum Payment")
UTIL90 = _ph_bal("Utilization (Active Accounts Only) (90th percentile)")
UTIL50 = _ph_bal("Utilization (Active Accounts Only) (50th percentile)")
STRAIN = ('<section class="box"><h2>Card: strain on the existing book</h2>'
          '<p class="cap">Three measures of how cardholders are carrying their balances (large banks, 2012 on), each drawn as its change over '
          'a year, around its own normal, over the rise in card 30&ndash;89 days past due (solid red). Not moved: these turn at the same '
          'time as delinquency, like refreshed FICO, so they confirm stress rather than warn of it.</p>'
          '<h3>Share of accounts paying only the minimum</h3>%s'
          '<h3>Utilization, 90th percentile (the most stretched tenth of active accounts)</h3>%s'
          '<h3>Utilization, median: the one with a small lead, moved 4 quarters later</h3>%s'
          '<p class="cap">Paying only the minimum and the most-stretched utilization match 30&ndash;89 best in the same quarter (0.85 and 0.90) '
          'and charge-offs about a year later. Median utilization matches 30&ndash;89 best 2 to 6 quarters later (0.66; 0.53 with '
          '2020&ndash;2023 left out). Credit line cuts and increases are banks reacting and show no lead.</p></section>'
          % (ov(yoy(MINPAY), 0, Y3089, qrange("2013Q3", "2026Q2"), "var(--c-oth)", "change in share paying only the minimum", "rise in card 30-89"),
             ov(yoy(UTIL90), 0, Y3089, qrange("2013Q3", "2026Q2"), "var(--c-mtg)", "change in 90th-percentile utilization", "rise in card 30-89"),
             ov(yoy(UTIL50), 4, Y3089, qrange("2013Q3", "2027Q2"), "var(--c-he)", "change in median utilization, 4 quarters earlier", "rise in card 30-89")))

# ---------- mortgage terms at origination, 1998 on (FHFA National Mortgage Database) ----------
NM = json.loads((S / "nmdb" / "nmdb.json").read_text())
num = lambda s: {k: float(v) for k, v in s.items() if v not in ("", None)}       # noqa: E731
PUR = {k: num(v) for k, v in NM["All Mortgages (Home Purchase)"].items()}
ALLM = {k: num(v) for k, v in NM["All Mortgages"].items()}
POOR = {k: ALLM["PCT_VS_POOR"][k] + ALLM["PCT_VS_VERYPOOR"][k] for k in ALLM["PCT_VS_POOR"]}
FCL = yoy(num(NM["All Mortgages"]["PFORECL"]))
P90M = yoy(num(NM["All Mortgages"]["P90DL"]))
LQ = qrange("1998Q1", "2025Q4")
levels = svg_chart(LQ, [{"data": PUR["PCT_CLTV_GT97"], "color": "var(--c-card)", "w": 2.4},
                        {"data": PUR["PCT_DTI_GE44"], "color": "var(--c-mtg)", "w": 2.4},
                        {"data": POOR, "color": "var(--c-oth)", "w": 2.4},
                        {"data": ALLM["PCT_CASHOUT"], "color": "var(--c-he)", "w": 2.4}],
                   0, 45, [0, 10, 20, 30, 40], lambda v: "%d%%" % v, h=240,
                   notes=[("2006Q1", "loosest"), ("2025Q4", "now")],
                   label="Mortgage terms at origination, 1998 to 2025")
perf = svg_chart(qrange("2002Q1", "2026Q2"), [{"data": num(NM["All Mortgages"]["P90DL"]), "color": "var(--ink)", "w": 2.2},
                                              {"data": num(NM["All Mortgages"]["PFORECL"]), "color": "var(--c-card)", "w": 2.2}],
                 0, 6, [0, 2, 4, 6], lambda v: "%d%%" % v, h=170, label="Mortgages 90+ days past due and in foreclosure")
LQ2 = qrange("2001Q1", "2028Q4")
MORT = ('<section class="box"><h2>Mortgage: terms at origination, tested against 2008</h2>'
        '<p class="cap">FHFA&rsquo;s National Mortgage Database: a 5%% sample of every first-lien mortgage in the U.S., all lenders, '
        'terms at origination by quarter from 1998 and performance of the whole book from 2002. Unlike the large-bank data (2012 on), '
        'it covers the run-up to 2008.</p>'
        '<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>purchase loans with combined LTV over 97%%</span>'
        '<span><i class="sw" style="background:var(--c-mtg)"></i>purchase loans with DTI 44%% or more</span>'
        '<span><i class="sw" style="background:var(--c-oth)"></i>loans to poor or very poor scores</span>'
        '<span><i class="sw" style="background:var(--c-he)"></i>cash-out share of all loans</span></div>'
        '<h3>Share of new mortgages on each risky term</h3><div class="chart">%s</div>'
        '<div class="legend"><span><i class="sw" style="background:var(--ink)"></i>90+ days past due</span>'
        '<span><i class="sw" style="background:var(--c-card)"></i>in foreclosure</span></div>'
        '<h3>What the whole book did</h3><div class="chart">%s</div>'
        '<h3>Slid forward and laid over the rise in foreclosure</h3>'
        '<p class="cap">Purchase loans with combined LTV over 97%%, moved 12 quarters later (match 0.85):</p>%s'
        '<p class="cap">Loans to poor or very poor scores, moved 12 quarters later (match 0.80):</p>%s'
        '<p class="cap">Purchase loans with DTI 44%% or more, moved 8 quarters later (match 0.70):</p>%s'
        '<p class="cap">One episode carries these matches: terms loosened through 2005&ndash;2007 and serious delinquency and foreclosure '
        'peaked in 2009&ndash;2010. Now: purchase loans with DTI 44%% or more are %.1f%%, above early 2008&rsquo;s %.1f%% (the series high '
        'was 40.1%% in 2023Q4); combined LTV over 97%% is %.1f%% (2005: %.1f%%); poor or very poor scores %.1f%% (2005: %.1f%%). The DTI rise partly reflects '
        'higher rates raising payments, not only looser lending. Scores here are VantageScore, from the NMDB&rsquo;s own credit data.</p></section>'
        % (levels, perf,
           ov(PUR["PCT_CLTV_GT97"], 12, FCL, LQ2, "var(--c-card)", "CLTV over 97%, 12 quarters earlier", "rise in foreclosure"),
           ov(POOR, 12, FCL, LQ2, "var(--c-oth)", "poor or very poor scores, 12 quarters earlier", "rise in foreclosure"),
           ov(PUR["PCT_DTI_GE44"], 8, FCL, LQ2, "var(--c-mtg)", "DTI 44% or more, 8 quarters earlier", "rise in foreclosure"),
           PUR["PCT_DTI_GE44"]["2025Q4"], PUR["PCT_DTI_GE44"]["2008Q1"], PUR["PCT_CLTV_GT97"]["2025Q4"],
           PUR["PCT_CLTV_GT97"]["2005Q1"], POOR["2025Q4"], POOR["2005Q1"]))

MTM = json.loads((S / "nmdb" / "mtm.json").read_text())
over90 = {k: MTM["PCT_MTMLTV_91_100"][k] + MTM["PCT_MTMLTV_GT100"][k] for k in MTM["PCT_MTMLTV_GT100"]}
mtm_chart = svg_chart(qrange("2013Q1", "2026Q2"), [{"data": over90, "color": "var(--c-card)", "w": 2.6},
                                                   {"data": MTM["PCT_MTMLTV_GT100"], "color": "var(--ink)", "w": 2.2},
                                                   {"data": num(NM["All Mortgages"]["PFORECL"]), "color": "var(--c-mtg)", "w": 2.2, "dash": True}],
                      0, 26, [0, 5, 10, 15, 20, 25], lambda v: "%d%%" % v, h=210,
                      label="Share of outstanding mortgages owing more than 90% and more than 100% of the home's current value")
EQUITY = ('<section class="box"><h2>Mortgage: why high DTI is not turning into foreclosures</h2>'
          '<p class="cap">The same database values every outstanding mortgage against today&rsquo;s home price (current, or mark-to-market, '
          'loan-to-value), from 2013. A borrower with equity who cannot pay can sell; one who owes more than the house is worth cannot.</p>'
          '<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>owe more than 90%% of current value</span>'
          '<span><i class="sw" style="background:var(--ink)"></i>owe more than 100%% (underwater)</span>'
          '<span><i class="sw" style="background:var(--c-mtg)"></i>in foreclosure</span></div>'
          '<div class="chart">%s</div>'
          '<p class="cap">2013Q1: %.1f%% owed more than 90%% of their home&rsquo;s value and %.1f%% were underwater, with foreclosure still '
          'high. 2026Q2: %.1f%% and %.1f%%; the average outstanding mortgage owes %.0f%% of current value. That cushion, from the 2020&ndash;2022 '
          'price rise, is why the high share of high-DTI loans has not produced foreclosures. The point to worry is when this line climbs: '
          'home prices falling, or new loans at high combined LTV piling up. The series starts in 2013, after the crisis, so it cannot show '
          'the run-up to 2008.</p></section>'
          % (mtm_chart, over90["2013Q1"], MTM["PCT_MTMLTV_GT100"]["2013Q1"], over90["2026Q2"], MTM["PCT_MTMLTV_GT100"]["2026Q2"],
             MTM["AVE_MTMLTV"]["2026Q2"]))

# ---------- card origination, narrowed ----------
CARD_ORIG = ('<section class="box"><h2>Card: who got new accounts, and what followed</h2>'
             '<p class="cap">The score of the bottom tenth of new card accounts each quarter (lower is riskier), and the share of new accounts '
             'going to scores under 660, each moved later by its best delay and laid over the rise in card charge-offs (solid red).</p>'
             '<h3>Score at origination, 10th percentile (drawn so lower is up), moved 8 quarters later</h3>%s'
             '<h3>Share of new accounts under 660, moved 9 quarters later</h3>%s'
             '<p class="cap">Both lead charge-offs by about two years: 0.85 to 0.96 with 2020&ndash;2023 left out, 0.40 to 0.42 with them in. '
             'The 2021 low (bottom tenth at 614) sits over the 2023 rise. Now: bottom tenth %d (a year earlier %d); share under 660 %.1f%% '
             '(a year earlier %.1f%%).</p></section>'
             % (ov(CARD_ORIG_RISK, 8, YNCO, qrange("2013Q1", "2028Q2"), "var(--c-he)", "lower origination scores, 8 quarters earlier", "rise in card charge-offs"),
                ov(SUB_ACC, 9, YNCO, qrange("2013Q1", "2028Q3"), "var(--c-he)", "new accounts under 660, 9 quarters earlier", "rise in card charge-offs"),
                CO["10th"]["2026Q2"], CO["10th"]["2025Q2"], SUB_ACC["2026Q2"], SUB_ACC["2025Q2"]))

SUMMARY = ('<section class="box"><h2>What comes first, and what comes with</h2>'
           '<table style="width:100%;border-collapse:collapse;font-size:13px">'
           '<tr><th style="text-align:left">Signal</th><th style="text-align:left">Turns</th><th style="text-align:left">Data</th></tr>'
           + "".join('<tr style="border-top:1px solid var(--grid)"><td>%s</td><td>%s</td><td>%s</td></tr>' % r for r in (
               ("Card: score at origination; share of new accounts under 660", "about 2 years before card charge-offs", "large banks, 2012 on"),
               ("Card: banks easing standards (loan officer survey)", "about 3 years before card charge-offs", "all banks, 1996 on"),
               ("Card: median utilization", "2 to 6 quarters before 30&ndash;89", "large banks, 2012 on"),
               ("Card: refreshed FICO; paying only the minimum; most-stretched utilization", "with 30&ndash;89; a year before charge-offs", "large banks, 2012 on"),
               )) +
           '</table><p class="cap">With 2020&ndash;2023 the card matches weaken (the pandemic ran both ways). Mortgage origination terms were '
           'tested and set aside. Full workings, KeyCorp and competitor FICO: the companion page.</p></section>')


# ---------- across products: does consumer delinquency come before mortgage? ----------
def dq(prod, m):
    return yoy(_rd("%s_industry_delinquency-%s_quarter-end.csv" % (prod, m)))


OC30, CC30 = dq("other-consumer", "30-89"), dq("credit-card", "30-89")
MG30, MG90 = dq("mortgage", "30-89"), dq("mortgage", "90-plus-incl-nonaccrual")
HE30, HE90 = dq("home-equity", "30-89"), dq("home-equity", "90-plus-incl-nonaccrual")
XQ = qrange("2007Q1", "2026Q2")


def xlag(src, targets):
    w, h, pl, pr, pt, pb = 700, 250, 46, 200, 14, 40
    lags = list(range(-4, 13))
    X = lambda k: pl + (w - pl - pr) * (k + 4) / 16                       # noqa: E731
    Yp = lambda v: pt + (h - pt - pb) * (1 - (v + 1) / 2)                 # noqa: E731
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="How strongly a rise in this delinquency goes with a later rise in the others">' % (w, h)]
    for t in (-1, -0.5, 0, 0.5, 1):
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>' % (pl, w - pr, Yp(t), Yp(t), "var(--ink)" if t == 0 else "var(--grid)"))
        out.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%.1f</text>' % (pl - 6, Yp(t) + 4, t))
    for k, lab in ((-4, "1 yr before"), (0, "same quarter"), (4, "1 yr later"), (8, "2 yrs later"), (12, "3 yrs later")):
        out.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (X(k), h - 22, lab))
        out.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--grid)"/>' % (X(k), X(k), pt, h - pb))
    ends = []
    for name, tgt, col in targets:
        prof = {k: v for k, v in uw_profile(src, tgt, False).items() if v is not None}
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4"/>' % (" ".join("%.1f,%.1f" % (X(k), Yp(v)) for k, v in prof.items()), col))
        kmax = max(prof, key=prof.get)
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (X(kmax), Yp(prof[kmax]), col))
        ends.append((Yp(prof[max(prof)]), name, col, kmax, prof[kmax]))
    ends.sort(); last = None
    for yy, name, col, kmax, v in ends:
        yy = max(yy, last + 26) if last is not None else yy
        last = yy
        when = "same quarter" if kmax == 0 else ("%d qtrs later" % kmax if kmax > 0 else "%d qtrs earlier" % -kmax)
        out.append('<text x="%d" y="%.1f" class="an" style="fill:%s;font-weight:700">%s</text>' % (w - pr + 8, yy, col, name))
        out.append('<text x="%d" y="%.1f" class="an">peak %.2f, %s</text>' % (w - pr + 8, yy + 12, v, when))
    out.append("</svg>")
    return "".join(out)


TG = [("Mortgage 30-89", MG30, "var(--c-mtg)"), ("Mortgage 90+ incl. nonaccrual", MG90, "var(--c-card)"),
      ("Home equity 30-89", HE30, "var(--c-he)"), ("Home equity 90+ incl. nonaccrual", HE90, "var(--c-oth)")]
stack_x = "".join(
    svg_chart(XQ, [{"data": d_, "color": c_, "w": 2.2, "name": nm.split(" (")[0]}], lo, hi, ticks,
                                              lambda v: "%+.2f" % v if v else "0", h=120, notes=[("2008Q4", ""), ("2009Q4", "")],
                                              ytitle="%s: rise over the year, %% points" % nm.split(" (")[0],
                                              label="Rise over the year: " + nm)
    for nm, d_, c_, lo, hi, ticks in (
        ("Other consumer 30-89 (rise over the year, points)", OC30, "var(--c-oth)", -0.6, 0.6, [-0.5, 0, 0.5]),
        ("Card 30-89", CC30, "var(--c-card)", -1.2, 1.2, [-1, 0, 1]),
        ("Home equity 30-89", HE30, "var(--c-he)", -0.6, 0.6, [-0.5, 0, 0.5]),
        ("Mortgage 30-89", MG30, "var(--c-mtg)", -1.6, 1.6, [-1.5, 0, 1.5]),
        ("Mortgage 90+ incl. nonaccrual", MG90, "var(--ink)", -3, 4, [-3, 0, 3])))
CROSS = ('<section class="box"><h2>Across products: does consumer delinquency come before mortgage?</h2>'
         '<p class="cap">The book&rsquo;s industry series, every bank, 2007 to 2026, each drawn as its rise over the past year. Stacked on '
         'the same quarters so the turns can be compared; dotted lines mark 2008Q4 and 2009Q4.</p>%s'
         '<h3>How strongly a rise in other consumer 30&ndash;89 goes with a rise in each, that many quarters later</h3><div class="chart">%s</div>'
         '<h3>The same for card 30&ndash;89</h3><div class="chart">%s</div>'
         '<p class="cap">Early delinquency rises across products in the same quarter, with home equity 30&ndash;89 about two quarters '
         'ahead of card and other consumer. Other consumer 30&ndash;89 comes about a year before mortgage 90+ and nonaccrual (0.80; 0.82 '
         'with 2020&ndash;2023 left out); card 30&ndash;89 less clearly (0.48). Mortgage&rsquo;s own 30&ndash;89 turns at the same time, '
         'so the other products are not earlier than mortgage&rsquo;s own early delinquency. Mortgage 90+ includes government-guaranteed '
         'loans that banks hold at no loss (the book&rsquo;s note); other consumer breaks in 2011 (auto split out) and 2024Q4 (Call Report '
         'revision).</p></section>' % (stack_x, xlag(OC30, TG), xlag(CC30, TG)))


# ---------- mortgage delinquency on the book's own lines ----------
def lvl(prod, src, m):
    return {ql(r[0]): float(r[1]) for r in csv.reader(open(TE / "docs/walkthrough-book/out/series" / ("%s_%s_delinquency-%s_quarter-end.csv" % (prod, src, m))))
            if r and r[0][:2] == "20"}


MQ = qrange("2006Q1", "2026Q2")


def mpanel(m, title, y1, ticks):
    ind, kb, pk = lvl("mortgage", "industry", m), lvl("mortgage", "keybank", m), lvl("mortgage", "pack-composite", m)
    o = scale([ind[q_] for q_ in MQ if q_ in ind], "higher_is_worse", HW, LS, Z, True)
    late = scale([ind[q_] if q_ >= "2016Q1" else None for q_ in MQ if q_ in ind], "higher_is_worse", HW, LS, Z, True)
    chart = svg_chart(MQ, [{"data": ind, "color": "var(--ink)", "w": 2.2, "name": "Industry"}, {"data": pk, "color": "var(--muted)", "w": 1.6, "dash": True, "name": "Peer group"},
                           {"data": kb, "color": "var(--key)", "w": 2.6, "name": "KeyBank"}], 0, y1, ticks, lambda v: "%.2f%%" % v, h=200,
                      ytitle="mortgage %s, %% of balances" % title.lower(),
                      zones=o["bounds"], label="Mortgage %s with the industry's rating zones" % title)
    rate = lambda v, b: 1 + sum(v >= x for x in b)                         # noqa: E731
    since = [q_ for q_ in MQ if q_ >= "2016Q1" and q_ in ind]
    lows = sum(rate(ind[q_], o["bounds"]) == 1 for q_ in since)
    txt = ('Zones from the industry&rsquo;s whole history (2006 on): 2 begins %.2f%%, 3 %.2f%%, 4 %.2f%%, 5 High %.2f%%. Since 2016 the industry '
           'rated 1 Low in %d of %d quarters. Industry now %.2f%%, peer group %.2f%%, KeyBank %.2f%%.'
           % (tuple(o["bounds"]) + (lows, len(since), ind["2026Q2"], pk["2026Q2"], kb["2026Q2"])))
    if late["bounds"]:
        txt += (' With lines from 2016 on only: 2 begins %.2f%%, 3 %.2f%%, 4 %.2f%%, 5 High %.2f%%; the industry now rates %d.'
                % (tuple(late["bounds"]) + (rate(ind["2026Q2"], late["bounds"]),)))
    else:
        txt += ' With lines from 2016 on only, the method refuses: %s.' % late["refused"]
    return '<h3>%s</h3><div class="chart">%s</div><p class="cap">%s</p>' % (title, chart, txt)


MDQ = ('<section class="box"><h2>Mortgage delinquency on the book&rsquo;s lines</h2>'
       '<p class="cap">The book&rsquo;s industry series (solid black), peer group (dashed gray) and KeyBank (red), 2006 to 2026, with the '
       'five rating zones drawn from the industry&rsquo;s history at the agreed settings (width 0.5, Moderate-Low 1.0, z 2.5).</p>'
       + mpanel("30-89", "30 to 89 days past due", 5, [0, 1, 2, 3, 4, 5])
       + mpanel("nonaccrual", "Nonaccrual", 7, [0, 2, 4, 6])
       + mpanel("90-plus-incl-nonaccrual", "90+ days past due including nonaccrual", 18, [0, 5, 10, 15])
       + '<p class="cap">The whole-history lines are set by 2008 and its long tail. They still separate quarters on nonaccrual (Low in 13 '
         'of 42 quarters since 2016) and on 90+ (22 of 42), but 30&ndash;89 has read Low in 33 of 42. Lines drawn only from 2016 on fit '
         'nonaccrual and refuse 30&ndash;89 and 90+, because nothing since 2016 is far enough from normal to rate High. Which window the '
         'lines come from is a setting on Decide (periods left out), not a change to the data.</p></section>')


# ---------- specialized: card balances under 660, KeyBank against peers (10-Q, exact cuts only) ----------
PE = json.loads((S / "peerfico" / "peers.json").read_text())["Card"]
U660 = {}
for bank in ("KeyCorp", "Bank of America", "Wells Fargo", "PNC", "Citi"):
    U660[bank] = {ql(d_): 100 * r["lo"] for d_, r in PE[bank].items() if abs(r["lo"] - r["hi"]) < 1e-12}
UQ = qrange("2018Q2", "2026Q2")
cols = {"KeyCorp": "var(--key)", "Bank of America": "var(--c-mtg)", "Wells Fargo": "var(--c-oth)", "PNC": "var(--c-he)", "Citi": "var(--muted)"}
u660_chart = svg_chart(UQ, [{"data": U660[b_], "color": cols[b_], "w": 2.8 if b_ == "KeyCorp" else 1.8, "name": b_} for b_ in U660],
                       0, 25, [0, 5, 10, 15, 20, 25], lambda v: "%.0f%%" % v, h=220, ytitle="% of card balances scored under 660",
                       label="Share of card balances with a refreshed score under 660, by bank, where the bank cuts at 660")
def _bnco(f):
    return {ql(r[0]): float(r[1]) for r in csv.reader(open(TE / "docs/walkthrough-book/out/series" / f)) if r and r[0][:2] == "20"}


BNCO = {"KeyCorp": _bnco("credit-card_keybank_net.csv"), "Bank of America": _bnco("banks/credit-card_bank-of-america_net.csv"),
        "Wells Fargo": _bnco("banks/credit-card_wells-fargo_net.csv"), "PNC": _bnco("banks/credit-card_pnc_net.csv"),
        "Citi": _bnco("banks/credit-card_citi_net.csv")}
kc_nco = svg_chart(UQ, [{"data": BNCO[b_], "color": cols[b_], "w": 2.8 if b_ == "KeyCorp" else 1.8, "name": b_} for b_ in BNCO],
                   0, 6, [0, 1, 2, 3, 4, 5, 6], lambda v: "%.1f%%" % v, h=220, ytitle="card net charge-offs, trailing four quarters",
                   label="Card net charge-offs by bank, trailing four quarters")


def scatter660():
    w, h, pl, pr, pt, pb = 700, 300, 50, 16, 14, 44
    X = lambda v: pl + (w - pl - pr) * v / 25                     # noqa: E731
    Y = lambda v: pt + (h - pt - pb) * (1 - v / 6)                # noqa: E731
    o = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Each bank-quarter: share of card balances under 660 against card net charge-offs">' % (w, h)]
    for t in (0, 2, 4, 6):
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)"/>' % (pl, w - pr, Y(t), Y(t)))
        o.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%d%%</text>' % (pl - 6, Y(t) + 4, t))
    for t in (0, 5, 10, 15, 20, 25):
        o.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%d%%</text>' % (X(t), h - 26, t))
    o.append('<text x="%.1f" y="%d" class="an" text-anchor="middle">share of card balances under 660</text>' % ((pl + w - pr) / 2, h - 8))
    o.append('<text x="14" y="%.1f" class="an" transform="rotate(-90 14 %.1f)" text-anchor="middle">card net charge-offs</text>' % ((pt + h - pb) / 2, (pt + h - pb) / 2))
    for b_, sh in U660.items():
        for q_, v in sh.items():
            if q_ in BNCO[b_]:
                o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" fill-opacity="0.75"><title>%s %s: %.1f%% under 660, %.2f%% net</title></circle>'
                         % (X(v), Y(BNCO[b_][q_]), cols[b_], b_, q_, v, BNCO[b_][q_]))
    o.append("</svg>")
    return "".join(o)


U660S = ('<section class="box"><h2>Card: balances under 660, KeyBank against peers</h2>'
         '<div class="legend">' + "".join('<span><i class="sw" style="background:%s"></i>%s</span>' % (c_, b_) for b_, c_ in cols.items()) + '</div>'
         '<div class="chart">%s</div><h3>Card net charge-offs, same banks and quarters (trailing four quarters, each bank&rsquo;s Call Report)</h3><div class="chart">%s</div>''<h3>Each bank-quarter: balances under 660 against net charge-offs</h3><div class="chart">%s</div>'
         '<p class="cap">From each bank&rsquo;s 10-Q: the share of its scored card balances with a refreshed score under 660, drawn only for '
         'the quarters the bank cuts at 660 (KeyCorp from 2018, PNC from 2020Q4, Wells Fargo from 2022Q4, Citi from 2024Q1, Bank of America '
         'from 2025Q1). No public series gives this for the whole industry. KeyCorp now %.1f%%; its low was %.1f%% (%s). Its yearly rise went '
         'with KeyBank&rsquo;s card losses the same year (0.67) and the next (0.59).</p></section>'
         % (u660_chart, kc_nco, scatter660(), U660["KeyCorp"]["2026Q2"], min(U660["KeyCorp"].values()), min(U660["KeyCorp"], key=U660["KeyCorp"].get)))

# ---------- specialized: estimated roll and cure, card and other consumer ----------
FLOW = json.loads((S / "rolls" / "flow.json").read_text())
ROLL = json.loads((S / "rolls" / "rolls.json").read_text())
RQ = qrange("2007Q1", "2026Q2")
def fl(k, lo=0, hi=1.2):
    return {q_: 100 * v for q_, v in FLOW[k].items() if lo <= v <= hi}
flow_chart = lambda prod: svg_chart(RQ, [{"data": fl("%s|Industry" % prod), "color": "var(--ink)", "w": 2.2, "name": "Industry"},       # noqa: E731
                                         {"data": fl("%s|Peer group" % prod), "color": "var(--muted)", "w": 1.6, "dash": True, "name": "Peer group"},
                                         {"data": fl("%s|KeyBank" % prod), "color": "var(--key)", "w": 2.4, "name": "KeyBank"}],
                                    0, 110, [0, 25, 50, 75, 100], lambda v: "%.0f%%" % v, h=200, ytitle="% of delinquent dollars charged off within two quarters", notes=[("2009Q2", ""), ("2023Q2", "")],
                                    label="Estimated share of delinquent dollars that end up charged off: %s" % prod)
roll_card = svg_chart(RQ, [{"data": {q_: v["roll"] for q_, v in ROLL["Card|Industry"].items()}, "color": "var(--ink)", "w": 2.2, "name": "Industry"},
                           {"data": {q_: v["roll"] for q_, v in ROLL["Card|Peer group"].items()}, "color": "var(--muted)", "w": 1.6, "dash": True, "name": "Peer group"}],
                      0.8, 1.4, [0.8, 1.0, 1.2, 1.4], lambda v: "%.2f" % v, h=170, ytitle="90+ this quarter ÷ 30–89 last quarter",
                      label="Card roll ratio: 90+ this quarter over 30-89 last quarter")
def st2(k):
    return {q_: 100 * v["co_from_90"] for q_, v in ROLL[k].items() if 0 <= v["co_from_90"] <= 1.5}


stage2 = svg_chart(RQ, [{"data": st2("Card|Industry"), "color": "var(--ink)", "w": 2.2, "name": "Industry"},
                        {"data": st2("Card|Peer group"), "color": "var(--muted)", "w": 1.6, "dash": True, "name": "Peer group"},
                        {"data": st2("Card|KeyBank"), "color": "var(--key)", "w": 2.4, "name": "KeyBank"}],
                   40, 120, [40, 60, 80, 100, 120], lambda v: "%.0f%%" % v, h=180, ytitle="gross charge-offs as % of last quarter’s 90+",
                   label="Card: gross charge-offs this quarter over 90+ last quarter")
def co_over(k, n):
    """Gross charge-offs over the next n quarters as % of 90+ (incl. nonaccrual) at the quarter-end."""
    v = ROLL[k]; ks = sorted(v); out = {}
    for i in range(len(ks) - n):
        if v[ks[i]]["sev"] > 0:
            r = sum(v[ks[i + j]]["co"] for j in range(1, n + 1)) / v[ks[i]]["sev"]
            if 0 <= r <= 3:
                out[ks[i]] = 100 * r
    return out


def win_chart(prod, n, hi):
    return svg_chart(RQ, [{"data": co_over("%s|Industry" % prod, n), "color": "var(--ink)", "w": 2.2, "name": "Industry"},
                          {"data": co_over("%s|Peer group" % prod, n), "color": "var(--muted)", "w": 1.6, "dash": True, "name": "Peer group"},
                          {"data": co_over("%s|KeyBank" % prod, n), "color": "var(--key)", "w": 2.4, "name": "KeyBank"}],
                     0, hi, [x for x in range(0, hi + 1, 50)], lambda v: "%.0f%%" % v, h=190,
                     ytitle="gross charge-offs over the next %s as %% of 90+ at the quarter-end" % ("quarter" if n == 1 else "%d quarters" % n),
                     label="%s: charge-offs over the next %d quarter(s) over 90+" % (prod, n))


def avg4(d_):
    ks = sorted(d_); out = {}
    for i in range(3, len(ks)):
        w = ks[i - 3:i + 1]
        if all(q_ in d_ for q_ in w):
            out[ks[i]] = sum(d_[q_] for q_ in w) / 4
    return out


def move(d_):
    a = avg4(d_)
    return {q_: v - a[k4] for q_, v in a.items() for k4 in ["%dQ%s" % (int(q_[:4]) - 1, q_[5])] if k4 in a}


def step_series(prod, who):
    r = ROLL["%s|%s" % (prod, who)]
    s1 = {q_: 100 * v["roll"] for q_, v in r.items() if 0 < v["roll"] < 3}
    s2 = co_over("%s|%s" % (prod, who), 1)
    s3 = {q_: v for q_, v in FLOW["%s|%s" % (prod, who)].items()}
    s3 = {q_: 100 * v for q_, v in s3.items() if 0 <= v <= 2}
    return move(s1), move(s2), move(s3)


def mv_chart(prod, idx, title, lim):
    lines = []
    for who, col, w, dash in (("Industry", "var(--ink)", 2.4, False), ("Peer group", "var(--muted)", 1.6, True), ("KeyBank", "var(--key)", 2.0, False)):
        lines.append({"data": step_series(prod, who)[idx], "color": col, "w": w, "dash": dash, "name": who})
    return '<p class="cap" style="color:var(--ink);font-weight:600">%s</p>' % title + svg_chart(RQ, lines, -lim, lim, [-lim, -lim / 2, 0, lim / 2, lim], lambda v: "%+.0f" % v if v else "0", h=170,
                     notes=[("2009Q2", ""), ("2020Q2", ""), ("2023Q2", "")],
                     ytitle="points vs a year earlier; up = more reaching loss",
                     label="%s, %s, change over the year" % (prod, title))


import statistics as _st2


def diverge(prod, who, idx):
    a = step_series(prod, who)[idx]; i = step_series(prod, "Industry")[idx]
    return {q_: a[q_] - i[q_] for q_ in a if q_ in i and q_ >= "2011Q1"}


DQ = qrange("2011Q1", "2026Q2")


def div_chart(prod, idx, title, lim):
    kb, pg = diverge(prod, "KeyBank", idx), diverge(prod, "Peer group", idx)
    sd = 1.4826 * _st2.median([abs(v - _st2.median(kb.values())) for v in kb.values()])
    med = _st2.median(kb.values())
    band = {q_: med + sd for q_ in DQ}; band_lo = {q_: med - sd for q_ in DQ}
    chart = svg_chart(DQ, [{"data": band, "color": "var(--grid)", "w": 1.2, "dash": True},
                           {"data": band_lo, "color": "var(--grid)", "w": 1.2, "dash": True},
                           {"data": pg, "color": "var(--muted)", "w": 1.6, "name": "Peer group"},
                           {"data": kb, "color": "var(--key)", "w": 2.6, "name": "KeyBank"}],
                      -lim, lim, [-lim, -lim / 2, 0, lim / 2, lim], lambda v: "%+.0f" % v if v else "0", h=170,
                      ytitle="change vs a year earlier, minus the industry\u2019s, points; up = worse than industry",
                      label="%s %s: divergence from the industry" % (prod, title))
    out = [q_ for q_ in sorted(kb) if abs(kb[q_] - med) > 2 * sd]
    latest = sorted(kb)[-1]
    note = ('Dashed band: KeyBank&rsquo;s typical swing either side of its usual gap (1.4826 &times; median absolute deviation, %.1f points). '
            'Now %+.1f points (%s). Beyond twice that swing: %s.'
            % (sd, kb[latest], latest, ", ".join(out[-8:]) if out else "none"))
    return '<p class="cap" style="color:var(--ink);font-weight:600">%s</p>%s<p class="cap">%s</p>' % (title, chart, note)


# ---------- 30+ to charge-off as a rating: level and peer gap ----------
def flow4(prod, who):
    return avg4({q_: 100 * v for q_, v in FLOW["%s|%s" % (prod, who)].items() if 0 <= v <= 2 and q_ >= "2011Q1"})


GQ = qrange("2011Q4", "2025Q4")


def rate_panels(prod, ylo, yhi, ticks, glim):
    ind, pg, kb = flow4(prod, "Industry"), flow4(prod, "Peer group"), flow4(prod, "KeyBank")
    o = scale([pg[q_] for q_ in sorted(pg)], "higher_is_worse", HW, LS, Z, True)
    lvl = svg_chart(GQ, [{"data": ind, "color": "var(--ink)", "w": 1.8, "dash": True, "name": "Industry"},
                         {"data": pg, "color": "var(--muted)", "w": 2.0, "name": "Peer group"},
                         {"data": kb, "color": "var(--key)", "w": 2.8, "name": "KeyBank"}],
                    ylo, yhi, ticks, lambda v: "%.0f%%" % v, h=210, zones=o["bounds"],
                    ytitle="% of 30+ (incl. nonaccrual) dollars charged off within two quarters, four-quarter average",
                    label="%s 30+ to charge-off with rating zones from the peer group's history" % prod)
    gap = {q_: kb[q_] - pg[q_] for q_ in kb if q_ in pg}
    go = scale([gap[q_] for q_ in sorted(gap)], "higher_is_worse", HW, LS, Z, False)
    fit = (go["worst"] - go["median"]) / go["spread_of_levels"]
    zb = go["bounds"] or scale([gap[q_] for q_ in sorted(gap)], "higher_is_worse", HW, LS, round(fit - 0.005, 2), False)["bounds"]
    gz = svg_chart(GQ, [{"data": gap, "color": "var(--key)", "w": 2.8, "name": "KeyBank minus peers"}],
                   -glim, glim, [-glim, -glim / 2, 0, glim / 2, glim], lambda v: "%+.0f" % v if v else "0", h=180, zones=zb,
                   ytitle="KeyBank minus peer group, points; up = KeyBank converting more delinquency to loss",
                   label="%s: KeyBank's gap to the peer group on 30+ to charge-off" % prod)
    last = sorted(kb)[-1]
    rate = lambda v, bd: 1 + sum(v >= x for x in bd)              # noqa: E731
    return lvl, gz, o["bounds"], rate(kb[last], o["bounds"]), gap[last], (rate(gap[last], zb), go["bounds"] is None, fit), last


c_l, c_g, c_b, c_r, c_gap, c_gr, c_last = rate_panels("Card", 60, 110, [60, 70, 80, 90, 100, 110], 30)
o_l, o_g, o_b, o_r, o_gap, o_gr, o_last = rate_panels("Other consumer", 0, 110, [0, 25, 50, 75, 100], 50)
RATE = ('<section class="box"><h2>30+ to charge-off as a rating: the level, and the gap to peers</h2>'
        '<p class="cap">Two ratings from the same measure, both by level, as the book rates everything else. The level: KeyBank&rsquo;s share of '
        '30+ (including nonaccrual) dollars charged off within two quarters, on rating zones drawn from the peer group&rsquo;s history at '
        'the agreed settings. The gap: KeyBank minus the peer group in the same quarter, on zones drawn from the gap&rsquo;s own history; '
        'this is &ldquo;performing worse than peers&rdquo;.</p>'
        '<h3>Card: the level</h3><div class="chart">%s</div>'
        '<p class="cap">Zones from the peer group: 2 begins %.1f%%, 3 %.1f%%, 4 %.1f%%, High %.1f%%. KeyBank %s: rates %d. KeyBank&rsquo;s 30+ '
        'includes its nonaccrual card loans, which most banks do not use, so its share reads lower than it would on the same definition.</p>'
        '<h3>Card: KeyBank minus peers</h3><div class="chart">%s</div><p class="cap">Now %+.1f points: rates %d. %s</p>'
        '<h3>Other consumer: the level</h3><div class="chart">%s</div>'
        '<p class="cap">Zones from the peer group: 2 begins %.1f%%, 3 %.1f%%, 4 %.1f%%, High %.1f%%. KeyBank %s: rates %d. Every source stepped '
        'up from about 35%% to 60&ndash;85%% from 2023, which looks like reporting and product mix rather than a collapse in cures, so lines '
        'drawn across the whole history flag everything since.</p>'
        '<h3>Other consumer: KeyBank minus peers</h3><div class="chart">%s</div><p class="cap">Now %+.1f points: rates %d. %s The gap is '
        'measured in the same quarter, so the industry-wide step in 2023 largely cancels out.</p></section>'
        % (c_l, c_b[0], c_b[1], c_b[2], c_b[3], c_last, c_r, c_g, c_gap, c_gr[0],
           ("At z 2.5 the method refuses the gap&rsquo;s own history; zones shown at z %.2f, the highest that fits." % (c_gr[2] - 0.005)) if c_gr[1] else "Zones at the agreed settings.",
           o_l, o_b[0], o_b[1], o_b[2], o_b[3], o_last, o_r, o_g, o_gap, o_gr[0],
           ("At z 2.5 the method refuses the gap&rsquo;s own history; zones shown at z %.2f, the highest that fits." % (o_gr[2] - 0.005)) if o_gr[1] else "Zones at the agreed settings."))

DIV = ('<section class="box"><h2>Roll-rate divergence: where KeyBank moves differently from the industry</h2>'
       '<p class="cap">For each step of the waterfall: KeyBank&rsquo;s change from a year earlier minus the industry&rsquo;s (both averaged '
       'over four quarters), and the same for the peer group. Common forces (charge-off rules, the economy, reporting) cancel out; what is '
       'left is the bank&rsquo;s own. Measured on movement, not level, so KeyBank&rsquo;s use of nonaccrual for cards and its small card '
       'book before 2013 do not create a gap by themselves. From 2011.</p>'
       '<h3>Card</h3>%s%s%s'
       '<h3>Other consumer</h3>%s%s%s'
       '<p class="cap">How far is far enough to act on, and over how many quarters, are settings to choose; the band shown is only a reading '
       'of how much this gap usually moves.</p></section>'
       % (div_chart("Card", 0, "Step 1: 30&ndash;89 rolling to 90+", 40), div_chart("Card", 1, "Step 2: 90+ to charge-off", 40),
          div_chart("Card", 2, "30+ to charge-off (all delinquent dollars charged off within two quarters)", 40),
          div_chart("Other consumer", 0, "Step 1: 30&ndash;89 rolling to 90+", 60), div_chart("Other consumer", 1, "Step 2: 90+ to charge-off", 60),
          div_chart("Other consumer", 2, "30+ to charge-off (all delinquent dollars charged off within two quarters)", 60)))
MOVE = ('<section class="box"><h2>Loss mitigation over time: is less delinquency turning into loss?</h2>'
        '<p class="cap">Each line is how much a step of the waterfall changed from a year earlier, after averaging it over four quarters. '
        'Up means more of the delinquent book is moving on toward loss (mitigation working less well); down means more is curing or '
        'being worked out. Levels above 100%% (other consumer) do not matter here: only the movement is drawn. Dotted lines mark 2009Q2, '
        '2020Q2 and 2023Q2.</p>'
        '<h3>Card</h3>%s%s%s'
        '<h3>Other consumer</h3>%s%s%s'
        '<p class="cap">Read the three together: the first step (30&ndash;89 rolling to 90+) is where cures show first; the second (90+ to '
        'charge-off) is where workouts and settlements show; the third is the combined share of delinquent dollars that end up charged off '
        '(one minus the estimated cure). KeyBank&rsquo;s card figures include nonaccrual loans, and its book was small before 2013, so its '
        'early movements are large.</p></section>'
        % (mv_chart("Card", 0, "Step 1: 30&ndash;89 rolling to 90+", 30), mv_chart("Card", 1, "Step 2: 90+ to charge-off", 30),
           mv_chart("Card", 2, "30+ to charge-off: share of delinquent dollars charged off", 30),
           mv_chart("Other consumer", 0, "Step 1: 30&ndash;89 rolling to 90+", 60), mv_chart("Other consumer", 1, "Step 2: 90+ to charge-off", 60),
           mv_chart("Other consumer", 2, "30+ to charge-off: share of delinquent dollars charged off", 60)))
WIN = ('<section class="box"><h2>90+ to charge-off: one quarter and two quarters later</h2>'
       '<p class="cap">For each quarter-end: gross charge-offs over the next quarter, and over the next two quarters, as a share of the '
       '90+ (including nonaccrual) dollars at that quarter-end. If everything in 90+ either charges off or cures within a quarter, the two '
       'lines sit close together; where the second runs well above the first, charge-offs are also coming from loans that were not yet '
       '90+ at the quarter-end.</p>'
       '<h3>Card, next quarter</h3><div class="chart">%s</div><h3>Card, next two quarters</h3><div class="chart">%s</div>'
       '<p class="cap">Card charges off at 180 days, so the 90+ bucket (90&ndash;179 days) clears within one quarter: the one-quarter figure '
       'is the 90+ roll to charge-off (about 80%% for the industry). The two-quarter figure adds the next wave, loans that were 30&ndash;89 '
       'at the quarter-end, so it runs about twice as high and is not a rate of the 90+ bucket.</p>'
       '<h3>Other consumer, next quarter</h3><div class="chart">%s</div><h3>Other consumer, next two quarters</h3><div class="chart">%s</div>'
       '<p class="cap">Closed-end loans charge off at 120 days, often inside a quarter without appearing in a quarter-end 90+ figure, so '
       'even the one-quarter figure can exceed 100%%. It measures how much is charged off relative to the visible 90+ stock, not a roll '
       'rate.</p></section>' % (win_chart("Card", 1, 150), win_chart("Card", 2, 250), win_chart("Other consumer", 1, 250),
                                win_chart("Other consumer", 2, 300)))
ROLLS = ('<section class="box"><h2>Estimated roll and cure, card and other consumer</h2>'
         '<p class="cap">Built from every bank&rsquo;s Call Report: 30&ndash;89, 90+ and nonaccrual dollars at each quarter-end, and gross '
         'charge-offs each quarter. Not tracked cohorts, so these are estimates of the waterfall, not true roll rates. Industry solid black, '
         'peer group dashed, KeyBank red.</p>'
         '<p class="cap">All charge-offs here are gross (before recoveries): recoveries arrive later and mostly come from loans '
         'charged off in earlier quarters. The waterfall in three steps: 30&ndash;89 to 90+, 90+ to charge-off, and the two together.</p>'
         '<h3>Step 1, card: the roll ratio, 90+ this quarter over 30&ndash;89 last quarter</h3><div class="chart">%s</div>'
         '<p class="cap">Above 1 because the 90+ bucket holds about three months of loans and 30&ndash;89 two. Its rise came before '
         'rising card charge-offs by 2&ndash;3 quarters, loosely (0.40 to 0.43 industry, 0.25 peers).</p>'
         '<h3>Step 2, card: gross charge-offs this quarter over 90+ last quarter</h3><div class="chart">%s</div>'
         '<p class="cap">Industry about 80&ndash;90%%: most of the 90+ bucket charges off in the next quarter, at 180 days. KeyBank '
         'has fallen to about 64%% because its 90+ includes nonaccrual card loans, which most banks do not use and which are not all '
         'on the way to charge-off. Peers ran low in 2008&ndash;2010 as delinquency piled up faster than it was charged off.</p>'
         '<h3>30+ to charge-off, card: share of delinquent dollars that end up charged off (steps 1 and 2 together)</h3><div class="chart">%s</div>'
         '<p class="cap">Charge-offs over the next two quarters &divide; (30&ndash;89 + 90+) at the quarter-end. Cards charge off at 180 days, so '
         'every delinquent dollar either charges off within two quarters or cures; one minus this is the estimated cure. About 80%% charge '
         'off; it rose to 85%% in 2009 and 88%% in 2023. It needs the next two quarters, so it is known six months late. KeyBank includes '
         'nonaccrual, which it uses for cards where most banks do not.</p>'
         '<h3>30+ to charge-off, other consumer</h3><div class="chart">%s</div>'
         '<p class="cap">Lower and less steady: 24&ndash;50%% before 2023, 64&ndash;81%% since. Closed-end loans charge off at 120 days and '
         'open-end at 180, and the line mixes student, auto (until 2011), unsecured and secured loans; it breaks at 2011 and 2024Q4.</p>'
         '<p class="cap">For other consumer there is no usable link from the roll ratio to charge-offs. A tracked cohort, internally, would separate rolling from curing directly.</p></section>' % (roll_card, stage2, flow_chart("Card"), flow_chart("Other consumer")))

PV = {k: _ph_bal("Average Purchase Volume by Credit Score Group: %s" % c) for k, c in
      (("lo", "< 660 Credit Score"), ("mid", "660-719 Credit Score"), ("hi", ">= 720 Credit Score"))}
PVG = {q_: 100 * (PV["lo"][q_] / PV["lo"][k4] - 1) for q_ in PV["lo"] for k4 in ["%dQ%s" % (int(q_[:4]) - 1, q_[5])] if k4 in PV["lo"]}
pv_lvl = svg_chart(qrange("2012Q3", "2026Q2"), [{"data": PV["hi"], "color": "var(--c-mtg)", "w": 2.0, "name": "720 and above"},
                                                {"data": PV["mid"], "color": "var(--c-he)", "w": 2.0, "name": "660-719"},
                                                {"data": PV["lo"], "color": "var(--c-card)", "w": 2.6, "name": "under 660"}],
                   0, 3000, [0, 1000, 2000, 3000], lambda v: "$%.0f" % v, h=210,
                   ytitle="average purchases per active account in the quarter, by score group",
                   label="Card purchase volume per active account by score group")
PVS = ('<section class="box"><h2>Card: are low-score borrowers spending more before losses rise?</h2>'
       '<p class="cap">Large banks (Philadelphia Fed), 2012 on: average purchases per active card account in the quarter, by score group.</p>'
       '<div class="chart">%s</div>'
       '<h3>Growth in purchases by accounts under 660 (moved 0 quarters) over the rise in card 30&ndash;89</h3>%s'
       '<p class="cap">No. When delinquency rises, accounts under 660 spend less in the same quarter (&minus;0.7 to &minus;0.85): they are '
       'at their limits, have had lines cut, or are delinquent. It does not move ahead of losses. This is purchases, not balances; no public '
       'series gives revolving balances by score group, so the weakest borrowers drawing their lines is best read from the share paying only '
       'the minimum and the most stretched tenth&rsquo;s utilization.</p></section>'
       % (pv_lvl, ov(PVG, 0, Y3089, qrange("2013Q3", "2026Q2"), "var(--c-card)", "growth in purchases, under 660", "rise in card 30-89")))
MINPAY_NOTE = ('<section class="box"><h2>Minimum payments and utilization: one signal or two?</h2>'
               '<p class="cap">The share of accounts paying only the minimum and the most stretched tenth&rsquo;s utilization move together: '
               'their yearly changes match at 0.92 (0.70 with 2020&ndash;2023 left out). They are largely the same borrowers. Median '
               'utilization overlaps less (0.42 without 2020&ndash;2023) and is the one with a small lead on delinquency, so it carries '
               'something the minimum-payment share does not.</p></section>')

t = (HERE / "template.html").read_text(encoding="utf-8")
style = t[:t.index("<main>")]
style = style.replace("<title>Refreshed FICO Evidence</title>", "<title>Early Warning Signals</title>")
html = (style + '<main><header style="display:grid;gap:8px"><div class="eyebrow">CONSUMER INDUSTRY ANALYSIS &middot; EARLY WARNING &middot; 17 OCT 2026</div>'
        '<h1>What turns before card losses</h1>'
        '<p class="lede">Only the thread under discussion: where each signal stands, what leads, what moves with delinquency. Public data; '
        'every chart names its source.</p></header>'
        + SUMMARY + RATE + U660S + PVS + MINPAY_NOTE + MOVE + DIV + ROLLS + WIN + NOW + CARD_ORIG
        + ('<section class="box"><h2>Card: banks easing standards (loan officer survey)</h2><p class="cap">Net share of banks easing card '
           'standards, 1996 on, moved 11 quarters later and laid over the rise in card charge-offs. Match 0.63; 0.92 with 2020&ndash;2023 left out. '
           'In the short run it runs the other way: banks tighten while losses climb.</p>%s</section>'
           % ov(EASE, 11, YNCO, qrange("2007Q1", "2029Q1"), "var(--c-mtg)", "banks easing, 11 quarters earlier", "rise in card charge-offs"))
        + STRAIN + LAG.replace("When does the score move: before delinquency, or with it?", "Refreshed FICO: before delinquency, or with it?") + CROSS + MDQ + "</main>")
(HERE / "focus.html").write_text(html, encoding="utf-8")
print("written", len(html))
