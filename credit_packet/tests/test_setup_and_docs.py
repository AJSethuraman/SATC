import importlib
from pathlib import Path
import pytest

from credit_packet.config import get_settings


def test_cli_importable():
    m = importlib.import_module('credit_packet.cli')
    assert hasattr(m, 'main')


def test_env_loading(monkeypatch, tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('SEC_USER_AGENT="Tester test@example.com"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    import credit_packet.config as cfg
    cfg.load_dotenv(env_file, override=False)
    s = get_settings()
    assert s.sec_user_agent.startswith('Tester')


def test_env_missing_error(monkeypatch):
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    with pytest.raises(ValueError):
        get_settings()


def test_filing_text_uses_bs4_import():
    src = Path('src/credit_packet/filing_text.py').read_text()
    assert 'from bs4 import BeautifulSoup' in src


def test_docs_do_not_require_pythonpath():
    readme = Path('README.md').read_text().lower()
    assert 'pythonpath' not in readme


def test_sample_output_has_full_sections():
    sample = Path('examples/sample_packet.md').read_text()
    required = [
        '## Important Limitation',
        '## Latest Filing Activity',
        '## Annual Financial Trends',
        '## Calculated Metrics',
        '## Rule-Based Watchlist Flags',
        '## Debt, Liquidity, and Risk Excerpts',
        '## Filing Language Changes',
        '## Questions for Human Review',
        '## Memo Shell',
        '## Source and Audit Trail',
    ]
    for r in required:
        assert r in sample
