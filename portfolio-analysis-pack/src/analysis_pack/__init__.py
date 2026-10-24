"""Portfolio Analysis Pack.

A loan extract plus a short question file in; one self-contained workbook out.
Python does every calculation over the loans and writes a small count cube;
the workbook derives each rate, interval and headline word from that cube by
live formula, so a reviewer can move the confidence level and watch it move.

The package knows no domain: no column name, no list of anything, no outcome word.
Everything of that kind lives in the question file. A test enforces it.
"""

__version__ = "0.1.0"
