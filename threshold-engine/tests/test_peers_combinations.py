"""Bank combinations: an absorbed affiliate's year-to-date is counted once,
and a quarter whose acquisitions bring in the acquisition share is left out.

The comparability tie-out (14 Oct 2026, docs/tie-out/comparability-2026-10)
found the industry card series counting an absorbed affiliate's year-to-date
charge-offs twice in the merger quarter, $74m to $4.8bn in six quarters, and
the 25% jump rule missing 60 of 130 material acquisitions. The books here are
small and made up, so the right answer is known by hand."""
import json

import pytest

from threshold_engine.peers import fdic
from threshold_engine.peers.books import (
    PARENT, WHY_ACQUIRED, WHY_JUMP, acquired_quarters, bank_book, industry, repeated_ytd,
    without_repeats)
from threshold_engine.peers.run import load_absorptions

QUARTERS = ["20110331", "20110630", "20110930", "20111231",
            "20120331", "20120630", "20120930", "20121231"]


def books(*, parent_a="100", parent_b="100", merge_quarter="20110930", flow_a=10.0, flow_b=5.0,
          bal_a=1000.0, bal_b=60.0, drop_parent=False):
    """Bank 1 absorbs bank 2 in ``merge_quarter``. Each charges off its flow
    every quarter. Under common control the survivor's year-to-date carries
    bank 2's earlier quarters of the year, as the Call Report instructions
    require; otherwise it carries only what it booked after the merger."""
    common = parent_a == parent_b
    data, ytd_a, ytd_b, merged = {}, 0.0, 0.0, False
    for q in QUARTERS:
        if q[4:6] == "03":
            ytd_a = ytd_b = 0.0
        if q == merge_quarter:
            merged = True
            if common:
                ytd_a += ytd_b                    # the restated year to date
        ytd_a += flow_a + (flow_b if merged else 0.0)
        rows = [{"CERT": 1, "REPDTE": q, "LNCRCD": bal_a + (bal_b if merged else 0.0),
                 "DRCRCD": ytd_a, "CRCRCD": 0.0, PARENT: parent_a}]
        if not merged:
            ytd_b += flow_b
            rows.append({"CERT": 2, "REPDTE": q, "LNCRCD": bal_b, "DRCRCD": ytd_b, "CRCRCD": 0.0,
                         PARENT: parent_b})
        if drop_parent:
            for r in rows:
                r.pop(PARENT)
        data[q] = rows
    return data


LINK = [{"acquirer": "1", "absorbed": "2", "quarter": "2011-09-30"}]


def gross_ttm(data):
    return {r["quarter"]: r["gross"] for r in industry(data, "Credit card")}


def test_without_the_fix_the_survivor_repeats_the_affiliates_year_to_date():
    """The defect, reproduced: 15 a quarter is the truth; the merger quarter
    reads 25, bank 2's first-half 10 counted a second time."""
    assert gross_ttm(books())["2011Q4"] == 60 + 10


def test_the_repeated_year_to_date_is_taken_off_once():
    data = books()
    repeats = repeated_ytd(data, LINK, ["Credit card"])
    assert repeats == [{"acquirer": "1", "absorbed": "2", "quarter": "20110930",
                        "field": "DRCRCD", "amount": 10.0}]
    fixed = without_repeats(data, repeats)
    assert gross_ttm(fixed) == {q: 60.0 for q in ("2011Q4", "2012Q1", "2012Q2", "2012Q3", "2012Q4")}
    assert data["20110930"][0]["DRCRCD"] == 45.0          # the data given is not touched


def test_the_survivors_own_flows_count_each_dollar_once():
    fixed = without_repeats(books(), repeated_ytd(books(), LINK, ["Credit card"]))
    rows = bank_book(fixed, "1", "Credit card", 1.0, 0, acquired=())
    assert [r["gross"] for r in rows] == [55.0, 60.0, 60.0, 60.0]   # 10, 10, 15, 15 / then 15 a quarter


