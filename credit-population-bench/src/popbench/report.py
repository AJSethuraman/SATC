"""Workpaper HTML export — a committee-grade examination report from a run.

Renders an :class:`~popbench.engine.AnalysisResult` into a self-contained HTML
workpaper in the house KeyBank palette (INK header band, KEY_RED accent, CANVAS
tiles, CRIMSON alerts). Every figure is the engine's own output; each rate
carries both a dollar and a count basis. Deterministic and offline.

This is a *runtime* artifact and may contain real borrower loan numbers (the PII
boundary: it runs only on bank equipment). The shipped/demo report carries only
synthetic identities.
"""

from __future__ import annotations

import html

import pandas as pd

from popbench import bands, contract, metrics
from popbench.cohorts import Cohort, Rule, ab_compare


def _usd(x): return "&mdash;" if x is None else f"${x:,.0f}"
def _usdk(x):
    if x is None: return "&mdash;"
    return f"${x/1e6:.1f}M" if abs(x) >= 1e6 else f"${x/1e3:.0f}k"
def _pct(x, d=1): return "&mdash;" if x is None else f"{x*100:.{d}f}%"
def _fico(x): return "&mdash;" if x is None else f"{x:.0f}"
def _rowsjoin(x): return "\n".join(x)


def render(result, title: str = "Consumer portfolio review") -> str:
    """Return a complete HTML workpaper for ``result`` (an AnalysisResult)."""
    clean = result.clean
    pop_n = int(len(clean))
    pop_b = float(clean["current_balance"].sum())
    has_dpd = "dpd_min" in clean.columns

    wa = {w.attribute: w for w in metrics.weighted_average_table(
        clean, ["fico_orig", "fico_refresh", "dti", "rate", "ltv"])}

    d90b = float(clean.loc[clean["dpd_min"] >= 90, "current_balance"].sum()) if has_dpd else 0.0
    d90c = int((clean["dpd_min"] >= 90).sum()) if has_dpd else 0

    kpis = [("Loans", f"{pop_n:,}"), ("Total UPB", _usdk(pop_b))]
    if "fico_orig" in wa:
        kpis.append(("WA FICO", _fico(wa["fico_orig"].dollar_weighted)))
    if "dti" in wa:
        kpis.append(("WA DTI", _pct(wa["dti"].dollar_weighted)))
    if "rate" in wa:
        kpis.append(("WA rate", _pct(wa["rate"].dollar_weighted, 2)))
    if has_dpd:
        kpis.append(("90+ DPD ($ / #)",
                     f"{_pct(d90b/pop_b if pop_b else 0)} <span class='sub'>/ {_pct(d90c/pop_n if pop_n else 0)}</span>"))
    if result.charge_off is not None:
        kpis.append(("Gross charge-off ($)", _pct(result.charge_off.dollar_rate, 2)))
    kpi_html = _rowsjoin(f"<div class='kpi'><span class='k'>{k}</span><span class='v'>{v}</span></div>"
                         for k, v in kpis)

    sections = [_masthead(title, pop_n, pop_b), f"<section class='kpis'>{kpi_html}</section>"]
    if result.delinquency is not None:
        sections.append(_delinquency(result.delinquency))
    grid = []
    if has_dpd and "fico_orig" in clean.columns:
        grid.append(_fico_gradient(clean, pop_b))
    if result.urccp:
        grid.append(_urccp(result.urccp))
    if grid:
        sections.append(f"<div class='grid'>{''.join(grid)}</div>")
    if result.vintage_rows:
        sections.append(_vintage(result.vintage_rows, result.triangle))
    grid2 = []
    if result.cohorts is not None:
        grid2.append(_cohorts(result.cohorts))
    if has_dpd and "fico_orig" in clean.columns:
        grid2.append(_ab(clean))
    if grid2:
        sections.append(f"<div class='grid'>{''.join(grid2)}</div>")
    if result.sampling_doc is not None:
        sections.append(_sample(result.sampling_doc))
    sections.append(_colophon())

    return _CSS + "<div class='wrap'>" + "".join(sections) + "</div>"


def _masthead(title, n, b):
    return (f"<header class='masthead'><div class='eyebrow'>Consumer Credit Population "
            f"Bench &middot; examination workpaper</div>"
            f"<h1>{html.escape(title)} &mdash; {n:,} loans, {_usdk(b)}</h1>"
            f"<p class='dek'>Real engine output; every rate carries both a dollar and a count "
            f"basis. URCCP thresholds come from the shared credit-core.</p></header>")


