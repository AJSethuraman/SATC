"""The readers of each publisher's file: numbers in, gaps kept as gaps.

The case that matters most is the October 2025 hole in BLS data. FRED prints
"." there and BLS prints "-(9)"; read as zero, it would be the lowest
unemployment rate in the series' history and the strongest outlier the tool
could find.
"""
import io
import zipfile

import pytest

from threshold_engine.macro import sources
from threshold_engine.macro.catalog import BY_KEY


def test_fred_keeps_dot_and_blank_as_missing_not_zero():
    raw = b"observation_date,UNRATE\n2025-09-01,4.4\n2025-10-01,.\n2025-11-01,\n2025-12-01,4.4\n"
    pts = sources.read_fred(raw, "UNRATE")
    assert pts == [("2025-09-01", 4.4), ("2025-10-01", None), ("2025-11-01", None), ("2025-12-01", 4.4)]
    assert all(v != 0 for _, v in pts)


def test_fred_refuses_a_file_for_another_series():
    with pytest.raises(ValueError, match="not a FRED file for UNRATE"):
        sources.read_fred(b"observation_date,ICSA\n2026-10-03,197000\n", "UNRATE")


def _bls_page(rows, sid="CUSR0000SETE"):
    body = "".join('<TR><TH scope="row">%s</TH>%s</TR>' % (y, "".join("<TD>%s</TD>" % c for c in cells))
                   for y, cells in rows)
    return ("<html>Series Id: %s <table id=\"table0\"><TBODY>%s</TBODY></table></html>" % (sid, body)).encode()


def test_bls_dash_and_inner_blank_are_missing_trailing_blanks_are_unpublished():
    page = _bls_page([("2025", ["1"] * 9 + ["-(9)", "", "2"]),
                      ("2026", ["4.3(12)", "3", "&nbsp;"] + [""] * 9)])
    pts = dict(sources.read_bls(page, "CUSR0000SETE"))
    assert pts["2025-10-01"] is None          # the dash with footnote 9
    assert pts["2025-11-01"] is None          # blank between two numbers
    assert pts["2026-01-01"] == 4.3           # footnote mark stripped, number kept
    assert "2026-03-01" not in pts            # after the last number: not published yet
    assert max(pts) == "2026-02-01"


def test_bls_refuses_another_page():
    with pytest.raises(ValueError, match="not the BLS page"):
        sources.read_bls(_bls_page([("2025", ["1"] * 12)], sid="LNS14000000"), "CUSR0000SETE")


def test_fed_ebp_column_and_refusal():
    raw = b"date,gz_spread,ebp,est_prob\n1990-08-01,1.2,0.3,0.4\n1990-09-01,1.3,,0.5\n"
    assert sources.read_fed_ebp(raw, "ebp") == [("1990-08-01", 0.3), ("1990-09-01", None)]
    with pytest.raises(ValueError, match="no column"):
        sources.read_fed_ebp(raw, "spread")


