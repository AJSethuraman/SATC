#!/bin/sh
# Every step of the full tie-out, from the two loan files and the two workbooks beside this script to roster.csv.
# About twenty minutes, most of it the independent road's 10,000 shuffles and the forest grown again.
#
#   sh run-it-all.sh work          # "work" is a folder of your choosing for the in-between files
#
# Needs Python 3 with openpyxl, numpy, scipy, statsmodels, scikit-learn and Pillow, and LibreOffice (soffice).
# Making the two workbooks again from nothing is separate (walk_both_runs.py, make_scout_book.py): these are the
# ones the Runs of 28 Sep 2026 wrote.
set -e
OUT=${1:-work}
mkdir -p "$OUT"
Q3="../2026-09-28/Consumer book Q3.csv"

# ---- Road 1, PocketBook: every view of each workbook, calculated by LibreOffice, read cell by cell
python3 views.py "Consumer book Q3 - PocketBook.xlsx" "$OUT/views-bleed"
python3 read_bleed.py "$OUT/views-bleed"
python3 -c "import sys; sys.path.insert(0, '../../../tests'); import recalc; \
print(recalc.recalc_file('Scouting book - PocketBook.xlsx', '$OUT/calculated-scout'))"
python3 read_scout.py "$OUT/calculated-scout/Scouting book - PocketBook.xlsx" "$OUT/figures-scout.json"

# ---- Road 2, the loan files alone: no PocketBook code
python3 by_hand_bleed.py "$Q3" "$OUT/expected-bleed.json" 10000
python3 by_hand_bleed.py "$Q3" "$OUT/expected-bleed-flip.json" 10000 "$OUT/views-bleed/wb-pockets.json"
python3 by_hand_scout.py "Scouting book.csv" "$OUT/expected-scout.json" "$OUT/figures-scout.json"
python3 -W ignore forest_scout.py "Scouting book.csv" "$OUT/expected-forest.json" "$OUT/figures-scout.json" \
    > "$OUT/forest.log"

# ---- Where they meet
python3 compare.py "$OUT/views-bleed/figures.json" "$OUT/expected-bleed.json" "$OUT/roster-bleed.csv" bleed \
    "$OUT/expected-bleed-flip.json"
python3 compare.py "$OUT/figures-scout.json" "$OUT/expected-scout.json" "$OUT/roster-scout.csv" scout - \
    "$OUT/expected-forest.json"
python3 roster.py "$OUT/roster-bleed.csv" "$OUT/roster-scout.csv" roster.csv > "$OUT/tallies.json"
python3 mutate.py "$OUT/views-bleed/figures.json" "$OUT/expected-bleed.json" > "$OUT/mutate-bleed.txt"
python3 mutate.py "$OUT/figures-scout.json" "$OUT/expected-scout.json" > "$OUT/mutate-scout.txt"
cat "$OUT/mutate-bleed.txt" "$OUT/mutate-scout.txt"
echo "roster.csv written; the tallies are in $OUT/tallies.json"
