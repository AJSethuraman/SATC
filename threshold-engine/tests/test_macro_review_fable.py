"""The blank-context review of 17 Oct 2026: nine findings, each a test that failed against the code as it
stood, written by a Fable session that had never seen the tool (PR #452; its branch fable/macro-adversarial
and draft PR #453 hold the originals and the report). Taken back by hand, fixed, and moved here so nothing
puts them back. Each docstring is the reviewer's, describing the fault as found.
"""
import hashlib
import re
import zipfile

import pytest

from threshold_engine.macro import pull as P
from threshold_engine.macro import rate as R
from threshold_engine.macro import settings as S
from threshold_engine.macro.catalog import BY_KEY, LOWER
from threshold_engine.macro.compare import compare

from test_macro_pull import _fake
from test_macro_rate import _fetcher, cache                       # noqa: F401  (the fixture: a pull on disk)
from test_macro_settings import answered


# ---------------------------------------------------------------------------------------------------------------
# 1. The pull
# ---------------------------------------------------------------------------------------------------------------

def test_a_file_the_pull_could_not_read_leaves_its_readings_not_rated_rather_than_crashing_the_rating(tmp_path):
    """A download that is not what the publisher usually serves (here FHFA's zip replaced by an HTML
    error page, which a server does on a bad day) is recorded by the pull as "could not read", and
    TOOL.md promises "a failure is recorded and the rest still pull". The rating should then list the
    three FHFA readings under Not rated with that reason. Instead ``rate_all`` raises ``BadZipFile``:
    ``Pull._get`` catches only ``SystemExit``, ``ValueError`` and ``OSError``, and the zip reader raises
    neither. One bad file stops every rating, and the workbook with it. (DESIGN-PRINCIPLES: unknown is a
    third answer; refuse visibly, never crash.)"""
    f, _ = _fake()

    def fetcher(url):
        if "nmdb" in url:
            return b"<html><body>Service unavailable</body></html>"
        return f(url)
    m = P.pull(tmp_path, keys=["mortgage_90", "unemployment"], today="2026-10-17", fetcher=fetcher)
    assert "could not read" in m["series"]["mortgage_90"]["error"]        # the pull knew
    result = R.rate_all(tmp_path, S.check(answered()))                     # so the rating must not crash
    why = {(x["key"], x["reading"]): x["why"] for x in result["not_rated"]}
    assert ("mortgage_90", "position") in why
    assert "could not read" in why[("mortgage_90", "position")]
    assert any(r["key"] == "unemployment" for r in result["ratings"])      # and the rest is still rated


def test_a_refused_pull_leaves_the_cache_as_it_was(tmp_path):
    """``pull`` with a key that is not in the catalog refuses by name, which is right. But it makes the
    day's folder before it checks the keys, so the refusal leaves an empty ``2026-10-17`` behind. The
    next real pull that day then lands in ``2026-10-17-2``, ``rate --vintage 2026-10-17`` is refused
    ("no pull named 2026-10-17") although the day's data is right beside it, and the workbook names a
    vintage that does not match the day. A refused pull should write nothing."""
    f, _ = _fake()
    with pytest.raises(SystemExit, match="not in the catalog"):
        P.pull(tmp_path, keys=["unemployment", "nope"], today="2026-10-17", fetcher=f)
    assert sorted(p.name for p in tmp_path.iterdir()) == []               # nothing written
    m = P.pull(tmp_path, keys=["unemployment"], today="2026-10-17", fetcher=f)
    assert m["pulled"] == "2026-10-17"                                     # the day's first pull is the day's folder


def test_pulling_a_derived_reading_is_not_called_not_in_the_catalog(tmp_path):
    """``list`` prints ``mortgage_spread`` and ``house_price_to_income`` in the same column as every
    pullable key, under "Derived from two of the above". ``pull mortgage_spread`` answers "not in the
    catalog: mortgage_spread (list them with: ... list)", which sends the analyst back to the listing
    that shows it. A derived reading is in the catalog; the pull should fetch its inputs, or refuse
    saying it is made from ``mortgage_rate`` and ``treasury_10y`` and that those are what to pull."""
    f, _ = _fake()
    try:
        m = P.pull(tmp_path, keys=["mortgage_spread"], today="2026-10-17", fetcher=f)
    except SystemExit as e:
        msg = str(e)
        assert "not in the catalog" not in msg
        assert "mortgage_rate" in msg and "treasury_10y" in msg
    else:
        assert {"mortgage_rate", "treasury_10y"} <= set(m["series"])