def _nmdb_zip(rows):
    head = "SOURCE,FREQUENCY,GEOLEVEL,GEOID,GEONAME,MARKET,PERIOD,YEAR,QUARTER,MONTH,SUPPRESSED,SERIESID,VALUE1\n"
    body = "".join("NMDB,Quarterly,National,%s,x,%s,p,%s,%s,m,%s,%s,%s\n" % r for r in rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("nmdb.csv", head + body)
    return buf.getvalue()


def test_fhfa_selects_one_market_and_series_and_keeps_suppressed_as_missing():
    raw = _nmdb_zip([("USA", "All Mortgages", 2002, 2, 0, "P90DL", "0.9"),
                     ("USA", "All Mortgages", 2002, 1, 0, "P90DL", "0.8"),
                     ("USA", "All Mortgages", 2002, 3, 1, "P90DL", "0.7"),
                     ("USA", "All Mortgages", 2002, 1, 0, "P3089DL", "2.3"),
                     ("USA", "Government / Non-Conventional", 2002, 1, 0, "P90DL", "2.0")])
    assert sources.read_fhfa_nmdb(raw, "USA|All Mortgages|P90DL") == [
        ("2002-01-01", 0.8), ("2002-04-01", 0.9), ("2002-07-01", None)]


def test_every_catalog_source_has_a_reader_and_an_address():
    for s in BY_KEY.values():
        assert s.source in sources.READERS
        assert sources.url_for(s, "2026").startswith("https://")


def sce_workbook(rows, sheet="Delinquency expectations",
                 title="Mean probability of missing minimum debt payment over the next three months"):
    """The NY Fed's SCE workbook as it is laid out: four rows of source and title, then month and mean."""
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.active.title = "Disclaimer"
    ws = wb.create_sheet(sheet)
    ws.append(["Source:  Survey of Consumer Expectations, (c) 2013-26 Federal Reserve Bank of New York (FRBNY)."])
    ws.append(["Debt delinquency expectations"])
    ws.append([None])
    ws.append([None, title])
    for r in rows:
        ws.append(list(r))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def test_sce_reads_each_month_and_keeps_a_blank_month_missing():
    raw = sce_workbook([(201306, 13.408), (201307, None), (201308, "."), (201309, 12.2)])
    pts = sources.read(BY_KEY["expected_missed_payment"], raw)
    assert pts == [("2013-06-01", 13.408), ("2013-07-01", None), ("2013-08-01", None), ("2013-09-01", 12.2)]


def test_sce_refuses_a_workbook_without_the_sheet_or_with_another_question_in_it():
    with pytest.raises(ValueError, match="no sheet"):
        sources.read_nyfed_sce(sce_workbook([(201306, 13.4)], sheet="Inflation expectations"),
                               "Delinquency expectations")
    # Another question laid out the same way is never read as this one.
    with pytest.raises(ValueError, match="does not hold"):
        sources.read_nyfed_sce(sce_workbook([(201306, 3.1)], title="Median one-year-ahead expected inflation rate"),
                               "Delinquency expectations")
    with pytest.raises(ValueError, match="not the NY Fed's SCE workbook"):
        sources.read_nyfed_sce(b"<html>We'll be back soon!</html>", "Delinquency expectations")


def test_sce_refuses_a_number_that_is_not_a_month():
    with pytest.raises(ValueError, match="201313 where a month belongs"):
        sources.read_nyfed_sce(sce_workbook([(201312, 13.4), (201313, 13.5)]), "Delinquency expectations")


HHDC_COLUMNS = ["Mortgage", "HE Revolving", "Auto Loan", "Credit Card", "Student Loan", "Other", "Total"]


def hhdc_workbook(rows, sheet="Page 3 Data", title="Total Debt Balance and Its Composition", unit="Trillions of $",
                  columns=HHDC_COLUMNS):
    """The NY Fed's household debt workbook as it is laid out on 22 Oct 2026: a contents sheet, then on Page 3
    Data the title, the unit, a link back, the heading row, and one row a quarter as 03:Q1."""
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.active.title = "TABLE OF CONTENTS"
    ws = wb.create_sheet(sheet)
    ws.append([title])
    ws.append([unit])
    ws.append(["Return to Table of Contents"])
    ws.append([None] + list(columns))
    for r in rows:
        ws.append(list(r))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def hhdc_page(*quarters):
    """The household debt report's page, with a Data link for each quarter named."""
    return "".join('<a class="glossary-download" href="/medialibrary/interactives/householdcredit/data/xls/'
                   'HHD_C_Report_%s">Data</a>' % q for q in quarters).encode()


def test_household_debt_reads_each_type_by_its_heading_and_keeps_a_blank_quarter_missing():
    raw = hhdc_workbook([("25:Q4", 13.17, 0.4336, 1.667, 1.277, 1.664, 0.5641, 18.7757),
                         ("26:Q1", 13.191, 0.446, None, 1.242, 1.658, 0.562, 18.784),
                         ("26:Q2", 13.117, 0.4585, 1.713, 1.263, 1.651, 0.568, 18.7705)])
    assert sources.read(BY_KEY["household_credit_card"], raw) == [
        ("2025-10-01", 1.277), ("2026-01-01", 1.242), ("2026-04-01", 1.263)]
    assert sources.read(BY_KEY["household_auto"], raw)[1] == ("2026-01-01", None)
    assert sources.read(BY_KEY["household_total"], raw)[-1] == ("2026-04-01", 18.7705)


def test_household_debt_refuses_another_sheet_another_table_or_a_missing_type():
    row = [("26:Q2", 13.1, 0.4, 1.7, 1.2, 1.6, 0.5, 18.7)]
    with pytest.raises(ValueError, match="no sheet"):
        sources.read_nyfed_hhdc(hhdc_workbook(row, sheet="Page 4 Data"), "Mortgage")
    # The next table in the workbook is laid out the same way and is never read as this one.
    with pytest.raises(ValueError, match="is not"):
        sources.read_nyfed_hhdc(hhdc_workbook(row, title="Number of Accounts by Loan Type",
                                              unit="Millions"), "Mortgage")
    with pytest.raises(ValueError, match="no column 'Credit Card'"):
        sources.read_nyfed_hhdc(hhdc_workbook([r[:4] for r in row], columns=HHDC_COLUMNS[:3]), "Credit Card")
    with pytest.raises(ValueError, match="not the NY Fed's household debt workbook"):
        sources.read_nyfed_hhdc(b"<html>Page Not Found</html>", "Mortgage")


def test_household_debt_refuses_quarters_out_of_order():
    with pytest.raises(ValueError, match="not in order"):
        sources.read_nyfed_hhdc(hhdc_workbook([("26:Q2", 1, 1, 1, 1, 1, 1, 6), ("26:Q1", 1, 1, 1, 1, 1, 1, 6)]),
                                "Mortgage")


def test_the_household_debt_file_is_the_newest_the_reports_page_links():
    # The file is named for the quarter it runs to; a name guessed for the next quarter was served as a page of
    # HTML with status 200 (22 Oct 2026), so the address is read from the report's own page.
    assert sources.hhdc_file(hhdc_page("2025Q4", "2026Q2", "2026Q1")) == (
        "https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/HHD_C_Report_2026Q2")
    with pytest.raises(ValueError, match="links no data file"):
        sources.hhdc_file(b"<html><a href='/microeconomics/hhdc'>Household debt</a></html>")
