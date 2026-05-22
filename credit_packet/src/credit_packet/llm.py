import json
import re
import urllib.error
import urllib.request
from .models import SourceBoundBrief, BriefPoint, ReviewTheme, ReviewQuestionItem, MissingInformation
from .llm_validate import validate_source_bound_output

SYSTEM_PROMPT = "You are a source-bound research packet assistant. Use only the provided evidence bundle. Do not use outside knowledge. Do not make credit, investment, legal, tax, approval, decline, buy, sell, or rating recommendations. Do not assign ratings or scores. Every substantive claim must cite one or more source IDs from the evidence bundle. Do not invent numbers. Only use numeric values present in the evidence bundle. If evidence is insufficient, state what is missing. Output JSON only with no prose before or after."
PROHIBITED_PATTERNS=[r"\brecommend\s+approval\b",r"\brecommend\s+decline\b",r"\bapproved\s+for\s+credit\b",r"\bdeclined\s+for\s+credit\b",r"\bbuy\s+rating\b",r"\bsell\s+rating\b",r"\bhold\s+rating\b",r"\binvestment\s+recommendation\b",r"\bcredit\s+rating\s*:",r"\brisk\s+rating\s*:"]


def extract_json_object(raw: str) -> dict | None:
    if raw is None:
        return None
    text=raw.strip()
    if not text:
        return None
    candidate=None
    if text.startswith('{'):
        candidate=text
    else:
        m=re.fullmatch(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.I)
        if not m:
            return None
        candidate=m.group(1).strip()
    try:
        parsed=json.loads(candidate)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None

def normalize_schema_aliases(payload: dict) -> tuple[dict, bool]:
    alias_map={
        'summary':'summary_points',
        'themes':'review_themes',
        'questions':'review_questions',
        'missing_info':'missing_information',
    }
    out=dict(payload)
    normalized=False
    for old,new in alias_map.items():
        if new not in out and old in out:
            out[new]=out.pop(old)
            normalized=True
    return out, normalized


