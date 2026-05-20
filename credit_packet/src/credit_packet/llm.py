import json, urllib.request, re
SYSTEM_PROMPT="You are a source-bound formatting assistant. You do not make credit judgments, investment recommendations, ratings, or unsupported inferences. Use only provided facts."
PROHIBITED_PATTERNS=[r'\bapprove\b',r'\bdecline\b',r'\bbuy\b',r'\bsell\b',r'\bhold\b',r'credit rating',r'investment recommendation']

class LLMClient:
    def __init__(self,settings): self.settings=settings
    def enabled(self): return self.settings.llm_provider=='ollama'
    def _call(self,prompt):
        if not self.enabled(): return None
        try:
            body=json.dumps({'model':self.settings.ollama_model,'system':SYSTEM_PROMPT,'prompt':prompt,'stream':False}).encode()
            req=urllib.request.Request(self.settings.ollama_base_url.rstrip('/')+'/api/generate',data=body,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=15) as r: return json.loads(r.read().decode()).get('response','').strip()
        except Exception: return None
    def generate_review_questions(self,flags,changes):
        base=[f"What evidence in filings explains flag {f.code} in period {f.period}?" for f in flags[:8]]+[f"For section {c.section}, what explains {c.change_type} language versus prior filing?" for c in changes[:5]]
        if not base: base=["No deterministic flags triggered. Confirm missing data and filing coverage."]
        return base
    def draft_memo_shell(self,packet): return "Manual credit conclusion: Manual review required. No automated credit conclusion generated."

def guardrail_check(markdown:str):
    body=markdown.lower().split('## latest filing activity',1)[-1]
    for pat in PROHIBITED_PATTERNS:
        for m in re.finditer(pat,body):
            ctx=body[max(0,m.start()-24):m.end()+24]
            if 'revenue_decline' in ctx:
                continue
            raise ValueError(f'Guardrail violation: prohibited phrase {m.group(0)}')