def _delinquency(delq):
    maxd = max((d.dollar_rate for d in delq["per_bucket"]), default=0) or 1
    per = _rowsjoin(
        f"<tr><td class='lbl'>{d.label}</td><td class='n'>{d.count:,}</td><td class='n'>{_pct(d.count_rate)}</td>"
        f"<td class='n'>{_usd(d.dollars)}</td><td class='n strong'>{_pct(d.dollar_rate)}</td>"
        f"<td class='bar'><i style='width:{d.dollar_rate/maxd*100:.0f}%'></i></td></tr>"
        for d in delq["per_bucket"])
    cum = _rowsjoin(
        f"<tr class='cum'><td class='lbl'>{d.label}</td><td class='n'>{d.count:,}</td>"
        f"<td class='n'>{_pct(d.count_rate)}</td><td class='n'>{_usd(d.dollars)}</td>"
        f"<td class='n strong'>{_pct(d.dollar_rate)}</td><td></td></tr>" for d in delq["cumulative"])
    return (f"<article class='card wide'><h2>Delinquency distribution <span class='tag'>both bases</span></h2>"
            f"<p class='cap'>the dollar bar shows why both are reported</p>"
            f"<table><thead><tr><th>Bucket</th><th class='n'>#</th><th class='n'>count %</th>"
            f"<th class='n'>$</th><th class='n'>dollar %</th><th style='width:22%'>dollar %</th></tr></thead>"
            f"<tbody>{per}{cum}</tbody></table></article>")


def _fico_gradient(clean, pop_b):
    sch = bands.get_preset("fico_orig", "cfpb")
    work = clean.copy()
    work["__fb__"] = sch.assign(work["fico_orig"]).astype("object")
    rows = []
    for lab in sch.labels:
        g = work[work["__fb__"] == lab]
        if not len(g):
            continue
        b = float(g["current_balance"].sum())
        r90 = (float(g.loc[g["dpd_min"] >= 90, "current_balance"].sum()) / b) if b else 0
        wdti = metrics.weighted_average(g, "dti").dollar_weighted if "dti" in g else None
        heat = min(1.0, r90 / 0.35)
        rows.append(f"<tr><td class='lbl'>{lab}</td><td class='n'>{len(g):,}</td><td class='n'>{_usdk(b)}</td>"
                    f"<td class='n'>{_pct(b/pop_b if pop_b else 0)}</td><td class='n'>{_pct(wdti)}</td>"
                    f"<td class='n heat' style='--h:{heat:.2f}'>{_pct(r90)}</td></tr>")
    return (f"<article class='card'><h2>FICO band &mdash; risk gradient</h2>"
            f"<p class='cap'>CFPB six-tier; 90+ dollar rate heat-shaded</p>"
            f"<table><thead><tr><th>Band</th><th class='n'>#</th><th class='n'>UPB</th>"
            f"<th class='n'>% $</th><th class='n'>WA DTI</th><th class='n'>90+ $</th></tr></thead>"
            f"<tbody>{_rowsjoin(rows)}</tbody></table></article>")


def _urccp(urccp):
    def loss(u): return "&mdash;" if u.loss_count is None else f"<span class='chip crit'>{u.loss_count}</span>"
    rows = _rowsjoin(
        f"<tr><td class='lbl'>{u.structure.replace('_',' ')}</td><td class='n'>{u.count:,}</td>"
        f"<td class='n'>{_usdk(u.balance)}</td><td class='n'><span class='chip warn'>{u.substandard_count:,}</span></td>"
        f"<td class='n'>{_usd(u.substandard_dollars)}</td><td class='n'>{loss(u)}</td>"
        f"<td class='n'>{_usd(u.loss_dollars)}</td></tr>" for u in urccp)
    return (f"<article class='card'><h2>URCCP classification <span class='tag'>65 FR 36903</span></h2>"
            f"<p class='cap'>shared floors; residential Loss is an attestation</p>"
            f"<table><thead><tr><th>Structure</th><th class='n'>#</th><th class='n'>UPB</th>"
            f"<th class='n'>Sub #</th><th class='n'>Sub $</th><th class='n'>Loss #</th><th class='n'>Loss $</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></article>")


