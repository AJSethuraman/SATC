"""peers.fdic: the pull, its cache and the merger record, driven entirely by
fakes. No test here opens a socket: every fetch is a function in this file."""
import json
import urllib.parse

import pytest

from threshold_engine.peers import fdic


def params(url):
    """The query of a request URL, as a plain dict."""
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}


class FakeFinancials:
    """Serves ``n`` banks for any quarter, paging the way the API does."""

    def __init__(self, n, total=True):
        self.n, self.total, self.calls = n, total, []

    def __call__(self, url):
        self.calls.append(url)
        p = params(url)
        q = p["filters"].split(":")[1]
        start, limit = int(p["offset"]), int(p["limit"])
        rows = [{"data": {"CERT": c, "REPDTE": q, "LNCRCD": c * 10}}
                for c in range(start + 1, min(start + limit, self.n) + 1)]
        payload = {"data": rows}
        if self.total:
            payload["meta"] = {"total": self.n}
        return payload


def no_sleep(_):
    pass


def refuse(url):
    raise AssertionError("fetched %s although it is cached" % url)


# ------------------------------------------------------------- quarter list

def test_quarter_ends_runs_across_years():
    assert fdic.quarter_ends("2006Q3", "2007Q2") == ["20060930", "20061231", "20070331", "20070630"]
    assert fdic.quarter_ends("2026Q2", "2026Q2") == ["20260630"]
    assert len(fdic.quarter_ends("2006Q1", "2026Q2")) == 82
    assert len(fdic.quarter_ends("1992Q1", "2026Q2")) == 138


@pytest.mark.parametrize("first,last", [("2006Q5", "2007Q1"), ("2006-03-31", "2007Q1"),
                                        ("2007Q1", "2006Q4")])
def test_quarter_ends_refuses_bad_labels_and_backwards_ranges(first, last):
    with pytest.raises(ValueError):
        fdic.quarter_ends(first, last)


# ------------------------------------------------------------- pagination

def test_pull_pages_past_10000_rows(tmp_path):
    fake = FakeFinancials(23456)
    data = fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=fake, sleep=no_sleep)
    rows = data["20240331"]
    assert len(rows) == 23456
    assert [params(u)["offset"] for u in fake.calls] == ["0", "10000", "20000"]
    assert {params(u)["limit"] for u in fake.calls} == {"10000"}
    assert params(fake.calls[0])["fields"] == "CERT,REPDTE,LNCRCD"
    assert params(fake.calls[0])["filters"] == "REPDTE:20240331"
    assert params(fake.calls[0])["format"] == "json"
    assert (params(fake.calls[0])["sort_by"], params(fake.calls[0])["sort_order"]) == ("CERT", "ASC")
    assert fake.calls[0].startswith(fdic.FINANCIALS_URL + "?")
    assert [r["CERT"] for r in rows] == list(range(1, 23457))      # no gaps, no repeats


def test_pull_exactly_10000_asks_once_more_and_stops_on_the_empty_page(tmp_path):
    fake = FakeFinancials(10000)
    rows = fdic.pull(["20240331"], ["LNCRCD"], tmp_path, fetch=fake, sleep=no_sleep)["20240331"]
    assert len(rows) == 10000 and len(fake.calls) == 2


def test_pull_refuses_rows_short_of_the_stated_total(tmp_path):
    def short(url):
        return {"data": [{"data": {"CERT": 1, "REPDTE": "20240331"}}], "meta": {"total": 5}}
    with pytest.raises(RuntimeError, match="stated 5 rows"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=short, sleep=no_sleep)
    assert not (tmp_path / "q20240331.json").exists()


def test_pull_refuses_rows_beyond_the_stated_total(tmp_path):
    def over(url):
        return {"data": [{"data": {"CERT": c, "REPDTE": "20240331"}} for c in (1, 2, 3)],
                "meta": {"total": 2}}
    with pytest.raises(RuntimeError, match="more than 2 rows"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=over, sleep=no_sleep)
    assert not (tmp_path / "q20240331.json").exists()


