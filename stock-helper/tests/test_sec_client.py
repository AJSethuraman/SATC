"""SEC request wrapper: ticker lookup, caching, User-Agent enforcement."""

import pytest

from conftest import load_fixture, transport_for
from stock_helper.connectors.sec import TICKER_MAP_URL, SecClient, TickerNotFoundError
from stock_helper.core.config import Settings


def make_client(settings, counter=None):
    routes = {TICKER_MAP_URL: load_fixture("company_tickers.json")}
    return SecClient(settings, transport=transport_for(routes, counter))


def test_ticker_to_cik(settings):
    client = make_client(settings)
    assert client.ticker_to_cik("aapl") == 320193
    assert client.ticker_to_cik("KEY") == 91576


def test_unknown_ticker_raises(settings):
    client = make_client(settings)
    with pytest.raises(TickerNotFoundError, match="ZZZZ"):
        client.ticker_to_cik("ZZZZ")


def test_response_caching(settings):
    counter: dict = {}
    client = make_client(settings, counter)
    client.load_ticker_map()
    client.load_ticker_map()
    assert counter[TICKER_MAP_URL] == 1  # second call served from disk cache

    # A fresh client (same cache dir) also hits the cache, not the network.
    counter2: dict = {}
    client2 = make_client(settings, counter2)
    client2.load_ticker_map()
    assert TICKER_MAP_URL not in counter2


def test_cache_ttl_zero_disables_reuse(settings):
    fresh = settings.model_copy(update={"sec_cache_ttl_hours": 0.0})
    counter: dict = {}
    client = make_client(fresh, counter)
    client.load_ticker_map()
    client.load_ticker_map()
    assert counter[TICKER_MAP_URL] == 2


def test_placeholder_user_agent_rejected(tmp_path):
    bad = Settings(
        sec_user_agent="stock-helper dev (you@example.com)",
        data_dir=tmp_path / "data",
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        SecClient(bad)