def _vintage(vrows, tri):
    vin = _rowsjoin(
        f"<tr><td class='lbl'>{v.vintage}</td><td class='n'>{v.orig_count:,}</td><td class='n'>{_usdk(v.orig_balance)}</td>"
        f"<td class='n'>{v.co_count:,}</td><td class='n strong'>{_pct(v.cum_gross_loss_rate,2)}</td>"
        f"<td class='n'>{_pct(v.ever90_balance_rate)}</td></tr>" for v in vrows)
    tri_html = ""
    if tri is not None:
        maxl = max((max(r.values()) for r in tri.rows.values()), default=0) or 1
        head = "".join(f"<th class='n'>MOB {mb}</th>" for mb in tri.mob_bounds)
        body = _rowsjoin("<tr><td class='lbl'>" + v + "</td>" + "".join(
            f"<td class='n tcell' style='--h:{min(1.0,tri.rows[v][mb]/maxl):.2f}'>"
            f"{_pct(tri.rows[v][mb],2) if tri.rows[v][mb] else '&middot;'}</td>" for mb in tri.mob_bounds)
            + "</tr>" for v in sorted(tri.rows))
        tri_html = (f"<div><p class='cap' style='margin-bottom:8px'>Cumulative gross-loss rate by MOB</p>"
                    f"<div class='scroll'><table class='tri'><thead><tr><th>vintage</th>{head}</tr></thead>"
                    f"<tbody>{body}</tbody></table></div></div>")
    return (f"<article class='card wide'><h2>Vintage analysis <span class='tag'>single file</span></h2>"
            f"<p class='cap'>gross loss (no recoveries); triangle times each charge-off by orig&rarr;charge-off MOB</p>"
            f"<div class='split2'><table><thead><tr><th>Vintage</th><th class='n'>orig #</th><th class='n'>orig $</th>"
            f"<th class='n'>CO #</th><th class='n'>cum loss</th><th class='n'>ever-90+</th></tr></thead>"
            f"<tbody>{vin}</tbody></table>{tri_html}</div></article>")


def _cohorts(cc):
    reports = _rowsjoin(
        f"<tr><td class='lbl'>{html.escape(r.label)}</td><td class='n'>{r.count:,}</td>"
        f"<td class='n'>{_usdk(r.balance)}</td><td class='n'>{_pct(r.balance/cc.population_dollars if cc.population_dollars else 0)}</td></tr>"
        for r in cc.reports)
    lab = {r.id: r.label for r in cc.reports}
    ov = _rowsjoin(
        f"<tr><td class='lbl'>{html.escape(lab[a])} <span class='x'>&times;</span> {html.escape(lab[b])}</td>"
        f"<td class='n'>{n:,}</td><td class='n'>{_usdk(cc.overlap_dollars[(a,b)])}</td></tr>"
        for (a, b), n in cc.overlap_count.items())
    return (f"<article class='card accent'><h2>Derived cohorts &mdash; never summed</h2>"
            f"<p class='cap'>independent reports + overlap + residual</p>"
            f"<table><thead><tr><th>Cohort</th><th class='n'>#</th><th class='n'>UPB</th><th class='n'>% $</th></tr></thead>"
            f"<tbody>{reports}</tbody></table>"
            f"<table style='margin-top:12px'><thead><tr><th>Pairwise overlap</th><th class='n'>#</th><th class='n'>$</th></tr></thead>"
            f"<tbody>{ov}<tr class='resid'><td class='lbl'>In no cohort (residual)</td>"
            f"<td class='n'>{cc.residual_count:,}</td><td class='n'>{_usdk(cc.residual_dollars)}</td></tr></tbody></table></article>")


