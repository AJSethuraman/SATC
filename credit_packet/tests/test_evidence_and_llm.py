from credit_packet.models import *
from credit_packet.evidence import build_evidence_bundle, valid_evidence_ids, allowed_values, compact_evidence_for_llm
from credit_packet.llm_validate import validate_source_bound_output
from credit_packet.llm import LLMClient, extract_json_object, normalize_schema_aliases, unwrap_known_envelope
import json

class S:
    llm_provider='none'; ollama_model='x'; ollama_base_url='http://localhost:11434'

class SOllama:
    llm_provider='ollama'; ollama_model='x'; ollama_base_url='http://localhost:11434'

def pkt(no_flags=False, excerpt_text="cash declined 10% on 2025-01-01"):
    flags=[] if no_flags else [WatchlistFlag(code='NEGATIVE_FREE_CASH_FLOW',severity='high',description='d',metric='m',threshold='<0',observed_value='-5',period='2024',source='metrics')]
    return ResearchPacket(company=CompanyIdentity('ABC','0001','ABC Inc'),filings=[FilingRecord(accession_number='0001-01',form='10-K',filing_date='2025-01-01',report_date='2024-12-31',filing_url='u'),FilingRecord(accession_number='0001-02',form='10-Q',filing_date='2025-04-01',report_date='2025-03-31',filing_url='u2'),FilingRecord(accession_number='0001-03',form='8-K',filing_date='2025-05-01',report_date='2025-05-01',filing_url='u3')],calculated_metrics=[CalculatedMetric(fiscal_year=2024,revenue_growth=-0.1,free_cash_flow=-5)],watchlist_flags=flags,excerpts=[Excerpt(filing='10-K',section='Risk',category='liquidity',text=excerpt_text,matched_keywords=['cash'],source_url='u',accession_number='a',filing_date='2025-01-01')],filing_changes=[FilingChange(section='Risk',category='liquidity',old_excerpt='a 15%',new_excerpt='b 12%',change_type='modified',similarity_score=0.8,source_old='o',source_new='n')],audit_log=['llm_provider:none'])

def test_extract_json_object_direct():
    assert extract_json_object('{"a":1}') == {'a':1}

def test_extract_json_object_json_fence():
    assert extract_json_object('```json\n{"a":1}\n```') == {'a':1}

def test_extract_json_object_plain_fence():
    assert extract_json_object('```\n{"a":1}\n```') == {'a':1}

def test_extract_json_object_rejects_prose_before():
    assert extract_json_object('Here\n{"a":1}') is None

def test_extract_json_object_rejects_prose_after():
    assert extract_json_object('{"a":1}\nthanks') is None

def test_extract_json_object_malformed_none():
    assert extract_json_object('{"a":') is None

def test_extract_json_object_non_dict_none():
    assert extract_json_object('[1,2,3]') is None



def test_normalize_schema_aliases_maps_expected_keys():
    payload={'summary':[],'themes':[],'questions':[],'missing_info':[]}
    out, changed = normalize_schema_aliases(payload)
    assert changed and set(out.keys())=={'summary_points','review_themes','review_questions','missing_information'}

def test_prompt_contains_required_empty_skeleton():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    captured={}
    def fake_call(prompt, timeout=90):
        captured['prompt']=prompt
        return '{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]}'
    c._call=fake_call
    c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert '"summary_points": []' in captured['prompt']
    assert '"review_themes": []' in captured['prompt']
    assert '"review_questions": []' in captured['prompt']
    assert '"missing_information": []' in captured['prompt']

def test_missing_required_keys_falls_back():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"summary":[],"themes":[]}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback'


def test_alias_schema_normalized_then_validated():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"summary":[],"themes":[],"questions":[],"missing_info":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='ollama' and 'normalized LLM schema aliases' in brief.validation_notes

def test_alias_normalized_unsafe_still_fails_validation():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"summary":[{"text":"recommend approval","sources":["bad:id"]}],"themes":[],"questions":[],"missing_info":[]}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and brief.validation_notes
def test_evidence_bundle_creation_and_stable_ids():
    b1=build_evidence_bundle(pkt()); b2=build_evidence_bundle(pkt())
    assert b1['filings'][0]['id']==b2['filings'][0]['id']

def test_forms_and_dates_allowed_values():
    b=build_evidence_bundle(pkt()); av=allowed_values(b)
    assert '10-K' in av and '10-Q' in av and '8-K' in av and '2025-01-01' in av

