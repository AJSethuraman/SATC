"""KeyBank-styled native-Excel charts for time-series credit-risk data.

These build real openpyxl chart objects (LineChart) that float over the sheet —
no images, no add-ins. Two archetypes cover almost every question:

    A. trend_chart      one or many series vs time         (the workhorse)
    B. comparison       two series, one axis, diverging     (e.g. HPI vs CRE)

Plus a sparkline note (Excel sparklines are not writable by openpyxl — see
add_sparklines below for the supported route via the macro).

Colours come from keybank_style so charts match the cells around them.
Raw blocks are newest-first; pass the trailing window and the helper keeps the
category order so time reads left (old) -> right (new).
"""
from __future__ import annotations

from openpyxl.chart import LineChart, Reference, Series
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties

from keybank_style import INK, KEY_RED, SLATE, STONE


def _styled_line(ref, name, hex_color, width_emu=28000):
    s = Series(ref, title=name)
    s.graphicalProperties = GraphicalProperties()
    s.graphicalProperties.line = LineProperties(solidFill=hex_color, w=width_emu)
    s.smooth = False                      # straight segments — honest, not splined
    return s


def trend_chart(ws, anchor, title, cats_ref, series_defs,
                y_title="%", height_cm=6.0, width_cm=16.0):
    """Archetype A — a KeyBank line chart placed at `anchor` (e.g. 'K9').

    cats_ref    : Reference to the date column (the X categories)
    series_defs : list of (value_ref, name, hex_color)  e.g.
                  [(allb_ref, 'All banks', KEY_RED), (top_ref, 'Top 100', INK)]
    """
    ch = LineChart()
    ch.title = title
    ch.height, ch.width = height_cm, width_cm
    ch.y_axis.title = y_title
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.y_axis.majorGridlines = ChartLines()   # faint horizontal grid only
    ch.x_axis.majorGridlines = None           # no vertical grid — keep it clean
    ch.legend.position = "b"                   # legend below, like the spec
    for ref, name, hex_color in series_defs:
        ch.series.append(_styled_line(ref, name, hex_color))
    ch.set_categories(cats_ref)
    ws.add_chart(ch, anchor)
    return ch


def comparison_chart(ws, anchor, title, cats_ref, ref_a, name_a, ref_b, name_b,
                     y_title="index", **kw):
    """Archetype B — two series on one axis: A in INK, B in KEY_RED."""
    return trend_chart(
        ws, anchor, title, cats_ref,
        [(ref_a, name_a, INK), (ref_b, name_b, KEY_RED)],
        y_title=y_title, **kw)


def raw_window_refs(raw_ws, block, n=12):
    """Build (dates_ref, values_ref) for the trailing `n` observations of a
    raw block. Assumes the project's fixed-anchor layout: dates in col A,
    values in col B, newest at block.first_data_row.

        block : the runner.RawBlock for the series
        n     : how many trailing quarters to chart
    """
    r0 = block.first_data_row
    dates = Reference(raw_ws, min_col=1, min_row=r0, max_row=r0 + n - 1)
    vals  = Reference(raw_ws, min_col=2, min_row=r0, max_row=r0 + n - 1)
    return dates, vals


# --- sparklines -------------------------------------------------------------
# openpyxl cannot write Excel's native sparklines. Two supported routes:
#   1) Let the "Extract & Run" macro add them after the data lands (preferred):
#        Range("J9:J40").SparklineGroups.Add Type:=xlSparkLine, _
#            SourceData:="Raw_Consumer!B<r0>:B<r0+7>"
#        With Range("J9").SparklineGroups.Item(1)
#            .SeriesColor.Color = RGB(87, 83, 75)      ' SLATE
#            .Points.Markers.Visible = False
#            .Points.Highlight(xlSparkColumnLast).Visible = True
#            .Points.Highlight(xlSparkColumnLast).Color.Color = RGB(204, 0, 0) ' KEY_RED on last
#        End With
#   2) Or drop a tiny one-series trend_chart() per row (heavier, but pure Python).
def sparkline_vba_snippet(col_letter, first_row, last_row, source_sheet, src_col="B"):
    """Return a VBA snippet string to add KeyBank sparklines to a column.
    Append this into macro.bas / the _code_vba tab so the button paints them.
    """
    return (
        f'Range("{col_letter}{first_row}:{col_letter}{last_row}").SparklineGroups.Add _\n'
        f'    Type:=xlSparkLine, SourceData:="{source_sheet}!{src_col}{first_row}:{src_col}{last_row}"\n'
        f'With Range("{col_letter}{first_row}").SparklineGroups.Item(1)\n'
        f'    .SeriesColor.Color = RGB(87, 83, 75)\n'
        f'    .Points.Highlight(xlSparkColumnLast).Visible = True\n'
        f'    .Points.Highlight(xlSparkColumnLast).Color.Color = RGB(204, 0, 0)\n'
        f'End With'
    )
