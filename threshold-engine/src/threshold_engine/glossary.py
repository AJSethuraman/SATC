"""Every term the workbook uses: what it means, and exactly how it is calculated.

Written for the person reading the workbook, not the person who built it.
Each calculation is the one the code performs, so a reviewer can redo it by
hand. The workbook's tests check that every column heading on Thresholds and
on Assess's inputs has an entry here, so a new heading cannot ship without its
definition.
"""

# (term, what it means, how it is calculated)
TERMS = [
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
     "strip and grey dots on the line, and recorded on Run."),
    ("Median kept",
     "The middle of the quarters kept: half were higher, half lower. The centre of Moderate.",
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
     "Typed in Your settings on Assess. 0.5 makes Moderate one typical yearly move wide in total."),
    ("Moderate-Low",
     "Better than normal by more than ordinary movement, but not by enough to be Low.",
     "From the Moderate-Low line up to where Moderate begins."),
    ("Moderate-Low begins (yearly moves)",
     "How far below the median Low ends, counted in typical yearly moves.",
     "Median minus this number times the typical yearly move. Typed in Your settings on Assess. It must be "
     "larger than the width of Moderate."),
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
    ("How rare High is (z)",
     "How many spreads of levels above the median High starts. The same number means the same rarity on "
     "every series.",
     "Typed in Your settings on Assess. 3.5 is the usual line for an outlier (Iglewicz and Hoaglin, 1993). With a crisis left "
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
    ("On a line, rate it",
     "Which rating a value exactly on a line gets.",
     "Picked in Your settings on Assess. 'worse' gives the worse of the two ratings, 'better' the better."),
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
    ("Spell",
     "An unbroken stretch of quarters worse than the median.",
     "From the first quarter worse than the median to the last before it returns."),
    ("Robust z",
     "How far a level sits from the rest of history, in units that one extreme period cannot distort.",
     "(value - median) / (1.4826 x MAD), with the median and MAD taken over every quarter outside the spell "
     "being measured. Not a probability: neighbouring quarters of a TTM rate are not independent."),
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
     "Where each colour starts, from three views side by side: KeyBank's own history, the industry's and the "
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
    ("Competitive check",
     "How KeyBank's filed figures compare with each peer's, as a count. It does not say how bad is bad enough.",
     "KeyBank's filed median over the quarters the internal series holds, and how many peers' medians over "
     "the same quarters are better than it (below it, or above it when lower is worse)."),
]

