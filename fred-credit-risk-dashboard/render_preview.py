#!/usr/bin/env python3
"""Render the FRED Credit-Risk Dashboard (KeyBank style) to HTML for preview.

Excel/LibreOffice can't run here, so this reproduces what the workbook shows:
it uses the SAME DemoProvider + runner transforms that fill the workbook, and
the SAME keybank_style tokens, then draws each tab as HTML with live SVG
sparklines and trend charts. The numbers match the .xlsm in demo mode.
"""
import os
import sys
import math

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)

import pandas as pd
import runner as R
import series_seed as SEED
import build_workbook as BW
import keybank_style as KB
from datetime import date

ASOF = date(2026, 3, 1)


# ---------- colour helpers ----------
def _hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    a, b = _hx(a), _hx(b)
    return "#" + "".join(f"{int(round(a[i] + (b[i] - a[i]) * t)):02x}" for i in range(3))


def z_heat(z):
    if z is None or (isinstance(z, float) and math.isnan(z)):
        return "transparent"
    z = max(-2.0, min(2.0, z))
    if z <= 0:
        return _mix(KB.HEAT_MID, KB.HEAT_GOOD, -z / 2)
    return _mix(KB.HEAT_MID, KB.HEAT_BAD, z / 2)


def yoy_heat(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "transparent"
    v = max(-10.0, min(10.0, v))
    if v <= 0:
        return _mix("FFFFFF", KB.HEAT_BAD, -v / 10)
    return _mix("FFFFFF", KB.HEAT_GOOD, v / 10)


def sparkline(vals_old_to_new, w=120, h=26):
    pts = [v for v in vals_old_to_new if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    n = len(pts)
    xs = [4 + i * (w - 8) / (n - 1) for i in range(n)]
    ys = [h - 3 - (v - lo) / rng * (h - 6) for v in pts]
    path = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{ys[i]:.1f}" for i in range(n))
    last = f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.6" fill="#CC0000"/>'
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<path d="{path}" fill="none" stroke="#57534B" stroke-width="1.3"/>{last}</svg>')


def trend_chart_svg(series, title, w=520, h=190):
    # series: list of (name, color, [values old->new]); shared x of len 12
    pad_l, pad_b, pad_t, pad_r = 38, 24, 26, 12
    allv = [v for _, _, vs in series for v in vs if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not allv:
        return ""
    lo, hi = min(allv), max(allv)
    rng = (hi - lo) or 1.0
    n = max(len(vs) for _, _, vs in series)
    plot_w, plot_h = w - pad_l - pad_r, h - pad_b - pad_t
    def X(i): return pad_l + i * plot_w / (n - 1)
    def Y(v): return pad_t + plot_h - (v - lo) / rng * plot_h
    grid = ""
    for g in range(4):
        gy = pad_t + g * plot_h / 3
        val = hi - g * rng / 3
        grid += f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w-pad_r}" y2="{gy:.1f}" stroke="#E7E2D8"/>'
        grid += f'<text x="{pad_l-6}" y="{gy+3:.1f}" font-size="9" fill="#57534B" text-anchor="end">{val:.1f}</text>'
    lines, legend = "", ""
    for k, (name, color, vs) in enumerate(series):
        pts = [(X(i), Y(v)) for i, v in enumerate(vs) if v is not None and not (isinstance(v, float) and math.isnan(v))]
        if len(pts) > 1:
            d = " ".join(f"{'M' if i==0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
            lines += f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.2"/>'
            lines += f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{color}"/>'
        legend += (f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:18px">'
                   f'<span style="width:14px;height:3px;background:{color};display:inline-block"></span>'
                   f'<span style="font:11px Calibri,sans-serif;color:#16130F">{name}</span></span>')
    svg = (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{grid}{lines}</svg>')
    return (f'<div style="background:#fff;border:1px solid #E7E2D8;border-radius:4px;padding:8px 10px;margin:10px 0">'
            f'<div style="font:bold 11px Arial;color:#16130F;margin-bottom:2px">{title}</div>'
            f'{svg}<div style="margin-top:4px">{legend}</div></div>')


# ---------- data (same path the workbook uses) ----------
def gather():
    cfg = R.parse_config(BW.config_rows())
    specs = cfg.series
    prov = R.DemoProvider(asof=ASOF)
    data = {}
    for s in specs:
        if s.is_dead:
            continue
        # keep NaNs (blanks) exactly as the runner writes them into the raw block,
        # so the preview's positional/window math matches the workbook formulas.
        data[s.series_id] = prov.fetch(s.series_id)
    return cfg, specs, data


def _ok(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def series_metrics(s, ser):
    ppy = R.periods_per_year(s.frequency)
    nf = list(ser.sort_index().values)[::-1]          # newest-first, NaNs kept
    latest = nf[0] if nf and _ok(nf[0]) else None
    prior = nf[1] if len(nf) > 1 and _ok(nf[1]) else None
    yago = nf[ppy] if len(nf) > ppy and _ok(nf[ppy]) else None
    yoy = ((latest - yago) / yago * 100) if (_ok(latest) and _ok(yago) and yago != 0) else None
    win = nf[:8]
    ws = pd.Series(win, dtype="float64")              # mean/std skip NaN, like Excel
    mean, std = ws.mean(), ws.std(ddof=1)
    z = ((latest - mean) / std) if (_ok(latest) and _ok(std) and std != 0) else None
    return latest, prior, yoy, z, win[::-1]            # window old->new for sparkline


# ---------- html ----------
def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def dashboard_html(title, subtitle, lane, specs, data, cfg):
    rows = sorted([s for s in specs if s.dashboard_capable and not s.is_dead and s.lane == lane],
                  key=lambda s: (s.category, s.series_id))
    zsum, n_alert, n_tight = [], 0, 0
    body = ""
    chart_series = []
    palette = ["#CC0000", "#0A0908"]
    for s in rows:
        if s.series_id not in data:
            continue
        latest, prior, yoy, z, win = series_metrics(s, data[s.series_id])
        if z is not None and not math.isnan(z):
            zsum.append(z)
        flag = ""
        if s.alert_rule == "zscore" and z is not None and z >= cfg.zscore_band:
            flag, n_alert = "⚠ ALERT", n_alert + 1
        elif s.alert_rule == "sloos_level" and latest is not None and latest >= cfg.sloos_band:
            flag, n_tight = "⚠ TIGHTENING", n_tight + 1
        if len(chart_series) < 2:
            full = list(data[s.series_id].values)[-12:]
            chart_series.append((s.title[:34], palette[len(chart_series)], full))
        tier = BW._tier(s.series_id)
        flag_cell = ""
        if flag == "⚠ ALERT":
            flag_cell = f'<td style="background:#F7DEDE;color:#960019;font-weight:bold;text-align:center">{flag}</td>'
        elif flag:
            flag_cell = f'<td style="background:#E4DFD5;color:#57534B;font-weight:bold;text-align:center">{flag}</td>'
        else:
            flag_cell = '<td></td>'
        def num(v, f="{:.2f}"):
            return f.format(v) if (v is not None and not (isinstance(v, float) and math.isnan(v))) else "—"
        body += (
            f'<tr>'
            f'<td>{esc(tier)}</td>'
            f'<td class="mut">{esc(s.category)}</td>'
            f'<td class="mono">{esc(s.series_id)}</td>'
            f'<td>{esc(s.title)}</td>'
            f'<td class="num">{num(latest)}</td>'
            f'<td class="num">{num(prior)}</td>'
            f'<td class="num">{num(yoy,"{:.1f}")}</td>'
            f'<td class="num" style="background:{z_heat(z)}">{num(z)}</td>'
            f'<td style="text-align:center">{sparkline(win)}</td>'
            f'{flag_cell}'
            f'</tr>')
    stress = (sum(zsum) / len(zsum)) if zsum else 0.0
    kpis = [("PORTFOLIO STRESS INDEX", f"{stress:.2f}", "8-qtr composite z-score", "#CC0000"),
            ("SERIES IN ALERT", f"{n_alert}", f"of {len(rows)} {lane}", "#CC0000"),
            ("TIGHTENING SIGNALS", f"{n_tight}", "SLOOS net tightening", "#0A0908")]
    kpi_html = "".join(
        f'<div class="kpi" style="border-top:3px solid {acc}">'
        f'<div class="kpi-l">{lab}</div><div class="kpi-v">{val}</div><div class="kpi-s">{sub}</div></div>'
        for lab, val, sub, acc in kpis)
    chart = trend_chart_svg(chart_series, f"{title} — trailing 12 quarters")
    return f"""
    <section>
      <div class="banner">
        <div class="b-title">{esc(title)}</div>
        <div class="b-sub">{esc(subtitle)}</div>
        <div class="b-status">Last run&nbsp; {ASOF.isoformat()}<br><span class="mut2">Pulled 146/147 · 0 stale · {n_alert} alerts &nbsp;·&nbsp; Member FDIC</span></div>
      </div>
      <div class="kpis">{kpi_html}</div>
      {chart}
      <table>
        <thead><tr>
          <th>Tier</th><th>Category</th><th>Series ID</th><th>Title</th>
          <th class="num">Latest</th><th class="num">Prior</th><th class="num">YoY %</th>
          <th class="num">Z-score (8)</th><th style="text-align:center">Trend (8q)</th><th style="text-align:center">Flag</th>
        </tr></thead>
        <tbody>{body}</tbody>
      </table>
    </section>"""


def watchlist_html(specs, data):
    wl = [s for s in R.watchlist_series(specs) if s.series_id in data]
    recs = []
    for s in wl:
        latest, prior, yoy, z, win = series_metrics(s, data[s.series_id])
        recs.append((s, latest, yoy, win))
    ranked = sorted([r for r in recs if r[2] is not None], key=lambda r: r[2])
    rank_of = {id(r): i + 1 for i, r in enumerate(ranked)}
    body = ""
    for s, latest, yoy, win in recs:
        geo = BW._geo_label(s)
        src = BW._source(s.category)
        rk = rank_of.get(id((s, latest, yoy, win)), "")
        # recompute rank lookup safely
        rk = next((i + 1 for i, r in enumerate(ranked) if r[0].series_id == s.series_id), "")
        def num(v, f="{:.1f}"):
            return f.format(v) if (v is not None and not (isinstance(v, float) and math.isnan(v))) else "—"
        body += (
            f'<tr><td>{esc(geo)}</td><td class="mono">{esc(s.series_id)}</td><td class="mut">{esc(src)}</td>'
            f'<td class="num">{num(latest)}</td>'
            f'<td class="num" style="background:{yoy_heat(yoy)}">{num(yoy)}</td>'
            f'<td class="num">{rk}</td>'
            f'<td style="text-align:center">{sparkline(win)}</td></tr>')
    return f"""
    <section>
      <div class="banner">
        <div class="b-title">Watchlist_Geo — Geographic Stress Watchlist</div>
        <div class="b-sub">States &amp; metros ranked by house-price deterioration (FHFA / Case-Shiller).</div>
      </div>
      <div class="gate">Geographic stress watchlist — apply against portfolio collateral location manually.
      National credit-quality series are excluded by design; they cannot localize a portfolio subset.</div>
      <table>
        <thead><tr><th>Geography</th><th>Series ID</th><th>Source</th>
          <th class="num">Latest</th><th class="num">YoY %</th><th class="num">Rank</th>
          <th style="text-align:center">Trend</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </section>"""


def main():
    cfg, specs, data = gather()
    parts = [
        dashboard_html("Consumer Credit-Risk Dashboard",
                       "Charge-offs, delinquencies, G.19, debt-service, SLOOS — national, bank-tier where available.",
                       "consumer", specs, data, cfg),
        dashboard_html("Commercial Credit-Risk Dashboard",
                       "C&I, CRE, all-loans charge-offs/delinquencies + SLOOS diffusion — national.",
                       "commercial", specs, data, cfg),
        dashboard_html("Price Dashboard",
                       "National house-price indices + commercial-real-estate price context.",
                       "price", specs, data, cfg),
        watchlist_html(specs, data),
    ]
    css = """
    body{margin:0;background:#E4DECF;color:#16130F;font-family:Calibri,Carlito,Arial,sans-serif;padding:28px}
    .wrap{max-width:1180px;margin:0 auto}
    .note{font:12px Calibri;color:#57534B;background:#F4F1EC;border-left:3px solid #CC0000;padding:10px 14px;margin:0 0 22px;border-radius:3px}
    section{background:#fff;border-radius:10px;overflow:hidden;margin-bottom:30px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
    .banner{background:#0A0908;color:#fff;padding:18px 22px;border-bottom:3px solid #CC0000;position:relative}
    .b-title{font:bold 18px Arial;letter-spacing:.2px}
    .b-sub{font:12px Calibri;color:#B9B4AC;margin-top:3px;max-width:760px}
    .b-status{position:absolute;top:16px;right:22px;text-align:right;font:11px Calibri;color:#B9B4AC}
    .mut2{font-size:10px;color:#8a857c}
    .kpis{display:flex;gap:14px;padding:16px 22px 4px}
    .kpi{flex:1;background:#F4F1EC;border-radius:4px;padding:12px 14px}
    .kpi-l{font:bold 9px Arial;letter-spacing:.6px;color:#57534B}
    .kpi-v{font:bold 30px Arial;color:#0A0908;line-height:1.1;margin:2px 0}
    .kpi-s{font:11px Calibri;color:#57534B}
    table{border-collapse:collapse;width:100%;font:12px Calibri;margin-top:6px}
    thead th{background:#0A0908;color:#fff;font:bold 11px Arial;text-align:left;padding:7px 9px;position:sticky;top:0}
    th.num{text-align:right}
    tbody td{padding:5px 9px;border-bottom:1px solid #EFEBE3;vertical-align:middle}
    td.num{text-align:right;font-variant-numeric:tabular-nums}
    td.mono{font-family:Consolas,monospace;font-size:11px}
    td.mut{color:#57534B}
    tbody tr:hover{background:#FAF8F4}
    .gate{background:#F7DEDE;color:#960019;font:bold 12px Arial;padding:12px 18px;border-bottom:1px solid #E3C9C9}
    .charts{padding:0 22px}
    h1{font:bold 22px Arial;color:#0A0908;margin:0 0 4px}
    .sub{font:13px Calibri;color:#57534B;margin:0 0 18px}
    """
    # move trend chart inside padding
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>
    <body><div class="wrap">
    <h1>FRED Credit-Risk Dashboard — KeyBank style</h1>
    <p class="sub">Rendered from the workbook's own demo data ({ASOF.isoformat()}) and the keybank_style tokens.
    Sparklines and trend charts are live SVG. This mirrors the .xlsm; it is an HTML preview, not Excel itself.</p>
    <div class="note">BLACK grounds · RED leads sparingly · NEUTRALS breathe. Heat is brand-muted (HEAT_GOOD↔HEAT_MID↔HEAT_BAD).
    The watchlist is the one place Key Red leads a banner — the geographic-boundary gate.</div>
    {''.join(parts)}
    </div></body></html>"""
    out = os.path.join(PROJ, "build", "dashboard_preview.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(out)


if __name__ == "__main__":
    main()