def test_different_parents_are_not_common_control():
    """An acquirer from outside the group reports only what it booked after
    the merger, so nothing is repeated and nothing is taken off."""
    data = books(parent_b="200")
    assert repeated_ytd(data, LINK, ["Credit card"]) == []
    assert gross_ttm(data)["2011Q4"] == 60


@pytest.mark.parametrize("blank", ["", None, "0"])
def test_a_blank_parent_is_not_a_shared_one(blank):
    assert repeated_ytd(books(parent_a=blank, parent_b=blank), LINK, ["Credit card"]) == []


def test_a_first_quarter_merger_repeats_nothing():
    link = [{"acquirer": "1", "absorbed": "2", "quarter": "2012-03-31"}]
    assert repeated_ytd(books(merge_quarter="20120331"), link, ["Credit card"]) == []


def test_a_cache_without_the_parent_is_refused_where_it_matters():
    with pytest.raises(ValueError, match="RSSDHCR.*Pull again"):
        repeated_ytd(books(drop_parent=True), LINK, ["Credit card"])
    assert repeated_ytd(books(drop_parent=True), [], ["Credit card"]) == []


@pytest.mark.parametrize("bal_b,hit", [(60.0, True), (50.0, True), (40.0, False)])
def test_an_acquisition_is_left_out_at_the_share(bal_b, hit):
    got = acquired_quarters(books(bal_b=bal_b), LINK, "Credit card", 0.05)
    assert got == ({"1": ["20110930"]} if hit else {})


def test_acquisitions_in_one_quarter_are_added_together():
    """Two banks of 3% each are 6% together: PNC's eleven 2007Q3 mortgage
    acquisitions were each under 5% and 16.5% together."""
    data = books(bal_b=30.0)
    for q in QUARTERS[:2]:
        data[q].append({"CERT": 3, "REPDTE": q, "LNCRCD": 30.0, "DRCRCD": 0.0, "CRCRCD": 0.0,
                        PARENT: "300"})
    links = LINK + [{"acquirer": "1", "absorbed": "3", "quarter": "2011-09-30"}]
    assert acquired_quarters(data, LINK, "Credit card", 0.05) == {}
    assert acquired_quarters(data, links, "Credit card", 0.05) == {"1": ["20110930"]}


def test_the_four_windows_holding_the_acquisition_are_left_out_and_say_why():
    data = books(parent_b="200")
    rows = bank_book(data, "1", "Credit card", 1.0, 0,
                     acquired=acquired_quarters(data, LINK, "Credit card", 0.05)["1"])
    assert [(r["quarter"], r["why"]) for r in rows] == [
        ("2012Q1", WHY_ACQUIRED), ("2012Q2", WHY_ACQUIRED), ("2012Q3", None), ("2012Q4", None)]
    assert bank_book(data, "1", "Credit card", 1.0, 0, acquired=())[0]["why"] is None


def test_the_jump_still_speaks_first():
    data = books(parent_b="200", bal_b=900.0)
    rows = bank_book(data, "1", "Credit card", 0.25, 0, acquired=["20110930"])
    assert rows[0]["why"] == WHY_JUMP


def test_acquired_is_required_and_a_string_is_refused():
    with pytest.raises(TypeError):
        bank_book(books(), "1", "Credit card", 0.25, 0)
    with pytest.raises(ValueError, match="list of quarter-ends"):
        bank_book(books(), "1", "Credit card", 0.25, 0, acquired="20110930")


@pytest.mark.parametrize("share", [-0.01, float("nan")])
def test_a_share_below_zero_is_refused(share):
    with pytest.raises(ValueError, match="share"):
        acquired_quarters(books(), LINK, "Credit card", share)


