"""Streamlit UI: Screener · Dashboard · Tear Sheet · Valuation · Evidence · Scorecard.

Reads the local database only (no SEC calls from the UI). Fetch data first:
    stock-helper fetch-sec AAPL          # one company
    stock-helper fetch-universe --top 100 # a cross-company universe (Screener)
Design system lives in ui/theme.py (calm navy/white cards, colorblind-safe
status palette, shared Plotly template). Research aid — never advice; prices are
non-canonical; forensic scores are screens, not verdicts.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlmodel import select

from stock_helper.ai.interfaces import EvidenceChunk
from stock_helper.ai.rule_based import RuleBasedRiskExtractor
from stock_helper.connectors.prices import PRICE_SOURCE_LABEL, fetch_daily_prices
from stock_helper.core.config import get_settings
from stock_helper.core.format import money, multiple, pct, per_share, ratio, shares
from stock_helper.features.context import build_all_extras
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.reports import excel
from stock_helper.screening.engine import build_cross_section
from stock_helper.screening.screens import SAVED_SCREENS, run_screen
from stock_helper.signals.engine import assess_data_confidence, evaluate_signals
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import (
    Company,
    Filing,
    FilingSection,
    SecurityIdentifier,
)
from stock_helper.storage.queries import load_series
from stock_helper.storage.search import search_sections
from stock_helper.ui import theme
from stock_helper.ui.theme import ACCENT, NAVY, apply_plotly, flag_badges
from stock_helper.valuation.compose import compute_valuation
from stock_helper.valuation.dcf import dcf_value
from stock_helper.valuation.types import LEVERED, OWNER_EARNINGS, UNLEVERED

st.set_page_config(page_title="stock-helper", page_icon="📄", layout="wide")
st.markdown(theme.INJECTED_CSS, unsafe_allow_html=True)

BADGES = {
    "OK": ("sh-ok", "OK"),
    "NOT_APPLICABLE": ("sh-na", "n/a for industry"),
    "INSUFFICIENT_DATA": ("sh-warn", "insufficient data"),
    "UNAVAILABLE": ("sh-warn", "unavailable"),
    "PLACEHOLDER": ("sh-plan", "planned"),
}

DIRECTION_ICONS = {"improving": "▲", "deteriorating": "▼", "stable": "▬", "mixed": "◆"}

FCF_BASIS_LABELS = {
    LEVERED: "Levered FCF (OCF − capex)",
    OWNER_EARNINGS: "Owner earnings (NI + D&A + SBC − maint. capex)",
    UNLEVERED: "Unlevered FCFF (WACC; subtract net debt)",
}


@st.cache_resource
def _init():
    settings = get_settings()
    init_db(settings)
    return settings


settings = _init()


def load_companies() -> list[tuple[str, Company]]:
    with get_session(settings) as session:
        rows = session.exec(
            select(SecurityIdentifier, Company).join(
                Company, Company.id == SecurityIdentifier.company_id
            )
        ).all()
    return sorted(((i.ticker, c) for i, c in rows), key=lambda x: x[0])


def load_company_bundle(ticker: str, as_of=None):
    with get_session(settings) as session:
        identifier = session.exec(
            select(SecurityIdentifier).where(SecurityIdentifier.ticker == ticker)
        ).first()
        company = session.get(Company, identifier.company_id)
        series = load_series(session, company, as_of=as_of)
        filings_query = select(Filing).where(Filing.company_id == company.id)
        if as_of is not None:
            filings_query = filings_query.where(Filing.filed_date <= as_of)
        filings = session.exec(
            filings_query.order_by(Filing.filed_date.desc()).limit(30)  # type: ignore[attr-defined]
        ).all()
        sections_query = (
            select(FilingSection)
            .join(Filing, Filing.id == FilingSection.filing_id)  # type: ignore[arg-type]
            .where(Filing.company_id == company.id)
        )
        if as_of is not None:
            sections_query = sections_query.where(Filing.filed_date <= as_of)
        sections = session.exec(
            sections_query.order_by(FilingSection.section_name, FilingSection.chunk_index)  # type: ignore[arg-type]
        ).all()
        derived = compute_derived_metrics(series)
        # Extras only for the current view — see reports/tearsheet.py rationale.
        extras = (
            build_all_extras(session, company, ticker, series, derived, settings)
            if as_of is None else None
        )
    signals = evaluate_signals(company.industry_bucket, derived, extras)
    latest_filed = filings[0].filed_date if filings else None
    confidence = assess_data_confidence(company.industry_bucket, series, latest_filed)
    return company, series, derived, signals, filings, sections, confidence, extras or {}


@st.cache_data(ttl=600)
def load_cross_section(as_of):
    """Build the standardized cross-company universe (cached; cross-ticker)."""
    with get_session(settings) as session:
        return build_cross_section(session, settings=settings, as_of=as_of)


def fmt_value(metric, value: float) -> str:
    if metric.unit == "ratio":
        return pct(value) if "margin" in metric.key or metric.key == "accrual_proxy" else ratio(value)
    if metric.unit == "USD":
        return money(value)
    if metric.unit == "shares":
        return shares(value)
    return f"{value:g}"


def badge(status: str) -> str:
    css, label = BADGES.get(status, ("sh-na", status))
    return f'<span class="sh-badge {css}">{label}</span>'


def metric_trend_chart(metric, title: str):
    frame = pd.DataFrame(metric.points, columns=["Period end", "Value"])
    fig = px.line(frame, x="Period end", y="Value", markers=True, title=title)
    fig.update_traces(line_color=ACCENT)
    apply_plotly(fig)
    fig.update_layout(height=280)
    return fig


# --- Sidebar -------------------------------------------------------------------

st.sidebar.title("📄 stock-helper")
st.sidebar.caption("Evidence-backed research aid. **Not investment advice.**")

companies = load_companies()
if not companies:
    st.title("Welcome to stock-helper")
    st.info(
        "No companies fetched yet. From a terminal, run:\n\n"
        "```\nstock-helper fetch-sec AAPL\nstock-helper fetch-universe --top 100\n```\n"
        "then refresh this page."
    )
    st.stop()

tickers = [t for t, _ in companies]
page = st.sidebar.radio(
    "Section",
    [
        "Screener",
        "Dashboard",
        "Company Tear Sheet",
        "Company Valuation",
        "Filing Evidence",
        "Signal Scorecard",
    ],
)
selected = st.sidebar.selectbox("Ticker", tickers, disabled=(page == "Screener"))

st.sidebar.divider()
pit_enabled = st.sidebar.checkbox(
    "Point-in-time view",
    help="Rebuild everything as it was knowable on a past date: facts and filings "
    "filed later are excluded, and originally-filed values are used instead of "
    "later restatements.",
)
as_of = st.sidebar.date_input("As-of date", disabled=not pit_enabled) if pit_enabled else None

st.sidebar.divider()
st.sidebar.caption(
    "Signals are transparent rules over as-filed SEC data. Nothing here is "
    "backtested; no predictive accuracy is implied. See DISCLAIMER.md."
)

# Per-ticker bundle load is SKIPPED on the (cross-company) Screener page.
company = series = derived = signals = filings = sections = confidence = None
extras = {}
if page != "Screener":
    company, series, derived, signals, filings, sections, confidence, extras = (
        load_company_bundle(selected, as_of=as_of)
    )

if as_of is not None:
    st.info(
        f"**Point-in-time view as of {as_of}.** Facts and filings filed after this "
        "date are excluded; values are as originally filed at the time, not later "
        "restatements."
    )


# --- helpers used by the richer pages ------------------------------------------


def _cols_html(html_tiles: list[str]) -> None:
    """Render a row of pre-built HTML tiles across equal columns."""
    cols = st.columns(len(html_tiles))
    for col, html in zip(cols, html_tiles, strict=False):
        col.markdown(html, unsafe_allow_html=True)


# --- Pages ----------------------------------------------------------------------

if page == "Screener":
    st.title("Screener")
    st.caption(
        "Cross-sectional outlier screener over your fetched universe. "
        "**Candidate screens — not buy lists; unscored, not backtested.** "
        "Distress / manipulation flags are names to READ, never verdicts."
    )

    cs = load_cross_section(as_of)
    if not cs.rows:
        st.markdown(
            '<div class="sh-hero"><b>No universe yet.</b><br>'
            "The screener is cross-company. Fetch some tickers first:<br>"
            "<code>stock-helper fetch-universe --top 100</code><br>"
            '<span class="sh-caveat">Then reopen this page — the cross-section is '
            "cached for 10 minutes.</span></div>",
            unsafe_allow_html=True,
        )
        st.stop()

    n_cheap = sum(1 for t in (r.ticker for r in cs.rows) if (cs.value_score.get(t) or -9) > 1)
    n_quality = sum(1 for t in (r.ticker for r in cs.rows) if (cs.quality_score.get(t) or -9) > 1)
    n_distress = sum(1 for r in cs.rows if "distress" in cs.flags.get(r.ticker, []))
    _cols_html([
        theme.metric_tile("Universe", str(len(cs.rows)), "companies standardized"),
        theme.metric_tile("Cheap", str(n_cheap), "value z &gt; 1"),
        theme.metric_tile("Quality", str(n_quality), "quality z &gt; 1"),
        theme.metric_tile("Distress flags", str(n_distress), "screens, not verdicts"),
    ])

    # Build the ranked table.
    records = []
    for r in cs.rows:
        t = r.ticker
        records.append({
            "Ticker": t,
            "Name": r.name,
            "Sector": r.bucket,
            "Market cap": r.market_cap,
            "FV gap": r.metrics.get("fair_value_gap"),
            "Value z": cs.value_score.get(t),
            "Quality z": cs.quality_score.get(t),
            "Combined z": cs.combined_score.get(t),
            "EV/EBIT": r.metrics.get("ev_ebit"),
            "P/B": r.metrics.get("p_b"),
            "Earnings yield": r.metrics.get("earnings_yield"),
            "Piotroski": r.metrics.get("piotroski_f"),
            "Altman Z": r.metrics.get("altman_z"),
            "Flags": ", ".join(cs.flags.get(t, [])),
        })
    df = pd.DataFrame(records)

    # --- filter row ---
    sectors = sorted({r.bucket for r in cs.rows})
    all_flags = sorted({f for fl in cs.flags.values() for f in fl})
    f1, f2, f3, f4, f5 = st.columns([2, 1.4, 2, 1.6, 1.6])
    pick_sectors = f1.multiselect("Sector", sectors, default=[])
    caps = [c for c in df["Market cap"].tolist() if c is not None]
    min_cap = f2.number_input("Min market cap ($)", min_value=0.0,
                              value=0.0, step=1e9, format="%.0f")
    pick_flags = f3.multiselect("Require flags", all_flags, default=[])
    sort_by = f4.selectbox(
        "Sort by",
        ["Combined z", "Value z", "Quality z", "FV gap", "Piotroski", "Altman Z"],
    )
    screen_key = f5.selectbox(
        "Saved screen",
        ["(none)"] + list(SAVED_SCREENS.keys()),
        format_func=lambda k: "(none)" if k == "(none)" else SAVED_SCREENS[k].label,
    )

    filtered = df.copy()
    if pick_sectors:
        filtered = filtered[filtered["Sector"].isin(pick_sectors)]
    if min_cap > 0:
        filtered = filtered[filtered["Market cap"].fillna(-1) >= min_cap]
    if pick_flags:
        filtered = filtered[
            filtered["Flags"].apply(lambda s: all(f in s.split(", ") for f in pick_flags))
        ]

    active_caveat = SAVED_SCREENS["deep_value"].caveat
    if screen_key != "(none)":
        spec = SAVED_SCREENS[screen_key]
        active_caveat = spec.caveat
        ranked = run_screen(cs, spec)
        order = {e.ticker: e.rank for e in ranked}
        filtered = filtered[filtered["Ticker"].isin(order)].copy()
        filtered["_rank"] = filtered["Ticker"].map(order)
        filtered = filtered.sort_values("_rank").drop(columns="_rank")
        st.caption(f"**{spec.label}** — {spec.description}")
    else:
        filtered = filtered.sort_values(sort_by, ascending=False, na_position="last")

    if filtered.empty:
        st.warning("No companies match these filters. Loosen the sector / cap / flag filters.")
    else:
        # --- value-vs-quality 2x2 scatter ---
        scat = filtered.dropna(subset=["Value z", "Quality z"])
        if not scat.empty:
            fig = px.scatter(
                scat, x="Value z", y="Quality z", color="FV gap",
                hover_name="Ticker", hover_data={"Sector": True, "FV gap": ":.1%"},
                color_continuous_scale=theme.VALUE_RAMP,
                title="Value vs quality (each dot a company; color = fair-value gap)",
            )
            fig.update_traces(marker=dict(size=12, line=dict(width=1, color="white")))
            fig.add_hline(y=0, line_dash="dot", line_color=theme.NEUTRAL, opacity=0.5)
            fig.add_vline(x=0, line_dash="dot", line_color=theme.NEUTRAL, opacity=0.5)
            apply_plotly(fig)
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Top-right = cheap **and** high-quality. Bottom-right = cheap but "
                       "weak (possible value trap). A map for reading, not a ranking.")

        # --- ranked table ---
        display = filtered.copy()
        display["FV gap %"] = display["FV gap"] * 100
        table_cols = ["Ticker", "Name", "Sector", "Market cap", "FV gap %",
                      "Value z", "Quality z", "Combined z", "EV/EBIT", "P/B",
                      "Piotroski", "Altman Z", "Flags"]
        st.dataframe(
            display[table_cols],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Market cap": st.column_config.NumberColumn("Market cap", format="$%.0f"),
                "FV gap %": st.column_config.NumberColumn(
                    "FV gap", help="(fair − price) / fair; higher = cheaper",
                    format="%.1f%%"),
                "Value z": st.column_config.NumberColumn(format="%.2f"),
                "Quality z": st.column_config.NumberColumn(format="%.2f"),
                "Combined z": st.column_config.NumberColumn(format="%.2f"),
                "EV/EBIT": st.column_config.NumberColumn(format="%.1fx"),
                "P/B": st.column_config.NumberColumn(format="%.1fx"),
                "Piotroski": st.column_config.NumberColumn(format="%.0f / 9"),
                "Altman Z": st.column_config.NumberColumn(format="%.2f"),
            },
        )

        meta = {
            "as_of": as_of,
            "universe": f"{len(cs.rows)} companies, {len(sectors)} sector(s)",
            "screen": SAVED_SCREENS[screen_key].label if screen_key != "(none)" else "custom filter",
            "source_label": "Local DB; prices non-canonical (Stooq)",
        }
        c_dl1, c_dl2 = st.columns(2)
        c_dl1.download_button(
            "⬇ Download screen (Excel)",
            data=excel.screen_to_xlsx(filtered, meta),
            file_name="stock-helper-screen.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        c_dl2.download_button(
            "⬇ Download screen (CSV)",
            data=excel.screen_to_csv(filtered),
            file_name="stock-helper-screen.csv",
            mime="text/csv",
        )

    st.caption(f"⚠️ {active_caveat}")

elif page == "Dashboard":
    st.title("Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Company", selected)
    col2.metric("Industry bucket", company.industry_bucket)
    col3.metric("Data confidence", confidence.level)
    col4.metric("Latest filing", str(confidence.latest_filing or "—"))

    st.markdown(
        f'<div class="sh-card"><b>{company.name}</b> · CIK {company.cik} · '
        f"SIC {company.sic or 'n/a'} ({company.sic_description or 'n/a'})<br>"
        f'<span class="sh-source">Source: SEC submissions API · retrieved '
        f"{company.retrieved_at or 'n/a'}</span></div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Latest filings")
        if filings:
            frame = pd.DataFrame(
                [
                    {
                        "Form": f.form,
                        "Filed": f.filed_date,
                        "Period": f.period_end,
                        "Accession": f.accession,
                    }
                    for f in filings[:10]
                ]
            )
            st.dataframe(frame, hide_index=True, use_container_width=True)
        else:
            st.caption("No filings stored.")
    with right:
        st.subheader("Quick signal summary")
        ok_signals = [s for s in signals if s.outcome.status == "OK"]
        flags = [s for s in ok_signals if (s.outcome.score or 0) < 0]
        positives = [s for s in ok_signals if (s.outcome.score or 0) > 0]
        st.markdown(
            f"- **{len(ok_signals)}** signals evaluated\n"
            f"- **{len(positives)}** supportive · **{len(flags)}** flagged\n"
            f"- {sum(1 for s in signals if s.outcome.status == 'NOT_APPLICABLE')} "
            "not applicable to this industry\n"
            f"- {sum(1 for s in signals if s.outcome.status in ('UNAVAILABLE', 'INSUFFICIENT_DATA'))} "
            "missing data"
        )
        for s in flags[:4]:
            st.markdown(
                f'<div class="sh-card">▼ <b>{s.definition.name}</b> — '
                f'{s.outcome.interpretation}<br><span class="sh-caveat">'
                f"{s.outcome.caveat}</span></div>",
                unsafe_allow_html=True,
            )
        if not flags:
            st.caption("No rule-level flags. See the full scorecard for detail.")

elif page == "Company Tear Sheet":
    st.title(f"{company.name} ({selected})")
    st.caption(
        f"CIK {company.cik} · SIC {company.sic or 'n/a'} — {company.sic_description or 'n/a'} · "
        f"bucket `{company.industry_bucket}` · fiscal year end {company.fiscal_year_end or 'n/a'}"
    )
    from stock_helper.industry.sic_buckets import peer_group_label

    st.markdown(
        f'<div class="sh-card">{peer_group_label(company.sic, company.sic_description)}</div>',
        unsafe_allow_html=True,
    )

    peers = extras.get("peers")
    if peers is not None and peers.percentiles:
        rows = "".join(
            f"<tr><td>{k}</td><td>p{v:.0f}</td></tr>"
            for k, v in sorted(peers.percentiles.items())
        )
        st.markdown(
            f'<div class="sh-card"><b>Local-universe percentiles</b> — vs '
            f"{peers.n_peers} same-bucket compan{'y' if peers.n_peers == 1 else 'ies'} "
            f"({', '.join(peers.peer_tickers)})<br>"
            f'<table>{rows}</table>'
            f'<span class="sh-caveat">Your fetched universe only, not the market. '
            f"Market-wide peer mapping is Phase 4.</span></div>",
            unsafe_allow_html=True,
        )

    market = extras.get("market")
    if market is not None:
        bits = [f"close {market.price:.2f} ({market.price_date})"]
        if market.momentum_12_1 is not None:
            bits.append(f"12-1 momentum {market.momentum_12_1:+.1%}")
        if market.volatility_60d is not None:
            bits.append(f"60d vol {market.volatility_60d:.0%}")
        if market.pe is not None:
            bits.append(f"P/E {market.pe:.1f}")
        if market.ps is not None:
            bits.append(f"P/S {market.ps:.1f}")
        st.markdown(
            f'<div class="sh-card"><b>Market context</b> — {" · ".join(bits)}<br>'
            f'<span class="sh-caveat">⚠️ {market.source_label} — context only, '
            "never used as a prediction.</span></div>",
            unsafe_allow_html=True,
        )

    if settings.enable_price_data:
        prices = fetch_daily_prices(selected, settings)
        if prices is not None:
            fig = px.line(prices.tail(756), x="Date", y="Close",
                          title=f"{selected} daily close — {PRICE_SOURCE_LABEL}")
            fig.update_traces(line_color=ACCENT)
            apply_plotly(fig)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"⚠️ {PRICE_SOURCE_LABEL} — context only, never used in signals.")
        else:
            st.caption("Price data enabled but unavailable for this ticker.")
    else:
        st.caption("Price chart disabled (set ENABLE_PRICE_DATA=true to enable a "
                   "non-canonical context chart).")

    st.subheader("Fundamental metrics (annual, as filed)")
    if not derived:
        st.warning("No canonical metrics could be mapped from this filer's XBRL. "
                   "This is reported honestly rather than guessed.")
    else:
        cards = st.columns(3)
        for i, metric in enumerate(derived.values()):
            with cards[i % 3]:
                latest = metric.latest
                st.markdown(
                    f'<div class="sh-card"><b>{metric.label}</b><br>'
                    f'<span style="font-size:1.4rem;color:{NAVY}" class="sh-num">'
                    f"{fmt_value(metric, latest) if latest is not None else 'n/a'}</span><br>"
                    f'<span class="sh-caveat">{len(metric.points)} annual periods · '
                    f"formula: <code>{metric.formula}</code></span><br>"
                    f'<span class="sh-source">tags: {", ".join(metric.input_tags)}</span></div>',
                    unsafe_allow_html=True,
                )

        st.subheader("Metric trends")
        chartable = [m for m in derived.values() if len(m.points) >= 2]
        chosen = st.multiselect(
            "Metrics to chart",
            [m.key for m in chartable],
            default=[k for k in ("revenue", "operating_margin", "free_cash_flow", "deposits")
                     if k in derived][:3],
        )
        chart_cols = st.columns(2)
        for i, key in enumerate(chosen):
            with chart_cols[i % 2]:
                st.plotly_chart(metric_trend_chart(derived[key], derived[key].label),
                                use_container_width=True)

    st.subheader("Filing timeline")
    if filings:
        frame = pd.DataFrame([{"Form": f.form, "Filed": f.filed_date} for f in filings])
        counts = frame.groupby(["Filed", "Form"]).size().reset_index(name="Count")
        fig = px.scatter(counts, x="Filed", y="Form", size="Count", color="Form",
                         title="Recent filings")
        apply_plotly(fig)
        fig.update_layout(height=260, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

elif page == "Company Valuation":
    st.title(f"Valuation — {company.name} ({selected})")
    st.caption(
        "Scenario estimates from explicit, editable assumptions — **not a price "
        "target and not advice.** Prices are non-canonical; forensic scores are "
        "screens, not verdicts."
    )

    market = extras.get("market") if as_of is None else None
    with get_session(settings) as _s:
        val = compute_valuation(_s, company, selected, series, derived, market, settings, as_of)

    # --- Row 1: hero (fair-value bar with price marker + MoS band · flags) ---
    dcf = val.dcf
    fv = val.fair_value_per_share
    uncertainty = theme.uncertainty_from_dcf(dcf)
    hero_left, hero_mid = st.columns(2)
    with hero_left:
        st.markdown(
            theme.metric_tile(
                "Fair value / share",
                per_share(fv) if fv is not None else "n/m",
                f"method: {dcf.method if dcf else 'n/a'} · bucket {val.bucket}",
            ),
            unsafe_allow_html=True,
        )
    with hero_mid:
        if val.price is not None:
            st.markdown(
                theme.metric_tile("Current price", per_share(val.price),
                                  f"{val.price_date} · non-canonical"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                theme.metric_tile("Current price", "n/a", "no price — intrinsic only"),
                unsafe_allow_html=True,
            )
    # Fair-value bar is the hero visual (not a gauge — a gauge reads as a
    # needle pointing at a recommendation). The margin-of-safety band widens
    # with estimate uncertainty, so a shakier DCF must clear a bigger discount.
    st.plotly_chart(
        theme.fair_value_bar(fv, val.price, uncertainty=uncertainty),
        use_container_width=True,
    )
    disc = int(theme.UNCERTAINTY_DISCOUNT.get(uncertainty, 0.30) * 100)
    if val.margin_of_safety is not None:
        st.caption(
            f"Margin of safety **{pct(val.margin_of_safety)}** · this estimate is "
            f"**{uncertainty.replace('_', ' ')}** uncertainty, so it should clear a "
            f"~{disc}% discount before it reads as cheap. A research estimate, not a target."
        )
    else:
        st.caption(
            f"Intrinsic value only (no price). Estimate uncertainty: "
            f"**{uncertainty.replace('_', ' ')}** (terminal-value weight drives this)."
        )
    if val.flags:
        st.markdown(flag_badges(val.flags), unsafe_allow_html=True)

    st.divider()

    # --- Row 2: live DCF ---
    st.subheader("DCF — live assumptions")
    base_fcf = dcf.base_fcf if dcf else None
    if dcf and dcf.status == "OK" and base_fcf is not None:
        net_debt = dcf.net_debt or 0.0
        n_shares = dcf.shares
        d_growth = dcf.stage1_growth if dcf.stage1_growth is not None else 0.05
        d_disc = dcf.discount_rate if dcf.discount_rate is not None else 0.09
        d_term = dcf.terminal_growth if dcf.terminal_growth is not None else 0.025
        d_years = dcf.stage1_years or 5

        s1, s2, s3 = st.columns(3)
        g = s1.slider("Stage-1 growth %", -10.0, 30.0, round(d_growth * 100, 1), 0.5) / 100.0
        r = s2.slider("Discount rate %", 4.0, 20.0, round(d_disc * 100, 2), 0.25) / 100.0
        tg = s3.slider("Terminal growth %", 0.0, 5.0, round(d_term * 100, 1), 0.1) / 100.0
        s4, s5 = st.columns([1, 2])
        yrs = s4.slider("Horizon (yrs)", 3, 15, int(d_years))
        basis = s5.selectbox("FCF basis", list(FCF_BASIS_LABELS),
                             index=list(FCF_BASIS_LABELS).index(dcf.fcf_basis)
                             if dcf.fcf_basis in FCF_BASIS_LABELS else 0,
                             format_func=lambda b: FCF_BASIS_LABELS[b])

        live = dcf_value(base_fcf, g, yrs, r, tg, n_shares,
                         net_debt=net_debt, fcf_basis=basis)

        lc1, lc2 = st.columns([2, 3])
        with lc1:
            if live.status == "OK" and live.fair_value_per_share is not None:
                st.markdown(
                    theme.metric_tile("Live fair value / share",
                                      per_share(live.fair_value_per_share),
                                      f"equity value {money(live.equity_value)}"),
                    unsafe_allow_html=True,
                )
                # Range from the composed sensitivity grid (not just the point).
                sens = val.sensitivity
                if sens is not None and sens.grid:
                    vals = [c for row in sens.grid for c in row if c is not None]
                    if vals:
                        st.caption(
                            f"Sensitivity range (±growth/discount): "
                            f"{per_share(min(vals))} – {per_share(max(vals))}"
                        )
                tw = live.terminal_weight
                if tw is not None:
                    tw_cls = "sh-warn" if tw > 0.75 else "sh-na"
                    st.markdown(
                        f'<span class="sh-badge {tw_cls}">terminal value = '
                        f"{pct(tw)} of equity</span>",
                        unsafe_allow_html=True,
                    )
                    if tw > 0.75:
                        st.caption("⚠️ Terminal value dominates (&gt;75%) — the result "
                                   "leans heavily on the perpetuity assumption.")
            else:
                st.warning("This assumption set has no finite value: "
                           + (live.caveats[0] if live.caveats else
                              "discount rate must exceed terminal growth."))
        with lc2:
            if live.status == "OK" and live.pv_explicit is not None:
                bridge = go.Figure()
                bridge.add_bar(x=["Explicit PV"], y=[live.pv_explicit],
                               marker_color=ACCENT, name="Explicit")
                bridge.add_bar(x=["Terminal PV"], y=[live.pv_terminal],
                               marker_color=theme.WARNING, name="Terminal")
                bridge.update_layout(title="Value bridge (PV of flows)", showlegend=False)
                apply_plotly(bridge)
                bridge.update_layout(height=280)
                st.plotly_chart(bridge, use_container_width=True)
        st.caption("Sliders recompute the pure DCF instantly (no I/O). "
                   "Base FCF is the 3-yr median of as-filed free cash flow.")
    elif dcf:
        st.info(f"**DCF {dcf.status}** — {'; '.join(dcf.caveats) or dcf.method}. "
                "Live sliders need a positive FCF base on a non-financial bucket.")

    st.divider()

    # --- Row 3: reverse DCF ---
    st.subheader("Reverse DCF — what the price implies")
    rev = val.reverse
    if rev is not None and rev.implied_growth is not None:
        hist = (f"vs its own historical FCF CAGR of **{pct(rev.historical_fcf_cagr)}**"
                if rev.historical_fcf_cagr is not None else
                "(no clean historical FCF CAGR to compare)")
        st.markdown(
            f'<div class="sh-card">At today\'s price the market is pricing in '
            f"~<b>{pct(rev.implied_growth)}</b> stage-1 FCF growth {hist}.<br>"
            f'<span class="sh-caveat">{rev.caveat}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("Reverse DCF unavailable — needs a market price and a positive FCF base "
                   + ("(point-in-time view has no price)." if as_of is not None else "."))

    st.divider()

    # --- Row 3b: Monte Carlo fair-value spread ---
    mc = val.monte_carlo
    if mc is not None:
        st.subheader("Monte Carlo — how wide is the fair value?")
        mcc1, mcc2, mcc3 = st.columns(3)
        with mcc1:
            st.markdown(
                theme.metric_tile("Median fair value", per_share(mc.median),
                                  f"{mc.n_sims:,} valid draws · seed {mc.seed}"),
                unsafe_allow_html=True,
            )
        with mcc2:
            st.markdown(
                theme.metric_tile("Middle 80% (p10–p90)",
                                  f"{per_share(mc.p10)} – {per_share(mc.p90)}",
                                  "input-uncertainty fan"),
                unsafe_allow_html=True,
            )
        with mcc3:
            if mc.prob_undervalued is not None:
                st.markdown(
                    theme.metric_tile("Draws above price", pct(mc.prob_undervalued),
                                      "diagnostic, NOT a forecast"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    theme.metric_tile("Draws above price", "n/a", "no price"),
                    unsafe_allow_html=True,
                )
        st.plotly_chart(
            theme.monte_carlo_fan(mc, val.price),
            use_container_width=True,
        )
        st.caption(
            "⚠️ Spread reflects **input** uncertainty only (growth, discount, "
            "terminal growth, FCF base) — not model risk or the chance the base "
            "assumptions are simply wrong. A sensitivity fan around one editable "
            "scenario, **not** a probability the stock goes up or a price target."
        )

        st.divider()

    # --- Row 4: multiples table ---
    st.subheader("Multiples — company vs peers")
    if val.multiples:
        rows = []
        for key, m in val.multiples.items():
            is_yield = key.endswith("_yield")
            company_val = (pct(m.value) if is_yield and m.value is not None
                           else (multiple(m.value) if not is_yield else "n/m"))
            pr = val.peer_relative.get(key)
            peer_med = multiple(pr.peer_median) if pr is not None else "n/m"
            upside = pct(pr.upside_pct) if pr is not None and pr.upside_pct is not None else "n/m"
            rows.append({"Multiple": m.label, "Company": company_val,
                         "Peer median": peer_med, "Implied upside": upside})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.caption("No market multiples — intrinsic-only view (no price).")

    st.divider()

    # --- Row 5: quality & forensic scorecard ---
    st.subheader("Quality & forensic scorecard")
    q = val.quality
    if q is not None:
        qc1, qc2 = st.columns(2)
        with qc1:
            pio = q.factors.get("piotroski_f")
            if pio is not None and pio.status == "OK" and pio.value is not None:
                st.markdown(f"**Piotroski F-score:** {int(pio.value)} / 9", unsafe_allow_html=True)
                st.progress(pio.value / 9.0)
            else:
                st.caption("Piotroski F-score: n/a")
            for key, label in (("gross_profitability", "Gross profitability"),
                               ("roe", "ROE")):
                fr = q.factors.get(key)
                if fr is not None and fr.status == "OK" and fr.value is not None:
                    st.markdown(f"- **{label}:** {pct(fr.value)}")
            mf = q.factors.get("magic_formula")
            if mf is not None and mf.status == "OK" and mf.detail.get("roic") is not None:
                st.markdown(f"- **ROIC (Magic Formula):** {pct(mf.detail['roic'])}")
        with qc2:
            panel = q.distress_panel or {}
            st.markdown("**Distress models**")
            for key, label in (("altman_z", "Altman Z"), ("ohlson_o", "Ohlson O"),
                               ("zmijewski", "Zmijewski")):
                fr = q.factors.get(key)
                if fr is not None and fr.status == "OK":
                    zone = (fr.detail or {}).get("zone", "?")
                    cls = {"distress": "sh-distress", "safe": "sh-cheap"}.get(zone, "sh-fair")
                    st.markdown(
                        f'{label}: <b>{ratio(fr.value)}</b> '
                        f'<span class="sh-badge {cls}">{zone}</span>',
                        unsafe_allow_html=True,
                    )
            if panel.get("note"):
                st.caption(panel["note"])

    st.markdown("**Forensic panel — screens, not accusations**")
    fpanel = []
    if val.beneish is not None and val.beneish.m_score is not None:
        verdict = ("possible manipulation (&gt; -1.78)" if val.beneish.flag
                   else "below manipulation threshold")
        fpanel.append(f"Beneish M-score **{ratio(val.beneish.m_score)}** — {verdict}")
    montier = val.quality.factors.get("montier_c") if val.quality else None
    if montier is not None and montier.value is not None:
        fpanel.append(f"Montier C-score **{int(montier.value)}** of "
                      f"{montier.detail.get('max', 6)} (aggressive-accounting flags)")
    if val.stress and val.stress.stress_flags:
        for _key, reason, _v in val.stress.stress_flags:
            fpanel.append(f"{reason}")
    if fpanel:
        st.markdown(
            '<div class="sh-card">' + "<br>".join(fpanel)
            + '<br><span class="sh-caveat">Statistical screens for further reading — '
            "never an accusation of fraud or a verdict.</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("No forensic/stress flags fired on the latest year.")

    st.divider()

    # --- Row 6: sensitivity heatmap ---
    st.subheader("Sensitivity — fair value vs growth × discount")
    sens = val.sensitivity
    if sens is not None and sens.grid:
        z = [[c if c is not None else float("nan") for c in row] for row in sens.grid]
        fig = px.imshow(
            z,
            x=[f"{r_ * 100:.1f}%" for r_ in sens.discount_rates],
            y=[f"{g_ * 100:.1f}%" for g_ in sens.growths],
            color_continuous_scale=theme.VALUE_RAMP,
            labels={"x": "Discount rate", "y": "Stage-1 growth", "color": "Fair value/sh"},
            aspect="auto", text_auto=".0f",
        )
        apply_plotly(fig)
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Each cell is the per-share fair value at that (growth, discount) pair. "
                   "Cells left blank where the scenario is invalid (r ≤ g).")
    else:
        st.caption("Sensitivity grid unavailable (needs a valid DCF base).")

    st.download_button(
        "⬇ Download valuation (Excel)",
        data=excel.valuation_to_xlsx(val),
        file_name=f"stock-helper-valuation-{selected}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption("⚠️ " + (val.caveats[0] if val.caveats else
                        "Research aid — not investment advice."))

elif page == "Filing Evidence":
    st.title("Filing Evidence")
    st.caption("Source documents and extracted sections. Extraction is heuristic "
               "(parser v0.1) — always verify against the SEC archive link.")

    st.subheader("Search filing text")
    query = st.text_input(
        "Search extracted sections (all fetched companies)",
        placeholder='e.g. "supply chain" OR impairment',
    )
    if query:
        with get_session(settings) as _s:
            hits = search_sections(_s, query, limit=15)
        if hits:
            for hit in hits:
                st.markdown(
                    f'<div class="sh-card"><code>{hit.chunk_id}</code> · '
                    f"section <b>{hit.section_name}</b><br>{hit.snippet}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No matches. Sections exist only for companies fetched with "
                       "--with-documents.")

    risk_chunks = [s for s in sections if s.section_name == "risk_factors"]
    if risk_chunks:
        st.subheader("Rule-based risk highlights")
        st.caption("Selected (not generated) sentences, ranked by risk-word density — "
                   "no AI involved. Each cites its source chunk.")
        highlights = RuleBasedRiskExtractor().extract_risks(
            [EvidenceChunk(chunk_id=c.chunk_id, text=c.text) for c in risk_chunks]
        )
        for grounded in highlights:
            st.markdown(
                f'<div class="sh-card">{grounded.text}<br>'
                f'<span class="sh-source">source chunk: '
                f"{', '.join(grounded.cited_chunk_ids)}</span></div>",
                unsafe_allow_html=True,
            )
        if not highlights:
            st.caption("No high-density risk sentences found by the rule set.")

    st.subheader("Latest filings")
    if filings:
        for f in filings[:12]:
            st.markdown(
                f'<div class="sh-card"><b>{f.form}</b> filed {f.filed_date}'
                + (f" · period {f.period_end}" if f.period_end else "")
                + f" · accession <code>{f.accession}</code><br>"
                f'<a href="{f.index_url}">SEC archive index</a>'
                + (f' · <a href="{f.primary_document_url}">primary document</a>'
                   if f.primary_document_url else "")
                + "</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No filings stored.")

    st.subheader("Extracted sections")
    if not sections:
        st.info(
            f"No sections extracted yet. Run:\n\n"
            f"```\nstock-helper fetch-sec {selected} --with-documents\n```"
        )
    else:
        names = sorted({s.section_name for s in sections})
        chosen = st.selectbox(
            "Section", names,
            format_func=lambda n: {"mdna": "MD&A", "risk_factors": "Risk Factors"}.get(
                n, n.replace("item_", "8-K Item ").replace("_", ".")
            ),
        )
        chunks = [s for s in sections if s.section_name == chosen]
        st.caption(
            f"{len(chunks)} chunks · parser {chunks[0].parser_version} · "
            f"chunk ids are stable for future citation use"
        )
        for chunk in chunks[:20]:
            with st.expander(f"chunk `{chunk.chunk_id}`"):
                st.text(chunk.text[:4000])
        if len(chunks) > 20:
            st.caption(f"…{len(chunks) - 20} more chunks stored.")

elif page == "Signal Scorecard":
    st.title("Signal Scorecard")
    st.caption(
        "Transparent rules over as-filed data. Each row shows metric, value, "
        "direction, interpretation, source, confidence, and caveat. Descriptive — "
        "**not** predictions, **not** advice."
    )

    st.markdown(
        f'<div class="sh-card"><b>Data confidence: {confidence.level}</b> · '
        f"{confidence.metrics_mapped}/{confidence.metrics_total} canonical metrics mapped · "
        f"{confidence.annual_periods} annual periods · latest filing "
        f"{confidence.latest_filing or 'n/a'}"
        + "".join(f'<br><span class="sh-caveat">⚠️ {n}</span>' for n in confidence.notes)
        + "</div>",
        unsafe_allow_html=True,
    )

    categories = sorted({s.definition.category for s in signals})
    for category in categories:
        st.subheader(category)
        for s in [x for x in signals if x.definition.category == category]:
            outcome = s.outcome
            icon = DIRECTION_ICONS.get(outcome.direction, "")
            body = f"<b>{s.definition.name}</b> {badge(outcome.status)}"
            if outcome.status == "OK":
                body += (
                    f"<br>{icon} <b>{outcome.value_text}</b> · direction: {outcome.direction} "
                    f"· confidence: {outcome.confidence}"
                    f"<br>{outcome.interpretation}"
                    f'<br><span class="sh-caveat">Caveat: {outcome.caveat}</span>'
                )
                for evidence in outcome.evidence:
                    body += (
                        f'<br><span class="sh-source">Source: {evidence.description} '
                        f"— accessions {evidence.reference}</span>"
                    )
            else:
                body += f'<br><span class="sh-caveat">{outcome.interpretation}</span>'
            st.markdown(f'<div class="sh-card">{body}</div>', unsafe_allow_html=True)
