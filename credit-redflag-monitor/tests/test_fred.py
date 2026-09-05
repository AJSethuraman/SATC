"""FRED parsing and missing-value handling (spec section 7.1)."""

from __future__ import annotations

import pytest

from redflag_monitor.fred import (
    FredClient,
    FredError,
    parse_observations,
    valid_observations,
)


def _payload(pairs):
    return {"observations": [{"date": d, "value": v} for d, v in pairs]}


# A TERMCBCCALLNS-shaped series: "monthly" labeled but only populates ~quarterly,
# with "." in the gap months (spec section 7.1).
TERMCB_PAIRS = [
    ("2024-01-01", "."),
    ("2024-02-01", "."),
    ("2024-03-01", "20.75"),
    ("2024-04-01", "."),
    ("2024-05-01", "."),
    ("2024-06-01", "21.40"),
    ("2024-07-01", "."),
]

# A DGS10-shaped dense daily series, no gaps.
DGS10_PAIRS = [
    ("2024-06-03", "4.10"),
    ("2024-06-04", "4.15"),
    ("2024-06-05", "4.22"),
]


def test_drops_missing_values_to_none():
    obs = parse_observations(_payload(TERMCB_PAIRS))
    assert [o.value for o in obs[:3]] == [None, None, 20.75]


def test_last_two_valid_for_quarterly_gapped_series():
    valid = valid_observations(parse_observations(_payload(TERMCB_PAIRS)))
    # Naive "last row" would be the 2024-07-01 "." gap; we must skip it.
    assert valid[-1].period == "2024-06-01"
    assert valid[-1].value == 21.40
    assert valid[-2].period == "2024-03-01"
    assert valid[-2].value == 20.75


def test_dense_daily_series_keeps_all():
    valid = valid_observations(parse_observations(_payload(DGS10_PAIRS)))
    assert len(valid) == 3
    assert valid[-1].value == 4.22


def test_observations_sorted_ascending_regardless_of_input_order():
    shuffled = _payload([("2024-03-01", "3"), ("2024-01-01", "1"), ("2024-02-01", "2")])
    obs = parse_observations(shuffled)
    assert [o.period for o in obs] == ["2024-01-01", "2024-02-01", "2024-03-01"]


def test_blank_value_treated_as_missing():
    obs = parse_observations(_payload([("2024-01-01", "")]))
    assert obs[0].value is None


def test_missing_observations_key_raises():
    with pytest.raises(FredError):
        parse_observations({})


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(FredError):
        FredClient()


def test_client_uses_injected_requester():
    class FakeResp:
        status_code = 200

        def json(self):
            return _payload(DGS10_PAIRS)

    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["series_id"] = params["series_id"]
        return FakeResp()

    client = FredClient(api_key="test", requester=fake_get)
    obs = client.fetch_observations("DGS10")
    assert captured["series_id"] == "DGS10"
    assert len(obs) == 3


def test_client_raises_on_http_error():
    class FakeResp:
        status_code = 400
        text = "bad request"

    client = FredClient(api_key="test", requester=lambda *a, **k: FakeResp())
    with pytest.raises(FredError, match="HTTP 400"):
        client.fetch_observations("DGS10")
