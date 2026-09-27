#!/bin/sh
# render.sh BOOK.xlsx OUTDIR PREFIX : the workbook as LibreOffice prints it, one PNG per page
set -e
mkdir -p "$2"
cp "$1" "$2/$3.xlsx"
H=$(mktemp -d)
HOME=$H soffice --headless --norestore --convert-to pdf --outdir "$2" "$2/$3.xlsx" >/dev/null 2>&1
pdftoppm -r 90 -png "$2/$3.pdf" "$2/$3-p"
ls "$2" | grep "^$3-p"