def test_pull_refuses_overlapping_pages_even_when_the_count_adds_up(tmp_path):
    """Page two repeats CERT 10000 and loses 10002: the count still says 10002."""
    def overlap(url):
        certs = range(1, 10001) if params(url)["offset"] == "0" else (10000, 10001)
        return {"data": [{"data": {"CERT": c, "REPDTE": "20240331", "LNCRCD": 1}} for c in certs],
                "meta": {"total": 10002}}
    with pytest.raises(RuntimeError, match="CERT 10000 arrived twice"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=overlap, sleep=no_sleep)
    assert not (tmp_path / "q20240331.json").exists()


def test_pull_refuses_a_total_that_changes_between_pages(tmp_path):
    def moving(url):
        first = params(url)["offset"] == "0"
        certs = range(1, 10001) if first else (10001,)
        return {"data": [{"data": {"CERT": c, "REPDTE": "20240331", "LNCRCD": 1}} for c in certs],
                "meta": {"total": 10001 if first else 1}}
    with pytest.raises(RuntimeError, match="stated 10001 rows .* then 1 on a later page"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=moving, sleep=no_sleep)


def test_pull_reads_a_total_given_as_a_value_object(tmp_path):
    def es(url):
        return {"data": [{"data": {"CERT": 1, "REPDTE": "20240331", "LNCRCD": 1}}],
                "meta": {"total": {"value": 2, "relation": "eq"}}}
    with pytest.raises(RuntimeError, match="stated 2 rows"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=es, sleep=no_sleep)


def test_paging_that_never_ends_is_stopped(tmp_path, monkeypatch):
    """An API that keeps sending full pages and states no total would page forever."""
    monkeypatch.setattr(fdic, "MAX_ROWS", 25000)
    calls = []

    def endless(url):
        calls.append(url)
        base = int(params(url)["offset"])
        return {"data": [{"data": {"CERT": base + c, "REPDTE": "20240331"}} for c in range(10000)]}
    with pytest.raises(RuntimeError, match="paging is not ending"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=endless, sleep=no_sleep)
    assert len(calls) == 3


def test_fields_are_asked_for_once_each(tmp_path):
    fake = FakeFinancials(2)
    fdic.pull(["20240331"], "LNCRCD, LNCRCD,CERT,,REPDTE", tmp_path, fetch=fake, sleep=no_sleep)
    assert params(fake.calls[0])["fields"] == "CERT,REPDTE,LNCRCD"


@pytest.mark.parametrize("q", ["2024Q1", "20240401", "../../evil", "2024033"])
def test_pull_refuses_a_quarter_that_is_not_a_quarter_end(tmp_path, q):
    with pytest.raises(ValueError, match="quarter-end"):
        fdic.pull([q], "LNCRCD", tmp_path, fetch=refuse, sleep=no_sleep)
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------- unpublished quarter
#
# Real API, 12 Oct 2026: REPDTE 20260930 returned {"meta": {"total": 0}, "data": []}.

def unpublished(url):
    return {"data": [], "meta": {"total": 0}}


def test_an_unpublished_quarter_is_refused_and_not_cached(tmp_path):
    with pytest.raises(RuntimeError, match="no filers for 20260930"):
        fdic.pull(["20260930"], "LNCRCD", tmp_path, fetch=unpublished, sleep=no_sleep)
    assert list(tmp_path.iterdir()) == []
    fake = FakeFinancials(3)                          # once it is published, it is fetched
    assert len(fdic.pull(["20260930"], "LNCRCD", tmp_path, fetch=fake, sleep=no_sleep)["20260930"]) == 3
    assert len(fake.calls) == 1


def test_refresh_against_an_unpublished_answer_keeps_the_good_cache(tmp_path):
    fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=FakeFinancials(4), sleep=no_sleep)
    with pytest.raises(RuntimeError, match="not published"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=unpublished, refresh=True, sleep=no_sleep)
    assert len(json.loads((tmp_path / "q20240331.json").read_text(encoding="utf-8"))) == 4


