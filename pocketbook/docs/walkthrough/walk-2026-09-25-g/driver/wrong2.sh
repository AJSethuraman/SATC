#!/bin/sh
# wrong2.sh : the wrong turns that change the extract or the file, not a cell (E, F, G, H, K, N).
# Each in $WALK/wrong/<name>; screens land in $WALK/shots/wrong-<name>-*.png.
set -e
W=${WALK:?set WALK to the scratch folder}; D=$(dirname "$0"); X="$W/book/Consumer book Q3.csv"; G=${GOOD:-$W/run1.xlsx}
PY=${PY:-/usr/bin/python3.12}
prep() { d="$W/wrong/$1"; rm -rf "$d"; mkdir -p "$d"; cp "$X" "$d/"; cp "$G" "$d/Consumer book Q3 - Origination Cube.xlsx"; }
b() { echo "$W/wrong/$1/Consumer book Q3 - Origination Cube.xlsx"; }
x() { echo "$W/wrong/$1/Consumer book Q3.csv"; }
# E: the workbook still open in Excel (a lock, simulated by making the file unwritable)
prep open; chattr +i "$(b open)"; timeout 100 "$D/win.sh" "$W/shots/wrong-open" "$(x open)" run setup; chattr -i "$(b open)"
# F: a column renamed in the extract after Set up, then Run, then Set up
prep extract-renamed-col; sed -i '1s/CHANNEL/CHNL/' "$(x extract-renamed-col)"
timeout 100 "$D/win.sh" "$W/shots/wrong-extract-renamed-col" "$(x extract-renamed-col)" run
timeout 100 "$D/win.sh" "$W/shots/wrong-extract-renamed-col-b" "$(x extract-renamed-col)" setup
# G: fewer rows after Set up
prep extract-fewer-rows; head -6001 "$X" > "$(x extract-fewer-rows)"
timeout 100 "$D/win.sh" "$W/shots/wrong-extract-fewer-rows" "$(x extract-fewer-rows)" run
# H: the workbook copied to a folder holding a different extract of the same name
prep copied-folder; $PY -c "import csv,sys; r=list(csv.reader(open(sys.argv[1]))); csv.writer(open(sys.argv[2],'w',newline='')).writerows(r[:1]+r[4001:7001])" "$X" "$(x copied-folder)"
timeout 100 "$D/win.sh" "$W/shots/wrong-copied-folder" "$(x copied-folder)" run
# K: the workbook picked in place of the extract
prep picked-workbook; timeout 100 "$D/win.sh" "$W/shots/wrong-picked-workbook" "$(b picked-workbook)" setup run
# N: new columns in a refreshed extract
prep new-columns; $PY -c "
import csv,sys,random
r=list(csv.reader(open(sys.argv[1]))); rng=random.Random(3)
r[0]+= ['CURR_STATUS','DTI']
for row in r[1:]: row += [rng.choice(['Current','30DPD','Paid off']), str(round(rng.uniform(5,55),1))]
csv.writer(open(sys.argv[1],'w',newline='')).writerows(r)" "$(x new-columns)"
timeout 100 "$D/win.sh" "$W/shots/wrong-new-columns" "$(x new-columns)" setup run
