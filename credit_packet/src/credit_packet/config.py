from dataclasses import dataclass
import os

@dataclass
class Settings:
    sec_user_agent: str
    llm_provider: str = 'none'
    ollama_base_url: str = 'http://localhost:11434'
    ollama_model: str = 'llama3.1'
    sec_base_submissions: str = 'https://data.sec.gov/submissions'
    sec_base_facts: str = 'https://data.sec.gov/api/xbrl/companyfacts'
    sec_ticker_url: str = 'https://www.sec.gov/files/company_tickers.json'
    request_timeout: int = 30
    rate_limit_seconds: float = 0.25


def get_settings() -> Settings:
    ua = os.getenv('SEC_USER_AGENT', '').strip()
    if not ua:
        raise ValueError('SEC_USER_AGENT must be set in environment or .env')
    return Settings(sec_user_agent=ua, llm_provider=os.getenv('LLM_PROVIDER', 'none'), ollama_base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'), ollama_model=os.getenv('OLLAMA_MODEL', 'llama3.1'))
