from pathlib import Path
from credit_packet.filing_text import clean_filing_text
from credit_packet.sections import extract_sections
from credit_packet.excerpts import find_excerpts

LATEST = Path('tests/fixtures/sec_filings/sample_10k_latest.html').read_text()

def test_clean_removes_script_and_style():
    text, _ = clean_filing_text(LATEST)
    assert 'var a=1' not in text

def test_clean_keeps_body_text():
    text, _ = clean_filing_text(LATEST)
    assert 'revolving credit facility' in text.lower()

def test_clean_outputs_paragraphs():
    _, paras = clean_filing_text(LATEST)
    assert len(paras) >= 4

def test_sections_extract_risk_factors():
    text, _ = clean_filing_text(LATEST)
    secs = extract_sections(text, '10-K')
    assert any(s['section'] == 'Risk Factors' for s in secs)

def test_sections_extract_mda():
    text, _ = clean_filing_text(LATEST)
    secs = extract_sections(text, '10-K')
    assert any(s['section'] == 'MD&A' for s in secs)

def test_sections_not_full_text_only():
    text, _ = clean_filing_text(LATEST)
    secs = extract_sections(text, '10-K')
    assert len(secs) > 1

def test_excerpts_from_body_not_filename():
    text, paras = clean_filing_text(LATEST)
    secs = extract_sections(text, '10-K')
    proc = [{'form':'10-K','filing_date':'2025-01-01','accession_number':'x','source_url':'u','paragraphs':paras,'section_map':{i:'Risk Factors' for i,_ in enumerate(paras)},'sections':secs,'primary_document':'d10k.htm'}]
    ex = find_excerpts(proc)
    assert any('revolving credit facility' in e.text.lower() for e in ex)

def test_excerpts_have_keywords():
    text, paras = clean_filing_text(LATEST)
    proc = [{'form':'10-K','filing_date':'2025-01-01','accession_number':'x','source_url':'u','paragraphs':paras,'section_map':{i:'Risk Factors' for i,_ in enumerate(paras)}}]
    ex = find_excerpts(proc)
    assert any(e.matched_keywords for e in ex)
