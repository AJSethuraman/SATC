"""Every term the workbook uses: what it means, and exactly how it is calculated.

Written for the person reading the workbook, not the person who built it.
Each calculation is the one the code performs, so a reviewer can redo it by
hand. The workbook's tests check that every column heading on Thresholds and
Settings has an entry here, so a new heading cannot ship without its
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
     "The quarters the thresholds are built from: every quarter, except any periods left out on Settings.",
     "A quarter is left out if it falls between a Leave out from and to on Settings, inclusive."),
    ("Left out",
     "A period set aside because it does not represent the risk being rated, with the reason recorded.",
     "Typed on Settings as first and last quarter plus a reason. Up to two periods per product. Shown on "
     "Assess as a dark strip under the chart and grey dots on the line, and recorded on Run."),
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
    ("Moderate: half-width",
     "How wide Moderate is on each side of the median, counted in typical yearly moves.",
     "A Settings cell. 0.5 makes Moderate one typical yearly move wide in total."),
    ("Moderate-Low",
     "Better than normal by more than ordinary movement, but not by enough to be Low.",
     "From the Moderate-Low line up to where Moderate begins."),
    ("Moderate-Low begins",
     "How far below the median Low ends, counted in typical yearly moves.",
     "Median minus this number times the typical yearly move. A Settings cell. It must be larger than the "
     "Moderate half-width."),
    ("Low",
     "Clearly better than normal.",
     "Below the Moderate-Low line. A loss rate at or below zero is always Low."),
    ("Moderate-High",
     "Worse than normal by more than ordinary movement, but short of stress.",
     "From the top of Moderate (median plus half-width times the typical yearly move) up to where High begins."),
    ("High",
     "Stress: a level far enough above normal to count as unusual for this product.",
     "From the median plus the High z times the spread of levels. It is the same robust z the evidence uses to "
     "call a level unusual, so High and stress mean one thing."),
    ("High begins at this z",
     "How many spreads of levels above the median High starts. The same number means the same rarity on "
     "every product.",
     "A Settings cell. 3.5 is the usual line for an outlier (Iglewicz and Hoaglin, 1993). With a crisis left "
     "out it can sit beyond everything kept, which the workbook refuses. The Dial on Assess shows 2.0 to 3.5 "
     "side by side."),
    ("Spread of levels",
     "How widely the quarters kept range around their median, measured so that one extreme stretch cannot "
     "inflate it. The unit High is measured in.",
     "1.4826 x the median of each kept quarter's distance from the median kept (the median absolute "
     "deviation, MAD)."),
    ("Dial",
     "A table on Assess showing what one setting would do at other values, before you change it.",
     "For each value: the four lines with that setting changed and the others as on Settings, and how many "
     "quarters kept fall in each score. The highlighted row is the current setting."),
    ("2 Moderate-Low from, 3 Moderate from, 4 Moderate-High from, 5 High from",
     "The four lines the scoring file uses. Each is where that score begins.",
     "As defined under Moderate-Low, Moderate, Moderate-High and High above."),
    ("A value on a line takes the",
     "Which score a value exactly on a line gets.",
     "A Settings cell. 'worse' gives the higher score, 'better' the lower."),
    ("Score",
     "1 to 5: Low, Moderate-Low, Moderate, Moderate-High, High.",
     "1 plus the number of lines the value is at or past (past only, if a value on a line takes the better score)."),
    ("Rating",
     "The score's name.",
     "1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High."),
    ("Latest",
     "The most recent quarter in the source file and its value.",
     "Read from the source, not recalculated."),
    ("Check",
     "Says why the workbook will not draw a scale, rather than drawing one that cannot be right.",
     "Refuses when the median is at or below zero, when Moderate-Low would not begin below Moderate, when High "
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
    ("Above the path, below the path",
     "Whether a departure was worse or better than the path around it.",
     "The sign of the average distance from the straight line."),
    ("Backtest",
     "How well a scale would have predicted what came next, using only history available at the time.",
     "Every quarter is scored on lines built from the quarters before it, then compared with the value four "
     "quarters later."),
    ("Spearman",
     "How consistently a higher score came before a higher value (1 is perfect, 0 is none, negative is reverse).",
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
]

