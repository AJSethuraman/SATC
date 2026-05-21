from credit_packet.models import *
from credit_packet.evidence import build_evidence_bundle, valid_evidence_ids, allowed_values
from credit_packet.llm_validate import validate_source_bound_output
from credit_packet.llm import LLMClient

class S:
    llm_provider='none'; ollama_model='x'; ollama_base_url='http://localhost:11434'

def pkt():
    return ResearchPacket(company=CompanyIdentity('ABC','0001','ABC Inc'),filings=[FilingRecord(accession_number='0001-01',form='10-K',filing_date='2025-01-01',filing_url='u')],calculated_metrics=[CalculatedMetric(fiscal_year=2024,revenue_growth=-0.1,free_cash_flow=-5)],watchlist_flags=[WatchlistFlag(code='NEGATIVE_FREE_CASH_FLOW',severity='high',description='d',metric='m',threshold='<0',observed_value='-5',period='2024',source='metrics')],excerpts=[Excerpt(filing='10-K',section='Risk',category='liquidity',text='cash declined 10%',matched_keywords=['cash'],source_url='u',accession_number='a',filing_date='2025-01-01')],filing_changes=[FilingChange(section='Risk',category='liquidity',old_excerpt='a',new_excerpt='b',change_type='modified',similarity_score=0.8,source_old='o',source_new='n')],audit_log=['llm_provider:none'])

def test_evidence_bundle_creation_and_stable_ids():
    b1=build_evidence_bundle(pkt()); b2=build_evidence_bundle(pkt())
    assert b1['filings'][0]['id']==b2['filings'][0]['id']

def test_valid_source_bound_json_passes():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'Free cash flow is -5','sources':[b['flags'][0]['id']]}],'review_themes':[{'theme':'Liquidity','why_it_matters':'Flag was triggered','sources':[b['flags'][0]['id']]}],'review_questions':[{'question':'What explains negative FCF?','based_on':[b['flags'][0]['id']]}],'missing_information':[{'item':'Debt maturity schedule','reason':'Not in bundle'}]}
    r=validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)); assert r.is_valid

def test_invalid_source_id_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'x','sources':['bad:id']}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['flags'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['flags'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_prohibited_phrase_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'recommend approval','sources':[b['flags'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['flags'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['flags'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_numeric_hallucination_rejected():
    b=build_evidence_bundle(pkt())
    payload={'summary_points':[{'text':'Revenue growth was 99%','sources':[b['metrics'][0]['id']]}],'review_themes':[{'theme':'t','why_it_matters':'w','sources':[b['flags'][0]['id']]}],'review_questions':[{'question':'q','based_on':[b['flags'][0]['id']]}],'missing_information':[{'item':'i','reason':'r'}]}
    assert not validate_source_bound_output(payload,valid_evidence_ids(b),allowed_values(b)).is_valid

def test_no_llm_deterministic_fallback():
    b=build_evidence_bundle(pkt())
    brief=LLMClient(S()).generate_source_bound_brief(b,valid_evidence_ids(b),allowed_values(b))
    assert brief.generation_mode.startswith('deterministic') and brief.summary_points
