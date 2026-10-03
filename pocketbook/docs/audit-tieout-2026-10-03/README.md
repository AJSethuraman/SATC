# Audit workbook tie-out, 3 October 2026

An independent check of PocketBook's audit workbook (`src/pocketbook/audit.py`) on one synthetic bleed-test Run:
50,000 loans, FICO bands by CHANNEL, 10,000 shuffles. The workpaper is `TIEOUT.html` (self-contained; open it in a
browser).

## Files

| File | Side | What it does |
|---|---|---|
| `make_scenario.py` | PocketBook | Writes the synthetic loan file (`synth.write_extract`, n=50,000, seed 7), sets Control, runs PocketBook, writes the main and audit workbooks |
| `tieout.py` | Independent | Recomputes every figure from the loan file's text. Imports nothing from PocketBook; standard library only |
| `tieout_band.py` | Independent | The same shuffle test, longer, for one band (section 7.2) |
| `compare.py` | Reader | Recalculates both workbooks with LibreOffice headless and lines up the three sides |
| `pictures.py` | Reader | The two pictures in the workpaper |
| `build_html.py` | Reader | Writes `TIEOUT.html` from the results |

The loan file and workbooks are not committed (about 15 MB); `make_scenario.py` regenerates them byte for byte. The
loan file's SHA-256 is `9b4190398a30d2c1414a72cf0ed7b24e58cd4b4b608c5183fdb86e8eb7ba0681`.

## Commands

Needs Python 3 with openpyxl, numpy and Pillow, LibreOffice (`soffice`) and poppler (`pdftoppm`). About fifteen
minutes in all.

```
cd pocketbook/docs/audit-tieout-2026-10-03
R=/tmp/pb-tieout

python make_scenario.py $R
python tieout.py $R/loans.csv $R/indep.json
python tieout_band.py $R/loans.csv "653 - 685" 100000 777 $R/deep.json
python compare.py $R $R/indep.json $R/cmp.json
python pictures.py $R $R/pics
python build_html.py $R $R/indep.json $R/cmp.json $R/deep.json $R/pics TIEOUT.html
rm -rf $R
```
