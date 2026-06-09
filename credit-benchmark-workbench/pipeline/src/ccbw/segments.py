"""Portfolio segment taxonomy.

Each segment carries its own peer-set definition (SIC ranges and/or
financial screens), normalization rules, and cyclicality treatment. One
generic ruleset across segments is explicitly NOT used: a CRE operating
company's leverage reads off the balance sheet against assets and NOI-like
earnings, an agribusiness borrower's leverage must be judged through the
crop cycle, and a healthcare provider's leverage is understated unless
lease/rent obligations are capitalized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class SizeBucket:
    key: str
    label: str
    ebitda_lo: float          # USD
    ebitda_hi: float


# EBITDA bands aligned to private-credit market segmentation. The public
# universe skews far above these bands -- that is the size-distortion
# problem the adjustment engine exists to handle.
SIZE_BUCKETS: list[SizeBucket] = [
    SizeBucket("lmm", "Lower middle market ($5-25M EBITDA)", 5e6, 25e6),
    SizeBucket("cmm", "Core middle market ($25-100M EBITDA)", 25e6, 100e6),
    SizeBucket("umm", "Upper middle market ($100-300M EBITDA)", 100e6, 300e6),
    SizeBucket("large", "Public-scale (> $300M EBITDA, context only)", 300e6, float("inf")),
]

BUCKET_BY_KEY = {b.key: b for b in SIZE_BUCKETS}


def size_bucket_for_ebitda(ebitda: float) -> Optional[str]:
    for b in SIZE_BUCKETS:
        if b.ebitda_lo <= ebitda < b.ebitda_hi:
            return b.key
    return None  # below $5M: out of the modeled middle-market range


@dataclass(frozen=True)
class SegmentSpec:
    key: str
    label: str
    sic_ranges: tuple[tuple[int, int], ...]
    sic_excludes: tuple[tuple[int, int], ...]
    peer_definition: str
    normalization_rules: tuple[str, ...]
    cyclicality_treatment: str
    # Metrics emphasized / suppressed for this segment
    primary_metrics: tuple[str, ...]
    suppressed_metrics: tuple[str, ...] = ()
    # Extra screen applied to a company's panel rows (e.g. leveraged/ABL)
    screen: Optional[Callable] = None
    # Use 3y-average EBITDA for leverage (through-cycle) in addition to spot
    through_cycle_leverage: bool = False
    # Capitalize rent into leverage/coverage (EBITDAR basis)
    rent_adjusted: bool = False


def _leveraged_abl_screen(row: dict) -> bool:
    """Leveraged / ABL-adjacent is a financial-profile screen, not a SIC code.

    Qualifies if spot leverage >= 4.0x on positive EBITDA, OR the asset base
    is working-capital-intensive (receivables + inventory >= 35% of total
    assets) the way ABL borrowing bases are built.
    """
    ebitda = row.get("ebitda")
    debt = row.get("total_debt")
    ta = row.get("total_assets")
    ar = row.get("receivables") or 0.0
    inv = row.get("inventory") or 0.0
    if ebitda and ebitda > 0 and debt is not None and debt / ebitda >= 4.0:
        return True
    if ta and ta > 0 and (ar + inv) / ta >= 0.35:
        return True
    return False


SEGMENTS: dict[str, SegmentSpec] = {}


def _seg(spec: SegmentSpec) -> None:
    SEGMENTS[spec.key] = spec


_seg(SegmentSpec(
    key="cni",
    label="Middle-Market C&I",
    sic_ranges=((2000, 3999), (5000, 5199), (7300, 7399)),
    sic_excludes=((2833, 2836), (3841, 3851), (2000, 2099)),  # pharma/devices -> healthcare; food -> agribusiness
    peer_definition=(
        "Public manufacturers, distributors and business-services companies "
        "(SIC 2000-3999 ex pharma/devices/food, 5000-5199, 7300-7399). "
        "Generic commercial & industrial credit: diversified end markets, "
        "cash-flow lending basis."
    ),
    normalization_rules=(
        "EBITDA = operating income + D&A (no addbacks for non-recurring items; "
        "public data does not support consistent addback identification -- "
        "noted as a basis difference vs. sponsor-adjusted private EBITDA).",
        "Total debt includes current portions and short-term borrowings.",
        "Working-capital cycle on a trade basis: DSO/DIO/DPO from year-end "
        "balances (point-in-time, not average -- basis-labeled).",
    ),
    cyclicality_treatment=(
        "Moderate cyclicality: 3-year revenue/EBITDA growth volatility is "
        "reported alongside levels; current-year readings are anchored "
        "against the pre-2020 baseline to avoid judging a peak as normal."
    ),
    primary_metrics=("debt_ebitda", "net_debt_ebitda", "interest_coverage",
                     "ebitda_margin", "ccc", "current_ratio"),
))

_seg(SegmentSpec(
    key="cre_opco",
    label="CRE Operating Companies (office / multifamily / retail exposure)",
    sic_ranges=((6500, 6599), (6798, 6798)),
    sic_excludes=(),
    peer_definition=(
        "Public real estate operators and equity REITs (SIC 6500-6599, 6798) "
        "with office, multifamily and retail exposure. Public REITs are the "
        "only sizable public CRE-operating universe; their FFO/EBITDAre "
        "conventions differ from a private opco's NOI -- treated as a "
        "comparability note on every CRE benchmark, not silently merged."
    ),
    normalization_rules=(
        "Primary leverage basis is debt / total assets (book LTV proxy), not "
        "debt/EBITDA: asset-backed lending logic, and public REIT EBITDA is "
        "not comparable to private-opco NOI without adjustment.",
        "Interest coverage on EBITDA as an NOI proxy (DSCR analog); "
        "amortization-inclusive DSCR is not computable from public data -- "
        "flagged as a coverage gap.",
        "Trade working-capital metrics (DSO/DIO/CCC) suppressed: not "
        "meaningful for property operators.",
    ),
    cyclicality_treatment=(
        "Long cycles tied to occupancy, lease rollover and rates. Trend "
        "context uses 5 years where available; post-2020 office stress makes "
        "the pre-2020 baseline mandatory context for any current reading."
    ),
    primary_metrics=("debt_assets", "interest_coverage", "debt_ebitda",
                     "ebitda_margin"),
    suppressed_metrics=("dso", "dio", "dpo", "ccc", "gross_margin"),
))

_seg(SegmentSpec(
    key="healthcare",
    label="Healthcare (providers & services)",
    sic_ranges=((8000, 8099),),
    sic_excludes=(),
    peer_definition=(
        "Public healthcare providers and services (SIC 8000-8099): hospitals, "
        "outpatient, skilled nursing, home health, labs. Pharma and devices "
        "excluded -- different credit (IP/product risk, not reimbursement risk)."
    ),
    normalization_rules=(
        "Rent-adjusted leverage where rent is disclosed: "
        "(total debt + 8x rent) / EBITDAR -- many providers lease their real "
        "estate, and unadjusted leverage understates fixed obligations.",
        "DSO is a primary metric: payor mix (government vs. commercial) "
        "drives the receivables cycle and is the early-warning channel for "
        "reimbursement stress.",
        "Inventory metrics de-emphasized (supplies, not trade inventory).",
    ),
    cyclicality_treatment=(
        "Low macro cyclicality but high policy/reimbursement-event risk: "
        "trend breaks matter more than cycle position; flags weight "
        "margin/DSO deterioration over level departures."
    ),
    primary_metrics=("debt_ebitda", "rent_adj_leverage", "interest_coverage",
                     "ebitda_margin", "dso", "current_ratio"),
    suppressed_metrics=("dio", "dpo"),
    rent_adjusted=True,
))

_seg(SegmentSpec(
    key="agribusiness",
    label="Agribusiness (production & processing)",
    sic_ranges=((100, 999), (2000, 2099), (5150, 5159)),
    sic_excludes=(),
    peer_definition=(
        "Public agricultural producers, food/beverage processors and farm-"
        "product wholesalers (SIC 0100-0999, 2000-2099, 5150-5159). Public "
        "names are dominated by large processors; pure-play production "
        "comparables are scarce -- a standing coverage gap for the segment."
    ),
    normalization_rules=(
        "Through-cycle leverage: total debt / 3-year average EBITDA reported "
        "alongside spot leverage -- a single crop year is not a basis for a "
        "leverage judgment.",
        "Inventory metrics carry a seasonality basis note: year-end balances "
        "depend on fiscal-year-end position relative to harvest.",
        "Commodity pass-through means margins are structurally thin and "
        "volatile; margin level is judged against the segment's own "
        "distribution, never against C&I.",
    ),
    cyclicality_treatment=(
        "High cyclicality on a 3-5 year commodity cycle. Spot ratios are "
        "always paired with 3-year averages; cyclicality stats (EBITDA "
        "growth volatility) are first-class metrics for this segment."
    ),
    primary_metrics=("debt_ebitda", "debt_ebitda_3y", "interest_coverage",
                     "ebitda_margin", "current_ratio", "dio"),
    through_cycle_leverage=True,
))

_seg(SegmentSpec(
    key="leveraged_abl",
    label="Leveraged / ABL-adjacent",
    sic_ranges=((2000, 3999), (5000, 5999), (7300, 7399)),
    sic_excludes=(),
    peer_definition=(
        "Cross-industry financial-profile screen, not a SIC bucket: spot "
        "leverage >= 4.0x on positive EBITDA, or working-capital-intensive "
        "balance sheets (AR + inventory >= 35% of assets) of the kind that "
        "support borrowing-base lending."
    ),
    normalization_rules=(
        "Net leverage emphasized alongside gross (cash sweeps are the norm "
        "in leveraged structures).",
        "Fixed-charge coverage proxy: (EBITDA - capex) / interest. True FCC "
        "(with scheduled amortization) is not computable from public data -- "
        "coverage gap.",
        "Working-capital cycle is a primary metric: borrowing-base capacity "
        "and the cash-conversion cycle drive liquidity for ABL names.",
        "Revolver availability/utilization is not observable in XBRL -- "
        "standing coverage gap; liquidity judged via current ratio + CCC.",
    ),
    cyclicality_treatment=(
        "Leverage amplifies cyclicality: flags tighten coverage thresholds "
        "rather than leverage levels (a 5x name with 3x coverage differs "
        "from a 5x name at 1.5x). EBITDA volatility is reported with every "
        "leverage stat."
    ),
    primary_metrics=("debt_ebitda", "net_debt_ebitda", "fcc_proxy",
                     "interest_coverage", "ccc", "current_ratio"),
    screen=_leveraged_abl_screen,
))


def sic_in_segment(sic: int, seg: SegmentSpec) -> bool:
    if any(lo <= sic <= hi for lo, hi in seg.sic_excludes):
        return False
    return any(lo <= sic <= hi for lo, hi in seg.sic_ranges)


def segments_for_company(sic: int, panel_rows: list[dict]) -> list[str]:
    """All segments a company qualifies for. SIC-based segments first; the
    leveraged/ABL screen runs on the company's most recent panel row and can
    overlap a SIC segment (a leveraged C&I name informs both peer sets)."""
    out = [k for k, s in SEGMENTS.items()
           if s.screen is None and sic_in_segment(sic, s)]
    lev = SEGMENTS["leveraged_abl"]
    if panel_rows and sic_in_segment(sic, lev) and lev.screen(panel_rows[-1]):
        out.append("leveraged_abl")
    return out