def test_an_empty_cached_quarter_is_refused_not_read_as_complete(tmp_path):
    (tmp_path / "q20260930.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="holds no filers"):
        fdic.pull(["20260930"], "LNCRCD", tmp_path, fetch=refuse, sleep=no_sleep)


# ------------------------------------------------------------- retry

def test_pull_retries_with_growing_waits_then_succeeds(tmp_path):
    fake, waits, fails = FakeFinancials(3), [], [2]

    def flaky(url):
        if fails[0]:
            fails[0] -= 1
            raise OSError("connection reset")
        return fake(url)

    rows = fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=flaky, sleep=waits.append)
    assert len(rows["20240331"]) == 3
    assert waits == [5, 10]


def test_a_cut_off_json_body_is_retried_too(tmp_path):
    fake, fails = FakeFinancials(3), [1]

    def truncated(url):
        if fails[0]:
            fails[0] -= 1
            return json.loads('{"data": [')               # raises a ValueError
        return fake(url)

    assert len(fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=truncated,
                         sleep=no_sleep)["20240331"]) == 3


def test_pull_raises_after_the_fourth_failure_and_writes_nothing(tmp_path):
    calls, waits = [], []

    def down(url):
        calls.append(url)
        raise OSError("timed out")

    with pytest.raises(OSError, match="timed out"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=down, sleep=waits.append)
    assert len(calls) == 4
    assert waits == [5, 10, 15]
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------- cache

def test_cache_is_written_and_never_fetched_again(tmp_path):
    qs = fdic.quarter_ends("2024Q1", "2024Q2")
    first = fdic.pull(qs, "LNCRCD", tmp_path, fetch=FakeFinancials(4), sleep=no_sleep)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["q20240331.json", "q20240630.json"]
    again = fdic.pull(qs, "LNCRCD", tmp_path, fetch=refuse, sleep=no_sleep)
    assert again == first


def test_only_the_missing_quarter_is_fetched(tmp_path):
    fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=FakeFinancials(4), sleep=no_sleep)
    fake = FakeFinancials(6)
    data = fdic.pull(["20240331", "20240630"], "LNCRCD", tmp_path, fetch=fake, sleep=no_sleep)
    assert {params(u)["filters"] for u in fake.calls} == {"REPDTE:20240630"}
    assert len(data["20240331"]) == 4 and len(data["20240630"]) == 6


def test_refresh_fetches_again_and_overwrites(tmp_path):
    fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=FakeFinancials(4), sleep=no_sleep)
    fake = FakeFinancials(7)
    data = fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=fake, refresh=True, sleep=no_sleep)
    assert len(fake.calls) == 1 and len(data["20240331"]) == 7
    on_disk = json.loads((tmp_path / "q20240331.json").read_text(encoding="utf-8"))
    assert len(on_disk) == 7
    assert not list(tmp_path.glob("*.part"))


def test_the_cache_folder_is_made_with_its_parents(tmp_path):
    cache = tmp_path / "a" / "b"
    fdic.pull(["20240331"], "LNCRCD", cache, fetch=FakeFinancials(2), sleep=no_sleep)
    assert (cache / "q20240331.json").exists()


def test_a_crash_while_writing_leaves_no_quarter_behind(tmp_path, monkeypatch):
    real = type(tmp_path).write_text

    def half(self, text, *a, **k):
        real(self, text[:10], *a, **k)
        raise OSError("disk full")
    monkeypatch.setattr(type(tmp_path), "write_text", half)
    with pytest.raises(OSError, match="disk full"):
        fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=FakeFinancials(4), sleep=no_sleep)
    assert not (tmp_path / "q20240331.json").exists()


