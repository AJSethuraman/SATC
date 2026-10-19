"""A build stops if its merger list does not reach back as far as the history.

The firm, 18 Oct 2026, question 22 of the round 2 commercial docket ("agreed
with the recommendation", after the pictures: First Niagara 2016Q4 combined
against as filed, and two banks merged in 2004Q4 that a list from 2005 cannot
see): "The merger and absorption files record the date they start from; a
build whose first quarter is earlier refuses."

'peers pull --mergers SINCE' writes {"since": SINCE, "acquirers": ...} and
{"since": SINCE, "absorptions": [...]}; 'peers build' refuses a first
quarter that begins before either date, naming both, and refuses a file in
the earlier format (no date) with the command to pull it again. The build
here is test_new_charters.py's: KeyBank and Key Bank USA, 1994Q1 to 1997Q4,
public data.
"""
import json

import pytest

from conftest import ROOT
from threshold_engine import internal as I
from threshold_engine.peers import run
from test_new_charters import KEYBANK, KEY_USA, build, lay_out

PEERS = ROOT / "tests" / "data" / "peers"


def record(cache, mergers_since, absorptions_since):
    (cache / "mergers.json").write_text(json.dumps(
        {"since": mergers_since, "acquirers": {KEYBANK: ["2004-12-31"]}}), encoding="utf-8")
    (cache / "absorptions.json").write_text(json.dumps({"since": absorptions_since, "absorptions": [
        {"acquirer": KEYBANK, "absorbed": KEY_USA, "quarter": "2004-12-31"}]}), encoding="utf-8")


def test_a_quarter_starts_on_its_first_day():
    assert run.quarter_start("1994Q1") == "1994-01-01"
    assert run.quarter_start("2005Q4") == "2005-10-01"
    assert run.quarter_start("20060630") == "2006-04-01"


def test_a_record_from_the_first_day_of_the_first_quarter_builds(tmp_path, monkeypatch):
    cache = lay_out(tmp_path)
    record(cache, "1994-01-01", "1994-01-01")
    assert build(tmp_path, cache, monkeypatch) == 0


@pytest.mark.parametrize("which", ["mergers", "absorptions"])
def test_a_record_starting_a_day_later_is_refused_naming_both_dates(tmp_path, monkeypatch, capsys, which):
    cache = lay_out(tmp_path)
    record(cache, *(("1994-01-02", "1990-01-01") if which == "mergers" else ("1990-01-01", "1994-01-02")))
    assert build(tmp_path, cache, monkeypatch) == 2
    err = capsys.readouterr().err
    what = "the merger record" if which == "mergers" else "the absorptions record"
    assert ("the first quarter, 1994Q1, starts on 1994-01-01, before %s (%s.json) starts, on 1994-01-02"
            % (what, which)) in err
    assert "--mergers SINCE" in err
    assert not (tmp_path / "peers.xlsx").exists() and not (tmp_path / "series").exists()


@pytest.mark.parametrize("which", ["mergers", "absorptions"])
def test_a_record_in_the_earlier_format_is_refused_with_the_pull_to_run(tmp_path, monkeypatch, capsys, which):
    cache = lay_out(tmp_path)
    old = ({KEYBANK: ["2004-12-31"]} if which == "mergers"
           else [{"acquirer": KEYBANK, "absorbed": KEY_USA, "quarter": "2004-12-31"}])
    (cache / ("%s.json" % which)).write_text(json.dumps(old), encoding="utf-8")
    assert build(tmp_path, cache, monkeypatch) == 2
    err = capsys.readouterr().err
    assert "%s.json does not record the date" % which in err
    assert "Pull it again: 'peers pull --cache DIR" in err and "--mergers SINCE" in err


def test_the_picture_a_list_from_2005_under_a_1991_build_is_refused(tmp_path, monkeypatch, capsys):
    # The case the firm was shown: the record since 2005 read by a build from
    # 1991Q1 (question 6's measurement: 21 of KeyBank's kept windows mixed
    # two books, without a word). Here, 1994Q1 against a record from 2005.
    cache = lay_out(tmp_path)
    record(cache, "2005-01-01", "2005-01-01")
    assert build(tmp_path, cache, monkeypatch) == 2
    assert "before the merger record (mergers.json) starts, on 2005-01-01" in capsys.readouterr().err


def test_the_committed_fixtures_state_their_start():
    m = json.loads((PEERS / "mergers_roster.json").read_text(encoding="utf-8"))
    a = json.loads((PEERS / "absorptions_none.json").read_text(encoding="utf-8"))
    assert m["since"] == a["since"] == "2005-10-01" and a["absorptions"] == []
    assert min(d for v in m["acquirers"].values() for d in v) == "2006-03-31"
    assert run.load_mergers(PEERS / "mergers_roster.json", "2006Q1") == m["acquirers"]
    with pytest.raises(ValueError, match="starts on 2005-07-01"):
        run.load_mergers(PEERS / "mergers_roster.json", "2005Q3")


def test_internal_reconcile_reads_the_same_format_and_refuses_the_same_way(tmp_path):
    c = tmp_path / "c"
    c.mkdir()
    (c / I.ABSORPTIONS).write_text(json.dumps({"since": "2025-01-01", "absorptions": []}), encoding="utf-8")
    assert I.read_absorptions(c, "20250331") == []
    with pytest.raises(ValueError, match="starts on 2024-10-01.*internal pull"):
        I.read_absorptions(c, "20241231")
    (c / I.ABSORPTIONS).write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="does not record the date.*internal pull"):
        I.read_absorptions(c, "20250331")


def test_industry_long_reads_a_later_record_and_names_its_start(tmp_path):
    since, links = run.read_absorptions(PEERS / "absorptions_none.json", again="x")
    assert (since, links) == ("2005-10-01", [])
    old = tmp_path / "absorptions.json"
    old.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="does not record the date"):
        run.read_absorptions(old, again="x")