def test_absorptions_are_read_from_the_fdic_history():
    """The absorbed bank is OUT_CERT: a failure's row leaves CERT blank (seen
    in the FDIC history, e.g. code 211 rows from 2007), and is still an
    acquisition whose book counts towards the share."""
    rows = [
        {"CERT": 23360, "OUT_CERT": 23360, "ACQ_CERT": 7213, "CHANGECODE": 223, "EFFDATE": "2011-07-01T00:00:00"},
        {"CERT": 23360, "OUT_CERT": 23360, "ACQ_CERT": 7213, "CHANGECODE": 810, "EFFDATE": "2011-07-01T00:00:00"},
        {"CERT": 23360, "OUT_CERT": 23360, "ACQ_CERT": 7213, "CHANGECODE": 223, "EFFDATE": "2011-07-01T00:00:00"},
        {"OUT_CERT": 35353, "ACQ_CERT": 6058, "CHANGECODE": 211, "EFFDATE": "2007-02-02T00:00:00"},
        {"CERT": 1, "OUT_CERT": "", "ACQ_CERT": 7213, "CHANGECODE": 223, "EFFDATE": "2011-07-01T00:00:00"},
        {"CERT": 58180, "OUT_CERT": 58180, "ACQ_CERT": 7213, "CHANGECODE": 224, "EFFDATE": "2022-07-01T00:00:00"},
    ]
    assert fdic.absorptions(rows) == [
        {"acquirer": "6058", "absorbed": "35353", "quarter": "2007-03-31"},
        {"acquirer": "7213", "absorbed": "23360", "quarter": "2011-09-30"},
        {"acquirer": "7213", "absorbed": "58180", "quarter": "2022-09-30"},
    ]


@pytest.mark.parametrize("content", ['{"7213": []}', '[{"acquirer": "7213"}]',
                                     '[{"acquirer": "7213", "absorbed": "x", "quarter": "2011-09-30"}]',
                                     '[{"acquirer": "7213", "absorbed": "1", "quarter": "2011-13-30"}]',
                                     "not json"])
def test_a_bad_absorptions_file_is_refused_by_name(tmp_path, content):
    f = tmp_path / "absorptions.json"
    f.write_text(content)
    with pytest.raises(ValueError, match="absorptions.json"):
        load_absorptions(f)


def test_a_good_absorptions_file_is_read(tmp_path):
    f = tmp_path / "absorptions.json"
    f.write_text(json.dumps(LINK))
    assert load_absorptions(f) == LINK


def test_delinquency_blanks_the_four_quarter_average_at_an_acquisition_never_a_rate():
    from threshold_engine.peers import delinquency as D
    data = {q: [{"CERT": 1, "REPDTE": q, "LNCRCD": 1000.0, "P3CRCD": 10.0, "P9CRCD": 5.0, "NACRCD": 1.0}]
            for q in QUARTERS}
    plain = D.bank_delinquency(data, "1", "Credit card", "30-89", 1.0, 0, False, acquired=())
    bought = D.bank_delinquency(data, "1", "Credit card", "30-89", 1.0, 0, False, acquired=["20110930"])
    assert [r["rate"] for r in bought] == [r["rate"] for r in plain]
    assert [r["avg4"] is None for r in bought] == [True, True, True, True, True, False, False, False]
    assert bought[4]["why_avg4"].startswith(D.WHY_ACQUIRED_PREFIX)
    assert plain[4]["avg4"] == 1.0


def test_the_comparability_lines_follow_the_tie_out():
    from threshold_engine.peers import delinquency as D
    assert D.comparability("Credit card", "30+ incl. nonaccrual") == []
    assert D.comparability("Credit card", "nonaccrual") == [D.POLICY]
    assert D.comparability("Mortgage", "90+ accruing") == [D.POLICY, D.GUARANTEED]
    assert D.comparability("Mortgage", "90+ incl. nonaccrual") == [D.GUARANTEED]
    assert D.comparability("Mortgage", "30-89") == []
    with pytest.raises(ValueError):
        D.comparability("Mortgage", "60+")


def test_the_books_path_is_stated_not_judged():
    from threshold_engine.peers.books import balance_path
    rows = [{"quarter": "2024Q%d" % (i % 4 + 1), "avg_balance": 100.0 - 5 * i} for i in range(9)]
    line = balance_path(rows, 9)
    assert "100 ($000)" in line and "60 at" in line and "(-40.0%)" in line and "fell in 8 of the 8" in line
    assert balance_path(rows[:5], 9) is None