# ---------------------------------------------------------------------------------------------------------------
# 2. Settings validation
# ---------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("reading,says", [
    ("position", "cpi position"),       # an answer to a question the tool never asks: CPI is rated on its change only
    ("chnage", "cpi chnage"),           # a misspelt reading name
])
def test_a_direction_for_a_reading_the_series_does_not_carry_is_refused_by_name(reading, says):
    """The settings refuse an unknown top-level key ("colour: not a setting the tool has") and a direction
    for a series the research already states ("unemployment: its direction is stated by the research").
    A direction for a *reading* a series does not carry passes in silence: ``cpi: {"position": ...}``
    is accepted although CPI's level is never rated, and so is a misspelt reading name. The firm can
    believe it has set how CPI's level is read when nothing reads it. Every other stray answer is
    named; this one should be too."""
    t = answered()
    t["directions"]["answer"]["cpi"][reading] = LOWER
    with pytest.raises(S.Refused) as e:
        S.check(t)
    assert says in str(e.value)


# ---------------------------------------------------------------------------------------------------------------
# 3. The ratings
# ---------------------------------------------------------------------------------------------------------------

def _quarterly(values, first_year=2000):
    return [("%d-%02d-01" % (first_year + i // 4, 3 * (i % 4) + 1), v) for i, v in enumerate(values)]


@pytest.mark.parametrize("reading,points,months,bad", [
    # a quarterly series under a 4-month horizon: no change can ever land on a quarter, so there is none
    ("change", _quarterly([float(i) for i in range(40)]), 4, "changes readings"),
    # a series whose every value the publisher left blank
    ("position", [("2026-01-01", None), ("2026-04-01", None)], 12, "values readings"),
])
def test_the_reason_a_reading_cannot_be_rated_reads_as_english_and_does_not_blame_the_pull(reading, points,
                                                                                            months, bad):
    """The reason a reading has no rating is printed by ``rate`` and written to the Not rated tab and
    the What if tab, where a reader meets it as prose. It reads "no changes readings in the pull" and
    "no values readings in the pull". Worse than the grammar: for a quarterly series under a horizon
    that is not a multiple of three months, the pull holds every quarter and the cause is the horizon,
    but the reason says the pull. The reason should read as a sentence and name the actual cause."""
    item = BY_KEY["house_prices"]
    s = S.check(answered(change_months=months))
    out, why = R.rate_reading(item, reading, points, s, LOWER)
    assert out is None
    assert bad not in why, why
    if reading == "change":
        assert "in the pull" not in why, why                        # the pull holds 40 quarters


# ---------------------------------------------------------------------------------------------------------------
# 4. The what-if
# ---------------------------------------------------------------------------------------------------------------

def test_a_change_rated_as_you_have_it_only_is_not_labelled_with_the_what_ifs_horizon(cache):  # noqa: F811
    """Codex found three branches that named a change with the wrong side's horizon, and each fix covered
    the branch in front of it. This is the fourth. Settings count the change over 6 months and rate
    CPI's change; the what-if counts over 12 months and does not rate it. The Ratings tab's What if
    cell reads "Change (what if: over 12 months): rated as you have it only": the only rating in that
    cell is the 6-month one, and the what-if, whose horizon it names, rated nothing. The cell should
    name the horizon of the rating it reports, or none."""
    from threshold_engine.macro.workbook import move_text
    b = answered(change_months=12)
    b["directions"]["answer"]["cpi"]["change"] = S.NOT_RATED
    pull = R.Pull(cache)
    ra = R.rate_all(cache, S.check(answered(change_months=6)), pull=pull)
    rb = R.rate_all(cache, S.check(b), pull=pull)
    c = compare(ra, rb, "settings.json", "what-if.json")
    row = next(x for x in c["rows"] if x["key"] == "cpi" and x["reading"] == "change")
    assert row["a"] and row["b"] is None and not row["same_measure"]
    words = move_text([row], c["months"])
    assert "rated as you have it only" in words
    assert "what if: over 12 months" not in words, words


# ---------------------------------------------------------------------------------------------------------------
# 5. The workbook
# ---------------------------------------------------------------------------------------------------------------

def test_a_series_with_no_rows_in_the_pull_does_not_crash_the_workbook_when_the_sahm_reading_is_shown(tmp_path):
    """A FRED file with a header and no observations is a series the pull holds and the rating cannot
    rate; it goes to Not rated ("no values ..."), and the workbook builds for every other series. For
    the unemployment rate with the Sahm reading shown, ``build`` instead raises ``IndexError`` in
    ``years_axis``: the Sahm chart is drawn from an empty list of dates. A tab with nothing to draw
    should say so, as the series tabs do for a series not in the pull, and the workbook should still
    be written."""
    openpyxl = pytest.importorskip("openpyxl")
    from threshold_engine.macro.workbook import build
    f = _fetcher()

    def fetcher(url):
        if "id=UNRATE" in url:
            return b"observation_date,UNRATE\n"
        return f(url)
    P.pull(tmp_path, keys=["unemployment", "cpi"], today="2026-10-17", fetcher=fetcher)
    result = R.rate_all(tmp_path, S.check(answered(show_sahm=True)))
    assert any(x["key"] == "unemployment" for x in result["not_rated"])
    out = build(str(tmp_path / "b.xlsx"), result, R.Pull(tmp_path))
    assert "Unemployment" in openpyxl.load_workbook(out).sheetnames


def test_the_sources_tab_fingerprints_the_file_the_rating_read(tmp_path):
    """The Sources tab's SHA-256 is described as the fingerprint of the file the rating read
    (``test_the_sources_sheet_fingerprints_every_file_the_pull_fetched``). It is copied from the
    manifest, written at pull time, and nothing compares it with the file. Change a file in the pull
    folder after the pull (here one row appended; opening a CSV in a spreadsheet and saving does as
    much) and the rating reads the changed file while the workbook publishes the old fingerprint. The
    tab should hash what was read, or the run should refuse a pull whose files no longer match its
    manifest. (DESIGN-PRINCIPLES: facts are recorded, not inferred; earn the claim.)"""
    openpyxl = pytest.importorskip("openpyxl")
    from threshold_engine.macro.workbook import build
    P.pull(tmp_path, keys=["unemployment"], today="2026-10-17", fetcher=_fetcher())
    path = tmp_path / "2026-10-17" / "fred-UNRATE.csv"
    with open(path, "a") as fh:
        fh.write("2026-10-01,2.0\n")                                # the file the rating will read
    result = R.rate_all(tmp_path, S.check(answered()))
    u = next(r for r in result["ratings"] if r["key"] == "unemployment" and r["reading"] == "position")
    assert u["date"] == "2026-10-01"                                 # it did read the changed file
    out = build(str(tmp_path / "b.xlsx"), result, R.Pull(tmp_path))
    ws = openpyxl.load_workbook(out)["Sources"]
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Unemployment rate")
    assert ws.cell(row, 10).value == hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_history_of_one_value_gets_a_chart_axis_with_a_span(tmp_path):
    """``nice_axis`` rounds a chart's value axis out to a tidy step. When every reading in a series is
    the same value and that value sits on the step (4.0, 0.0, 100.0), it returns the same number for
    bottom and top: an axis of no height, written to the chart as ``<c:min>`` equal to ``<c:max>``.
    Nothing can be drawn on it, and Excel does not accept a scaling whose minimum is not below its
    maximum. The axis should always span something."""
    pytest.importorskip("openpyxl")
    from threshold_engine.macro.workbook import build, nice_axis
    for v in (4.0, 0.0, 100.0):
        lo, hi, step = nice_axis(v, v)
        assert lo < hi, (v, lo, hi, step)
    f = _fetcher()

    def fetcher(url):
        if "id=UNRATE" in url:
            rows = ["observation_date,UNRATE"] + ["%d-%02d-01,4.0" % (2000 + i // 12, i % 12 + 1) for i in range(60)]
            return ("\n".join(rows) + "\n").encode()
        return f(url)
    P.pull(tmp_path, keys=["unemployment"], today="2026-10-17", fetcher=fetcher)
    result = R.rate_all(tmp_path, S.check(answered(show_sahm=False)))
    out = build(str(tmp_path / "b.xlsx"), result, R.Pull(tmp_path))
    with zipfile.ZipFile(out) as z:
        for n in z.namelist():
            if n.startswith("xl/charts/chart"):
                x = z.read(n).decode()
                for m in re.finditer(r'<c:scaling>.*?</c:scaling>', x, re.S):
                    lo = re.search(r'<c:min val="([^"]+)"/>', m.group(0))
                    hi = re.search(r'<c:max val="([^"]+)"/>', m.group(0))
                    if lo and hi:
                        assert float(lo.group(1)) < float(hi.group(1)), (n, m.group(0))