def _ab(clean):
    ab = ab_compare(clean, Cohort("s", "subprime", (Rule("fico_orig", "<", 660),)),
                    Cohort("p", "prime+", (Rule("fico_orig", ">=", 660),)),
                    attributes=("fico_orig", "dti", "rate"))
    def f(v, a): return "&mdash;" if v is None else (f"{v:.0f}" if a == "fico_orig" else _pct(v, 2 if a == "rate" else 1))
    rows = _rowsjoin(
        f"<tr class='{'div' if x.diverges else ''}'><td class='lbl'>{contract.get(x.attribute).label}</td>"
        f"<td class='n'>{f(x.a_dollar,x.attribute)} / {f(x.a_count,x.attribute)}</td>"
        f"<td class='n'>{f(x.b_dollar,x.attribute)} / {f(x.b_count,x.attribute)}</td></tr>" for x in ab)
    return (f"<article class='card'><h2>Subprime vs prime+ <span class='tag'>A / B</span></h2>"
            f"<p class='cap'>FICO&lt;660 vs &ge;660, dollar / count</p>"
            f"<table><thead><tr><th>Metric</th><th class='n'>Subprime</th><th class='n'>Prime+</th></tr></thead>"
            f"<tbody>{rows}</tbody></table><p class='mini'>Rows in red: the bases disagree on direction.</p></article>")


def _sample(occ):
    focus = "<span class='chip crit'>focus</span>"
    cov = _rowsjoin(
        f"<tr><td class='lbl'>{c.value}{' ' + focus if c.flagged else ''}</td>"
        f"<td class='n'>{c.sel_count:,}/{c.seg_count:,}</td><td class='n'>{_pct(c.count_coverage)}</td>"
        f"<td class='n strong'>{_pct(c.dollar_coverage)}</td></tr>" for c in occ.coverage)
    return (f"<article class='card wide sample'><h2>Judgmental sample &amp; OCC documentation</h2>"
            f"<div class='split2'><div><p class='cap'>coverage per segment ($ and count):</p>"
            f"<table><thead><tr><th>Segment</th><th class='n'>selected</th><th class='n'>count cov</th>"
            f"<th class='n'>dollar cov</th></tr></thead><tbody>{cov}</tbody></table></div>"
            f"<dl class='occ'><dt>Population</dt><dd>{occ.population_count:,} / {_usd(occ.population_dollars)}</dd>"
            f"<dt>Areas of focus</dt><dd>{html.escape('; '.join(occ.areas_of_focus))}</dd>"
            f"<dt>Sample size</dt><dd>{occ.sample_count:,} / {_usd(occ.sample_dollars)}</dd>"
            f"<dt>Coverage</dt><dd>{_pct(occ.overall_dollar_coverage)} $ &middot; {_pct(occ.overall_count_coverage)} #</dd>"
            f"<dt>Rationale</dt><dd class='ra'>{html.escape(occ.selection_rationale)}</dd></dl></div>"
            f"<div class='banner'>{html.escape(occ.non_extrapolable)}</div></article>")


def _colophon():
    return ("<footer class='colophon'><span>Deterministic pandas engine behind an .xlsm surface "
            "&middot; URCCP from shared satc_credit_core (never forked)</span>"
            "<span class='pii'>PII boundary: runtime workbook may hold real borrower data "
            "(bank equipment only); shipped/demo output is synthetic.</span></footer>")


