"""No-op / rule-based implementations of the AI interfaces.

These keep the rest of the app honest: anything consuming AI outputs must
handle the "AI disabled" mode, which is the v0.1 default and permanent fallback.
"""

from stock_helper.ai.interfaces import EvidenceChunk, GroundedText


class NoOpSummarizer:
    def summarize(self, chunks: list[EvidenceChunk], max_words: int = 150) -> GroundedText:
        if not chunks:
            return GroundedText(text="No evidence available to summarize.")
        first = chunks[0]
        words = first.text.split()
        excerpt = " ".join(words[:max_words])
        suffix = "…" if len(words) > max_words else ""
        return GroundedText(
            text=f"[AI disabled — verbatim excerpt] {excerpt}{suffix}",
            cited_chunk_ids=[first.chunk_id],
        )


class NoOpRiskExtractor:
    def extract_risks(self, chunks: list[EvidenceChunk]) -> list[GroundedText]:
        return []  # rule-based risk extraction arrives with Phase 2 text features


class NoOpQuestionAnswerer:
    def answer(self, question: str, chunks: list[EvidenceChunk]) -> GroundedText:
        return GroundedText(
            text="AI question answering is disabled (Phase 6). "
            "Use the Filing Evidence view to read the source sections directly.",
            cited_chunk_ids=[c.chunk_id for c in chunks[:3]],
        )


class NoOpClassifier:
    def classify(self, chunk: EvidenceChunk, labels: list[str]) -> str:
        return labels[0] if labels else ""
