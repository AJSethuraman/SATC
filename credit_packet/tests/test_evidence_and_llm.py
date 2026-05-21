from credit_packet.models import *
from credit_packet.evidence import build_evidence_bundle, valid_evidence_ids, allowed_values
from credit_packet.llm_validate import validate_source_bound_output
from credit_packet.llm import LLMClient

class S:
    llm_provider='none'; ollama_model='x'; ollama_base_url='http://localhost:11434'

class SOllama:
    llm_provider='ollama'; ollama_model='x'; ollama_base_url='http://localhost:11434'

def pkt(no_flags=False):
    flags=[] if no_flags else [WatchlistFlag(code='NEGATIVE_FREE_CASH_FLOW',severity='high',description='d',metric='m',threshold='<0',observed_value='-5',period='2024',source='metrics')]
    return ResearchPacket(company=CompanyIdentity('ABC','0001','ABC Inc'),filings=[FilingRecord(accession_number='0001-01',form='10-K',filing_date='2025-01-01',report_date='2024-12-31',filing_url='u'),FilingRecord(accession_number='0001-02',form='10-Q',filing_date='2025-04-01',report_date='2025-03-31',filing_url='u2'),FilingRecord(accession_number='0001-03',form='8-K',filing_date='2025-05-01',report_date='2025-05-01',filing_url='u3')],calculated_metrics=[CalculatedMetric(fiscal_year=2024,revenue_growth=-0.1,free_cash_flow=-5)],watchlist_flags=flags,excerpts=[Excerpt(filing='10-K',section='Risk',category='liquidity',text='cash declined 10% on 2025-01-01',matched_keywords=['cash'],source_url='u',accession_number='a',filing_date='2025-01-01')],filing_changes=[FilingChange(section='Risk',category='liquidity',old_excerpt='a 15%',new_excerpt='b 12%',change_type='modified',similarity_score=0.8,source_old='o',source_new='n')],audit_log=['llm_provider:none'])

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

def test_llm_prose_before_json_fallback():
    b=build_evidence_bundle(pkt())
    c=LLMClient(SOllama())
    c._call=lambda prompt, timeout=20: 'Here is your JSON:\n{"summary_points":[],"review_themes":[],"review_questions":[],"missing_information":[]}'
    brief=c.generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode=='deterministic_fallback' and any('prose before JSON' in n for n in brief.validation_notes)

def test_no_llm_fallback_has_sourced_points_without_flags():
    b=build_evidence_bundle(pkt(no_flags=True))
    brief=LLMClient(S()).generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.summary_points and all(p.sources for p in brief.summary_points)
