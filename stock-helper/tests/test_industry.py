"""SIC → industry bucket mapping."""

from stock_helper.industry.sic_buckets import is_financial, sic_to_bucket


def test_seed_ticker_mappings():
    assert sic_to_bucket("3571") == "technology"  # AAPL
    assert sic_to_bucket("7372") == "technology"  # MSFT
    assert sic_to_bucket("6021") == "banking"     # JPM
    assert sic_to_bucket("6022") == "banking"     # KEY
    assert sic_to_bucket("3674") == "technology"  # NVDA
    assert sic_to_bucket("5331") == "consumer"    # COST


def test_financial_variants():
    assert sic_to_bucket("6712") == "banking"       # bank holding company
    assert sic_to_bucket("6311") == "insurance"
    assert sic_to_bucket("6798") == "real_estate"   # REIT
    assert sic_to_bucket("6199") == "other_financial"
    assert sic_to_bucket("6200") == "other_financial"


def test_specific_before_broad():
    assert sic_to_bucket("2836") == "healthcare"  # biologics, inside 2000-3999
    assert sic_to_bucket("2800") == "materials"   # chemicals
    assert sic_to_bucket("3711") == "industrials"  # autos fall through to broad range
    assert sic_to_bucket("1311") == "energy"
    assert sic_to_bucket("4911") == "utilities"


def test_unknown_and_missing():
    assert sic_to_bucket(None) == "other"
    assert sic_to_bucket("") == "other"
    assert sic_to_bucket("notanumber") == "other"
    assert sic_to_bucket("9999") == "other"


def test_is_financial():
    assert is_financial("banking")
    assert is_financial("insurance")
    assert not is_financial("technology")
