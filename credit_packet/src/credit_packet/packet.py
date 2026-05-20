from .models import CompanyIdentity, ResearchPacket
from .cik_lookup import ticker_to_identity
from .filings import get_recent_filings
from .facts import normalize_periods
from .metrics import calculate_metrics
from .excerpts import find_excerpts
from .changes import detect_changes
from .rules import evaluate_rules
from .llm import LLMClient

def build_packet(client, settings, ticker: str, years: int = 3):
    t,cik,name=ticker_to_identity(client,ticker)
    company=CompanyIdentity(ticker=t,cik=cik,name=name)
    filings=get_recent_filings(client,cik)
    periods,facts_source=normalize_periods(client,cik,years)
    metrics=calculate_metrics(periods)
    excerpts=find_excerpts(filings)
    changes=detect_changes(excerpts)
    flags=evaluate_rules(periods,metrics,excerpts)
    llm=LLMClient(settings)
    questions=llm.generate_review_questions(flags, excerpts)
    packet=ResearchPacket(company=company, filings=filings, financial_periods=periods, calculated_metrics=metrics, watchlist_flags=flags, excerpts=excerpts, filing_changes=changes, review_questions=questions, memo_draft=llm.draft_memo_shell(None), audit_log=[f"ticker_lookup:{client.settings.sec_ticker_url}", f"submissions:{client.settings.sec_base_submissions}/CIK{cik}.json", f"facts:{facts_source}", f"llm_provider:{settings.llm_provider}"])
    return packet
