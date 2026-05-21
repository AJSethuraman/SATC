import json
import re
import urllib.request
from .models import SourceBoundBrief, BriefPoint, ReviewTheme, ReviewQuestionItem, MissingInformation
from .llm_validate import validate_source_bound_output

SYSTEM_PROMPT = "You are a source-bound research packet assistant. Use only the provided evidence bundle. Do not use outside knowledge. Do not make credit, investment, legal, tax, approval, decline, buy, sell, or rating recommendations. Do not assign ratings or scores. Every substantive claim must cite one or more source IDs from the evidence bundle. Do not invent numbers. Only use numeric values present in the evidence bundle. If evidence is insufficient, state what is missing. Return valid JSON only."
PROHIBITED_PATTERNS=[r"\brecommend\s+approval\b",r"\brecommend\s+decline\b",r"\bapproved\s+for\s+credit\b",r"\bdeclined\s+for\s+credit\b",r"\bbuy\s+rating\b",r"\bsell\s+rating\b",r"\bhold\s+rating\b",r"\binvestment\s+recommendation\b",r"\bcredit\s+rating\s*:",r"\brisk\s+rating\s*:"]

class LLMClient:
    def __init__(self, settings): self.settings = settings
    def enabled(self): return self.settings.llm_provider == 'ollama'
    def _call(self, prompt, timeout=20):
        if not self.enabled(): return None
        try:
            body = json.dumps({'model': self.settings.ollama_model, 'system': SYSTEM_PROMPT, 'prompt': prompt, 'stream': False}).encode()
            req = urllib.request.Request(self.settings.ollama_base_url.rstrip('/') + '/api/generate', data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode()).get('response', '').strip()
        except Exception: return None

    def _fallback_brief(self, bundle, notes=None):
        notes=notes or []
        sps=[BriefPoint(text=f"Flag detected: {f['code']} ({f.get('observed_value')})",sources=[f['id']]) for f in bundle.get('flags',[])[:5]]
        if not sps:
            sps=[BriefPoint(text=f"Metric available: {m['label']} {m.get('value')}",sources=[m['id']]) for m in bundle.get('metrics',[])[:5]]
        themes=[ReviewTheme(theme='Watchlist Flags',why_it_matters='Deterministic rules triggered and require analyst validation.',sources=[f['id'] for f in bundle.get('flags',[])[:3]])] if bundle.get('flags') else []
        qs=[ReviewQuestionItem(question=f"What filing evidence explains {f['code']} in {f.get('period')}?",based_on=[f['id']]) for f in bundle.get('flags',[])[:5]]
        if not qs: qs=[ReviewQuestionItem(question='Which material data fields are unavailable and need manual sourcing?',based_on=[bundle.get('company',{}).get('id','company')])]
        missing=[MissingInformation(item='Debt maturity schedule',reason='Not explicitly normalized in current evidence bundle.')]
        return SourceBoundBrief(summary_points=sps,review_themes=themes,review_questions=qs,missing_information=missing,generation_mode='deterministic_fallback',validation_status='fallback',validation_notes=notes)

    def generate_source_bound_brief(self, evidence_bundle, valid_ids, allowed_values):
        if not self.enabled(): return self._fallback_brief(evidence_bundle,['LLM disabled'])
        prompt='Evidence bundle JSON:\n'+json.dumps(evidence_bundle)
        raw=self._call(prompt)
        if not raw: return self._fallback_brief(evidence_bundle,['LLM unavailable or empty response'])
        try: payload=json.loads(raw)
        except Exception: return self._fallback_brief(evidence_bundle,['Malformed JSON from LLM'])
        vr=validate_source_bound_output(payload,valid_ids,allowed_values)
        if not vr.is_valid: return self._fallback_brief(evidence_bundle,vr.errors)
        return SourceBoundBrief(summary_points=[BriefPoint(**x) for x in payload.get('summary_points',[])],review_themes=[ReviewTheme(**x) for x in payload.get('review_themes',[])],review_questions=[ReviewQuestionItem(**x) for x in payload.get('review_questions',[])],missing_information=[MissingInformation(**x) for x in payload.get('missing_information',[])],generation_mode='ollama',validation_status='valid',validation_notes=vr.warnings)

    def generate_review_questions(self, flags, changes):
        base = [f"What evidence in filings explains flag {f.code} in period {f.period}?" for f in flags[:8]] + [f"For section {c.section}, what explains {c.change_type} language versus prior filing?" for c in changes[:5]]
        return base or ["No deterministic flags triggered. Confirm missing data and filing coverage."]

    def draft_memo_shell(self, packet): return "Manual credit conclusion: Manual review required. No automated credit conclusion generated."

def guardrail_check(markdown: str):
    body = markdown.lower().split('## latest filing activity', 1)[-1]
    for pat in PROHIBITED_PATTERNS:
        if re.search(pat, body, flags=re.I):
            raise ValueError(f'Guardrail violation: prohibited phrase pattern {pat}')
