#!/bin/sh
# wrong.sh NAME GOODBOOK EXTRACT 'Sheet!A1=value'... : one wrong turn in a folder of its own.
# Copies the extract and an answered workbook into $WALK/wrong/NAME, types the edits (edit.py), presses Run
# in the window (win.sh), and prints what the window said. Screens land in $WALK/shots/wrong-NAME-*.png.
set -e
W=${WALK:?set WALK to the scratch folder}
n=$1; good=$2; ex=$3; shift 3
d="$W/wrong/$n"; rm -rf "$d"; mkdir -p "$d"
cp "$ex" "$d/"; x="$d/$(basename "$ex")"
cp "$good" "$d/$(basename "$ex" .csv) - Origination Cube.xlsx"
b="$d/$(basename "$ex" .csv) - Origination Cube.xlsx"
[ $# -gt 0 ] && ${PY:-/usr/bin/python3.12} "$(dirname "$0")/edit.py" "$b" "$@"
timeout 100 "$(dirname "$0")/win.sh" "$W/shots/wrong-$n" "$x" run
