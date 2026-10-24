# KeyBank Excel — style spec

The brand, translated honestly to native Excel. Excel can only use installed
fonts and rectangular cells, so the brand lives in **colour + structure**. The
rendered reference is `visual-spec.html` — match it.

## Tokens (hex as openpyxl wants — no `#`)

### Brand core
| token | hex | role |
|---|---|---|
| `INK` | `0A0908` | header bands, primary dark surfaces |
| `ONYX` | `16130F` | system-tab section bands (`_config`/`_code`/`_readme`) |
| `KEY_RED` | `CC0000` | the accent rule, alerts, KPI accent — leads sparingly |
| `CRIMSON` | `960019` | alert text / pressed red |

### Surfaces & text
| token | hex | role |
|---|---|---|
| `PAPER` | `FFFFFF` | sheet background |
| `CANVAS` | `F4F1EC` | KPI tiles, sub-headers |
| `MIST` | `E4DFD5` | caution fill, dividers |
| `STONE` | `B9B4AC` | disabled / faint rules |
| `SLATE` | `57534B` | secondary text / labels |
| `INK_TEXT` | `16130F` | primary data text (warm black) |

### Semantic & heat (brand-muted — NOT openpyxl defaults)
| token | hex | role |
|---|---|---|
| `ALERT_FG` | `F7DEDE` | deterioration fill |
| `POSITIVE` | `1E7A47` | improvement text |
| `HEAT_BAD` | `E0A6A6` | z high → stress |
| `HEAT_MID` | `F4F1EC` | z ≈ 0 |
| `HEAT_GOOD` | `BBD3BD` | z low → calm |

## Type — brand font → Excel font
| use | Excel font | size | note |
|---|---|---|---|
| Titles, headers, KPI numbers | **Arial** (bold/black) | 16 / 11 / 20 | Archivo → Arial |
| All data, labels, notes | **Calibri** | 11 / 9 | Hanken → Calibri; numerics right-aligned, tabular |
| Code tabs only | **Consolas** | 9 | `_code_py` / `_code_vba` |

Excel can't letter-space or load Archivo — that's expected. Confidence comes
from colour and layout, not bespoke type.

## Rules that travel
- Hide interior gridlines (`showGridLines = False`); borders only where designed.
- Freeze panes just below the column-header row.
- KPI tiles: merged cells, `CANVAS` fill, **3pt `KEY_RED` top border**; never a
  full red fill behind text.
- Numbers right-aligned, `0.00` (rates) / `0.0` (YoY) / `0.00` (z-score).
- Heat uses `HEAT_*` only. One red accent rule per banner. Red elsewhere = alert.

## Lane coding (so expansion stays consistent)
- **Dashboards** (Consumer · Commercial · Price) — share one system: **Ink**
  header band + red rule, KPI strip, trend chart, **brand heat** on the z-score
  column, sparkline per row.
- **Watchlist_Geo** — the one place **Key Red** leads a banner (the geographic
  boundary gate). Diverging heat on YoY (red = deterioration).
- **System tabs** (`_config` · `_code` · `_readme`) — **Onyx** section bands,
  Consolas, **no heat**. Quiet and structural.

## Chart archetypes (time series)
- **A · single series + stress band** — plot the series; shade the alert zone
  (8-qtr mean + 1σ) in faint `KEY_RED`; mark the latest point. Reads "is this in
  trouble?" at a glance.
- **B · two-series comparison** — two lines on one axis, `INK` + `KEY_RED`,
  legend below. Reads divergence (e.g. HPI rising vs CRE correcting).
- **C · Story Builder (variance + layers)** — a *focus* series in `INK` read
  against a dashed `SLATE` *baseline* (trend / mean / prior-Q); the gap drawn as
  native **up/down bars** — `POSITIVE` favorable, `KEY_RED` unfavorable (flip by
  series direction: higher is worse for delinquency, better for prices). **Data
  labels on every reading** put the nominal numbers on the chart; a `Qtr | Actual
  | Base | Var` table sits beside it. Up to three connected *layers* tell one
  credit-risk story; mixed units (%, index) split onto a **secondary axis**.
  Built by `keybank_story.py` — pure Python, no macro. This is the headline view.
- Default each dashboard to a **12-quarter** trend chart under the KPI strip,
  plus an **8-quarter sparkline** per data row.

## Files
`keybank_style.py` (tokens + helpers) · `keybank_charts.py` (LineChart builders)
· `keybank_story.py` (Archetype C — variance Story Builder) ·
`dummy_timeseries.csv` + `gen_dummy_timeseries.py` (fixture data) ·
`visual-spec.html` (rendered reference) · `AGENT_PROMPT.md` (the directive).
