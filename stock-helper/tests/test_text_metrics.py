"""Disclosure-language metrics and the rule-based risk extractor."""

from stock_helper.ai.interfaces import EvidenceChunk
from stock_helper.ai.rule_based import RuleBasedRiskExtractor
from stock_helper.parsing.text_metrics import (
    category_rates,
    compute_risk_language,
    shingle_novelty,
)


class FakeChunk:
    def __init__(self, chunk_id, text):
        self.chunk_id = chunk_id
        self.text = text


RISKY = (
    "We face litigation and regulatory proceedings in multiple jurisdictions. "
    "Adverse outcomes could result in penalties, impairment charges, and material "
    "losses. Our indebtedness imposes restrictive covenants that limit our "
    "flexibility. Demand may decline and results are uncertain and volatile."
)
CALM = (
    "The company designs quality products that customers enjoy using every day. "
    "Our teams collaborate across regions to deliver innovative experiences and "
    "support long term partnerships with suppliers and communities."
)


def test_category_rates():
    total, rates = category_rates(RISKY)
    assert total > 0
    assert rates["litigious"] > 0
    assert rates["negative"] > 0
    assert rates["constraining"] > 0
    _, calm_rates = category_rates(CALM)
    assert rates["negative"] > calm_rates["negative"]
    assert category_rates("")[0] == 0


def test_shingle_novelty_bounds():
    assert shingle_novelty(RISKY, RISKY) == 0.0
    assert shingle_novelty(RISKY, CALM) > 0.9
    assert shingle_novelty("", RISKY) == 0.0  # degenerate input → no claim


def test_compute_risk_language_with_prior():
    current = [FakeChunk("acc1:risk_factors:0", RISKY)]
    prior = [FakeChunk("acc0:risk_factors:0", RISKY + " New supply chain risks emerged this year across several geographies.")]
    metrics = compute_risk_language(current, prior)
    assert metrics is not None
    assert metrics.word_count > 0
    assert metrics.novelty_vs_prior is not None
    assert 0.0 <= metrics.novelty_vs_prior <= 1.0
    assert metrics.current_chunk_ids == ["acc1:risk_factors:0"]
    assert metrics.rate_delta("uncertainty") is not None


def test_compute_risk_language_without_prior():
    metrics = compute_risk_language([FakeChunk("a:risk_factors:0", RISKY)])
    assert metrics.novelty_vs_prior is None
    assert metrics.rate_delta("uncertainty") is None
    assert compute_risk_language([]) is None


def test_rule_based_risk_extractor_cites_chunks():
    chunks = [
        EvidenceChunk(chunk_id="a:risk_factors:0", text=RISKY),
        EvidenceChunk(chunk_id="a:risk_factors:1", text=CALM),
    ]
    results = RuleBasedRiskExtractor().extract_risks(chunks)
    assert results, "risky text should yield highlights"
    for grounded in results:
        assert grounded.cited_chunk_ids == ["a:risk_factors:0"]
        assert grounded.model_name == "rule-based (no AI)"
    # Calm text alone yields nothing — the extractor selects, never invents.
    assert RuleBasedRiskExtractor().extract_risks(
        [EvidenceChunk(chunk_id="b:0", text=CALM)]
    ) == []
