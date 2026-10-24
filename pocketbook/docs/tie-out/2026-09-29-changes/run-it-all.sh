#!/bin/sh
# Every step of the changes tie-out, from the loan files and the workbooks beside this script to roster.csv.
# About forty minutes on four cores, most of it LibreOffice calculating 340 views and the independent road's 10,000
# shuffles on three books (cached in WORK, so a second run takes a few minutes).
#
#   sh run-it-all.sh work          # "work" is a folder of your choosing for the in-between files
#
# Needs Python 3 with openpyxl, numpy, scipy, statsmodels, scikit-learn and Pillow, and LibreOffice (soffice).
# Making the workbooks again from nothing is separate (make_books.py, walk_bleed_run.py, make_scout_book.py): these
# are the ones this build's Runs wrote on 29 Sep 2026. excel_save_check.py runs PocketBook again (change 5).
set -e
OUT=${1:-work}
mkdir -p "$OUT"
Q3="../2026-09-28/Consumer book Q3.csv"

# ---- Road 1, PocketBook: every view of each workbook, calculated by LibreOffice, read cell by cell
# (SKIP_ROAD1=1 reuses the views and readings already in WORK)
if [ -z "$SKIP_ROAD1" ]; then
python3 views.py "Consumer book Q3 - PocketBook.xlsx" "$OUT/views-q3"
python3 views.py "Flag book - PocketBook.xlsx" "$OUT/views-flag"
python3 views.py "Two-flag book - PocketBook.xlsx" "$OUT/views-two"
for b in q3 flag two; do python3 read_book.py "$OUT/views-$b" > "$OUT/read-$b.log"; done
python3 -c "import sys; sys.path.insert(0, '../../../tests'); import recalc; \
print(recalc.recalc_file('Scouting book - PocketBook.xlsx', '$OUT/calculated-scout')); \
print(recalc.recalc_file('Bureau book - PocketBook.xlsx', '$OUT/calculated-bureau'))"
python3 read_scout.py "$OUT/calculated-scout/Scouting book - PocketBook.xlsx" "$OUT/figures-scout.json"
python3 read_look.py "$OUT/calculated-bureau/Bureau book - PocketBook.xlsx" "$OUT/figures-bureau.json"
python3 excel_save_check.py "Consumer book Q3 - PocketBook.xlsx" "$Q3" "$OUT/excel" > "$OUT/excel.log"
python3 excel_save_check.py "Flag book - PocketBook.xlsx" "Flag book.csv" "$OUT/excel-flag" > "$OUT/excel-flag.log"
fi

# ---- Road 2, the loan files alone: no PocketBook code
python3 by_hand_book.py "$Q3" "$OUT/expected-q3.json" 10000 REV_DEBT own_median "$OUT/views-q3/figures.json"
python3 by_hand_book.py "$Q3" "$OUT/expected-q3-flip.json" 10000 REV_DEBT own_median "$OUT/views-q3/figures.json" \
    "$OUT/views-q3/wb-pockets.json"
for b in flag two; do
    csv="Flag book.csv"; [ "$b" = two ] && csv="Two-flag book.csv"
    python3 by_hand_book.py "$csv" "$OUT/expected-$b.json" 10000 SYS_FLAG each_value "$OUT/views-$b/figures.json"
    python3 by_hand_book.py "$csv" "$OUT/expected-$b-flip.json" 10000 SYS_FLAG each_value \
        "$OUT/views-$b/figures.json" "$OUT/views-$b/wb-pockets.json"
done
python3 by_hand_scout.py "Scouting book.csv" "$OUT/expected-scout.json" "$OUT/figures-scout.json"
[ -n "$SKIP_ROAD1" ] && [ -s "$OUT/expected-forest.json" ] || \
    python3 -W ignore forest_scout.py "Scouting book.csv" "$OUT/expected-forest.json" "$OUT/figures-scout.json" \
    > "$OUT/forest.log"
python3 by_hand_look.py "Bureau book.csv" "$OUT/expected-bureau.json" "$OUT/figures-bureau.json"

# ---- Where they meet
for b in q3 flag two; do
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
python3 roster.py "$OUT/roster-q3.csv" "$OUT/roster-scout.csv" "$OUT/roster-flag.csv" "$OUT/roster-two.csv" \
    "$OUT/roster-bureau.csv" "$OUT/roster-excel.csv" "$OUT/roster-excel-flag.csv" roster.csv > "$OUT/tallies.json"

# ---- Check the checker: planted errors, first anywhere (as on 28 Sep), then only in what the changes added
NEW=panel,split-sum,split-pocket,split-differ,split-steady,pck-dot,pck-listed,groups
for b in q3 flag two; do
    python3 mutate.py "$OUT/views-$b/figures.json" "$OUT/expected-$b.json" > "$OUT/mutate-$b.txt"
    python3 mutate.py "$OUT/views-$b/figures.json" "$OUT/expected-$b.json" $NEW > "$OUT/mutate-new-$b.txt"
done
python3 mutate.py "$OUT/figures-scout.json" "$OUT/expected-scout.json" > "$OUT/mutate-scout.txt"
python3 mutate.py "$OUT/figures-bureau.json" "$OUT/expected-bureau.json" \
    look,look-bar,look-end,look-dots,low-values > "$OUT/mutate-bureau.txt"
head -n 2 "$OUT"/mutate-*.txt

# ---- The re-run against 28 Sep, and did anything get skipped
python3 rerun_compare.py ../2026-09-28-full/roster.csv "$OUT/roster-q3.csv" bleed "$OUT/roster-scout.csv" scout \
    > "$OUT/rerun.json"
python3 completeness.py roster.csv q3 "$OUT/views-q3/calculated" flag "$OUT/views-flag/calculated" \
    two "$OUT/views-two/calculated" scout "$OUT/calculated-scout" > "$OUT/completeness.txt"
head -n 30 "$OUT/completeness.txt"
echo "roster.csv written; the tallies are in $OUT/tallies.json"
