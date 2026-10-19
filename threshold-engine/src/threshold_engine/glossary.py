"""Every term the workbook uses: what it means, and exactly how it is calculated.

Written for the person reading the workbook, not the person who built it.
Each calculation is the one the code performs, so a reviewer can redo it by
hand. The workbook's tests check that every column heading on Thresholds and
on Assess's inputs has an entry here, so a new heading cannot ship without its
definition.
"""

# (term, what it means, how it is calculated)
#: Said of a combined product under every kind (the merge of 18 Oct 2026,
#: a rule the firm can overrule): it follows its parts' reporting changes
#: and events.
COMBINED_CHANGES = ("A reporting change or event named for any of its parts is labeled on it, and a change named "
                    "for any part can keep it going (see Continues across).")
#: The Combined product term in a commercial book (``terms_for``): no All
#: consumer, which is the consumer five, and no auto; the one combination
#: refused is a whole with a part it holds (books.INSIDE). Reworded with the
#: rest of the workbook (kinds.reword).
COMBINED_COMMERCIAL = (
    "A product made of others: two or more joined by ' + '. Nonfarm nonresidential may not be joined with "
    "Owner-occupied nonfarm nonresidential or Other nonfarm nonresidential, which it holds.",
    "Each bank's balances, charge-offs, recoveries and past-due amounts for the parts are added together before "
    "the rate is taken, so the rate is dollar-weighted, and the jump, acquisition and minimum book rules are "
    "applied to the combined book. A blank field is not filed, never 0, so a part not filed leaves the combined "
    "book not filed in that quarter. " + COMBINED_CHANGES)

