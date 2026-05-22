import pytest
from credit_packet.llm import guardrail_check


def test_allowed_revenue_decline():
    guardrail_check('## Latest Filing Activity\nRevenue decline was observed.')


def test_allowed_cash_declined():
    guardrail_check('## Latest Filing Activity\nCash declined year over year.')


def test_allowed_customers_buy_products():
    guardrail_check('## Latest Filing Activity\nCustomers buy products through distributors.')


def test_allowed_sell_inventory():
    guardrail_check('## Latest Filing Activity\nThe company may sell inventory seasonally.')


def test_allowed_hold_cash():
    guardrail_check('## Latest Filing Activity\nThe company may hold cash for liquidity.')


@pytest.mark.parametrize('bad', [
    'We recommend approval for this borrower.',
    'We recommend decline based on this packet.',
    'This borrower is approved for credit.',
    'This borrower is declined for credit.',
    'Assigned buy rating based on trend.',
    'Assigned sell rating based on trend.',
    'Assigned hold rating based on trend.',
    'Final investment recommendation is pending.',
    'credit rating: BBB',
    'risk rating: moderate',
])
def test_blocked_recommendation_phrases(bad):
    with pytest.raises(ValueError):
        guardrail_check('## Latest Filing Activity\n' + bad)
