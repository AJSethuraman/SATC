from __future__ import annotations
import re
from dataclasses import dataclass, field

PROHIBITED=[r"\brecommend\s+approval\b",r"\brecommend\s+decline\b",r"\bapproved\s+for\s+credit\b",r"\bdeclined\s+for\s+credit\b",r"\bbuy\s+rating\b",r"\bsell\s+rating\b",r"\bhold\s+rating\b",r"\binvestment\s+recommendation\b",r"\bcredit\s+rating\s*:",r"\brisk\s+rating\s*:",r"\bshould\s+lend\b",r"\bshould\s+not\s+lend\b",r"\bsafe\s+investment\b",r"\bgood\s+credit\s+risk\b",r"\bbad\s+credit\s+risk\b"]

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _nums(text:str):
    return re.findall(r"(?<![A-Za-z:])[-+]?\d+(?:\.\d+)?%?", text)


def validate_source_bound_output(payload: dict, valid_ids:set[str], allowed_values:set[str]) -> ValidationResult:
    errs=[]; warns=[]
    for k in ('summary_points','review_themes','review_questions','missing_information'):
        if k not in payload: errs.append(f'missing key {k}')
    if errs: return ValidationResult(False,errs,warns)

    def chk_sources(arr,key,src_key):
        for i,it in enumerate(arr):
            if not (it.get(key) or '').strip(): errs.append(f'{key} empty {i}')
            srcs=it.get(src_key,[])
            if not srcs: errs.append(f'{src_key} empty {i}')
            for s in srcs:
                if s not in valid_ids: errs.append(f'invalid source id {s}')

    chk_sources(payload['summary_points'],'text','sources')
    chk_sources(payload['review_themes'],'theme','sources')
    for i,it in enumerate(payload['review_themes']):
        if not (it.get('why_it_matters') or '').strip(): errs.append(f'why_it_matters empty {i}')
    chk_sources(payload['review_questions'],'question','based_on')

    text_fields=[]
    for it in payload.get('summary_points',[]): text_fields.append(str(it.get('text','')))
    for it in payload.get('review_themes',[]): text_fields.extend([str(it.get('theme','')),str(it.get('why_it_matters',''))])
    for it in payload.get('review_questions',[]): text_fields.append(str(it.get('question','')))
    for it in payload.get('missing_information',[]): text_fields.extend([str(it.get('item','')),str(it.get('reason',''))])
    joined=' '.join(text_fields).lower()
    for pat in PROHIBITED:
        if re.search(pat,joined,re.I): errs.append(f'prohibited phrase {pat}')

    allowed=allowed_values | {v.replace('%','') for v in allowed_values}
    for n in _nums(joined):
        if ':' in n: continue
        if n not in allowed and n.rstrip('%') not in allowed:
            errs.append(f'unsupported numeric value {n}')
            break
    return ValidationResult(len(errs)==0,errs,warns)