class LLMClient:
    def __init__(self, settings): self.settings = settings
    def enabled(self): return self.settings.llm_provider == 'ollama'
    def _call(self, prompt, timeout=20):
        if not self.enabled(): return None
        try:
            body = json.dumps({'model': self.settings.ollama_model, 'system': SYSTEM_PROMPT, 'prompt': prompt, 'stream': False, 'format': 'json'}).encode()
            req = urllib.request.Request(self.settings.ollama_base_url.rstrip('/') + '/api/generate', data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode()).get('response', '')
        except TimeoutError:
            return '[[OLLAMA_TIMEOUT]]'
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, 'reason', None), TimeoutError):
                return '[[OLLAMA_TIMEOUT]]'
            return None
        except Exception:
            return None

    def _fallback_brief(self, bundle, notes=None):
        notes=notes or []
        flags=bundle.get('flags',[])
        severity_counts={s:sum(1 for f in flags if f.get('severity')==s) for s in ('high','medium','low','info')}
        sps=[]
        filings=bundle.get('filings',[])
        if filings:
            lf=filings[0]
            sps.append(BriefPoint(text=f"Latest filing reviewed: {lf.get('form')} filed {lf.get('filing_date')}.",sources=[lf['id']]))
        sps.append(BriefPoint(text=f"Watchlist flag counts - high:{severity_counts['high']} medium:{severity_counts['medium']} low:{severity_counts['low']} info:{severity_counts['info']}.",sources=[f['id'] for f in flags[:3]] or [bundle.get('company',{}).get('id','company')]))
        for f in flags:
            if f.get('severity')=='high' and f.get('source') and str(f.get('source','')).startswith('http'):
                filing=f.get('filing') or f.get('period') or 'filing'
                section=f.get('section') or 'section'
                sps.append(BriefPoint(text=f"{f.get('description')} in {filing} / {section}. Review the linked excerpt.",sources=[f['id']]))
                if len([x for x in sps if 'Review the linked excerpt' in x.text])>=2:
                    break
        for c in bundle.get('filing_changes',[])[:2]: sps.append(BriefPoint(text=f"Filing change in {c.get('section')} ({c.get('change_type')}).",sources=[c['id']]))
        for e in bundle.get('excerpts',[])[:2]: sps.append(BriefPoint(text=f"Excerpt category {e.get('category')} from {e.get('filing')}.",sources=[e['id']]))
        if not sps:
            sps=[BriefPoint(text=f"Metric available: {m['label']} {m.get('value')}",sources=[m['id']]) for m in bundle.get('metrics',[])[:5]]
        themes=[ReviewTheme(theme='Watchlist Flags',why_it_matters='Deterministic rules and filing evidence should be reviewed by a human analyst.',sources=[f['id'] for f in flags[:3]] or [bundle.get('company',{}).get('id','company')])]
        qs=[ReviewQuestionItem(question=f"What filing evidence explains {f['code']} in {f.get('period')}?",based_on=[f['id']]) for f in flags[:5]]
        if not qs: qs=[ReviewQuestionItem(question='Which material data fields are unavailable and require manual sourcing?',based_on=[bundle.get('company',{}).get('id','company')])]
        missing=[MissingInformation(item='Debt maturity schedule',reason='Not explicitly normalized in current evidence bundle.')]
        return SourceBoundBrief(summary_points=sps,review_themes=themes,review_questions=qs,missing_information=missing,generation_mode='deterministic_fallback',validation_status='fallback',validation_notes=notes)

    def generate_source_bound_brief(self, evidence_bundle, valid_ids, allowed_values):
        if not self.enabled(): return self._fallback_brief(evidence_bundle,['LLM disabled'])
        ids = list(valid_ids)
        sid = ids[0] if ids else 'company:example'
        tid = ids[1] if len(ids) > 1 else sid
        qid = ids[2] if len(ids) > 2 else sid
        concrete_example={
          "summary_points":[{"text":"Watchlist flag detected and requires manual review.","sources":[sid]}],
          "review_themes":[{"theme":"Liquidity","why_it_matters":"A deterministic trigger appears in the evidence bundle.","sources":[tid]}],
          "review_questions":[{"question":"What filing evidence explains this trigger?","based_on":[qid]}],
          "missing_information":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]
        }
        required_skeleton={
          "summary_points": [],
          "review_themes": [],
          "review_questions": [],
          "missing_information": []
        }
        prompt=(
            'Return a single JSON object only. No prose before or after. '
            'The object MUST contain exactly these top-level keys: '
            'summary_points, review_themes, review_questions, missing_information. '
            'Do not use keys like summary, themes, questions, missing_info, notes, analysis, or response. '
            'If no items exist for a key, return an empty array for that key.\n'
            'Required empty skeleton:\n'
            + json.dumps(required_skeleton, indent=2)
            + '\nConcrete valid example (use bundle IDs, do not invent IDs):\n'
            + json.dumps(concrete_example, indent=2)
            + '\nEvidence bundle:\n'
            + json.dumps(evidence_bundle)
        )
        raw=self._call(prompt, timeout=90)
        if raw is None: return self._fallback_brief(evidence_bundle,['LLM unavailable'])
        if raw == '[[OLLAMA_TIMEOUT]]': return self._fallback_brief(evidence_bundle,['Ollama request timed out'])
        if not str(raw).strip(): return self._fallback_brief(evidence_bundle,['Ollama returned empty response'])
        payload=extract_json_object(str(raw))
        if payload is None: return self._fallback_brief(evidence_bundle,['LLM did not return parseable JSON'])
        payload, normalized = normalize_schema_aliases(payload)
        notes=['normalized LLM schema aliases'] if normalized else []
        vr=validate_source_bound_output(payload,valid_ids,allowed_values)
        if not vr.is_valid: return self._fallback_brief(evidence_bundle,notes + vr.errors)
        return SourceBoundBrief(summary_points=[BriefPoint(**x) for x in payload.get('summary_points',[])],review_themes=[ReviewTheme(**x) for x in payload.get('review_themes',[])],review_questions=[ReviewQuestionItem(**x) for x in payload.get('review_questions',[])],missing_information=[MissingInformation(**x) for x in payload.get('missing_information',[])],generation_mode='ollama',validation_status='valid',validation_notes=notes + vr.warnings)

    def generate_review_questions(self, flags, changes):
        base = [f"What evidence in filings explains flag {f.code} in period {f.period}?" for f in flags[:8]] + [f"For section {c.section}, what explains {c.change_type} language versus prior filing?" for c in changes[:5]]
        return base or ["No deterministic flags triggered. Confirm missing data and filing coverage."]

    def draft_memo_shell(self, packet): return "Manual credit conclusion: Manual review required. No automated credit conclusion generated."

def guardrail_check(markdown: str):
    body = markdown.lower().split('## latest filing activity', 1)[-1]
    for pat in PROHIBITED_PATTERNS:
        if re.search(pat, body, flags=re.I):
            raise ValueError(f'Guardrail violation: prohibited phrase pattern {pat}')
