"""Unit tests for the Yahoo price parser — pure, no network.

The fixture mirrors the shape of Yahoo's v8 /finance/chart JSON so the parser's
correctness is verified offline (the sandbox cannot reach Yahoo).
"""

import pandas as pd

from stock_helper.connectors.yahoo import parse_yahoo_chart

# Three daily bars; one has a null close that must be dropped. adjclose differs
# from raw close historically (split/div adjustment) and must win.
_PAYLOAD = {
    "chart": {
        "error": None,
        "result": [
            {
                "meta": {"symbol": "AAPL"},
                "timestamp": [1704067200, 1704153600, 1704240000],
                "indicators": {
                    "quote": [
                        {
                            "open": [100.0, 101.0, 102.0],
                            "high": [103.0, 104.0, 105.0],
                            "low": [99.0, 100.5, 101.5],
                            "close": [101.0, None, 104.0],
                            "volume": [1000, 1100, 1200],
                        }
                    ],
                    "adjclose": [{"adjclose": [100.5, None, 103.7]}],
                },
            }
        ],
    }
}


def test_parse_yahoo_chart_happy_path():
    frame = parse_yahoo_chart(_PAYLOAD)
    assert frame is not None
    # The middle bar (null close) is dropped -> two rows remain.
    assert list(frame.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert len(frame) == 2
    # Adjusted close wins over raw close.
    assert frame["Close"].tolist() == [100.5, 103.7]
    assert pd.api.types.is_datetime64_any_dtype(frame["Date"])
    assert frame["Date"].iloc[0] == pd.Timestamp("2024-01-01")


def test_parse_yahoo_chart_falls_back_to_raw_close_when_no_adjclose():
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "timestamp": [1704067200],
                    "indicators": {"quote": [{"close": [42.0]}]},
                }
            ],
        }
    }
    frame = parse_yahoo_chart(payload)
    assert frame is not None
    assert frame["Close"].tolist() == [42.0]


def test_parse_yahoo_chart_error_and_empty_return_none():
    assert parse_yahoo_chart({"chart": {"error": {"code": "Not Found"}}}) is None
    assert parse_yahoo_chart({"chart": {"result": []}}) is None
    assert parse_yahoo_chart({}) is None
    assert parse_yahoo_chart(None) is None
    # timestamps present but every close null -> no usable rows.
    allnull = {
        "chart": {
            "result": [
                {"timestamp": [1704067200], "indicators": {"quote": [{"close": [None]}]}}
            ]
        }
    }
    assert parse_yahoo_chart(allnull) is None
