"""AI layer interfaces — designed now, implemented in Phase 6.

Hard rules for any future implementation (Ollama or otherwise):
- AI never invents metrics; it only summarizes/classifies retrieved evidence.
- Every output must cite chunk IDs / source references it was given.
- The app must work fully with AI disabled (today's default: the no-op
  implementations in ai/noop.py).
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class EvidenceChunk:
    chunk_id: str
    text: str
    source_url: str | None = None


@dataclass
class GroundedText:
    """Text output that must carry the chunk ids it was derived from."""

    text: str
    cited_chunk_ids: list[str] = field(default_factory=list)
    model_name: str = "none"


class TextSummarizer(Protocol):
    def summarize(self, chunks: list[EvidenceChunk], max_words: int = 150) -> GroundedText: ...


class RiskExtractor(Protocol):
    def extract_risks(self, chunks: list[EvidenceChunk]) -> list[GroundedText]: ...


class FilingQuestionAnswerer(Protocol):
    def answer(self, question: str, chunks: list[EvidenceChunk]) -> GroundedText: ...


class EvidenceClassifier(Protocol):
    def classify(self, chunk: EvidenceChunk, labels: list[str]) -> str: ...