def test_a_year_to_date_restarted_under_a_new_parent_is_the_quarters_flow():
    """National City under PNC, 2008Q4: its card year-to-date went from
    94,608 to 0 as its parent changed. Differencing read -94.6m; the FDIC's
    Quarterly Banking Profile counts the filed year-to-date (14 Oct 2026)."""
    from threshold_engine.peers.books import flow, quarterly_flows, restarted
    prev = {"CERT": 6557, "REPDTE": "20080930", "LNCRCD": 1.0, "DRCRCD": 94608, "CRCRCD": 6221, PARENT: "1069125"}
    now = dict(prev, REPDTE="20081231", DRCRCD=0, CRCRCD=0, **{PARENT: "1069778"})
    assert restarted(now, prev) and flow(now, prev, "DRCRCD") == 0
    same = dict(now, **{PARENT: "1069125"})
    assert not restarted(same, prev) and flow(same, prev, "DRCRCD") == -94608
    rose = dict(now, DRCRCD=100000, CRCRCD=7000)
    assert not restarted(rose, prev) and flow(rose, prev, "DRCRCD") == 100000 - 94608
    level = dict(now, DRCRCD=94608, CRCRCD=6221)
    assert not restarted(level, prev)                   # nothing fell: differenced
    for blank in ("", None, "0"):
        assert not restarted(dict(now, **{PARENT: blank}), prev)
        assert not restarted(now, dict(prev, **{PARENT: blank}))
    data = {"20080930": [prev], "20081231": [now]}
    assert quarterly_flows(data, "6557", "Credit card")[1][1:3] == (0, 0)
    assert [r for r in industry({"20080331": [dict(prev, REPDTE="20080331", DRCRCD=30000, CRCRCD=2000)],
                                 "20080630": [dict(prev, REPDTE="20080630", DRCRCD=60000, CRCRCD=4000)],
                                 **data}, "Credit card")][0]["gross"] == 30000 + 30000 + 34608 + 0



def test_a_restart_is_one_decision_per_filing():
    """Push-down accounting restarts every year to date together. Card
    charge-offs fell (100 to 60) as the parent changed; recoveries rose (5 to
    8) but are the restarted quarter's too: 8, not 8 - 5 (review, 14 Oct)."""
    from threshold_engine.peers.books import flow
    prev = {"CERT": 1, "REPDTE": "20080930", "DRCRCD": 100, "CRCRCD": 5, PARENT: "P1"}
    now = {"CERT": 1, "REPDTE": "20081231", "DRCRCD": 60, "CRCRCD": 8, PARENT: "P2"}
    assert (flow(now, prev, "DRCRCD"), flow(now, prev, "CRCRCD")) == (60, 8)


def test_an_absorption_then_a_restart_in_the_same_year():
    """Bank 1 absorbs bank 2 (same parent) in Q3 and repeats its 40; in Q4
    bank 1 is sold to a new parent and restarts its year to date at 25. The
    40 comes off Q3 only: Q4's restarted figure never held it (review, 14
    Oct: it read -15)."""
    from threshold_engine.peers.books import quarterly_flows, without_repeats
    def row(c, q, dr, cr, parent, bal=1000.0):
        return {"CERT": c, "REPDTE": q, "LNCRCD": bal, "DRCRCD": dr, "CRCRCD": cr, PARENT: parent}
    data = {"20160331": [row(1, "20160331", 20, 1, "P1"), row(2, "20160331", 20, 1, "P1", 100)],
            "20160630": [row(1, "20160630", 40, 2, "P1"), row(2, "20160630", 40, 3, "P1", 100)],
            "20160930": [row(1, "20160930", 120, 6, "P1")],
            "20161231": [row(1, "20161231", 25, 2, "P2")]}
    link = [{"acquirer": "1", "absorbed": "2", "quarter": "2016-09-30"}]
    reps = repeated_ytd(data, link, ["Credit card"])
    assert {(r["field"], r["amount"]) for r in reps} == {("DRCRCD", 40.0), ("CRCRCD", 3.0)}
    fixed = without_repeats(data, reps)
    flows = [(q, g, rc) for q, g, rc, _ in quarterly_flows(fixed, "1", "Credit card")]
    assert flows == [("20160331", 20, 1), ("20160630", 20, 1), ("20160930", 40, 1), ("20161231", 25, 2)]
    # restarted in the merger quarter itself: nothing is taken off
    data["20160930"] = [row(1, "20160930", 30, 1, "P2")]
    data["20161231"] = [row(1, "20161231", 70, 2, "P2")]
    fixed = without_repeats(data, repeated_ytd(data, link, ["Credit card"]))
    flows = [(q, g) for q, g, _, _ in quarterly_flows(fixed, "1", "Credit card")]
    assert flows[2:] == [("20160930", 30), ("20161231", 40)]


