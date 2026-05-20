from pathlib import Path
from credit_packet.filing_text import clean_filing_text
from credit_packet.sections import extract_sections
from credit_packet.changes import compare_filings_for_changes

OLD = Path('tests/fixtures/sec_filings/sample_10k_prior.html').read_text()
NEW = Path('tests/fixtures/sec_filings/sample_10k_latest.html').read_text()

def _doc(raw, src):
    text, paras = clean_filing_text(raw)
    secs = extract_sections(text, '10-K')
    return {'paragraphs': paras, 'sections': secs, 'source_url': src}

def test_changes_detected():
    ch = compare_filings_for_changes(_doc(OLD,'old'), _doc(NEW,'new'))
    assert len(ch) > 0

def test_changes_section_not_unknown():
    ch = compare_filings_for_changes(_doc(OLD,'old'), _doc(NEW,'new'))
    assert any(c.section != 'Unknown' for c in ch)

def test_changes_include_modified_or_added():
    ch = compare_filings_for_changes(_doc(OLD,'old'), _doc(NEW,'new'))
    assert any(c.change_type in {'modified','added'} for c in ch)

def test_changes_sources_present():
    c = compare_filings_for_changes(_doc(OLD,'old'), _doc(NEW,'new'))[0]
    assert c.source_old == 'old' and c.source_new == 'new'

