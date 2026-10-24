"""The ratios tab: what to build, why, and what will bite you.

The firm: "you are free to have a tab in there that explains what ratios seem to
make sense and why."

So this DESCRIBES. It computes nothing. Every row names the two fields, the
question the ratio answers, and the trap -- because most of the trouble in this
whole exercise came from ratios whose denominator was not what it looked like.
"""
import csv
import pathlib

OUT = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite\verified-data")

ROWS = [
    # (name, question, numerator, denominator, why it makes sense, the trap)
    ("Noncurrent loan rate",
     "How much of the loan book has stopped performing?",
     "NCLNLS", "LNLSGR",
     "The clearest single read on credit quality. Both sides are filed lines, "
     "both are point-in-time, and both are verified here.",
     "Use GROSS loans (LNLSGR), not net. Net subtracts the reserve, which is "
     "itself a judgement about the numerator -- so a bank that reserves more "
     "would look worse on both sides at once."),

    ("Reserve coverage of bad loans",
     "Does the money set aside actually cover the loans that have gone bad?",
     "LNATRES", "NCLNLS",
     "Below 100% means the reserve does not cover what is already noncurrent. "
     "It is the most direct solvency question you can ask of two filed lines.",
     "The denominator can be very small or zero at a clean bank, which makes "
     "the ratio explode or divide by zero. Show it as blank, not as a big "
     "number."),

    ("Reserve as a share of loans",
     "How much has the bank set aside against its book?",
     "LNATRES", "LNLSGR",
     "A stable, slow-moving measure. Good for comparing banks with different "
     "sized books.",
     "Reserving practice changed with the CECL accounting standard. Comparing "
     "across that boundary compares two different rules."),

    ("Equity to assets",
     "How much of the bank is funded by its owners rather than borrowed?",
     "EQ", "ASSET",
     "The simplest capital measure there is, from two filed lines.",
     "It is not a regulatory capital ratio and will not match one. The bank "
     "files those itself -- RBC1AAJ and RBCRWAJ -- and those are here."),

    ("Loans to deposits",
     "How much of the deposit base is lent out?",
     "LNLSGR", "DEP",
     "A funding and liquidity read that needs no adjustment.",
     "A bank funded by borrowings rather than deposits will look extreme "
     "without being unusual. Read it beside the borrowings line."),

    ("Uninsured deposits share",
     "How much of the deposit base could leave quickly?",
     "DEPUNINS", "DEP",
     "This is the ratio that mattered in the 2023 bank failures. Both sides "
     "are filed lines.",
     "Uninsured is an estimate the bank makes, and the basis has changed over "
     "time. It is also a stock, not a behaviour -- a high share is not a run."),

    ("Brokered deposits share",
     "How much of the funding is bought rather than gathered?",
     "BRO", "DEP",
     "Bought funding is faster to leave and repricies quickly.",
     "The regulatory definition of brokered changed in 2021, so a level shift "
     "around that date is a rule change, not a behaviour change."),

    ("Past-due 30-89 rate, by loan class",
     "Which loan class is deteriorating first?",
     "P3<class>", "LN<class>",
     "The earliest visible sign of trouble, and it is class by class, so it "
     "shows you where rather than just how much.",
     "Match the class exactly: the 30-89 bucket for credit cards belongs over "
     "the credit card balance, not over total loans. And the classes DO NOT "
     "add up to the total -- home equity lines sit inside the residential "
     "figure, so summing them double-counts."),

    ("Noncurrent rate, by loan class",
     "Which class holds the loans that have already gone bad?",
     "NA<class>", "LN<class>",
     "Same idea as above, one stage later.",
     "Same class-matching trap, and the same overlap between residential and "
     "home equity."),

    ("Quarterly net charge-off rate, annualised",
     "How fast are losses actually crystallising?",
     "NT<class>Q", "LN<class>",
     "The flow measure. It tells you what is being written off now rather "
     "than what is merely late.",
     "**The one that produced a 670% rate.** Three traps at once: (1) the "
     "numerator is a quarter and the denominator a point-in-time balance, so "
     "annualising means multiplying by four; (2) in a merger quarter the flow "
     "mixes two banks -- check not-comparable-periods.csv and drop those; "
     "(3) a small or newly-transferred book makes the denominator tiny."),

    ("Return on assets",
     "How much does the bank earn on what it holds?",
     "(FDIC's ROAQ)", "—",
     "Already published by the FDIC in this data as ROAQ, so there is nothing "
     "to build.",
     "It is the FDIC's arithmetic, not a filed line. Labelled "
     "computed_by = the FDIC in the field dictionary."),

    ("Securities unrealised position",
     "How far under water is the securities book?",
     "SCAA - SCAF and SCHA - SCHF", "EQ",
     "The 2023 question. Held-to-maturity securities are carried at cost, so "
     "the loss does not show in equity until they are sold.",
     "Two portfolios with different accounting: available-for-sale marks "
     "already flow through equity, held-to-maturity ones do not. Do not add "
     "them and divide once."),

    ("House price index change",
     "How fast are prices moving in a market?",
     "any HPI series", "its own earlier value",
     "Index levels are meaningless on their own; the change is the signal.",
     "Each index has its own base year. Never compare LEVELS across indexes "
     "-- only changes. FHFA and Case-Shiller measure different things on "
     "different bases and will not agree."),

    ("Charge-off and delinquency rates at commercial banks",
     "What is the whole banking system doing, as a benchmark?",
     "the CORx / DRx series", "—",
     "The Federal Reserve already publishes these as rates, so they need no "
     "construction. They are the natural peer benchmark for a single bank's "
     "own rate.",
     "They are rates over AVERAGE loans for all commercial banks, not over "
     "one bank's period-end balance. Comparing a bank's own ratio to these is "
     "comparing two different denominators -- close enough to be useful, not "
     "close enough to be a variance."),

    ("Loan officer survey diffusion",
     "Are banks tightening or loosening, and for whom?",
     "the DRTS / DRSD series", "—",
     "Already a net percentage. Leading, and it moves before the loss data.",
     "It is a count of banks, not a volume. Eight small banks tightening "
     "outweighs one enormous one loosening. And a tightening series and a "
     "demand series look identical until you read the definition -- four were "
     "mislabelled in this system until they were checked."),

    ("Debt service ratio",
     "How stretched is the household sector?",
     "TDSP / MDSP / CDSP", "—",
     "Published as a ratio already.",
     "The methodology changed at 2024 Q2 to a credit-bureau basis. There is a "
     "level shift there that is a rule change, not an economy change."),

    ("Consumer credit growth",
     "Is household borrowing accelerating?",
     "TOTALSL / REVOLSL / NONREVSL", "its own earlier value",
     "Clean monthly levels, and revolving versus non-revolving separates the "
     "credit-card cycle from the auto and student loan cycle.",
     "These are levels in MILLIONS of dollars. They were labelled billions in "
     "this system until 5 September 2026 -- a factor of a thousand on a label "
     "that nothing computed with, so nothing caught it."),

    ("Peer comparison, any of the above",
     "Is this bank unusual, or is the whole peer group moving?",
     "one bank's ratio", "the same ratio for the other eleven",
     "Almost every question above is more useful as a rank than a level. The "
     "twelve banks here are a real peer set.",
     "They are not a like-for-like peer set: two are custody banks and two are "
     "broker-dealer banks, and their balance sheets are shaped nothing like a "
     "commercial lender's. Compare within kind."),
]

with (OUT / "ratios-worth-building.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["ratio", "question_it_answers", "numerator", "denominator",
                "why_it_makes_sense", "the_trap", "computed_here"])
    for r in ROWS:
        w.writerow(list(r) + ["no -- described only"])
print("ratios-worth-building.csv: %d ratios described, 0 computed" % len(ROWS))
