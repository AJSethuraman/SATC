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
     "The peers in the pack under In the pack on the Peers tab: each bank's cell reads Pack (follow Banks in "
     "the pack), Yes or No. It changes as those cells and Banks in the pack are changed."),
    ("Banks in the pack",
     "Who is in the pack for every bank whose cell reads Pack: every peer, the regionals only, the large banks "
     "only, or none.",
     "Regionals are the peers the roster marks regional; the large banks are the others (JPMorgan, Wells "
     "Fargo, Bank of America, Citi and Capital One). A bank set to Yes or No ignores it."),
    ("In the pack",
     "Whether a peer is in the pack: under its name at the top of the Peers tab, Pack (follow Banks in the "
     "pack), Yes or No. A bank out of the pack shows gray, its name struck through.",
     "Every view with a pack in it recalculates when one changes: the charge-off and delinquency composites "
     "and bands, the rank tables, the charge-off rate over the pack composite, the book index pack median, the "
     "lagged pack total, the normalization pack composite, best and worst in pack, the headline numbers, and "
     "the Peer group series on Decide, Thresholds and Summary (summed from Peers data and Peers delinquency "
     "data over the banks in the pack now; the Evidence and Backtest tabs stay as built)."),
    ("Chart shows",
     "How much history the charts draw: every quarter, or the last 48 or 20.",
     "Only the picture. Each chart starts at the first quarter any of its lines has, within that many quarters "
     "back from its last, and its axis fits what is drawn. No figure depends on it."),
    ("Headline numbers",
     "The strip of four numbers over each chart: KeyBank, the pack composite and the industry (on "
     "delinquency, the banks with a rate) in the latest quarter, and KeyBank's rank.",
     "The latest quarter's values of the lines drawn. KeyBank's rank counts the banks switched on with a rate "
     "that quarter, plus KeyBank, from the lowest rate (1); a tie shares the better rank."),
    ("Regional",
     "A peer in the regionals-only pack.",
     "Read from the roster (config/peers.json): every peer except the largest national banks and the card "
     "specialist."),
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
    ("Quarter-end balance",
     "The book as filed on the last day of the quarter.",
     "RC-C, in $ thousands as filed; blank when the bank did not file that quarter. The average balance "
     "is the mean of four of these. With pro forma, the sum over the bank and the banks it absorbed."),
    ("Pro forma",
     "Each bank's figures with those of every bank it absorbed, before each absorption, so an acquisition "
     "neither breaks its history nor leaves its rate out. A build setting, shown on the Run tab.",
     "Before the quarter a bank was absorbed, its charge-offs, recoveries and balances, each from its own "
     "filings, are added to the absorber's, through every bank in the chain. A bank absorbed without a "
     "filing in these quarters cannot be added: the Run tab names it, and its acquisition is treated as "
     "without pro forma. Two limits: in the quarter of the deal the absorbed bank files nothing, so its "
     "charge-offs count only from the close, in the absorber's filing; and the absorber books the loans it "
     "buys at fair value, so their charge-offs in the first quarters after a deal are not exactly what the "
     "absorbed bank would have reported. Charge-offs only: delinquency is each bank as filed."),
    ("Combined with",
     "On the Data tab, the banks whose figures are added into that row (pro forma).",
     "Each absorbed bank that filed in one of the row's four quarters, by certificate, with the quarter it "
     "was absorbed. Blank when the row is the bank's own filings alone."),
    ("Structural move",
     "A change in a book's size larger than lending accounts for: a merger, a purchase, a sale or a "
     "reclassification. Rates whose window includes it are not used. With pro forma, an absorption "
     "added in is not one: the combined book does not move.",
     "A quarter whose balance moved by more than the jump from the quarter before (|this / last - 1| > jump), "
     "or rose from zero. A rate is not kept if any quarter from the one before its window to its last quarter "
     "moved structurally."),
    ("Jump",
     "The largest quarter-on-quarter move in a book that still counts as lending rather than a structural "
     "move.",
     "A build setting, shown on the Run tab. 0.25 means a 25% move in one quarter."),
    ("Minimum book",
     "The smallest book whose rate is used.",
     "A build setting, in $ thousands, shown on the Run tab. A rate is not kept when the average balance is "
     "below it. KeyBank can be exempt, so its own line is never blank for size."),
    ("Kept",
     "Whether a bank's rate for a quarter is used.",
     "TRUE when the average balance is at least the minimum book and above zero, all four quarters' flows "
     "were filed, no quarter-on-quarter move from the quarter before the four through the last was larger "
     "than the jump, no recorded acquisition brought in at least the acquisition share (with pro forma, "
     "only an absorption that could not be added counts), and no stated acquisition is in the window. Why "
     "says the first reason it is not, in that order: a quarter missing from the data, the jump, an "
     "acquisition, a stated acquisition, the minimum, a flow not filed."),
    # What is left out, and why: one row per reason, as the bank asked
    # (12 Oct 2026): "it should list what we are omitting and why".
    ("Left out, and why",
     "The rows below starting \"Left out:\" are every reason a bank's number is kept out of a line, a "
     "composite or a band. Nothing left out is ever counted as 0.",
     "Each row says why the number is left out, the rule, and where each one is recorded, so every omission "
     "can be found by bank and quarter."),
    ("Left out: an acquisition (the jump)",
     "A quarter in which a bank bought, merged with or sold a book, and the quarters whose figures span it.",
     "A quarter whose balance moved by more than the jump from the one before, or rose from zero. "
     "Charge-offs: the rate is not kept if this happened in its window or the quarter before (the Data tab, "
     "Why not kept). Delinquency: the bank's four-quarter average is blank if it happened in the last three "
     "quarters (DelinquencyData, Why no four-quarter average); a quarter-end rate is one filing and is never "
     "left out for this. That bank is also left out of the pack composite's four-quarter average for that "
     "quarter, so the composite and the band are built from the same banks (the bank's decision, 12 Oct "
     "2026): DelinquencyData's last column marks it, and the composite's series file names each bank and "
     "quarter."),
    ("Left out: a small book (the minimum book)",
     "A book below the minimum book.",
     "Charge-offs: the average balance is under the minimum book. Delinquency: the quarter-end balance is "
     "under it. KeyBank can be exempt, so its own line is never blank for size. Recorded in Why not kept "
     "(the Data tab, DelinquencyData)."),
    ("Left out: not filed",
     "There is no number to use, and a blank is never read as 0.",
     "The bank did not file that quarter; a field the measure needs was not filed; or the balance is 0 or "
     "below (no book). Recorded in Why not kept (the Data tab, DelinquencyData), naming the field."),
    ("Left out: fewer than four quarters",
     "A trailing-four-quarter rate or a four-quarter average needs a whole year.",
     "Four consecutive quarter-ends in the data, each with a rate. Recorded in Why not kept (charge-offs) and "
     "Why no four-quarter average (delinquency)."),
    ("Left out: not included",
     "A peer someone has taken out of the pack.",
     "Switched off (No) on the Peers tab: left out of every pack figure (composites, bands, the rank tables, "
     "the book index pack median, the lagged pack total) and of best and worst in pack. It "
     "can still be drawn as Peer A or Peer B."),
    ("Left out: too few banks",
     "A quarter in which fewer banks are kept than a composite or band needs.",
     "A quarter with fewer kept banks than the Peers tab asks for is blank, never drawn from fewer. The headline "
     "over each chart counts the banks in at the latest quarter; Workings counts them every quarter."),
    ("Left out: a stated acquisition",
     "A quarter in which a bank took in a book the FDIC record cannot see, listed with its filing.",
     "From the stated acquisitions file the build is given (config/stated-acquisitions.json; the firm, 17 Oct "
     "2026): a failure with no FDIC row naming the buyer, a deal the FDIC codes as a branch purchase, or an "
     "asset purchase from a company that is not a bank. Every product's windows holding the quarter are left "
     "out for that bank, as for a recorded acquisition, with no share measured. Recorded in Why not kept (the "
     "Data tab, DelinquencyData) and on Run."),
    ("Left out: before a gap (series files)",
     "The thresholds workbook needs an unbroken run of quarters and never fills a gap.",
     "A series file is written from the first quarter after its last gap; its note names the quarters left "
     "out before and after. One gap does not break it: windows the jump left out only for a move in a quarter "
     "a reporting change names for the product and measure (an event never does). The file runs across them, declares "
     "them on its Continues across line and never fills them (the firm, 17 Oct 2026)."),
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
     "Each included peer's mean kept rate over the last quarters stated on the Peers tab, among peers with at "
     "least the stated number of kept quarters in that window. Lowest is best, highest is worst; a tie goes to "
     "the peer listed first."),
    ("Peer A, Peer B",
     "Two lines drawn beside KeyBank, each one named peer or whoever best or worst in pack resolves to.",
     "Picked on the Peers tab. Drawn whether or not that peer is included in the pack, kept quarters only."),
    ("Lagged rate",
     "A year's net charge-offs as a share of the book some years earlier.",
     "100 x the year's net charge-offs (the Q4 year-to-date charge-offs less recoveries, as filed) / the mean "
     "of the four quarter-end balances of the earlier year. A pack total sums the dollars before dividing."),
    ("Normalization",
     "How far a rate has moved between two years.",
     "Each year's figure is the mean of its four quarterly TTM net rates (blank unless all four were kept); "
     "the ratio is the later year's / the earlier year's, blank when the earlier year is 0 or below (net "
     "recoveries), because a ratio to it would read the wrong way."),
    ("Organic index",
     "A book's size against a base quarter, with purchased books taken out, so growth means lending.",
     "Base quarter = 100. Each quarter's growth from the one before is chained, except in an acquisition "
     "quarter, where the growth is set to 1. As reported is the plain balance / the base balance x 100."),
    ("Book index pack median",
     "How the pack's books grew, each bank counting once whatever its size.",
     "The median of the book indexes of the banks switched on and indexed, at the latest quarter: without "
     "acquisitions, and as reported. Blank when fewer banks than the Peers tab asks for are indexed. A bank "
     "is indexed when its book at the base is at least the smallest book indexed (a build setting, on the Run "
     "tab); otherwise the book index table says too small, or no book when it had none."),
    ("Rank tables",
     "Each bank switched on with a rate in the latest quarter, and KeyBank, in order of that rate, under "
     "Where each bank stands.",
     "Rank 1 is the lowest rate; a peer level with KeyBank ranks after it. vs composite is the bank's rate "
     "minus the pack composite, in percentage points. 4-quarter change is the bank's rate minus its own rate "
     "four quarters earlier, in percentage points, blank when either is missing. Balance ($bn) is the average "
     "balance on charge-offs and the quarter-end balance on delinquency. In pack marks Peer A and Peer B."),
    ("Peer loan classes",
     "What each peer's consumer book holds, from the holding company's own quarterly filing with the SEC: "
     "its loan classes, and whether it holds student loans, unsecured or personal loans and lines, and loans "
     "secured by anything other than a home or a car.",
     "Amounts are the filing's own at amortized cost, read from its XBRL by the members named, or as printed "
     "where the filing does not tag a class. The Call Report's other consumer line (RC-C 6.b + 6.d) mixes "
     "these classes."),
    ("Counted as",
     "What a class is counted as on Peer loan classes: student, unsecured or personal, secured non-auto, mixed "
     "other consumer, or other.",
     "A judgment stated per class in config/peer-loan-classes.json, with the filing's words quoted. "
     "Unsecured or personal holds classes the filing calls unsecured or personal loans, and solar energy "
     "installation loans, which the bank's analyst ruled count as unsecured (15 Oct 2026: the panels are "
     "little to recover). A filing that says personal without saying unsecured is said so."),
    ("For an unsecured comparison",
     "Whether a bank's other consumer rate on the Call Report can stand for its unsecured lending.",
     "Clean: the filing shows the unsecured or personal slice on its own and no student loans. Mixed: other "
     "consumer holds unsecured lending beside student, secured or undefined classes. Not comparable: secured, "
     "securities-based or fair-value lending dominates, or the book is too small. A judgment, with why."),
    ("How the amount was read",
     "Whether a class's amount came from the filing's XBRL (tagged with the members named) or as printed on "
     "the page named, because the filing does not tag that class.",
     "Either way the tie-out checks it against the filing (docs/tie-out/peer-loan-classes-2026q2)."),
    ("Book size",
     "The average balance of each bank's book in the product picked, in $ billions: KeyBank, Peer A and "
     "Peer B as lines, the pack as its median and shaded bands, and every bank ranked by size beside it.",
     "The mean of the four quarter-end balances, as on the Data tab, / 1,000,000; a quarter the bank did not "
     "file is a gap. The pack median and bands are the 10th, 25th, 50th, 75th and 90th percentiles of the "
     "banks switched on with a balance above zero, in quarters with at least the banks needed. The scale is "
     "logarithmic, so a balance of zero is not drawn."),
    ("Size rank",
     "Where a bank's book stands among the banks switched on with a balance, and KeyBank, in the latest "
     "quarter. 1 is the largest.",
     "Ordered by average balance, largest first; a peer level with KeyBank ranks after it. Share is the "
     "bank's balance / the total of the balances listed. 4-quarter change is the bank's balance / its own "
     "balance four quarters earlier, minus 1; on the strip, the pack median's is the pack median / the pack "
     "median four quarters earlier, minus 1. Charge-off rate is the bank's rate on the rate picked, blank "
     "when not kept."),
    ("Charge-off rate ÷ pack composite",
     "KeyBank's, Peer A's and Peer B's charge-off rate as a multiple of the pack composite; 1 is the composite.",
     "The bank's rate / the pack composite in the same quarter, on the rate picked. Blank when either is "
     "missing or the composite is 0."),
    ("Consumer book by product",
     "The share of KeyBank's consumer book in each product built, the product picked drawn first in red.",
     "Each product's average balance / the sum over the products built, each quarter; a product not filed "
     "counts as no balance."),
    ("Pack total (lagged)",
     "The pack's lagged rate as if its banks were one bank.",
     "100 x the summed net charge-offs of the banks switched on / their summed balances in the earlier year. "
     "Blank if any bank switched on lacks either year, rather than worked out over the banks that remain."),
    ("Acquisition quarter",
     "A quarter in which the bank took over another institution or a book of loans.",
     "The bank's mergers in the FDIC structure-change record (an allowlist of change codes: mergers, "
     "absorptions and consolidations, and failed banks taken over whole or split between several buyers, "
     "code 215; counted at the quarter-end on or after the effective date), plus any purchase declared at the build, such as one of a "
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
     "The base year's book as a multiple of this year's.",
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
     "with the Delinquency measure picker on the Peers tab.",
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
     "Whether a delinquency rate is one quarter-end's or smoothed over a year. Picked on the Peers tab.",
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
     "different books. For the composite it is the mean of four composite quarter-end rates, each without "
     "the banks whose own four-quarter average that rule blanked; for the industry, the mean of its four "
     "quarter-end rates."),
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
     "mean of the four composite quarter-end rates, each recomputed without the peers whose own four-quarter "
     "average the jump blanked at this quarter-end (see Left out, and why). Blank when fewer banks than the "
     "Peers tab asks for are kept in any of the four."),
    ("Delinquency band",
     "How spread out the pack's delinquency rates were, each bank counting once whatever its size.",
     "The 10th, 25th, 75th and 90th percentiles (PERCENTILE, interpolating as PERCENTILE.INC) of the included "
     "peers' rates on the basis picked, leaving out a bank with no rate. Not drawn when fewer banks than the "
     "Peers tab asks for have one."),
    ("Banks in the quarter-end composite",
     "How many of the pack's banks are in the delinquency composite at a quarter-end.",
     "The count of included peers kept that quarter-end. On the four-quarter average the composite is the mean "
     "of four quarter-end composites, each with its own count and without the banks the jump took out, so "
     "this is that quarter-end's count before any are taken out, not the band's."),
    ("Banks in the band",
     "How many of the pack's banks the delinquency band is drawn from.",
     "The count of included peers with a rate on the basis picked. On the four-quarter average a bank needs "
     "four consecutive quarter-ends kept and no jump, so this can be fewer than the composite's count; the "
     "band is blank while it is under what the Peers tab asks for."),
    ("Reporting change (on the charts)",
     "A change to the Call Report's definitions or forms, such as the move of margin loans out of other consumer "
     "from December 2024. A diamond on the pack composite marks each quarter one took effect for the product and "
     "measure shown.",
     "From the registry of reporting changes the build is given (config/reporting-changes.json): a quarter is "
     "marked when a change touching the product, on the charge-off rate or delinquency measure picked, took "
     "effect in it; a change reported over several quarters marks each of them. No diamond where the composite "
     "has no rate. Every series file the build writes names the changes touching it in its notes, with the "
     "source."),
]

#: The share panel's term, which names the book's kind as the panel does.
SHARE_TERM = "Consumer book by product"


def terms_for(book_kind=None, share_note=None):
    """``PEER_TERMS`` for a workbook whose book states ``book_kind``
    (``kinds.KINDS``). The share panel names the bank's book by that kind
    ("KeyBank's commercial book: share by product"), so its term does too: a
    commercial book's is "Commercial book by product", about KeyBank's
    commercial book. None, the standalone peers build, and a consumer book
    keep the list as it is.

    ``share_note`` is the share panel's caption when the products built
    overlap (``peers_workbook.mix_caption``), added to how the term is
    calculated; None (no product overlaps another) adds nothing."""
    out = []
    for term, meaning, calc in PEER_TERMS:
        if term == SHARE_TERM:
            if book_kind not in (None, "consumer"):
                term = "%s book by product" % book_kind.capitalize()
                meaning = meaning.replace("KeyBank's consumer book", "KeyBank's %s book" % book_kind)
            if share_note:
                calc = "%s %s" % (calc, share_note)
        out.append((term, meaning, calc))
    return out
