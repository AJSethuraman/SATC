import importlib
from pathlib import Path
import os
import pytest


def test_no_fake_bs4_package_dir():
    assert not Path('src/bs4').exists()


def test_no_fake_dotenv_package_dir():
    assert not Path('src/dotenv').exists()


def test_bs4_not_from_repo_shadow():
    pytest.importorskip('bs4')
    bs4 = importlib.import_module('bs4')
    assert '/workspace/SATC/credit_packet/src/bs4' not in str(getattr(bs4, '__file__', ''))


def test_dotenv_not_from_repo_shadow():
    pytest.importorskip('dotenv')
    dotenv = importlib.import_module('dotenv')
    assert '/workspace/SATC/credit_packet/src/dotenv' not in str(getattr(dotenv, '__file__', ''))


def test_run_sample_uses_sys_executable():
    src = Path('run_sample.py').read_text()
    assert 'sys.executable' in src
    assert "'credit-packet'" not in src and '"credit-packet"' not in src


def test_readme_quickstart_has_venv_commands():
    readme = Path('README.md').read_text()
    assert '.venv/bin/python run_sample.py' in readme
    assert '.venv\\Scripts\\python.exe run_sample.py' in readme


def test_readme_not_activation_only():
    readme = Path('README.md').read_text().lower()
    assert 'optional (if venv is activated)' in readme


def test_cli_importable():
    m = importlib.import_module('credit_packet.cli')
    assert hasattr(m, 'main')


def test_env_loading(monkeypatch, tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('SEC_USER_AGENT="Tester test@example.com"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    pytest.importorskip('dotenv')
    from dotenv import load_dotenv
    cfg = importlib.import_module('credit_packet.config')
    load_dotenv(env_file, override=False)
    s = cfg.get_settings()
    assert s.sec_user_agent.startswith('Tester')


def test_env_missing_error(monkeypatch):
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    cfg = importlib.import_module('credit_packet.config')
    if importlib.util.find_spec('dotenv') is None:
        with pytest.raises(RuntimeError):
            cfg.get_settings()
    else:
        with pytest.raises(ValueError):
            cfg.get_settings()


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
