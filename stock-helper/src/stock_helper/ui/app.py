"""Streamlit UI: Dashboard · Company Tear Sheet · Filing Evidence · Signal Scorecard.

Reads the local database only (no SEC calls from the UI). Fetch data first:
    stock-helper fetch-sec AAPL
Design: calm white/gray, navy accents, cards, status badges, caveats everywhere.
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlmodel import select

from stock_helper.connectors.prices import PRICE_SOURCE_LABEL, fetch_daily_prices
from stock_helper.core.config import get_settings
from stock_helper.core.format import money, pct, ratio, shares
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.signals.engine import assess_data_confidence, evaluate_signals
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import (
    Company,
    Filing,
    FilingSection,
    SecurityIdentifier,
)
from stock_helper.storage.queries import load_series

NAVY = "#1b2a4a"
ACCENT = "#2c4a7c"

st.set_page_config(page_title="stock-helper", page_icon="📄", layout="wide")

st.markdown(
    f"""
    <style>
      .stApp {{ background: #f7f8fa; }}
      h1, h2, h3 {{ color: {NAVY}; }}
      section[data-testid="stSidebar"] {{ background: #eef1f5; }}
      div[data-testid="stMetricValue"] {{ color: {NAVY}; }}
      .sh-card {{
        background: white; border: 1px solid #e3e7ee; border-radius: 10px;
        padding: 1rem 1.25rem; margin-bottom: 0.75rem;
      }}
      .sh-badge {{
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.78rem; font-weight: 600; margin-left: 6px;
      }}
      .sh-ok {{ background: #e3f2e8; color: #1b6b3a; }}
      .sh-na {{ background: #eceff3; color: #5b6472; }}
      .sh-warn {{ background: #fdf3dc; color: #8a6116; }}
      .sh-plan {{ background: #e8eaf6; color: {ACCENT}; }}
      .sh-caveat {{ color: #6b7280; font-size: 0.85rem; }}
      .sh-source {{ color: #8a93a3; font-size: 0.78rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

BADGES = {
    "OK": ("sh-ok", "OK"),
    "NOT_APPLICABLE": ("sh-na", "n/a for industry"),
    "INSUFFICIENT_DATA": ("sh-warn", "insufficient data"),
    "UNAVAILABLE": ("sh-warn", "unavailable"),
    "PLACEHOLDER": ("sh-plan", "planned"),
}

DIRECTION_ICONS = {"improving": "▲", "deteriorating": "▼", "stable": "▬", "mixed": "◆"}


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
    signals = evaluate_signals(company.industry_bucket, derived)
    latest_filed = filings[0].filed_date if filings else None
    confidence = assess_data_confidence(company.industry_bucket, series, latest_filed)
    return company, series, derived, signals, filings, sections, confidence


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
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", height=280,
        margin=dict(l=10, r=10, t=40, b=10), font_color=NAVY,
    )
    return fig


# --- Sidebar -------------------------------------------------------------------

st.sidebar.title("📄 stock-helper")
st.sidebar.caption("Evidence-backed research aid. **Not investment advice.**")

companies = load_companies()
if not companies:
    st.title("Welcome to stock-helper")
    st.info(
        "No companies fetched yet. From a terminal, run:\n\n"
        "```\nstock-helper fetch-sec AAPL\nstock-helper fetch-sec KEY\n```\n"
        "then refresh this page."
    )
    st.stop()

tickers = [t for t, _ in companies]
selected = st.sidebar.selectbox("Ticker", tickers)
page = st.sidebar.radio(
    "Section", ["Dashboard", "Company Tear Sheet", "Filing Evidence", "Signal Scorecard"]
)

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

company, series, derived, signals, filings, sections, confidence = load_company_bundle(
    selected, as_of=as_of
)

if as_of is not None:
    st.info(
        f"**Point-in-time view as of {as_of}.** Facts and filings filed after this "
        "date are excluded; values are as originally filed at the time, not later "
        "restatements."
    )

# --- Pages ----------------------------------------------------------------------

if page == "Dashboard":
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

    if settings.enable_price_data:
        prices = fetch_daily_prices(selected, settings)
        if prices is not None:
            fig = px.line(prices.tail(756), x="Date", y="Close",
                          title=f"{selected} daily close — {PRICE_SOURCE_LABEL}")
            fig.update_traces(line_color=ACCENT)
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=300,
                              margin=dict(l=10, r=10, t=40, b=10), font_color=NAVY)
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
                    f'<span style="font-size:1.4rem;color:{NAVY}">'
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
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=260,
                          margin=dict(l=10, r=10, t=40, b=10), font_color=NAVY,
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

elif page == "Filing Evidence":
    st.title("Filing Evidence")
    st.caption("Source documents and extracted sections. Extraction is heuristic "
               "(parser v0.1) — always verify against the SEC archive link.")

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
            format_func=lambda n: {"mdna": "MD&A", "risk_factors": "Risk Factors"}.get(n, n),
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
