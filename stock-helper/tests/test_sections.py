"""Heuristic filing section extraction."""

from conftest import load_fixture
from stock_helper.parsing.filing_sections import (
    chunk_section,
    extract_sections,
    html_to_text,
)


def extracted():
    return {s.section_name: s for s in extract_sections(html_to_text(load_fixture("sample_10k.html")))}


def test_finds_risk_factors_and_mdna():
    sections = extracted()
    assert "risk_factors" in sections
    assert "mdna" in sections
    assert "concentrated set of suppliers" in sections["risk_factors"].text
    assert "Net revenue increased 8%" in sections["mdna"].text


def test_skips_table_of_contents_entries():
    sections = extracted()
    # TOC lines mention the same headings but with no content after them; the
    # extractor must anchor on the real section body.
    assert len(sections["risk_factors"].text) > 500
    assert "... 10" not in sections["risk_factors"].text[:200]


def test_sections_end_at_next_item():
    sections = extracted()
    assert "Properties" not in sections["risk_factors"].text
    assert "Quantitative and Qualitative" not in sections["mdna"].text


def test_chunking_stable_ids():
    sections = extracted()
    chunks = chunk_section(sections["mdna"], accession="0000320193-24-000123")
    assert chunks
    assert chunks[0].chunk_id == "0000320193-24-000123:mdna:0"
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    rebuilt = "\n\n".join(c.text for c in chunks)
    assert "share repurchases" in rebuilt