def test_valid_source_bound_json_passes():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'Free cash flow is -5 in 2024 and reviewed in 10-K on 2025-01-01','sources':[b['filings'][0]['id']]}],'review_themes':[{'theme':'Liquidity','why_it_matters':'Flag was triggered','sources':[b['flags'][0]['id']]}],'review_questions':[{'question':'What explains negative FCF?','based_on':[b['flags'][0]['id']]}],'missing_information':[{'item':'Debt maturity schedule','reason':'Not in bundle'}]}
    assert validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_invalid_source_id_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'x','sources':['bad:id']}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['filings'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['filings'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_prohibited_phrase_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'recommend approval','sources':[b['filings'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['filings'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['filings'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_unsupported_metric_like_number_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'Revenue growth was 999.9%','sources':[b['metrics'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['filings'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['filings'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_missing_information_empty_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'ok -5','sources':[b['flags'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['flags'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['flags'][0]['id']]}],'missing_information':[{'item':'','reason':''}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_ollama_request_body_includes_format_json(monkeypatch):
    c=LLMClient(SOllama())
    captured={}
    class Resp:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self): return b'{"response":"{}"}'
    def fake_urlopen(req, timeout=0):
        captured['body']=json.loads(req.data.decode())
        return Resp()
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    c._call('p', timeout=1)
    assert captured['body']['format']=='json'





def test_compact_evidence_limits_arrays_and_preserves_ids():
    b=build_evidence_bundle(pkt())
    # inflate arrays
    b['metrics']=b['metrics']*5
    b['flags']=b['flags']*5
    b['excerpts']=b['excerpts']*30
    b['filing_changes']=b['filing_changes']*20
    c=compact_evidence_for_llm(b,max_filings=2,max_metrics=3,max_flags=4,max_excerpts=5,max_changes=6)
    assert len(c['filings'])<=2 and len(c['metrics'])<=3 and len(c['flags'])<=4 and len(c['excerpts'])<=5 and len(c['filing_changes'])<=6
    assert all(x['id'] for x in c['filings']+c['metrics']+c['flags']+c['excerpts']+c['filing_changes'])


def test_compact_prioritizes_high_severity_flags():
    b=build_evidence_bundle(pkt())
    b['flags']=[
        {'id':'flag:1','severity':'low','period':'2024'},
        {'id':'flag:2','severity':'high','period':'2024'},
        {'id':'flag:3','severity':'medium','period':'2024'},
    ]
    c=compact_evidence_for_llm(b,max_flags=1)
    assert c['flags'][0]['severity']=='high'


def test_compact_includes_material_weakness_excerpt_when_present():
    b=build_evidence_bundle(pkt())
    b['excerpts']=[
        {'id':'excerpt:liquidity:001','category':'liquidity','section':'Risk','text':'liquidity note','filing_date':'2025-01-01'},
        {'id':'excerpt:material_weakness:002','category':'material_weakness','section':'Controls','text':'material weakness in internal control', 'filing_date':'2025-01-01'}
    ]
    c=compact_evidence_for_llm(b,max_excerpts=1)
    assert c['excerpts'][0]['id']=='excerpt:material_weakness:002'
def test_unwrap_response_valid_schema_passes():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"response":{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]}}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='ollama'


def test_unwrap_data_valid_schema_passes():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"data":{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]}}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='ollama'


def test_wrapper_string_does_not_unwrap():
    payload={'response':'not-a-dict'}
    out, changed = unwrap_known_envelope(payload)
    assert not changed and out==payload


def test_validation_failure_notes_include_top_level_keys():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"response":{},"analysis":{}}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback'
    assert any('LLM returned top-level keys: response, analysis' in n for n in brief.validation_notes)


def test_unsafe_nested_content_still_fails():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"response":{"summary_points":[{"text":"recommend approval","sources":["bad:id"]}],"review_themes":[],"review_questions":[],"missing_information":[]}}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and brief.validation_notes
def test_generate_source_bound_brief_accepts_fenced_json():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '```json\n{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]}\n```'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='ollama' and brief.validation_status=='valid'

def test_generate_source_bound_brief_validation_still_applied():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '{"summary_points":[{"text":"recommend approval","sources":["bad:id"]}],"review_themes":[],"review_questions":[],"missing_information":[]}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and brief.validation_notes

def test_prose_response_fallback_parseable_json_error():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: 'Here is your JSON:\n{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[]}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and any('parseable JSON' in n for n in brief.validation_notes)

def test_empty_response_fallback_note():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: ''
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and 'Ollama returned empty response' in brief.validation_notes

def test_timeout_response_fallback_note():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=90: '[[OLLAMA_TIMEOUT]]'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and 'Ollama request timed out' in brief.validation_notes

def test_no_llm_fallback_has_sourced_points_without_flags():
    b=build_evidence_bundle(pkt(no_flags=True))
    brief=LLMClient(S()).generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.summary_points and all(p.sources for p in brief.summary_points)


def test_10_percent_rejected_if_not_in_bundle():
    b=build_evidence_bundle(pkt(excerpt_text='cash declined on date 2025-01-01'))
    payload={'summary_points':[{'text':'Liquidity fell by 10%','sources':[b['filings'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['filings'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['filings'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_8_percent_rejected_if_not_in_bundle():
    b=build_evidence_bundle(pkt(excerpt_text='cash declined on date 2025-01-01'))
    payload={'summary_points':[{'text':'Margin moved by 8%','sources':[b['filings'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['filings'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['filings'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid


def test_generate_source_bound_brief_uses_compact_bundle(monkeypatch):
    b=build_evidence_bundle(pkt())
    b['metrics']=b['metrics']*20
    c=LLMClient(SOllama())
    seen={}
    def fake_call(prompt, timeout=90):
        seen['prompt']=prompt
        return '{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[{"item":"Debt maturity schedule","reason":"Not present in the provided evidence bundle."}]}'
    c._call=fake_call
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='ollama'
    assert 'compact evidence bundle selected from a larger packet' in seen['prompt'].lower()
    assert any('compact_llm_evidence:' in n for n in brief.validation_notes)
