"""Centralized design system for the Streamlit UI.

Pure and server-free: this module holds only colors, the injected CSS string, a
Plotly layout template, and small HTML/figure helpers. It imports nothing from
Streamlit, so it is safe to import anywhere (tests, reports, scripts).

Palette philosophy: keep the existing calm navy/white card aesthetic, and add a
colorblind-safe positive/negative/warning triad (Okabe-Ito derived: bluish-green,
vermillion, amber) plus a blue<->orange diverging ramp for value maps — the one
diverging pair that survives red-green color vision deficiency.
"""

from __future__ import annotations

from typing import Any

# --- core brand tokens (unchanged from the original app) ----------------------
NAVY = "#1b2a4a"
ACCENT = "#2c4a7c"

# --- colorblind-safe status triad (Okabe-Ito) --------------------------------
POSITIVE = "#0b7a55"  # bluish-green: cheap / good / supportive
NEGATIVE = "#c0451b"  # vermillion: distress / flagged / rich-on-the-wrong-side
WARNING = "#b07d17"  # amber: caution / insufficient
NEUTRAL = "#5b6472"  # slate: n/a, in-line, informational

# Softer background tints for badges/tiles (paired with the text colors above).
POSITIVE_BG = "#e3f2e8"
NEGATIVE_BG = "#fbe7de"
WARNING_BG = "#fdf3dc"
NEUTRAL_BG = "#eceff3"
ACCENT_BG = "#e8eef7"

# --- diverging value ramp (low = expensive/overvalued, high = cheap/undervalued)
# Blue<->orange survives deuteranopia/protanopia. Used for fair-value gap maps
# and the sensitivity heatmap. Given as (position, color) stops for Plotly.
VALUE_RAMP: list[list[Any]] = [
    [0.0, "#c0451b"],   # deep orange — richly valued (negative gap)
    [0.25, "#e8a06b"],
    [0.5, "#f2f2ef"],   # near-neutral
    [0.75, "#6fa8c9"],
    [1.0, "#1b5e8a"],   # deep blue — deeply undervalued (positive gap)
]

# A sequential accent ramp (light -> navy) for single-signed magnitudes.
SEQUENTIAL_RAMP: list[list[Any]] = [
    [0.0, "#eef2f8"],
    [0.5, ACCENT],
    [1.0, NAVY],
]

GRID_COLOR = "#e3e7ee"

# --- Plotly layout template ---------------------------------------------------
PLOTLY_LAYOUT: dict[str, Any] = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": NAVY, "family": "Inter, -apple-system, Segoe UI, sans-serif", "size": 13},
    "margin": {"l": 12, "r": 12, "t": 40, "b": 12},
    "height": 320,
    "colorway": [ACCENT, POSITIVE, WARNING, NEGATIVE, "#6a7fb0", NEUTRAL],
    "hoverlabel": {"bgcolor": "white", "font": {"color": NAVY, "size": 12}},
    "xaxis": {"gridcolor": GRID_COLOR, "zerolinecolor": GRID_COLOR, "linecolor": GRID_COLOR},
    "yaxis": {"gridcolor": GRID_COLOR, "zerolinecolor": GRID_COLOR, "linecolor": GRID_COLOR},
    "title": {"font": {"color": NAVY, "size": 15}},
}


def apply_plotly(fig: Any) -> Any:
    """Apply the shared layout template to a Plotly figure (transparent bg, navy
    font, tight margins, consistent grid). Returns the same figure for chaining."""
    fig.update_layout(**PLOTLY_LAYOUT)
    # update_layout with nested axis dicts is shallow-merged by Plotly, so
    # re-assert the grid on any axes the figure created (e.g. facets).
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, linecolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, linecolor=GRID_COLOR)
    return fig


# --- flag rendering -----------------------------------------------------------
# Every flag maps to (badge-css-class, friendly label). Unknown flags fall back
# to a neutral "flag" chip with a humanized key so nothing ever renders raw.
_FLAG_META: dict[str, tuple[str, str]] = {
    # screener composite flags
    "deep_value": ("sh-cheap", "deep value"),
    "quality_compounder": ("sh-quality", "quality compounder"),
    "value_trap": ("sh-flag", "value-trap caution"),
    "distress": ("sh-distress", "distress"),
    "manipulation_risk": ("sh-flag", "manipulation risk"),
    # valuation / forensic flags
    "beneish_manipulation_flag": ("sh-flag", "Beneish M flag"),
    "beneish_flag": ("sh-flag", "Beneish M flag"),
    "altman_distress": ("sh-distress", "Altman distress"),
    "distress_models_agree": ("sh-distress", "distress models agree"),
    "distress_model_agreement": ("sh-distress", "distress models agree"),
    "high_accruals": ("sh-flag", "high accruals"),
    "ocf_ni_divergence": ("sh-flag", "OCF/NI divergence"),
    "receivables_outgrowing_sales": ("sh-flag", "receivables > sales"),
    "inventory_bloat": ("sh-flag", "inventory bloat"),
    "leverage_spike": ("sh-flag", "leverage spike"),
    "margin_collapse": ("sh-flag", "margin collapse"),
    "montier_high": ("sh-flag", "Montier C high"),
}


