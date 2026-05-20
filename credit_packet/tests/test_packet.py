from credit_packet.models import CompanyIdentity, ResearchPacket
from credit_packet.render import render_markdown

def test_render_manual_review_and_no_prohibited_phrases():
    p=ResearchPacket(company=CompanyIdentity(ticker='ABC',cik='0000000001',name='ABC Inc'))
    md=render_markdown(p)
    assert 'Manual review required' in md
    for bad in ['approve','decline','buy','sell','hold','investment recommendation','credit rating']:
        assert bad not in md.lower()
