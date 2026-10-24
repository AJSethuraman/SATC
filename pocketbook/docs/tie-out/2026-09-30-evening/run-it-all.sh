#!/bin/sh
# Every step of the evening tie-out (build 44734da4, 30 Sep 2026), from the loan files and the workbooks beside this
# script to roster.csv. On four cores, two hours or more, most of it LibreOffice calculating about 1,650 views. This
# machine stops a command after about 30 minutes, so every step keeps what it made in WORK and a step run again picks
# up where it stopped: run views.py until it prints "all calculated". The calculated views take about 3 GB.
#
#   sh run-it-all.sh work44
#
# Needs Python 3 with openpyxl, numpy, scipy, statsmodels, scikit-learn and Pillow, and LibreOffice (soffice).
# Making the workbooks again from nothing is separate (make_books.py, walk_bleed_run.py, make_scout_book.py): these
# are the ones build 44734da4's Runs wrote on 30 Sep 2026.
set -e
OUT=${1:-work44}
mkdir -p "$OUT"
Q3="../2026-09-28/Consumer book Q3.csv"
BOOKS="q3 flag two grey year yearsplit"
book() {    # a run's workbook
    case $1 in q3) echo "Consumer book Q3 - PocketBook.xlsx";; flag) echo "Flag book - PocketBook.xlsx";;
        two) echo "Two-flag book - PocketBook.xlsx";; grey) echo "Grey book - PocketBook.xlsx";;
        year) echo "Year book - PocketBook.xlsx";; yearsplit) echo "Year-split book - PocketBook.xlsx";; esac
}

# ---- Road 1, PocketBook: every view of each workbook, calculated by LibreOffice, read cell by cell; and 29 Sep's
# own views of Q3, Flag and Two-flag, for the re-run
if [ -z "$SKIP_ROAD1" ]; then
for b in $BOOKS; do python3 views.py "$(book $b)" "$OUT/views-$b"; done
for b in q3 flag two; do
    PLAN_FROM=../2026-09-29-changes/work/views-$b/plan.json python3 views.py "$(book $b)" "$OUT/views-$b-0929"
done
for b in $BOOKS q3-0929 flag-0929 two-0929; do python3 read_book.py "$OUT/views-$b" > "$OUT/views-$b-read.log"; done
python3 -c "import sys; sys.path.insert(0, '../../../tests'); import recalc; \
print(recalc.recalc_file('Scouting book - PocketBook.xlsx', '$OUT/calculated-scout')); \
print(recalc.recalc_file('Bureau book - PocketBook.xlsx', '$OUT/calculated-bureau'))"
python3 read_scout.py "$OUT/calculated-scout/Scouting book - PocketBook.xlsx" "$OUT/figures-scout.json"
python3 read_look.py "$OUT/calculated-bureau/Bureau book - PocketBook.xlsx" "$OUT/figures-bureau.json"
python3 excel_save_check.py "Consumer book Q3 - PocketBook.xlsx" "$Q3" "$OUT/excel" > "$OUT/excel.log"
python3 excel_save_check.py "Flag book - PocketBook.xlsx" "Flag book.csv" "$OUT/excel-flag" > "$OUT/excel-flag.log"
fi

# ---- Road 2, the loan files alone: no PocketBook code (grep -nE "^\s*(from|import)\s+pocketbook|sys\.path"
# by_hand_book.py by_hand_look.py by_hand_scout.py forest_scout.py look_extra.py cmh_check.py finds none).
# FILTER names the Filter by column (Grids' Only loans where); the split is the fourth and fifth arguments
road2() {   # run csv split how [filter]
    FILTER=${5:-} python3 by_hand_book.py "$2" "$OUT/expected-$1.json" 10000 $3 $4 "$OUT/views-$1/figures.json"
    FILTER=${5:-} python3 by_hand_book.py "$2" "$OUT/expected-$1-flip.json" 10000 $3 $4 "$OUT/views-$1/figures.json" \
        "$OUT/views-$1/wb-pockets.json"
}
road2 q3 "$Q3" REV_DEBT own_median
road2 flag "Flag book.csv" SYS_FLAG each_value SYS_FLAG
road2 two "Two-flag book.csv" SYS_FLAG each_value SYS_FLAG
road2 grey "Grey book.csv" REV_DEBT own_median
road2 year "Year book.csv" REV_DEBT own_median ORIG_YEAR
road2 yearsplit "Year-split book.csv" ORIG_YEAR each_value
road2 q3-0929 "$Q3" REV_DEBT own_median
road2 flag-0929 "Flag book.csv" SYS_FLAG each_value SYS_FLAG
road2 two-0929 "Two-flag book.csv" SYS_FLAG each_value SYS_FLAG
python3 by_hand_scout.py "Scouting book.csv" "$OUT/expected-scout.json" "$OUT/figures-scout.json"
[ -s "$OUT/expected-forest.json" ] || \
    python3 -W ignore forest_scout.py "Scouting book.csv" "$OUT/expected-forest.json" "$OUT/figures-scout.json" \
    > "$OUT/forest.log"
