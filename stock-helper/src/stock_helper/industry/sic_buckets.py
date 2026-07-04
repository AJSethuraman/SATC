"""SIC code -> industry bucket mapping and applicability helpers.

Coarse by design (Phase 4 refines this). The load-bearing distinction for v0.1
is financial vs non-financial: banks and insurers must not receive industrial
ratios (gross margin, current ratio, interest coverage), and bank-specific
signals apply only to the banking bucket.
"""

BANKING = "banking"
INSURANCE = "insurance"
OTHER_FINANCIAL = "other_financial"
REAL_ESTATE = "real_estate"
UTILITIES = "utilities"
ENERGY = "energy"
MATERIALS = "materials"
INDUSTRIALS = "industrials"
CONSUMER = "consumer"
HEALTHCARE = "healthcare"
TECHNOLOGY = "technology"
COMMUNICATIONS = "communications"
OTHER = "other"

FINANCIAL_BUCKETS = {BANKING, INSURANCE, OTHER_FINANCIAL}

ALL_BUCKETS = [
    BANKING, INSURANCE, OTHER_FINANCIAL, REAL_ESTATE, UTILITIES, ENERGY,
    MATERIALS, INDUSTRIALS, CONSUMER, HEALTHCARE, TECHNOLOGY, COMMUNICATIONS, OTHER,
]

# Ordered (start, end_inclusive, bucket). First match wins, so put specific
# sub-ranges before the broad ranges that contain them.
_SIC_RANGES: list[tuple[int, int, str]] = [
    # Financials — the ranges that matter most for correctness
    (6020, 6099, BANKING),          # depository institutions
    (6712, 6712, BANKING),          # bank holding companies
    (6300, 6499, INSURANCE),        # carriers, agents, brokers
    (6500, 6599, REAL_ESTATE),
    (6798, 6798, REAL_ESTATE),      # REITs
    (6000, 6799, OTHER_FINANCIAL),  # remaining finance: credit, brokers, holdings
    # Healthcare before broad manufacturing
    (2833, 2836, HEALTHCARE),       # drugs / biologicals
    (3826, 3826, HEALTHCARE),       # lab instruments
    (3840, 3851, HEALTHCARE),       # medical devices
    (8000, 8099, HEALTHCARE),       # health services
    # Technology before broad manufacturing/services
    (3570, 3579, TECHNOLOGY),       # computers & office equipment
    (3600, 3699, TECHNOLOGY),       # electronics incl. 3674 semiconductors
    (7370, 7379, TECHNOLOGY),       # software & data services
    # Communications & utilities
    (4800, 4899, COMMUNICATIONS),
    (4900, 4999, UTILITIES),
    # Energy & materials
    (1300, 1399, ENERGY),           # oil & gas extraction
    (2900, 2999, ENERGY),           # petroleum refining
    (1000, 1499, MATERIALS),        # mining, quarrying
    (2600, 2699, MATERIALS),        # paper
    (2800, 2899, MATERIALS),        # chemicals (non-pharma; pharma matched above)
    (3300, 3399, MATERIALS),        # primary metals
    # Consumer
    (2000, 2199, CONSUMER),         # food, beverage, tobacco
    (5000, 5999, CONSUMER),         # wholesale & retail (5331 = COST)
    (7000, 7099, CONSUMER),         # lodging
    (5800, 5899, CONSUMER),
    # Broad industrial ranges last
    (100, 999, OTHER),              # agriculture
    (1500, 1799, INDUSTRIALS),      # construction
    (2200, 3999, INDUSTRIALS),      # remaining manufacturing
    (4000, 4799, INDUSTRIALS),      # transportation
    (7100, 8999, OTHER),            # remaining services
]


def sic_to_bucket(sic: str | int | None) -> str:
    """Map an SIC code (as SEC reports it, e.g. "6022") to an industry bucket."""
    if sic in (None, ""):
        return OTHER
    try:
        code = int(sic)
    except (TypeError, ValueError):
        return OTHER
    for start, end, bucket in _SIC_RANGES:
        if start <= code <= end:
            return bucket
    return OTHER


def is_financial(bucket: str) -> bool:
    return bucket in FINANCIAL_BUCKETS


def peer_group_label(sic: str | None, sic_description: str | None) -> str:
    """Placeholder peer grouping (Phase 4 builds real peer lists): companies
    sharing the same 4-digit SIC are the provisional peer set."""
    if not sic:
        return "Peer group unavailable (no SIC on file)"
    desc = f" — {sic_description}" if sic_description else ""
    return f"Provisional peers: SIC {sic}{desc} (real peer mapping is Phase 4)"
