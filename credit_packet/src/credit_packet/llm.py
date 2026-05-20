SYSTEM_PROMPT = "You are a source-bound formatting assistant. You do not make credit judgments, investment recommendations, ratings, or unsupported inferences. Use only the provided facts, metrics, flags, and excerpts. If information is missing, say unavailable. Do not calculate. Do not infer. Do not add facts."

class LLMClient:
    def __init__(self, settings):
        self.settings=settings

    def summarize_excerpt(self, text: str) -> str:
        return text if self.settings.llm_provider == 'none' else text

    def generate_review_questions(self, flags, excerpts):
        if not flags and not excerpts:
            return ["No rule-based flags identified; confirm data completeness and unavailable fields."]
        qs=[f"What management explanation supports flag {f.code} observed in period {f.period}?" for f in flags[:8]]
        return qs

    def draft_memo_shell(self, packet):
        return "Manual review required. No automated credit conclusion generated."