python3 by_hand_look.py "Bureau book.csv" "$OUT/expected-bureau.json" "$OUT/figures-bureau.json"

# ---- Where they meet
for b in $BOOKS q3-0929 flag-0929 two-0929; do
    python3 compare.py "$OUT/views-$b/figures.json" "$OUT/expected-$b.json" "$OUT/roster-$b.csv" $b \
        "$OUT/expected-$b-flip.json" > "$OUT/compare-$b.txt"
done
python3 compare.py "$OUT/figures-scout.json" "$OUT/expected-scout.json" "$OUT/roster-scout.csv" scout - \
    "$OUT/expected-forest.json" > "$OUT/compare-scout.txt"
python3 compare.py "$OUT/figures-bureau.json" "$OUT/expected-bureau.json" "$OUT/roster-bureau.csv" bureau \
    > "$OUT/compare-bureau.txt"
python3 excel_roster.py "$OUT/excel/dropdowns.json" "$OUT/roster-excel.csv" excel > "$OUT/mutate-excel.txt"
python3 excel_roster.py "$OUT/excel-flag/dropdowns.json" "$OUT/roster-excel-flag.csv" excel-flag \
    > "$OUT/mutate-excel-flag.txt"

# ---- Change 7, column widths: every value shown on every visible tab of every view, against its column
for b in $BOOKS; do python3 widths_check.py "$OUT/widths-$b.csv" $b "$OUT/views-$b" > "$OUT/widths-$b.txt"; done
python3 widths_check.py "$OUT/widths-single.csv" \
    bureau:single "Bureau book - PocketBook.xlsx" "$OUT/calculated-bureau/Bureau book - PocketBook.xlsx" \
    scout:single "Scouting book - PocketBook.xlsx" "$OUT/calculated-scout/Scouting book - PocketBook.xlsx" \
    > "$OUT/widths-single.txt"

python3 roster.py $(for b in $BOOKS q3-0929 flag-0929 two-0929 scout bureau excel excel-flag; do \
    printf '%s ' "$OUT/roster-$b.csv"; done) $(for b in $BOOKS single; do printf '%s ' "$OUT/widths-$b.csv"; done) \
    roster.csv > "$OUT/tallies.json"
gzip -9 -f -k roster.csv                  # roster.csv.gz is what is kept: the CSV is 55 MB

# ---- Check the checker: planted errors anywhere, and the plausible wrong methods (mutate.py says both)
for b in $BOOKS; do python3 mutate.py "$OUT/views-$b/figures.json" "$OUT/expected-$b.json" > "$OUT/mutate-$b.txt"; done
python3 mutate.py "$OUT/figures-scout.json" "$OUT/expected-scout.json" > "$OUT/mutate-scout.txt"
python3 mutate.py "$OUT/figures-bureau.json" "$OUT/expected-bureau.json" > "$OUT/mutate-bureau.txt"

# ---- The re-run against 29 Sep, and did anything get skipped
python3 rerun_compare.py ../2026-09-29-changes/roster.csv "$OUT/roster-q3-0929.csv" q3 "$OUT/roster-flag-0929.csv" flag \
    "$OUT/roster-two-0929.csv" two "$OUT/roster-bureau.csv" bureau "$OUT/roster-scout.csv" scout \
    "$OUT/roster-excel.csv" excel "$OUT/roster-excel-flag.csv" excel-flag > "$OUT/rerun.json"
for b in $BOOKS; do       # one run a command: each opens every calculated view of its book
    python3 completeness.py roster.csv $b "$OUT/views-$b/calculated" > "$OUT/completeness-$b.txt"
done
python3 completeness.py roster.csv scout "$OUT/calculated-scout" > "$OUT/completeness-scout.txt"
python3 explain_border.py "$OUT" q3 flag two grey year yearsplit > "$OUT/border.txt"
python3 explain_new.py "$OUT" $BOOKS > "$OUT/new.txt"
echo "roster.csv written; the tallies are in $OUT/tallies.json"
