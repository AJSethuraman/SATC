from credit_packet.models import CompanyIdentity, ResearchPacket
from credit_packet.render import render_markdown

def test_render_sections_present():
    p=ResearchPacket(company=CompanyIdentity('ABC','0000000001','ABC Inc'))
    md=render_markdown(p)
    for h in ['## Important Limitation','## Latest Filing Activity','## Annual Financial Trends','## Calculated Metrics','## Rule-Based Watchlist Flags','## Debt, Liquidity, and Risk Excerpts','## Filing Language Changes','## Questions for Human Review','## Memo Shell','## Source and Audit Trail']:
        assert h in md

def test_manual_review_phrase_present():
    p=ResearchPacket(company=CompanyIdentity('ABC','0000000001','ABC Inc'))
    md=render_markdown(p)
    assert 'Manual review required' in md