TERMS = [
    ("Product",
     "The first of the three parts that name a series, such as Credit card.",
     "Taken from the book's series list. A series' label is its product, measure and source joined by ' - '."),
    ("Combined product",
     "A product made of others: All consumer (credit card, mortgage, home equity, other consumer and auto), "
     "or two or more joined by ' + ', such as Credit card + Other consumer.",
     "Each bank's balances, charge-offs, recoveries and past-due amounts for the parts are added together "
     "before the rate is taken, so the rate is dollar-weighted, and the jump, acquisition and minimum book "
     "rules are applied to the combined book. Its delinquency is written only for quarters in which every "
     "part's fields were filed (auto's begin in 2011Q1). " + COMBINED_CHANGES),
    ("30+ to charge-off",
     "Of the dollars 30 to 89 days past due, 90 or more days past due and still accruing, and on nonaccrual at a "
     "quarter-end, the percent charged off (gross, before recoveries) over the next two quarters. One minus it is "
     "the estimated cure.",
     "From each bank's own Call Report filings: the three RC-N fields of the product at the quarter-end, and the "
     "product's gross charge-offs (RI-B, year to date differenced) in the two quarters after, 100 x the second over "
     "the first. A card charges off at 180 days past due and a closed-end consumer loan at 120, so every delinquent "
     "dollar has charged off or left delinquency within two quarters. An aggregate estimate, not a tracked cohort: "
     "loans charged off within the two quarters that were current at the quarter-end count too. The series in the "
     "book is the four-quarter average of the quarter-end shares. The pack composite is the kept banks' dollars "
     "charged off summed over their delinquent dollars summed, and does not follow Banks in the pack. The latest "
     "two quarter-ends have no value yet."),
    ("Gap to peers on 30+ to charge-off, Gap to industry on 30+ to charge-off",
     "The bank's four-quarter average 30+ to charge-off less the peer group's, or less the industry's, in the same "
     "quarter, in percentage points. Above zero the bank turns more of its delinquent dollars into loss than they "
     "do; below zero, less.",
     "KeyBank's four-quarter average less the pack composite's (or the industry's) for the same quarter, where "
     "both exist. A measure with no floor at zero (the book's floor_off): a negative gap is rated on its lines, "
     "never as 1 Low by the floor. Its lines are set from its own history."),
    ("Share paying only the minimum",
     "Of the active consumer credit card accounts at the large banks, the percent whose payment in the quarter "
     "was the minimum due.",
     "The Philadelphia Fed's 'Share of Accounts Making the Minimum Payment' from its Large Bank Credit Card and "
     "Mortgage Data, quarterly from 2012Q3: the bank holding companies that file FR Y-14M (those with $100 "
     "billion or more in assets). A count of accounts, not dollars, across the panel: an industry reading with no "
     "KeyBank figure. The source is the file 'peers large-banks-pull' fetched, named with its SHA-256 in the "
     "series' notes and on Run."),
    ("Signals",
     "A tab laying every public signal found in the October 2026 early-warning work beside the book's own series, compared "
     "against whichever product, measure and source is picked, with the banks behind each chart recorded beside it.",
     "The picked series is looked up on Data by its label. Each signal's change over a year is set against that series' at "
     "every lead from four quarters after to twelve ahead (CORREL); the fit table shows the lead that fits best and how well, "
     "with and without 2020-23. The rescaled chart draws each line as (value - its normal) / its typical yearly move, the "
     "normal being the median of the quarters in the window and the move 1.4826 x the median absolute deviation of its "
     "yearly changes (scale.py's rule), so one grid line is one yearly move for either line; the inputs are printed under it. "
     "Nothing on the tab is rated; the public series are on Signals data with their sources, and the formulas on Signals workings."),
    ("Where the dollars are",
     "For the source picked, each consumer product's balance, gross charge-offs over four quarters and 30+ incl. nonaccrual "
     "dollars, and each product's share of the total.",
     "KeyBank's and the industry's are summed from the Call Report at build; the peer group's are summed from Peers data and "
     "Peers delinquency data over the banks in the pack, so they follow Banks in the pack on Peers."),
    ("Peer group in this chart",
     "Beside every chart on Signals that draws on the pack: each peer and its state this quarter: in; out by the book's "
     "rules; off because unticked under Banks in the pack on Peers.",
     "Out means the bank's own four-quarter average was blanked this quarter by the jump or the acquisition share, as Peers "
     "delinquency data records it. A chart drawn from a survey, the Philadelphia Fed's panel or the FHFA database says whose "
     "data it is instead: those are not the peer group."),
    ("Floor at zero",
     "Whether a value at or below zero is always 1 Low for a series. True of a rate; false of a gap between two "
     "rates.",
     "The workbook's floor_at_zero, switched off for each measure the book names under floor_off. Held per "
     "series on Lines by source (a hidden column) and read by every rating formula, so Decide, Thresholds and "
     "Lines by source rate the same way; the lines of a series without a floor are set without it too."),
    ("Measure",
     "The second of the three parts that name a series: the rate measured, such as Net charge-offs.",
     "Taken from the book's series list, as for Product."),
    ("Source",
     "The third of the three parts that name a series: the filer or group whose figures it holds.",
     "Taken from the book's series list, as for Product."),
    ("Quarter",
     "The period each value belongs to, written like 2010Q2.",
     "Read from the source's date: a date in April, May or June is Q2, whether the source dates the quarter "
     "by its first day (Federal Reserve) or its last (FDIC)."),
    ("Trailing twelve months (TTM)",
     "A rate measured over the last four quarters, not one quarter. It smooths out one-off quarters.",
     "For FDIC data: the four quarters' charge-offs less recoveries, divided by the average of the four "
     "quarter-end balances. For Federal Reserve data: the average of the four quarterly rates. The engine can "
     "also do this itself from quarterly values (smoothing 4: the mean of each quarter and the three before it)."),
    ("Quarters kept",
     "The quarters the thresholds are built from: every quarter, except any periods left out on Assess.",
     "A quarter is left out if a whole row of Periods left out on Assess names its series and the quarter "
     "falls between that row's From and To, inclusive."),
    ("Left out",
     "A period set aside because it does not represent the risk being rated, with the reason recorded.",
     "Picked on Assess: the series, the first and last quarter from lists of the quarters in the data, and a "
     "reason. As many periods as there are rows, for any series. A row with something missing says what in its "
     "Status and refuses its series until it is complete or cleared. Shown on the chart as a dark "
     "strip and gray dots on the line, and recorded on Run."),
    ("Left out as built",
     "Quarters a series' file does not hold, written to left-out.csv beside the series files with why: those "
     "before its last break, those it continues across, and its latest quarters when they have no value.",
     "A series is written from the first quarter after its last break, because the workbook refuses a gap it "
     "is not told of; the quarters it continues across (see Continues across) are the one gap it is told of. "
     "Each row names the series by Product, Measure and Source, the first and last quarter left out, and why: "
     "the reason the quarter at the break has no value, or that the series continues across them. The periods "
     "left out on Decide are not in it. Its SHA-256 is on Run."),
    ("Median kept",
     "The middle of the quarters kept: half were higher, half lower. The center of Moderate.",
     "MEDIAN of the quarters kept."),
    ("Typical yearly move",
     "How much the rate ordinarily changes in a year. It is the unit the Moderate band and the Moderate-Low "
     "line are measured in.",
     "Take every change over four quarters whose start and end are both kept. Take the median of those "
     "changes, then the median of each change's distance from it (the median absolute deviation, MAD), and "
     "multiply by 1.4826. That factor makes it comparable to a standard deviation, but one extreme year "
     "cannot inflate it."),
    ("Worst kept",
     "The worst quarter kept: the highest loss rate (or the lowest score, for a measure where lower is worse).",
     "MAX of the quarters kept (MIN when lower is worse)."),
    ("Moderate",
     "Normal risk. A band around the median wide enough that anything inside it is within the measure's "
     "ordinary year-to-year movement of normal.",
     "From the median minus the half-width times the typical yearly move, up to the median plus the same."),
    ("Width of Moderate (yearly moves)",
     "How wide Moderate is on each side of the median, counted in typical yearly moves (its half-width).",
     "Typed on Decide (in Your settings on Assess in a workbook without Decide). 0.5 makes Moderate one "
     "typical yearly move wide in total."),
    ("Moderate-Low",
     "Better than normal by more than ordinary movement, but not by enough to be Low.",
     "From the Moderate-Low line up to where Moderate begins."),
    ("Moderate-Low begins (yearly moves)",
     "How far below the median Low ends, counted in typical yearly moves.",
     "Median minus this number times the typical yearly move. Typed on Decide (in Your settings on Assess in "
     "a workbook without Decide). It must be larger than the width of Moderate."),
    ("Low",
     "Clearly better than normal.",
     "Below the Moderate-Low line. A loss rate at or below zero is always Low."),
    ("Moderate-High",
     "Worse than normal by more than ordinary movement, but short of stress.",
     "From the top of Moderate (median plus half-width times the typical yearly move) up to where High begins."),
    ("High",
     "Stress: a level far enough from normal, on the worse side, to count as unusual for this series.",
     "From the median plus the High z times the spread of levels. It is the same robust z the evidence uses to "
     "call a level unusual, so High and stress mean one thing."),
    ("What fits the history the lines are set from",
     "On Decide, beside each setting: the range in which it fits the history of the source picked under Lines "
     "set from, and whether the setting typed does. Nothing is changed for you.",
     "Width of Moderate fits below Moderate-Low begins. Moderate-Low begins fits above the width and, for a "
     "rate floored at zero, below the median kept / the typical yearly move, so line 2 stays above zero. How "
     "rare High is (z) fits above the width x the typical yearly move / the spread of levels (High beyond "
     "Moderate-High) and up to (the worst kept - the median kept) / the spread of levels (some quarter kept "
     "can rate High). These are the Check's own rules."),
    ("How rare High is (z)",
     "How many spreads of levels above the median High starts. The same number means the same rarity on "
     "every series.",
     "Typed on Decide (in Your settings on Assess in a workbook without Decide). 3.5 is the usual line for an "
     "outlier (Iglewicz and Hoaglin, 1993). With a crisis left "
     "out it can sit beyond everything kept, which the workbook refuses. The Dial on Assess shows 2.0 to 3.5 "
     "side by side."),
    ("Spread of levels",
     "How widely the quarters kept range around their median, measured so that one extreme stretch cannot "
     "inflate it. The unit High is measured in.",
     "1.4826 x the median of each kept quarter's distance from the median kept (the median absolute "
     "deviation, MAD)."),
    ("Dial",
     "A table on Assess showing what one setting would do at other values, before you change it.",
     "For each value: the four lines with that setting changed and the others as in Your settings, and how "
     "many "
     "quarters kept fall in each rating. The shaded row is your current setting."),
    ("2 Moderate-Low from, 3 Moderate from, 4 Moderate-High from, 5 High from",
     "The four lines the scoring file uses. Each is where that rating begins.",
     "As defined under Moderate-Low, Moderate, Moderate-High and High above."),
    ("2 Moderate-Low",
     "On Thresholds, the value at which a rating of 2 Moderate-Low begins.",
     "Median kept minus Moderate-Low begins (yearly moves) times the typical yearly move. When lower is worse, "
     "the sign reverses."),
    ("3 Moderate",
     "On Thresholds, the value at which a rating of 3 Moderate begins.",
     "Median kept minus the width of Moderate (yearly moves) times the typical yearly move. When lower is worse, "
     "the sign reverses."),
    ("4 Moderate-High",
     "On Thresholds, the value at which a rating of 4 Moderate-High begins.",
     "Median kept plus the width of Moderate (yearly moves) times the typical yearly move. When lower is worse, "
     "the sign reverses."),
    ("5 High",
     "On Thresholds, the value at which a rating of 5 High begins.",
     "Median kept plus How rare High is (z) times the spread of levels. When lower is worse, the sign reverses."),
    ("On a line, rate it",
     "Which rating a value exactly on a line gets.",
     "Picked on Decide (in Your settings on Assess in a workbook without Decide). 'worse' gives the worse of "
     "the two ratings, 'better' the better."),
    ("Status",
     "Whether a row of Periods left out is in use, and if it is not whole, what is missing.",
     "'Left out: N quarters' when the row names a series, two quarters in order and a reason. Otherwise it "
     "says what to do: 'Pick a series', 'Missing: ...' (From, To, reason), or 'From is after To', and names the "
     "series it refuses."),
    ("Rating",
     "1 to 5: Low, Moderate-Low, Moderate, Moderate-High, High. Called a rating so it is not confused with a "
     "measure that is itself a score.",
     "1 plus the number of lines the value is at or past (past only, if a value on a line gets the better "
     "rating)."),
    ("Rating name",
     "The rating's name.",
     "1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High."),
    ("Latest",
     "The most recent quarter in the source file and its value.",
     "Read from the source, not recalculated."),
    ("Check",
     "Says why the workbook will not draw a scale, rather than drawing one that cannot be right.",
     "Refuses when too little history is kept for a typical yearly move, when the median is at or below zero, when Moderate-Low would not begin below Moderate, when High "
     "would not begin beyond Moderate-High, when High would begin beyond the worst quarter kept (nothing could "
     "rate High), or when Moderate-Low would begin at or below zero."),
    ("Value",
     "On Thresholds, the series' value in its latest quarter.",
     "Read from the source file, after any smoothing set for the workbook. It is not recalculated."),
    ("Decision",
     "The decision recorded on Decide for a product and measure's lines: Not decided, Accept these lines or "
     "Reject.",
     "Selected in the Decision column of the table on Decide. Thresholds reads it from there; on Lines by "
     "source it shows on the source the lines are set from."),
    ("Lines set from",
     "The source whose history sets a product and measure's one set of lines. Every source's latest quarter "
     "is rated on those lines.",
     "Picked from a list on Decide, one per product and measure. A row with none picked has no lines and no "
     "ratings, and its Check says so. The lines are that source's own lines on Lines by source, computed with "
     "the row's settings and its period left out."),
    ("Lines by source",
     "The tab of each source's own lines: what its history gives with its product and measure's settings on "
     "Decide.",
     "Each series' median kept, typical yearly move, spread of levels and four lines, as defined in this "
     "glossary. Thresholds takes the lines of the source picked under Lines set from. A period left out on "
     "Decide is left out of that source's history only."),
    ("Thresholds",
     "In a workbook with Decide, one set of lines per product and measure: the four lines the scoring file "
     "uses, the source they are set from, and every source's latest quarter rated on them.",
     "Each row reads its source's lines from Lines by source. Each source's rating is calculated as for Rating, "
     "on those lines. A row's lines are blank until a source is picked, and while the Check refuses them."),
    ("Rating on these lines",
     "On Decide, each source's latest quarter rated on the lines picked for the product and measure.",
     "As for Rating, with the four lines of the source picked under Lines set from and the row's On a line, "
     "rate it. Blank when no source is picked or its lines are refused."),
    ("What each source's own history would give",
     "On Decide, the four lines each source's own history gives with the row's settings, and its worst quarter "
     "kept, so a source can be picked knowing what each gives.",
     "Read from Lines by source. Refused when the Check refuses that source's own lines."),
    ("Pick a source",
     "On Thresholds and Summary, a product and measure whose Lines set from is still blank on Decide.",
     "Shown until a source is picked; the row has no lines and no ratings until then."),
    ("Points",
     "On Summary, the gap between the bank's latest value and its peer group's latest value.",
     "The bank's latest value minus the peer group's latest value for the same product and measure, in the "
     "measure's units (percentage points for a rate). Blank when either value is missing."),
    ("Needs your attention",
     "On Summary, the bank's series rated 4 Moderate-High or 5 High, and the count of its series refused.",
     "Series rated 4 or 5 are listed by rating, highest first, then by latest value, highest first. The first "
     "five are named and the rest are counted. Refused counts the bank's series whose Check is not OK."),
    ("Spell",
     "An unbroken stretch of quarters worse than the median.",
     "From the first quarter worse than the median to the last before it returns."),
    ("Robust z",
     "How far a level sits from the rest of history, in units that one extreme period cannot distort.",
     "(value - median) / (1.4826 x MAD), with the median and MAD taken over every quarter outside the spell "
     "being measured. Not a probability: neighboring quarters of a TTM rate are not independent."),
    ("Unusual",
     "A spell whose peak stands well apart from the rest of history.",
     "Robust z of 3.5 or more, the usual line (Iglewicz and Hoaglin, How to Detect and Handle Outliers, 1993). "
     "Counts at 2.5 and 3.0 are also shown."),
    ("Years per spell this bad",
     "How often history reached a spell's peak or worse.",
     "Years of history divided by the number of spells whose peak reached it."),
    ("Deepest dip",
     "The largest fall inside a spell between two higher points, which hints at two cycles rather than one.",
     "The fall, divided by the standard deviation of the quarter-to-quarter change."),
    ("Temporary departure",
     "A stretch that left the series' path and came back, like the pandemic dip in charge-offs.",
     "For each window of 8, 12 or 16 quarters, draw a straight line from its first value to its last and "
     "average how far the series sits from that line in between. Each window is ranked by robust z against "
     "every window of its length. The most extreme is reported, then set aside with one window-length either "
     "side, and the search repeats."),
    ("Worse than trend, better than trend",
     "Whether a departure was worse or better than the straight line between the quarters either side of it.",
     "The sign of the average distance from that line, read in the direction that is worse for this measure."),
    ("Backtest",
     "How well a scale would have predicted what came next, using only history available at the time: the "
     "quarter rated and those before it, never one after.",
     "Every quarter is rated on lines built from that quarter and the quarters before it, then compared with "
     "the value four quarters later."),
    ("Spearman",
     "How consistently a higher rating came before a higher value (1 is perfect, 0 is none, negative is reverse).",
     "The correlation of the ranks of the two lists."),
    ("Half-life",
     "A way of weighting recent quarters more heavily.",
     "A quarter's weight halves for every half-life of age."),
    ("Percentile",
     "The value below which a stated share of history falls.",
     "Excel's PERCENTILE.INC: linear interpolation between ranked values."),
    ("SHA-256",
     "A fingerprint of a source file. Any change to the file, however small, changes it.",
     "Computed over the file's bytes and recorded on the Run tab."),
    ("Synthesis",
     "Where each color starts, from three views side by side: KeyBank's own history, the industry's and the "
     "peers'. You choose which view each line is taken from. Only in a workbook built with synthesis inputs.",
     "On the Synthesis tab, one block per series; the series showing on Assess has its four lines and Check "
     "under What each setting does. Every number follows Your settings on Assess."),
    ("Internal",
     "The lines from KeyBank's own series: the ones on Thresholds.",
     "Your settings and the periods left out on Assess, on the series' own quarters. A history with no stress "
     "in it can place lines 2 to 4 and not line 5 (High would begin beyond the worst quarter kept); it says so."),
    ("Industry",
     "The lines from the industry's series (every FDIC filer), which holds the 2008-10 crisis.",
     "The same scale and settings as Internal, on every quarter of the industry series, then carried to the "
     "internal level as Industry carried by says."),
    ("Industry carried by (yours)",
     "How the industry's lines are moved to KeyBank's level, which can sit above or below the industry's.",
     "'median ratio': each line times the median, over the quarters both series hold, of the internal value "
     "divided by the industry value. 'none': the industry's lines as they are. Picked on the Synthesis tab."),
    ("Peers",
     "The lines from KeyBank's peers: where a stated share of the peers sits.",
     "For each peer, the median of its values over the quarters the internal series holds. The line is the "
     "percentile of those medians you state (Excel's PERCENTILE, linear between ranked values), times the "
     "median, over the quarters both hold, of the internal value divided by KeyBank's filed value. For a "
     "measure where lower is worse, 100 minus the percentile is taken."),
    ("Peers at percentile (yours)",
     "The percentile across the peers' medians each line is drawn at.",
     "Four numbers from 0 to 100, rising from line 2 to line 5, typed on the Synthesis tab."),
    ("Taken from (yours)",
     "Which view a line is taken from: internal, industry or peers.",
     "Picked for each line on the Synthesis tab. A line can only be taken from a view that has it, and the four "
     "chosen lines must still run in order; otherwise the Check refuses and says which."),
    ("Chosen line",
     "Where the rating begins once each line is taken from the view you chose.",
     "The internal, industry or peers value on the same row, as Taken from says."),
    ("Internal data",
     "The bank's own figures, pasted into the InternalData table on the Internal data tab: one row per quarter, "
     "product and segment, with amounts in $ thousands.",
     "Columns are found by their header names (quarter, product, segment, balance, gross_charge_offs, "
     "net_charge_offs, recoveries, dpd_30_plus, dpd_60_plus, dpd_90_plus, and an optional crr_grade), in any "
     "order. A quarter is written YYYYQn or as a date. Of gross charge-offs, net charge-offs and recoveries, two "
     "are required and the third is worked out (gross less recoveries is net). The rules are those of the "
     "internal import (docs/INTERNAL-IMPORT.md)."),
    ("Mapped",
     "The workbook's name for a product or measure in the internal file, set once under Your products are and "
     "Your measures are on the Internal tab.",
     "A product name is matched to a workbook product by its exact name, then by the starting rules (card, "
     "mtg or mortgage, heloc or home eq, auto, oth or other). Net and gross charge-off rates start mapped to "
     "the workbook's charge-off measures, because they are calculated the same way. The past-due measures start "
     "as Internal tab only: whether an internal 30+ includes nonaccrual loans is not stated in the file."),
    ("Composite",
     "A product's figure across all its segments.",
     "The product's All rows where the file has them. Otherwise, every segment's amounts are summed quarter by "
     "quarter before any rate is calculated. A product with any row not used has no composite."),
    ("Segment",
     "The bank's own split of a product, such as unsecured lines of credit within other consumer.",
     "Read from the segment column as written. All is the product total."),
    ("Share of the product",
     "A segment's balance as a share of the product's composite balance at the latest quarter.",
     "Segment balance divided by composite balance."),
    ("Balance by segment ($ millions)",
     "Each segment's quarter-end balance over the last 48 quarters, stacked, with the composite as a line.",
     "The balance column summed by quarter, product and segment, divided by 1,000."),
    ("Rows not used",
     "Rows on Internal data that are left out of every figure, with the reason in Why not used.",
     "Rows with any entry, less the rows used, plus any rows below the table's last row."),
    ("Why not used",
     "The first problem found in a row of Internal data, or blank when the row is used.",
     "Checked in this order: the quarter, the product mapping, the segment, the balance and past-due amounts, "
     "a non-numeric charge-off or grade, fewer than two charge-off amounts, gross less recoveries not equal to "
     "net, an amount other than net charge-offs below zero, past-due amounts that are not cumulative, a "
     "repeated quarter, product and segment, and a missing quarter before the row's."),
    ("Call Report source",
     "The source in this workbook that holds the bank's own Call Report series.",
     "Picked on the Internal tab. Like for like reads its series, and the chart draws it in red."),
    ("Like for like",
     "The internal composite set against the Call Report lines that hold the same loans.",
     "The pairs are those of the internal reconcile command. The balance is the mean of four quarter-end "
     "balances. The net charge-off rate is four quarters' net charge-offs over that mean, times 100. The "
     "Call Report side is read from Peers data where the workbook holds it, and otherwise from the Call Report "
     "source's series. Named exclusions are not taken off."),
    ("What counts as reliable",
     "The three thresholds a source must meet for each verdict.",
     "Quarters both have, ratings that agree, and change correlation, typed on the Internal tab. The values "
     "given are starting values."),
    ("Quarters both have",
     "The quarters in which both the internal series and the outside source have a value.",
     "A count over the Data tab's quarters."),
    ("Level correlation",
     "How closely the two series move together in level.",
     "Pearson's correlation of the internal and source values over the quarters both have."),
    ("Change correlation",
     "How closely the two series' changes over four quarters move together.",
     "Pearson's correlation of each series' change from four quarters earlier, over the quarters in which both "
     "series have the value and the value four quarters earlier."),
    ("Average gap",
     "How far the internal series sits above the source on average, in the measure's units: internal less "
     "source.",
     "The mean of internal less source over the quarters both have."),
    ("Ratings that agree",
     "The share of quarters in which the internal value and the source's value get the same rating.",
     "Both values are rated on the source's own four lines from Thresholds, with the On a line rule set on "
     "Decide; a value at or below zero is rated 1 where Decide rates it so. Matches divided by quarters both "
     "have."),
    ("Within one rating",
     "The share of quarters in which the two ratings differ by one or less.",
     "As Ratings that agree, counting quarters where the two ratings are at most one apart."),
    ("Verdict",
     "Whether a source's lines can be used to set lines for the internal series.",
     "Checked in order: fewer quarters both have than the minimum gives Too few quarters; a source whose lines "
     "are refused on Thresholds gives Its lines are refused; ratings that agree and change correlation both at "
     "or above their minimums give Reliable for setting lines; ratings that agree at or above 75% of the "
     "minimum give Use with care; anything else is Not reliable. No outside series means the workbook holds no "
     "series for that product, measure and source."),
    ("CRR grade",
     "The bank's credit risk rating for the product or segment in a quarter, given in the optional crr_grade "
     "column.",
     "Read from a single row: a segment's own row, or a product's All row. Summed segments carry no grade."),
    ("Lowest CRR grade",
     "The lowest CRR grade that falls in each rating.",
     "A grade's rating is the highest rating whose lowest grade is at or below it. The starting values are 1, "
     "3, 5, 7 and 9. The agreement figure counts quarters where that rating equals the internal value's rating "
     "on the lines of the source picked under Shade with lines from."),
    ("Competitive check",
     "How KeyBank's filed figures compare with each peer's, as a count. It does not say how bad is bad enough.",
     "KeyBank's filed median over the quarters the internal series holds, and how many peers' medians over "
     "the same quarters are better than it (below it, or above it when lower is worse)."),
    # Reporting changes (the firm, 16 Oct 2026: "Definitely mark reporting
    # changes."), laid out as Left out, and why is: what it is, then where each
    # one is recorded.
    ("Reporting change",
     "A change to the Call Report's definitions or forms that moves a series without any change in risk, such "
     "as margin loans moved out of other consumer from December 2024. Labeled on every series it touches, in "
     "the quarter it took effect.",
     "Listed once, with its source, on the Reporting changes tab. Each series file the peers build writes "
     "carries a Reporting change line for every change touching its product and measure within its quarters, "
     "shown on Sources; a change a product's own note already describes points to that note instead. "
     "Decide's chart marks the quarters with a diamond along the top, for any source of the row shown; the "
     "Peers charts mark them on the pack composite."),
    ("Event",
     "Something that moved a series without being a change to the report, such as the 2020 revolving-line "
     "drawdowns and the PPP loans in C&I. Labeled on every series it touches, in the quarters it covers.",
     "Listed with its source on the Reporting changes tab, under Events. Each series file the peers build "
     "writes carries an Event line for every event touching its product and measure within its quarters, "
     "shown on Sources. It is never called a reporting change, is not marked on the charts, and never keeps "
     "a series going across a gap: only a reporting change does (the firm, 17 Oct 2026)."),
    ("Continues across",
     "On Sources: quarters a series leaves out and runs across, because the jump left them out only for a move "
     "in a quarter a reporting change names for that product and measure (for a combined product, for any of "
     "its parts), and only a change whose own source says it can step a balance in one quarter. An event never "
     "does.",
     "Those four-quarter windows are not written and never filled; the series keeps every quarter before them "
     "(the firm, 17 Oct 2026). The file names the moves and the changes. Every other reason a window "
     "is left out still starts the series after it. The workbook reads this gap and no other: the quarters "
     "stay on Data, blank, in no line, and a year is still four quarters."),
    ("Reporting changes",
     "The tab listing every reporting change this workbook labels, one row each.",
     "Written from the registry the book names (config/reporting-changes.json). Only changes read in a primary "
     "source are in it; what was left out, and why, is said at the top of the tab."),
    ("Change",
     "On Reporting changes: the change's short name.",
     "As the registry states it."),
    ("Took effect",
     "On Reporting changes: the quarter the change took effect, or the first and last when banks could report "
     "it over several quarters.",
     "As the registry states it: the December 2024 revision runs 2024Q4 to 2025Q2 because banks could report "
     "it on a best-efforts basis until 30 June 2025."),
    ("Products touched",
     "On Reporting changes: the products whose series the change moves, consumer and commercial.",
     "As the registry states it. None of the products means it touches only lines no product is built from, "
     "such as other loans or the memoranda."),
    ("Measures touched",
     "On Reporting changes: which charge-off and delinquency measures of those products it moves.",
     "As the registry states it: net or gross charge-offs, or a delinquency measure (30-89, 90+ accruing, "
     "nonaccrual, 90+ incl. nonaccrual, 30+ incl. nonaccrual)."),
    ("Call Report items",
     "On Reporting changes: the Call Report lines the change touches, kept for the commercial categories.",
     "As the registry states it, by schedule and item where the source gives the item (RC-C 4: C&I)."),
    ("What changed",
     "On Reporting changes: what the change did, in one sentence.",
     "As the registry states it, from the source."),
    ("Can step a balance",
     "On Reporting changes: whether the change can step a book's balance in a single quarter, Yes or No, and "
     "why, from its own source.",
     "As the registry states it. Only a Yes keeps a series going across windows the jump left out (the firm, "
     "18 Oct 2026); where the source does not say, it is No, so a jump it cannot explain still starts the "
     "series again. An event never keeps a series going, whatever it says."),
    ("Source document",
     "On Reporting changes: where the change was read, with its address.",
     "As the registry states it: a Federal Register notice, an FDIC publication or the FDIC's own data "
     "definitions."),
]