# ---------------------------------------------------------------- review findings 27, 28 and 21 (14 Oct 2026)

def test_an_absorbed_bank_still_filing_the_merger_quarter_repeats_nothing():
    """Review finding 27: the survivor's filing can only hold the absorbed
    bank's year to date once that bank has stopped filing. Bank 2 still files
    2011Q3, so nothing is taken off bank 1."""
    data = books()
    data["20110930"].append({"CERT": 2, "REPDTE": "20110930", "LNCRCD": 60.0, "DRCRCD": 15.0,
                             "CRCRCD": 0.0, PARENT: "100"})
    assert repeated_ytd(data, LINK, ["Credit card"]) == []


def test_no_quarter_before_in_the_data_repeats_nothing():
    """Review finding 27: with 2011Q2 not in the data, 2011Q1 is not the
    quarter before 2011Q3, and its year to date (bank 2's 5) is not the
    absorbed bank's last one."""
    data = books()
    del data["20110630"]
    assert repeated_ytd(data, LINK, ["Credit card"]) == []


def test_the_absorbed_banks_book_is_read_at_its_last_filing():
    """Review finding 28: bank 2 last filed in 2011Q1, two quarters before the
    merger; its 60 is still 6% of bank 1's 1,000 and counts towards the share."""
    data = books()
    data["20110630"] = [r for r in data["20110630"] if r["CERT"] != 2]
    assert acquired_quarters(data, LINK, "Credit card", 0.05) == {"1": ["20110930"]}


def test_an_acquirer_with_no_book_before_takes_the_book_in_whole():
    """Review finding 28: bank 1 holds no cards the quarter before, so bank
    2's 60 is all of its book, whatever the share."""
    assert acquired_quarters(books(bal_a=0.0), LINK, "Credit card", 0.05) == {"1": ["20110930"]}
    assert acquired_quarters(books(bal_a=0.0), LINK, "Credit card", 50.0) == {"1": ["20110930"]}


def test_the_composite_leaves_out_a_bank_an_acquisition_blanked():
    """Review finding 21: bank 1's 2012Q2 acquisition blanks its own
    four-quarter average at 2012Q2, Q3 and Q4, so the composite's average
    leaves it out there and names it. Worked by hand: every quarter-end the
    three banks hold 1%, 3% and 2% of 1,000 each, 60 / 3,000 = 2%; without
    bank 1, 50 / 2,000 = 2.5%."""
    from threshold_engine.peers import delinquency as D
    data = {q: [{"CERT": c, "REPDTE": q, "LNCRCD": 1000.0, "P3CRCD": p3, "P9CRCD": 0.0, "NACRCD": 0.0}
                for c, p3 in ((1, 10.0), (2, 30.0), (3, 20.0))] for q in QUARTERS}
    banks = {str(c): D.bank_delinquency(data, str(c), "Credit card", "30-89", 1.0, 0, False,
                                        acquired=["20120630"] if c == 1 else ())
             for c in (1, 2, 3)}
    comp = D.composite_delinquency(banks, ["1", "2", "3"], 2)
    assert [r["q"] for r in comp] == ["2011Q%d" % n for n in range(1, 5)] + ["2012Q%d" % n for n in range(1, 5)]
    assert [r["avg4_left_out"] for r in comp] == [[]] * 5 + [["1"]] * 3
    assert [r["rate"] for r in comp] == pytest.approx([2.0] * 8)
    assert [r["avg4"] for r in comp[3:]] == pytest.approx([2.0, 2.0, 2.5, 2.5, 2.5])
