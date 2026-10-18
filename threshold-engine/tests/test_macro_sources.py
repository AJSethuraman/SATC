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