def flag_meta(flag: str) -> tuple[str, str]:
    """(css-class, label) for a flag key, with a humanized neutral fallback."""
    return _FLAG_META.get(flag, ("sh-flag", flag.replace("_", " ")))


def flag_badge(flag: str) -> str:
    """Inline HTML chip for one flag. Screens, never verdicts."""
    css, label = flag_meta(flag)
    return f'<span class="sh-badge {css}">{label}</span>'


def flag_badges(flags: list[str]) -> str:
    """Join a list of flags into a chip row (empty string if none)."""
    return "".join(flag_badge(f) for f in flags)


def mos_gauge(value: float | None, *, title: str = "Margin of safety") -> Any:
    """A Plotly Indicator gauge for margin of safety (fair - price)/fair.

    ``value`` is a fraction (0.25 == +25%). None renders an empty 'n/a' gauge so
    a missing price never crashes or fabricates a reading. The band is centered
    on 0: negative (overvalued) reads vermillion, positive (undervalued) reads
    green, with a neutral middle."""
    import plotly.graph_objects as go

    if value is None:
        fig = go.Figure(
            go.Indicator(
                mode="gauge",
                value=0,
                title={"text": f"{title}<br><span style='font-size:0.7em;color:{NEUTRAL}'>n/a — no price</span>"},
                gauge={
                    "axis": {"range": [-50, 50], "ticksuffix": "%"},
                    "bar": {"color": NEUTRAL_BG},
                    "bgcolor": "white",
                },
            )
        )
        return apply_plotly(fig)

    pct_val = max(-50.0, min(50.0, value * 100.0))
    bar_color = POSITIVE if value >= 0 else NEGATIVE
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct_val,
            number={"suffix": "%", "font": {"color": bar_color}},
            title={"text": title},
            gauge={
                "axis": {"range": [-50, 50], "ticksuffix": "%", "tickcolor": NEUTRAL},
                "bar": {"color": bar_color, "thickness": 0.3},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": GRID_COLOR,
                "steps": [
                    {"range": [-50, 0], "color": NEGATIVE_BG},
                    {"range": [0, 50], "color": POSITIVE_BG},
                ],
                "threshold": {
                    "line": {"color": NAVY, "width": 3},
                    "thickness": 0.85,
                    "value": pct_val,
                },
            },
        )
    )
    fig.update_layout(height=240)
    return apply_plotly(fig)


# Margin-of-safety discount required by uncertainty tier (Morningstar-style
# ladder: the less confident the estimate, the bigger the discount it must
# clear). Encoding confidence as band WIDTH is the honest, non-signal device.
UNCERTAINTY_DISCOUNT = {"low": 0.20, "medium": 0.30, "high": 0.40, "very_high": 0.50}


def uncertainty_from_dcf(dcf: Any) -> str:
    """Rough estimate-uncertainty tier from a DcfResult: the more of the value
    that sits in the terminal (perpetuity) tail, the less trustworthy the point
    estimate, so the wider the margin-of-safety band should be."""
    tw = getattr(dcf, "terminal_weight", None) if dcf is not None else None
    if tw is None:
        return "high"
    if tw > 0.80:
        return "very_high"
    if tw > 0.65:
        return "high"
    if tw > 0.50:
        return "medium"
    return "low"


