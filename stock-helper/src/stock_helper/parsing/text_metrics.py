"""Rule-based disclosure-language metrics over extracted filing sections.

No AI involved: word-rate counting against curated finance word lists, plus a
shingle-overlap novelty measure between this year's and last year's risk
factors. Everything is a transparent calculation with documented limits —
these feed the disclosure signal at medium/low confidence by design.
"""

import re
from dataclasses import dataclass, field

from stock_helper.parsing.wordlists import CATEGORIES

TEXT_METRICS_VERSION = "text-metrics-0.1"

_WORD = re.compile(r"[a-z][a-z'-]*")


@dataclass
class RiskLanguageMetrics:
    """Disclosure-language summary for one company, current vs prior filing."""

    word_count: int
    rates_per_1000: dict[str, float]  # category -> hits per 1000 words
    prior_rates_per_1000: dict[str, float] = field(default_factory=dict)
    novelty_vs_prior: float | None = None  # 1 - shingle overlap; None if no prior
    current_chunk_ids: list[str] = field(default_factory=list)
    prior_chunk_ids: list[str] = field(default_factory=list)

    def rate_delta(self, category: str) -> float | None:
        if category not in self.prior_rates_per_1000:
            return None
        return self.rates_per_1000.get(category, 0.0) - self.prior_rates_per_1000[category]


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def category_rates(text: str) -> tuple[int, dict[str, float]]:
    """(word_count, category -> hits per 1000 words). Empty text -> zeros."""
    tokens = tokenize(text)
    total = len(tokens)
    if total == 0:
        return 0, {name: 0.0 for name in CATEGORIES}
    rates = {}
    for name, words in CATEGORIES.items():
        hits = sum(1 for token in tokens if token in words)
        rates[name] = hits / total * 1000
    return total, rates


def shingle_novelty(current: str, prior: str, shingle_size: int = 5) -> float:
    """1 - Jaccard similarity of word shingles: 0 = identical text, 1 = fully new.

    A rough but transparent proxy for "how much of the risk discussion changed".
    Boilerplate-heavy filings score low; substantive rewrites score high.
    """
    def shingles(text: str) -> set[tuple[str, ...]]:
        tokens = tokenize(text)
        return {
            tuple(tokens[i : i + shingle_size])
            for i in range(max(0, len(tokens) - shingle_size + 1))
        }

    a, b = shingles(current), shingles(prior)
    if not a or not b:
        return 0.0
    return 1.0 - len(a & b) / len(a | b)


def compute_risk_language(
    current_chunks: list,  # FilingSection-like: .text, .chunk_id
    prior_chunks: list | None = None,
) -> RiskLanguageMetrics | None:
    """Metrics over a section's chunks (typically risk_factors). None if empty."""
    if not current_chunks:
        return None
    current_text = "\n\n".join(c.text for c in current_chunks)
    word_count, rates = category_rates(current_text)
    if word_count == 0:
        return None
    metrics = RiskLanguageMetrics(
        word_count=word_count,
        rates_per_1000=rates,
        current_chunk_ids=[c.chunk_id for c in current_chunks],
    )
    if prior_chunks:
        prior_text = "\n\n".join(c.text for c in prior_chunks)
        prior_words, prior_rates = category_rates(prior_text)
        if prior_words > 0:
            metrics.prior_rates_per_1000 = prior_rates
            metrics.novelty_vs_prior = shingle_novelty(current_text, prior_text)
            metrics.prior_chunk_ids = [c.chunk_id for c in prior_chunks]
    return metrics
