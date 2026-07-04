"""Rule-based implementations of the AI interfaces — the permanent no-model
fallback ("AI disabled" mode must preserve core functionality).

RuleBasedRiskExtractor pulls the highest-signal sentences from risk-factor
chunks by scoring them against the curated finance word lists. Every output
cites the chunk ids it came from; nothing is generated, only selected.
"""

import re
from dataclasses import dataclass

from stock_helper.ai.interfaces import EvidenceChunk, GroundedText
from stock_helper.parsing.wordlists import CONSTRAINING, LITIGIOUS, NEGATIVE, UNCERTAINTY

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_STRONG_WORDS = NEGATIVE | LITIGIOUS | CONSTRAINING


@dataclass
class _Scored:
    sentence: str
    chunk_id: str
    score: float


class RuleBasedRiskExtractor:
    """Selects (never writes) risk sentences, ranked by risk-word density."""

    def extract_risks(
        self, chunks: list[EvidenceChunk], top_k: int = 5
    ) -> list[GroundedText]:
        scored: list[_Scored] = []
        for chunk in chunks:
            for sentence in _SENTENCE.split(chunk.text):
                words = re.findall(r"[a-z][a-z'-]*", sentence.lower())
                if not 8 <= len(words) <= 120:  # skip fragments and run-ons
                    continue
                strong = sum(1 for w in words if w in _STRONG_WORDS)
                uncertain = sum(1 for w in words if w in UNCERTAINTY)
                score = (strong * 2 + uncertain) / len(words)
                if strong >= 2 and score > 0.05:
                    scored.append(_Scored(sentence.strip(), chunk.chunk_id, score))
        scored.sort(key=lambda s: s.score, reverse=True)
        seen: set[str] = set()
        results: list[GroundedText] = []
        for item in scored:
            head = item.sentence[:80]
            if head in seen:
                continue
            seen.add(head)
            results.append(
                GroundedText(
                    text=item.sentence,
                    cited_chunk_ids=[item.chunk_id],
                    model_name="rule-based (no AI)",
                )
            )
            if len(results) >= top_k:
                break
        return results
