"""left-out.csv: the quarters each series left out as built, with why (the
agent building Book 2, 17 Oct 2026, asked for it; the analyst: "sure").
Synthetic rows, worked by hand."""
import csv

from threshold_engine.book import LEFT_OUT_HEAD, write_left_out
from threshold_engine.peers.run import break_reason, left_out_spans, unbroken_tail


def test_a_bank_rows_own_reason_is_used():
    assert break_reason({"quarter": "2021Q3", "net_rate": None, "why": "book moved more than the jump"},
                        "net_rate", 5) == "book moved more than the jump"
    assert break_reason({"q": "2010Q1", "avg4": None, "why": None, "why_avg4": "fewer than four"},
                        "avg4", 5) == "fewer than four"
    assert break_reason({"quarter": "2008Q1", "net_rate": None, "banks": 3}, "net_rate", 5) == \
        "3 banks kept, fewer than the 5 needed"
    assert break_reason({"quarter": "2008Q1", "net_rate": None}, "net_rate", 5) == "no value"
    assert break_reason(None, "rate", 5) == "not in the data"


def test_spans_before_the_last_break_and_after_the_last_value():
    rows = [("2020Q1", 1.0), ("2020Q2", None), ("2020Q3", 2.0), ("2020Q4", 3.0), ("2021Q1", None)]
    tail, before, after = unbroken_tail(rows)
    assert [q for q, _ in tail] == ["2020Q3", "2020Q4"]
    spans = left_out_spans(before, after, {"2020Q2": "book moved more than the jump"})
    assert spans[0][:2] == ("2020Q1", "2020Q2") and "2020Q2 has no value (book moved more than the jump)" in spans[0][2]
    assert spans[1] == ("2021Q1", "2021Q1", "the latest quarters have no value: 2021Q1 (no value)")
    assert left_out_spans([], [], {}) == []


def test_the_file_names_each_series_by_its_parts_and_skips_whole_ones(tmp_path):
    a, b = tmp_path / "auto_keybank_net.csv", tmp_path / "card_industry_net.csv"
    series = [("Auto - Net charge-offs - KeyBank", a), ("Credit card - Net charge-offs - Industry", b)]
    parts = {"Auto - Net charge-offs - KeyBank": ("Auto", "Net charge-offs", "KeyBank"),
             "Credit card - Net charge-offs - Industry": ("Credit card", "Net charge-offs", "Industry")}
    out = tmp_path / "left-out.csv"
    n = write_left_out(out, series, parts, {a: [("2007Q1", "2022Q3", "before the last break")], b: []})
    lines = out.read_text(encoding="utf-8").splitlines()
    assert n == 1 and all(l.startswith("# ") for l in lines[:2])
    rows = list(csv.reader(lines[2:]))
    assert rows == [list(LEFT_OUT_HEAD), ["Auto", "Net charge-offs", "KeyBank", "2007Q1", "2022Q3",
                                          "before the last break"]]