def fair_value_bar(
    fair_value: float | None,
    price: float | None,
    *,
    uncertainty: str = "medium",
    title: str = "Fair value vs price",
) -> Any:
    """Horizontal fair-value bar with the current price as a marker and a shaded
    margin-of-safety band (SimplyWall.st-style, preferred over a gauge because a
    gauge implies a needle pointing at a recommendation).

    The band runs from ``fair_value * (1 - discount)`` up to ``fair_value``,
    where ``discount`` grows with ``uncertainty`` — so a shakier estimate
    visibly demands a bigger discount before it reads as "cheap". Cheap is a
    ZONE, never a point, and never a buy signal.
    """
    import plotly.graph_objects as go

    if fair_value is None or fair_value <= 0:
        fig = go.Figure()
        fig.add_annotation(
            text="Intrinsic fair value not computable", showarrow=False,
            font={"color": NEUTRAL}, x=0.5, y=0.5, xref="paper", yref="paper",
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(height=140)
        return apply_plotly(fig)

    discount = UNCERTAINTY_DISCOUNT.get(uncertainty, 0.30)
    band_lo = fair_value * (1.0 - discount)
    hi = max(fair_value, price or 0.0) * 1.30

    fig = go.Figure()
    # Margin-of-safety band (the "buy zone" — deliberately a zone, not a line).
    fig.add_shape(
        type="rect", x0=band_lo, x1=fair_value, y0=0.0, y1=1.0,
        fillcolor=POSITIVE_BG, line={"width": 0}, layer="below",
    )
    fig.add_annotation(
        x=(band_lo + fair_value) / 2, y=1.18, yref="y", xref="x",
        text=f"margin of safety ({int(discount * 100)}%)", showarrow=False,
        font={"size": 11, "color": POSITIVE},
    )
    # Fair-value line.
    fig.add_shape(
        type="line", x0=fair_value, x1=fair_value, y0=-0.15, y1=1.15,
        line={"color": POSITIVE, "width": 2, "dash": "solid"},
    )
    fig.add_annotation(
        x=fair_value, y=-0.45, xref="x", yref="y",
        text=f"fair ${fair_value:,.2f}", showarrow=False,
        font={"size": 11, "color": POSITIVE},
    )
    # Baseline track for context.
    fig.add_shape(
        type="line", x0=0, x1=hi, y0=0.5, y1=0.5,
        line={"color": GRID_COLOR, "width": 6},
    )
    # Current price marker.
    if price is not None and price > 0:
        gap = (fair_value - price) / fair_value
        marker_color = POSITIVE if price <= fair_value else NEGATIVE
        fig.add_trace(
            go.Scatter(
                x=[price], y=[0.5], mode="markers",
                marker={"symbol": "diamond", "size": 18, "color": marker_color,
                        "line": {"color": "white", "width": 2}},
                hovertemplate="price $%{x:,.2f}<extra></extra>",
            )
        )
        fig.add_annotation(
            x=price, y=1.55, xref="x", yref="y",
            text=f"price ${price:,.2f} ({gap:+.0%})", showarrow=False,
            font={"size": 12, "color": marker_color},
        )
    fig.update_xaxes(range=[0, hi], tickprefix="$", showgrid=False, zeroline=False)
    fig.update_yaxes(range=[-0.6, 1.8], visible=False)
    fig.update_layout(height=170, showlegend=False, title=title,
                      margin={"l": 8, "r": 8, "t": 40, "b": 28})
    return apply_plotly(fig)


def monte_carlo_fan(mc: Any, price: float | None = None,
                    *, title: str = "Monte Carlo fair-value spread") -> Any:
    """Horizontal percentile fan of a Monte Carlo DCF distribution.

    Draws the 10th–90th percentile as a thin whisker, the 25th–75th as a thick
    band (the "interquartile" mass), a median marker, and the current price as a
    diamond. This is a SENSITIVITY fan around one editable scenario — it shows
    how wide the fair value gets when the inputs wobble, NOT a probability the
    stock rises. Only the summary percentiles are stored, so this is a fan, not
    a histogram (nothing is re-simulated in the browser).
    """
    import plotly.graph_objects as go

    if mc is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Monte Carlo not computable", showarrow=False,
            font={"color": NEUTRAL}, x=0.5, y=0.5, xref="paper", yref="paper",
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(height=150)
        return apply_plotly(fig)

    hi = max(mc.p90, price or 0.0) * 1.12
    lo = min(mc.p10, price or mc.p10) * 0.9
    fig = go.Figure()
    # 10-90 whisker.
    fig.add_shape(type="line", x0=mc.p10, x1=mc.p90, y0=0.5, y1=0.5,
                  line={"color": ACCENT, "width": 4})
    # 25-75 interquartile band.
    fig.add_shape(type="rect", x0=mc.p25, x1=mc.p75, y0=0.30, y1=0.70,
                  fillcolor=ACCENT_BG, line={"color": ACCENT, "width": 1})
    # Median.
    fig.add_shape(type="line", x0=mc.median, x1=mc.median, y0=0.18, y1=0.82,
                  line={"color": NAVY, "width": 3})
    fig.add_annotation(x=mc.median, y=0.98, xref="x", yref="y",
                       text=f"median ${mc.median:,.2f}", showarrow=False,
                       font={"size": 11, "color": NAVY})
    for x, lab in ((mc.p10, "p10"), (mc.p90, "p90")):
        fig.add_annotation(x=x, y=0.06, xref="x", yref="y",
                           text=f"{lab} ${x:,.2f}", showarrow=False,
                           font={"size": 10, "color": ACCENT})
    if price is not None and price > 0:
        marker_color = POSITIVE if price <= mc.median else NEGATIVE
        fig.add_trace(go.Scatter(
            x=[price], y=[0.5], mode="markers",
            marker={"symbol": "diamond", "size": 16, "color": marker_color,
                    "line": {"color": "white", "width": 2}},
            hovertemplate="price $%{x:,.2f}<extra></extra>",
        ))
        fig.add_annotation(x=price, y=1.30, xref="x", yref="y",
                           text=f"price ${price:,.2f}", showarrow=False,
                           font={"size": 11, "color": marker_color})
    fig.update_xaxes(range=[lo, hi], tickprefix="$", showgrid=False, zeroline=False)
    fig.update_yaxes(range=[-0.1, 1.5], visible=False)
    fig.update_layout(height=160, showlegend=False, title=title,
                      margin={"l": 8, "r": 8, "t": 40, "b": 20})
    return apply_plotly(fig)


# --- injected CSS -------------------------------------------------------------
# Extends the original tokens (.sh-card / .sh-badge / .sh-ok / .sh-na / .sh-warn
# / .sh-plan / .sh-caveat / .sh-source) with a hero card, valuation badges, a
# big-number metric tile, and a gauge wrapper. app.py imports this string.
INJECTED_CSS = f"""
<style>
  .stApp {{ background: #f7f8fa; }}
  h1, h2, h3 {{ color: {NAVY}; letter-spacing: -0.01em; }}
  section[data-testid="stSidebar"] {{ background: #eef1f5; }}
  div[data-testid="stMetricValue"] {{ color: {NAVY}; }}

  .sh-card {{
    background: white; border: 1px solid {GRID_COLOR}; border-radius: 10px;
    padding: 1rem 1.25rem; margin-bottom: 0.75rem;
  }}
  .sh-hero {{
    background: white; border: 1px solid {GRID_COLOR}; border-top: 3px solid {ACCENT};
    border-radius: 10px; padding: 1.1rem 1.35rem; margin-bottom: 0.85rem;
    box-shadow: 0 1px 3px rgba(27,42,74,0.06);
  }}
  .sh-metric {{
    background: white; border: 1px solid {GRID_COLOR}; border-radius: 10px;
    padding: 0.85rem 1.1rem; margin-bottom: 0.6rem; min-height: 92px;
  }}
  .sh-metric .sh-metric-label {{
    color: {NEUTRAL}; font-size: 0.78rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;
  }}
  .sh-metric .sh-metric-value {{
    color: {NAVY}; font-size: 1.9rem; font-weight: 700; line-height: 1.15;
    font-variant-numeric: tabular-nums; font-feature-settings: "tnum";
  }}
  .sh-metric .sh-metric-sub {{ color: {NEUTRAL}; font-size: 0.8rem; }}
  .sh-num {{ font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }}
  .sh-gauge {{
    background: white; border: 1px solid {GRID_COLOR}; border-radius: 10px;
    padding: 0.4rem 0.6rem; margin-bottom: 0.6rem;
  }}

  .sh-badge {{
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 600; margin: 2px 4px 2px 0;
    white-space: nowrap;
  }}
  /* original status badges */
  .sh-ok {{ background: {POSITIVE_BG}; color: #1b6b3a; }}
  .sh-na {{ background: {NEUTRAL_BG}; color: {NEUTRAL}; }}
  .sh-warn {{ background: {WARNING_BG}; color: {WARNING}; }}
  .sh-plan {{ background: {ACCENT_BG}; color: {ACCENT}; }}
  /* valuation verdict badges */
  .sh-cheap {{ background: {POSITIVE_BG}; color: {POSITIVE}; }}
  .sh-fair {{ background: {NEUTRAL_BG}; color: {NEUTRAL}; }}
  .sh-rich {{ background: {WARNING_BG}; color: {WARNING}; }}
  .sh-distress {{ background: {NEGATIVE_BG}; color: {NEGATIVE}; }}
  .sh-quality {{ background: {ACCENT_BG}; color: {ACCENT}; }}
  .sh-flag {{ background: {WARNING_BG}; color: {WARNING}; }}

  .sh-caveat {{ color: #6b7280; font-size: 0.85rem; }}
  .sh-source {{ color: #8a93a3; font-size: 0.78rem; }}
  .sh-good {{ color: {POSITIVE}; font-weight: 600; }}
  .sh-bad {{ color: {NEGATIVE}; font-weight: 600; }}
</style>
"""


def metric_tile(label: str, value: str, sub: str = "") -> str:
    """HTML for a big-number metric tile (tabular-nums). ``value`` should already
    be formatted (e.g. via core.format) — pass 'n/a' / 'n/m' for missing data."""
    sub_html = f'<div class="sh-metric-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="sh-metric"><div class="sh-metric-label">{label}</div>'
        f'<div class="sh-metric-value">{value}</div>{sub_html}</div>'
    )
