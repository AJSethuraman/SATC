"""The pull: dated folders, nothing overwritten, failures recorded, no network."""
import io
import json
import urllib.request
import zipfile

import pytest

from threshold_engine.macro import pull as P
from threshold_engine.macro.catalog import SERIES


def _fake(fail=()):
    calls = []
    nmdb = io.BytesIO()
    with zipfile.ZipFile(nmdb, "w") as z:
        z.writestr("n.csv", "SOURCE,FREQUENCY,GEOLEVEL,GEOID,GEONAME,MARKET,PERIOD,YEAR,QUARTER,MONTH,SUPPRESSED,"
                   "SERIESID,VALUE1\n" + "".join(
                       "NMDB,Q,N,USA,US,%s,p,2002,1,03,0,%s,1.0\n" % (m, s)
                       for m in ("All Mortgages", "Government / Non-Conventional") for s in ("P3089DL", "P90DL")))

    def fetcher(url):
        calls.append(url)
        if any(f in url for f in fail):
            raise OSError("refused")
        if "fredgraph" in url:
            sid = url.split("id=")[1]
            return ("observation_date,%s\n2025-09-01,1\n2025-10-01,.\n2025-11-01,2\n" % sid).encode()
        if "ebp_csv" in url:
            return b"date,gz_spread,ebp,est_prob\n2026-08-01,1,0.1,0.2\n"
        if "nmdb" in url:
            return nmdb.getvalue()
        if "newyorkfed.org" in url:
            from test_macro_sources import sce_workbook
            return sce_workbook([(202607, 12.0), (202608, 13.2), (202609, 12.2)])
        if "data.bls.gov" in url:
            return ('Series Id: CUSR0000SETE <table id="table0"><TR><TH scope="row">2025</TH>'
                    + "<TD>1</TD>" * 9 + "<TD>-(9)</TD><TD></TD><TD>2</TD></TR></table>").encode()
        raise AssertionError(url)
    return fetcher, calls


def test_pull_writes_a_dated_folder_with_a_manifest(tmp_path):
    f, calls = _fake()
    m = P.pull(tmp_path, today="2026-10-15", fetcher=f)
    assert m["failed"] == []
    assert len(m["series"]) == len(SERIES)
    u = m["series"]["unemployment"]
    assert u["missing_after_first"] == ["2025-10-01"] and u["last"] == "2025-11-01"
    assert m["series"]["motor_insurance"]["missing_after_first"] == ["2025-10-01", "2025-11-01"]
    on_disk = json.loads((tmp_path / "2026-10-15" / "manifest.json").read_text())
    assert on_disk["files"]["fred-UNRATE.csv"]["sha256"] and on_disk["files"]["fred-UNRATE.csv"]["bytes"] > 0


def test_a_shared_file_is_downloaded_once(tmp_path):
    f, calls = _fake()
    P.pull(tmp_path, today="2026-10-15", fetcher=f)
    assert sum("ebp_csv" in c for c in calls) == 1     # three series read the Fed's one file
    assert sum("nmdb" in c for c in calls) == 1


def test_one_failure_is_recorded_and_the_rest_still_pull(tmp_path):
    f, _ = _fake(fail=("id=ICSA",))
    m = P.pull(tmp_path, today="2026-10-15", fetcher=f)
    assert m["failed"] == ["initial_claims"]
    assert "refused" in m["series"]["initial_claims"]["error"]
    assert "error" not in m["series"]["unemployment"]


def test_an_earlier_pull_is_kept_and_the_newest_is_read(tmp_path):
    f, _ = _fake()
    P.pull(tmp_path, keys=["unemployment"], today="2026-10-14", fetcher=f)
    P.pull(tmp_path, keys=["unemployment"], today="2026-10-15", fetcher=f)
    assert (tmp_path / "2026-10-14" / "fred-UNRATE.csv").exists()
    points, vintage = P.load(tmp_path, "unemployment")
    assert vintage == "2026-10-15" and points[1] == ("2025-10-01", None)
    assert P.load(tmp_path, "unemployment", vintage="2026-10-14")[1] == "2026-10-14"


def test_an_unknown_key_is_refused_by_name(tmp_path):
    with pytest.raises(SystemExit, match="not in the catalog: nope"):
        P.pull(tmp_path, keys=["nope"], fetcher=_fake()[0])


def test_fred_is_asked_without_a_user_agent_and_the_fed_with_one(monkeypatch):
    seen = {}

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        seen[req.full_url.split("/")[2]] = req.get_header("User-agent")
        return R(b"x")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    P.fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE")
    P.fetch("https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv")
    assert seen["fred.stlouisfed.org"] is None
    assert seen["www.federalreserve.gov"].startswith("Mozilla/5.0")


def test_a_second_pull_the_same_day_gets_its_own_folder(tmp_path):
    # Walk, 16 Oct 2026 (W4): the second pull of a day replaced the first, so a
    # workbook made from the morning named a folder that no longer held its data.
    f, _ = _fake()
    first = P.pull(tmp_path, keys=["unemployment"], today="2026-10-16", fetcher=f)
    before = (tmp_path / "2026-10-16" / "manifest.json").read_text()
    second = P.pull(tmp_path, keys=["unemployment"], today="2026-10-16", fetcher=f)
    assert (first["pulled"], second["pulled"]) == ("2026-10-16", "2026-10-16-2")
    assert (tmp_path / "2026-10-16" / "manifest.json").read_text() == before
    assert P.latest(tmp_path).name == "2026-10-16-2"
    for _ in range(8):
        P.pull(tmp_path, keys=["unemployment"], today="2026-10-16", fetcher=f)
    assert P.latest(tmp_path).name == "2026-10-16-10"        # not -9, which sorts after it as text
    assert P.load(tmp_path, "unemployment")[1] == "2026-10-16-10"


def test_list_says_where_the_firms_directions_are_and_that_inputs_are_not_rated(capsys):
    # Walk (W2, W3): list printed "firm sets direction" after the firm had set
    # them, and said the same of two series that are never rated.
    from threshold_engine.macro.__main__ import main
    main(["list"])
    out = capsys.readouterr().out
    assert "firm sets direction" not in out
    assert out.count("the firm's settings") == 9
    assert all("input, not rated" in line for line in out.splitlines()
               if line.strip().startswith(("income_per_person", "treasury_10y")))