def test_a_field_some_rows_carry_is_read(tmp_path):
    """Refused only when NO row has the field: a bank that does not file it is normal."""
    rows = [{"CERT": 1, "REPDTE": "20240331", "LNAUTO": 5}, {"CERT": 2, "REPDTE": "20240331"}]
    (tmp_path / "q20240331.json").write_text(json.dumps(rows), encoding="utf-8")
    assert fdic.pull(["20240331"], "LNAUTO", tmp_path, fetch=refuse, sleep=no_sleep)["20240331"] == rows


def test_a_cache_pulled_for_other_fields_is_refused_not_read_as_zeros(tmp_path):
    fdic.pull(["20240331"], "LNCRCD", tmp_path, fetch=FakeFinancials(4), sleep=no_sleep)
    with pytest.raises(ValueError, match="LNAUTO"):
        fdic.pull(["20240331"], "LNCRCD,LNAUTO", tmp_path, fetch=refuse, sleep=no_sleep)


# ------------------------------------------------------------- mergers

def hist(code, acq, eff, out="99", id=None):
    return {"CERT": acq, "CHANGECODE": code, "ACQ_CERT": acq, "OUT_CERT": out,
            "EFFDATE": eff + "T00:00:00", "CHANGECODE_DESC": "x",
            "ID": id or "%s_%s_%s_%s" % (eff, code, acq, out)}


def test_quarter_end_of_an_effective_date():
    assert fdic.quarter_end("2022-10-03") == "2022-12-31"
    assert fdic.quarter_end("2022-07-01") == "2022-09-30"
    assert fdic.quarter_end("2023-03-26") == "2023-03-31"
    assert fdic.quarter_end("2023-06-30") == "2023-06-30"


def test_classify_keeps_allowlisted_acquisitions_by_quarter():
    rows = [hist(223, "4297", "2022-10-03", "33954"),       # Capital One, the 670% quarter
            hist(216, "11063", "2023-03-26"),               # First Citizens, SVB bridge bank
            hist(221, "4297", "2022-11-15", "77"),          # same quarter again: listed once
            hist(224, "4297", "2019-01-02")]
    assert fdic.classify(rows) == {"11063": ["2023-03-31"],
                                   "4297": ["2019-03-31", "2022-12-31"]}


def test_classify_ignores_codes_outside_the_allowlist():
    rows = [hist(712, "6384", "2020-05-01"),     # branch purchase: named, not a bank
            hist(810, "6384", "2020-05-01"),     # the mirror entry
            hist(520, "6384", "2020-05-01"),     # on neither list
            hist("nonsense", "6384", "2020-05-01"),
            hist(223, "", "2020-05-01"),         # no acquirer named
            hist(223, "6384", ""),               # no date
            hist(223, "6384", "2020-13-01"),     # no such month
            hist(223, "6384", "2020-00-01")]
    assert fdic.classify(rows) == {}
    # An allowlisted row that cannot be placed is reported with the unknown codes,
    # as credit-suite's ``unclassified`` does, not dropped without a word.
    assert [(r["CHANGECODE"], r["ACQ_CERT"], r["EFFDATE"][:10]) for r in fdic.unrecognised(rows)] == [
        (520, "6384", "2020-05-01"), ("nonsense", "6384", "2020-05-01"),
        (223, "", "2020-05-01"), (223, "6384", "T00:00:00"),
        (223, "6384", "2020-13-01"), (223, "6384", "2020-00-01")]


def test_classify_accepts_the_acquirer_as_a_number_as_the_api_sends_it():
    row = dict(hist(223, "x", "2008-09-05"), ACQ_CERT=18113)
    assert fdic.classify([row]) == {"18113": ["2008-09-30"]}
    assert fdic.unrecognised([row]) == []


@pytest.mark.parametrize("bad", ["2022-13-01", "2022-00-01", "2022-02-30", "20221003"])
def test_quarter_end_refuses_a_date_that_is_not_one(bad):
    with pytest.raises(ValueError, match="2022-10-03"):
        fdic.quarter_end(bad)