_CSS = """<style>
:root{--paper:#faf8f4;--card:#fff;--tile:#f4f1ec;--band:#0a0908;--ink:#16130f;--slate:#57534b;--hair:#e4dfd5;--stone:#b9b4ac;--key-red:#cc0000;--crimson:#960019;--red-soft:#f7dede;--warn-bg:#efd7cf;--warn:#8a3a1a;--ok:#1e7a47;--resid:#efe9df;--band-ink:#f4f1ec;--display:Arial,"Helvetica Neue",Helvetica,sans-serif;--sans:Calibri,system-ui,"Segoe UI",Roboto,sans-serif;--mono:Consolas,ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--paper:#0a0908;--card:#16130f;--tile:#1e1a15;--band:#000;--ink:#f1ece3;--slate:#b9b4ac;--hair:#2c2720;--stone:#57534b;--key-red:#e23b3b;--crimson:#e8788a;--red-soft:#2e1719;--warn-bg:#33231c;--warn:#e0a88f;--ok:#7fce9f;--resid:#211c16}}
:root[data-theme="light"]{--paper:#faf8f4;--card:#fff;--tile:#f4f1ec;--band:#0a0908;--ink:#16130f;--slate:#57534b;--hair:#e4dfd5;--key-red:#cc0000;--crimson:#960019;--red-soft:#f7dede;--warn-bg:#efd7cf;--warn:#8a3a1a;--resid:#efe9df}
:root[data-theme="dark"]{--paper:#0a0908;--card:#16130f;--tile:#1e1a15;--band:#000;--ink:#f1ece3;--slate:#b9b4ac;--hair:#2c2720;--key-red:#e23b3b;--crimson:#e8788a;--red-soft:#2e1719;--warn-bg:#33231c;--warn:#e0a88f;--resid:#211c16}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.5}
.wrap{max-width:1140px;margin:0 auto;padding:clamp(18px,3.5vw,48px)}
.masthead{background:var(--band);color:var(--band-ink);border-radius:12px;padding:26px 28px;margin-bottom:22px;border-top:4px solid var(--key-red)}
.eyebrow{font:700 12px/1 var(--display);letter-spacing:.16em;text-transform:uppercase;color:var(--key-red);margin-bottom:12px}
h1{font-family:var(--display);font-weight:700;font-size:clamp(24px,3.6vw,36px);margin:0 0 10px}
.dek{max-width:82ch;color:#cfc7ba;font-size:14px;margin:0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:var(--tile);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;border-left:3px solid var(--key-red)}
.kpi .k{font:700 10.5px/1.3 var(--display);letter-spacing:.05em;text-transform:uppercase;color:var(--slate)}
.kpi .v{font-family:var(--display);font-weight:700;font-size:22px;font-variant-numeric:tabular-nums}
.kpi .sub{color:var(--slate);font-weight:400;font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--hair);border-radius:12px;padding:20px 22px;margin-bottom:16px}
.card.wide{grid-column:1/-1}.card.accent{border-top:3px solid var(--key-red)}
h2{font-family:var(--display);font-weight:700;font-size:18px;margin:0 0 3px;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.tag{font:700 10px/1 var(--display);letter-spacing:.06em;text-transform:uppercase;color:var(--crimson);background:var(--red-soft);padding:4px 7px;border-radius:5px}
.cap{color:var(--slate);font-size:12.5px;margin:0 0 14px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{text-align:left;font:700 10.5px/1.4 var(--display);letter-spacing:.04em;text-transform:uppercase;color:var(--slate);border-bottom:2px solid var(--band);padding:0 9px 7px 0}
th.n{text-align:right}tbody td{padding:7px 9px 7px 0;border-bottom:1px solid var(--hair)}tbody tr:last-child td{border-bottom:none}
.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.lbl{font-weight:600}.strong{font-weight:700;color:var(--key-red)}.x{color:var(--stone)}
.chip{display:inline-block;font:700 10px/1 var(--display);padding:3px 6px;border-radius:4px}
.chip.warn{background:var(--warn-bg);color:var(--warn)}.chip.crit{background:var(--red-soft);color:var(--crimson)}
.bar i{display:block;height:9px;background:var(--key-red);border-radius:2px;min-width:2px}
tr.cum td{border-top:2px solid var(--band);background:var(--tile);font-weight:600}
.heat{background:color-mix(in srgb,var(--key-red) calc(var(--h)*72%),var(--tile));font-weight:700}
.tri td.tcell{background:color-mix(in srgb,var(--key-red) calc(var(--h)*82%),var(--tile));font-weight:600}
.tri th,.tri td{padding:6px 9px;font-size:12.5px}
.split2{display:grid;grid-template-columns:1fr 1fr;gap:24px}.resid td{background:var(--resid);font-weight:700}.scroll{overflow-x:auto}
tr.div td,tr.div .lbl{color:var(--crimson)}
.occ{margin:0;display:grid;grid-template-columns:auto 1fr;gap:7px 16px;font-size:13px}
.occ dt{font:700 10.5px/1.5 var(--display);letter-spacing:.04em;text-transform:uppercase;color:var(--slate)}.occ dd{margin:0}.occ .ra{font-size:12px;color:var(--slate)}
.banner{margin-top:16px;background:var(--red-soft);color:var(--crimson);border-left:3px solid var(--crimson);border-radius:6px;padding:11px 14px;font:700 12.5px/1.45 var(--sans)}
.mini{color:var(--slate);font-size:11.5px;margin:10px 0 0;font-style:italic}
.colophon{margin-top:28px;padding-top:16px;border-top:2px solid var(--band);display:flex;flex-direction:column;gap:6px;color:var(--slate);font-size:11.5px}.colophon .pii{color:var(--crimson)}
@media (max-width:820px){.grid,.split2{grid-template-columns:1fr}}
</style>"""