#: The Internal tab's own terms, from Internal data to Competitive check: a
#: workbook built without that tab (a commercial book, kinds.KINDS) leaves
#: them off, so the Glossary names no tab the workbook does not have.
_FIRST, _LAST = "Internal data", "Competitive check"
_names = [t for t, _, _ in TERMS]
INTERNAL_TAB_TERMS = frozenset(_names[_names.index(_FIRST):_names.index(_LAST) + 1])


#: The terms that define one or more measures, each with the measures it
#: defines (``peers.flows.MEASURE``, the book's floor_off gaps,
#: ``peers.large_banks.MEASURES``): a book's Glossary gives one only when the
#: book holds a series of one of them, so a commercial book, which holds none,
#: does not define a consumer credit card share or a cure rate argued from
#: consumer charge-off rules.
MEASURE_TERMS = {
    "30+ to charge-off": ("30+ to charge-off",),
    "Gap to peers on 30+ to charge-off, Gap to industry on 30+ to charge-off":
        ("Gap to peers on 30+ to charge-off", "Gap to industry on 30+ to charge-off"),
    "Share paying only the minimum": ("Share paying only the minimum",),
}


def terms_for(kind: dict, *, measures):
    """TERMS for a book of ``kind`` (an entry of ``kinds.KINDS``) holding
    series of ``measures`` (the second part of each series' name): the first
    part's example is the kind's own, the Internal tab's terms are left off
    where the kind builds no Internal tab, and a term of ``MEASURE_TERMS`` is
    left off where the book holds none of its measures."""
    held = set(measures)
    out = []
    for term, meaning, calc in TERMS:
        if term in INTERNAL_TAB_TERMS and not kind["internal_tab"]:
            continue
        if term in MEASURE_TERMS and not held & set(MEASURE_TERMS[term]):
            continue
        if term == "Product":
            meaning = meaning.replace("such as Credit card", "such as %s" % kind["example"])
        if term == "Combined product" and kind["word"] != "Product":
            meaning, calc = COMBINED_COMMERCIAL
        out.append((term, meaning, calc))
    return out
