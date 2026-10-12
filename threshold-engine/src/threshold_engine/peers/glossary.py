"""Every term the peer workbook uses: what it means, and exactly how it is calculated.

The peer workbook's own list, kept apart from ``threshold_engine.glossary``
(the threshold workbook's), as docs/PEERS-SPEC.md asks. Written for the person
reading the workbook. Each calculation is the one the code performs, so a
reviewer can redo it by hand from the Data tab. The peer workbook's tests
check that every term here is on its Glossary tab.
"""

# (term, what it means, how it is calculated)
PEER_TERMS = [
    ("Pack",
     "The peers a comparison is made against. KeyBank is never in its own pack.",
     "The peers whose Include cell on the Pack tab is TRUE. It starts as every peer or the regionals only, "
     "as the build was told, and changes as Include cells are changed."),
    ("Include",
     "Whether a peer is in the pack.",
     "A TRUE/FALSE cell on the Pack tab. The composite, the band and best and worst in pack all recalculate "
     "when it changes."),
    ("Regional",
     "A peer in the regionals-only pack.",
     "Read from the roster (config/peers.json): every peer except the largest national banks and the card "
     "specialist. A working grouping, not a definition."),
    ("TTM gross charge-off rate",
     "What a bank wrote off over the last four quarters, as a share of the book.",
     "100 x the four quarters' gross charge-offs / the mean of the four quarter-end balances. A quarter's "
     "charge-offs are its year-to-date figure less the previous quarter's (Q1 is its year-to-date)."),
    ("TTM net charge-off rate",
     "The same, after what was recovered on loans written off earlier.",
     "100 x (the four quarters' gross charge-offs - their recoveries) / the mean of the four quarter-end "
     "balances."),
    ("Average balance",
     "The size of the book over the four quarters a rate covers.",
     "The mean of the four quarter-end balances, in $ thousands as filed."),
    ("Structural move",
     "A change in a book's size too large to be lending: a merger, a purchase, a sale or a reclassification. "
     "Charge-offs over it describe a different book, so its rates are not used.",
     "A quarter whose balance moved by more than the jump from the quarter before (|this / last - 1| > jump), "
     "or rose from zero. A rate is not kept if any quarter from the one before its window to its last quarter "
     "moved structurally."),
    ("Jump",
     "The largest quarter-on-quarter move in a book that still counts as lending rather than a structural "
     "move.",
     "A build setting, shown on the Run tab. 0.25 means a 25% move in one quarter."),
    ("Minimum book",
     "The smallest book whose rate is used. A few charge-offs on a tiny book make a rate that means nothing.",
     "A build setting, in $ thousands, shown on the Run tab. A rate is not kept when the average balance is "
     "below it. KeyBank can be exempt, so its own line is never blank for size."),
    ("Kept",
     "Whether a bank's rate for a quarter is used.",
     "TRUE when the average balance is at least the minimum book and above zero, all four quarters' flows "
     "were filed, and there was no structural move. Why says the first reason it is not, in that order: "
     "the jump, the minimum, a missing quarter."),
    ("Composite",
     "The pack's rate as if its banks were one bank: every dollar counts once, so a large book weighs more "
     "than a small one.",
     "100 x the summed TTM charge-offs of the included peers kept that quarter / their summed average "
     "balances (net: charge-offs less recoveries). Blank when fewer banks than the minimum are kept."),
    ("Band",
     "How spread out the pack's banks were each quarter, each bank counting once whatever its size.",
     "The 10th, 25th, 75th and 90th percentiles of the kept rates of the included peers (PERCENTILE, which "
     "interpolates as PERCENTILE.INC does). The light band is 10th to 90th, the darker 25th to 75th. Not "
     "drawn in a quarter when fewer banks than the minimum are kept."),
    ("Banks in",
     "How many of the pack's banks are in a quarter's composite and band.",
     "The count of included peers whose rate is kept that quarter."),
    ("Best in pack, Worst in pack",
     "The included peer with the lowest and the highest recent loss rate.",
     "Each included peer's mean kept rate over the last quarters stated on the Pack tab, among peers with at "
     "least the stated number of kept quarters in that window. Lowest is best, highest is worst; a tie goes to "
     "the peer listed first."),
    ("Peer A, Peer B",
     "Two lines drawn beside KeyBank, each one named peer or whoever best or worst in pack resolves to.",
     "Picked on the Pack tab. Drawn whether or not that peer is included in the pack, kept quarters only."),
    ("Lagged rate",
     "A year's losses against the book that made them, lent some years earlier. Fast growth flatters a "
     "plain rate, because new loans have not had time to go bad.",
     "100 x the year's net charge-offs (the Q4 year-to-date charge-offs less recoveries, as filed) / the mean "
     "of the four quarter-end balances of the earlier year. A pack total sums the dollars before dividing."),
    ("Normalisation",
     "How far a rate has moved between two years.",
     "Each year's figure is the mean of its four quarterly TTM net rates (blank unless all four were kept); "
     "the ratio is the later year's / the earlier year's, blank when the earlier year is 0 or below (net "
     "recoveries), because a ratio to it would read the wrong way."),
    ("Organic index",
     "A book's size against a base quarter, with purchased books taken out, so growth means lending.",
     "Base quarter = 100. Each quarter's growth from the one before is chained, except in an acquisition "
     "quarter, where the growth is set to 1. As reported is the plain balance / the base balance x 100."),
    ("Acquisition quarter",
     "A quarter in which the bank took over another institution or a book of loans.",
     "The bank's mergers in the FDIC structure-change record (an allowlist of change codes, counted at the "
     "quarter-end on or after the effective date), plus any purchase declared at the build, such as one of a "
     "nonbank the FDIC record does not show."),
    ("Industry",
     "Every FDIC-insured filer's book taken together.",
     "Each quarter's flow summed bank by bank (a later quarter only over banks that filed both it and the "
     "quarter before), the balances summed, then the TTM rate as for one bank."),
    ("Own factor",
     "How much of a bank's change in loss rate is its own rather than the industry's. Above 1 the bank "
     "worsened more than the industry; below 1, less.",
     "(The bank's calendar-year net rate / its base-year rate) / (the industry's net rate / its base-year "
     "rate)."),
    ("Balance factor",
     "The pull of a growing or shrinking book on its rate.",
     "The base year's mean balance / this year's: below 1 the book has grown since the base year."),
    # Delinquency and nonaccrual (docs/V1-ROUND2-SPEC.md, section A; peers/delinquency.py).
    ("Delinquency rate",
     "The share of a book that is behind on its payments, or no longer accruing interest, on the day the "
     "quarter ends.",
     "100 x the measure's past-due or nonaccrual amount / the balance, both from the same quarter-end filing "
     "($ thousands as filed). Nothing is differenced between quarters: these amounts are what was owed on "
     "that day."),
    ("Measure",
     "Which loans count as delinquent. All five are built; which one the bank reports is its choice, made "
     "with the Measure picker on the Delinquency tab.",
     "30-89, 90+ accruing, nonaccrual, 90+ incl. nonaccrual or 30+ incl. nonaccrual, each defined below."),
    ("30-89",
     "Loans 30 to 89 days past due and still accruing interest.",
     "The Call Report's 30-89 days past due field for the product (P3CRCD, P3RERSFM, P3RELOC, P3CONOTH, "
     "P3AUTO)."),
    ("90+ accruing",
     "Loans 90 days or more past due that the bank still accrues interest on.",
     "The 90 days and over past due field for the product (P9CRCD, P9RERSFM, P9RELOC, P9CONOTH, P9AUTO)."),
    ("Nonaccrual",
     "Loans the bank has stopped accruing interest on, because full payment is not expected.",
     "The nonaccrual field for the product (NACRCD, NARERSFM, NARELOC, NACONOTH, NAAUTO)."),
    ("90+ incl. nonaccrual",
     "Loans 90 days or more past due, whether or not the bank still accrues on them.",
     "90+ accruing + nonaccrual, from the same filing."),
    ("30+ incl. nonaccrual",
     "Every loan 30 days or more past due, and every nonaccrual loan.",
     "30-89 + 90+ accruing + nonaccrual, from the same filing."),
    ("Basis",
     "Whether a delinquency rate is one quarter-end's or smoothed over a year. Picked on the Delinquency tab.",
     "Quarter-end or four-quarter average, each defined below."),
    ("Quarter-end rate",
     "A bank's delinquency rate on one filing.",
     "100 x numerator / balance from that quarter-end's filing. Blank when the bank did not file that quarter, "
     "the balance is 0 or below or under the minimum book (unless the bank is exempt), or a field the measure "
     "needs was not filed. An acquisition does not blank it: the ratio is from one filing, so the jump rule "
     "does not apply."),
    ("Four-quarter average",
     "A delinquency rate smoothed over the last year.",
     "The mean of the four quarter-end rates of this quarter and the three before, only when all four exist "
     "on consecutive quarter-ends. For a bank it is also blank when the book moved by more than the jump in "
     "any of the last three quarters against the one before: four filings across an acquisition describe "
     "different books. For the composite and the industry it is the mean of their four quarter-end rates."),
    ("Not filed",
     "A Call Report field with no value for that quarter. The 30-89 day fields are blank before 2001 for "
     "cards, home equity and other consumer and before 2002 for mortgages, and every auto field before 2011 "
     "(the FDIC API, probed 12 Oct 2026).",
     "A blank field, never read as 0. A rate that needs it is blank, and the DelinquencyData tab names the "
     "field."),
    ("Delinquency composite",
     "The pack's delinquency rate as if its banks were one bank, so a large book weighs more than a small one.",
     "Quarter-end: 100 x the summed numerators of the included peers kept that quarter-end / their summed "
     "balances. A bank not kept, or missing, is in neither sum, never counted as 0. Four-quarter average: the "
     "mean of the four composite quarter-end rates. Blank when fewer banks than the Pack tab asks for are kept."),
    ("Delinquency band",
     "How spread out the pack's delinquency rates were, each bank counting once whatever its size.",
     "The 10th, 25th, 75th and 90th percentiles (PERCENTILE, interpolating as PERCENTILE.INC) of the included "
     "peers' rates on the basis picked, leaving out a bank with no rate. Not drawn when fewer banks than the "
     "Pack tab asks for have one."),
    ("Banks in the quarter-end composite",
     "How many of the pack's banks are in the delinquency composite at a quarter-end.",
     "The count of included peers kept that quarter-end. On the four-quarter average the composite is the mean "
     "of four quarter-end composites, each with its own count, so this is that quarter-end's count, not the "
     "band's."),
    ("Banks in the band",
     "How many of the pack's banks the delinquency band is drawn from.",
     "The count of included peers with a rate on the basis picked. On the four-quarter average a bank needs "
     "four consecutive quarter-ends kept and no jump, so this can be fewer than the composite's count; the "
     "band is blank while it is under what the Pack tab asks for."),
]
