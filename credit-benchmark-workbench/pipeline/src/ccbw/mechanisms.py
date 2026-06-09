"""Mechanism-level explanations, weighted toward commercial credit.

When a borrower departs from peers, the workbench explains the *mechanism*
that usually produces that departure in that segment -- not just the delta.
Keyed (metric, segment) with a generic fallback per metric. Written for a
reviewer building commercial fluency: each entry names the channel through
which the number moves and what a lender should go verify.
"""

MECHANISMS: dict[tuple[str, str], str] = {
    # ---- leverage ----
    ("debt_ebitda", "*"): (
        "Leverage rises through two channels: the numerator (acquisitions, "
        "shareholder distributions, capex funded with debt, revolver creep "
        "funding working capital) or the denominator (EBITDA compression). "
        "Denominator-driven leverage is the more dangerous read because it "
        "compounds -- verify which channel moved before accepting a 'we'll "
        "grow into it' rationale."),
    ("debt_ebitda", "agribusiness"): (
        "In agribusiness, spot leverage swings with the crop cycle: a weak "
        "price year compresses EBITDA and spikes the multiple without any "
        "new borrowing. Judge against through-cycle (3-yr average EBITDA) "
        "leverage; structural concern is warranted when through-cycle "
        "leverage is also elevated, or when debt grew during a strong price "
        "year (expansion at the top of the cycle)."),
    ("debt_ebitda", "leveraged_abl"): (
        "For leveraged names the question is seldom the multiple itself but "
        "the path: sponsor dividends recapitalize leverage back up after "
        "deleveraging, and revolver usage migrating from seasonal to "
        "permanent signals working capital absorbing cash. Check whether "
        "current leverage reflects the original structure or re-levering."),
    ("net_debt_ebitda", "*"): (
        "A wide gap between gross and net leverage means a cash buffer -- "
        "but verify the cash is unrestricted and not trapped (foreign subs, "
        "regulatory deposits, borrowing-base collateral). Private MM "
        "borrowers typically sweep cash against the revolver, so a large "
        "idle balance alongside revolver usage deserves a question."),
    ("debt_ebitda_3y", "agribusiness"): (
        "Through-cycle leverage strips the crop cycle out of the read. If "
        "spot is high but through-cycle is in range, the borrower is in a "
        "weak price year (carry risk, not structure risk). If through-cycle "
        "is high, the balance sheet is structurally over-levered for a "
        "commodity business and a price recovery will not fix it."),
    # ---- coverage ----
    ("interest_coverage", "*"): (
        "Coverage erodes from the numerator (EBITDA decline) or the "
        "denominator (rate resets on floating debt, repricing at refinance, "
        "step-ups). Since most private MM debt floats, a coverage decline "
        "with stable EBITDA usually means the rate environment did it -- "
        "check hedging. Coverage below ~1.5x leaves no room for capex and "
        "taxes; below 1.0x the borrower is consuming liquidity to stay "
        "current."),
    ("interest_coverage", "cre_opco"): (
        "For property operators this is the DSCR analog. Erosion paths: "
        "occupancy/lease-rollover (revenue), opex inflation against fixed "
        "leases (NOI margin), or floating-rate resets. Office exposure "
        "post-2020 makes rollover schedule and re-leasing spreads the "
        "primary verification items."),
    ("fcc_proxy", "leveraged_abl"): (
        "(EBITDA - capex)/interest approximates fixed-charge coverage. For "
        "leveraged borrowers, scheduled amortization (not in public data) "
        "tightens this further -- a 1.2x proxy can be sub-1.0x after "
        "amortization. Capex deferral can flatter this ratio for a year or "
        "two at the cost of competitiveness: check maintenance vs. growth "
        "capex split."),
    # ---- margins ----
    ("ebitda_margin", "*"): (
        "Margin compression mechanisms: input-cost pass-through lag, mix "
        "shift toward lower-margin volume, pricing concessions to hold "
        "share, or fixed-cost deleveraging on falling volume. The "
        "pass-through-lag story is self-correcting within ~12 months; the "
        "mix and pricing stories are structural. Ask which one before "
        "accepting an 'inflation, temporary' rationale."),
    ("ebitda_margin", "healthcare"): (
        "Provider margins move with payor mix (government rates are fixed; "
        "commercial rates negotiated), labor (agency/contract staffing is "
        "the classic margin destroyer), and acuity mix. Reimbursement-rate "
        "cuts arrive on a policy calendar, not a business cycle -- a margin "
        "decline against stable volume points at rate or labor, both "
        "verifiable."),
    ("ebitda_margin", "agribusiness"): (
        "Processor margins are spread businesses (output price minus input "
        "cost), structurally thin and mean-reverting with the commodity "
        "complex. A margin departure here is only meaningful against the "
        "segment's own distribution and cycle position."),
    ("gross_margin", "*"): (
        "Gross margin isolates the production/procurement spread from "
        "overhead. Falling gross with stable EBITDA margin means overhead "
        "cuts are masking product-level erosion -- sustainable once, not "
        "twice."),
    # ---- working capital ----
    ("dso", "*"): (
        "Rising DSO mechanisms: customer-mix shift toward slower payers, "
        "extended terms granted to hold volume (disguised price cut), "
        "billing/collections breakdown, or disputed receivables aging on "
        "the book. Verify aging schedule and concentration -- one large "
        "slow-paying customer moves the whole ratio."),
    ("dso", "healthcare"): (
        "Provider DSO is the reimbursement-stress channel: payor-mix shift "
        "toward government (slower, audited), denials/recoupment activity, "
        "or coding/billing system transitions. A DSO drift of 10+ days in a "
        "provider is an early-warning flag well before margins move."),
    ("dio", "*"): (
        "Inventory build mechanisms: demand miss (involuntary build -- the "
        "bad one), strategic pre-buy ahead of input cost increases, new "
        "product/location stocking, or obsolescence accumulating unwritten. "
        "Involuntary build shows alongside falling revenue growth; check "
        "which direction revenue moved."),
    ("dio", "agribusiness"): (
        "Year-end inventory in agribusiness reflects harvest timing against "
        "the fiscal year end (basis note), commodity price levels (same "
        "bushels, different dollars), and carry decisions when futures "
        "curves reward storage. Compare units where possible; a dollar-DIO "
        "spike in a high-price year may be price, not volume."),
    ("dpo", "*"): (
        "Rising DPO is cheap financing up to the point it signals stress: "
        "payment stretching shows up as DPO drifting above peer norms while "
        "the revolver is drawn. Cross-check with revolver usage and any "
        "supplier-finance programs (which reclassify trade payables into "
        "what is economically debt)."),
    ("ccc", "*"): (
        "The cash conversion cycle is the financing the business model "
        "demands: each day of CCC is a day of revenue that must be funded "
        "by the revolver or equity. A lengthening CCC during growth is the "
        "classic mechanism of 'profitable companies that run out of cash' "
        "-- size the revolver against peak, not average, CCC."),
    ("ccc", "leveraged_abl"): (
        "For ABL structures the CCC maps directly to borrowing-base "
        "capacity: receivables and inventory ARE the collateral. A "
        "lengthening cycle simultaneously increases funding need and (via "
        "aging ineligibles) can shrink availability -- the squeeze arrives "
        "from both sides at once."),
    # ---- liquidity / structure ----
    ("current_ratio", "*"): (
        "Below-peer current ratio means reliance on external liquidity "
        "(revolver) to bridge the operating cycle. Acceptable when "
        "availability is verified and committed; a flag when paired with "
        "high revolver utilization -- the public data cannot see "
        "availability, so this must be verified from the borrower's "
        "compliance certificate."),
    ("debt_assets", "cre_opco"): (
        "Book LTV proxy. Rises via new borrowing or via impairments "
        "shrinking the asset base -- in a falling-value market (office), "
        "book lags market, so a stable ratio can mask real deterioration; "
        "current appraised or implied-cap-rate values are the verification "
        "item."),
    ("rent_adj_leverage", "healthcare"): (
        "Capitalizing rent (8x convention) restores comparability between "
        "owned-facility and leased-facility operators: an asset-light "
        "operator can show modest balance-sheet debt while carrying heavy "
        "fixed lease obligations with debt-like priority. Sale-leasebacks "
        "move leverage from the debt line into rent -- this metric catches "
        "that migration; unadjusted leverage does not."),
    ("rev_growth", "*"): (
        "Negative or decelerating growth interacts with fixed costs "
        "(operating leverage) before it reaches EBITDA. Distinguish volume "
        "vs. price vs. lost-customer effects -- customer-concentration "
        "losses are the least recoverable."),
    ("ebitda_volatility", "*"): (
        "Volatility is the denominator risk under any leverage multiple: a "
        "5x multiple on EBITDA that swings 30% is a different credit than "
        "5x on stable EBITDA. Higher volatility argues for structurally "
        "lower leverage tolerance and stronger covenant cushions, not just "
        "a watch flag."),
}


def mechanism_for(metric: str, segment: str) -> str:
    return (MECHANISMS.get((metric, segment))
            or MECHANISMS.get((metric, "*"))
            or "No mechanism note recorded for this metric.")