def test_allowlist_is_credit_suites_plus_215():
    # credit-suite's list, plus 215 (decided here 12 Oct 2026, LOG.md).
    assert sorted(fdic.ACQUISITIONS) == [211, 215, 216, 217, 221, 222, 223, 224]
    assert sorted(fdic.NOT_AN_ACQUISITION) == [712, 810, 811, 812]
    assert fdic.FIELDS == "CERT,EFFDATE,CHANGECODE,CHANGECODE_DESC,ACQ_CERT,OUT_CERT,OUT_NAME,PROCDATE"


class FakeHistory:
    """Serves history rows for any query, paging the way the API does."""

    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def __call__(self, url):
        self.calls.append(url)
        p = params(url)
        start = int(p["offset"])
        return {"data": [{"data": r} for r in self.rows[start:start + int(p["limit"])]],
                "meta": {"total": len(self.rows)}}


def test_pull_mergers_asks_for_every_code_naming_an_acquirer_pages_and_classifies():
    rows = [hist(223, str(1000 + i), "2010-%02d-15" % (i % 12 + 1)) for i in range(10003)]
    rows += [hist(712, "6384", "2020-05-01"), hist(810, "6384", "2020-05-01")]
    fake = FakeHistory(rows)
    out = fdic.pull_mergers("2005-10-01", fetch=fake, sleep=no_sleep)
    assert len(fake.calls) == 2
    p = params(fake.calls[0])
    assert fake.calls[0].startswith(fdic.HISTORY_URL + "?")
    # Not narrowed to the allowlist: an unknown code has to arrive to be seen.
    assert p["filters"] == "EFFDATE:[2005-10-01 TO *] AND ACQ_CERT:[1 TO *]"
    assert p["fields"] == fdic.FIELDS + ",ID"
    assert (p["sort_by"], p["sort_order"], p["format"]) == ("EFFDATE", "ASC", "json")
    assert len(out) == 10003
    assert out["1000"] == ["2010-03-31"] and out["1005"] == ["2010-06-30"]


def test_pull_mergers_refuses_a_code_on_neither_list_and_names_it():
    # A code neither list names (215 was one, live, on 12 Oct 2026, until it
    # was decided): it has to stop the pull, not vanish.
    rows = [hist(223, "4297", "2022-10-03"),
            dict(hist(520, "18113", "2008-09-05"), CHANGECODE_DESC="Something new"),
            hist(223, "", "2019-01-02")]
    with pytest.raises(RuntimeError) as err:
        fdic.pull_mergers("2005-10-01", fetch=FakeHistory(rows), sleep=no_sleep)
    msg = str(err.value)
    assert "2 FDIC history row(s)" in msg
    assert "code 520 (Something new), acquirer 18113, effective 2008-09-05" in msg
    assert "code 223 (x), acquirer not named, effective 2019-01-02" in msg


def test_pull_mergers_refuses_a_history_row_arriving_twice():
    rows = [hist(223, str(i), "2010-01-15", id="row%d" % i) for i in range(10001)]
    rows[10000] = rows[9999]                         # the last page repeats a row
    with pytest.raises(RuntimeError, match="ID row9999 arrived twice"):
        fdic.pull_mergers("2005-10-01", fetch=FakeHistory(rows), sleep=no_sleep)


@pytest.mark.parametrize("since", ["2005Q4", "2005-13-45"])
def test_pull_mergers_refuses_a_bad_date(since):
    with pytest.raises(ValueError):
        fdic.pull_mergers(since, fetch=refuse, sleep=no_sleep)


def test_a_failure_with_several_acquirers_marks_each_acquirer():
    # 215 as the live API returned it on 12 Oct 2026.
    rows = [hist(215, "18113", "2008-09-05"), hist(215, "2448", "2008-09-19")]
    out = fdic.pull_mergers("2005-10-01", fetch=FakeHistory(rows), sleep=no_sleep)
    assert out == {"18113": ["2008-09-30"], "2448": ["2008-09-30"]}
