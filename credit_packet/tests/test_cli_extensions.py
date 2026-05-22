import pytest
from credit_packet import cli


def test_unsupported_extension_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, 'get_settings', lambda: object())
    class DummyClient: pass
    monkeypatch.setattr(cli, 'SECClient', lambda settings: DummyClient())
    class P: company=type('C',(),{'ticker':'AAPL'})()
    monkeypatch.setattr(cli, 'build_packet', lambda *a, **k: P())
    monkeypatch.setattr(cli, 'render_markdown', lambda p: 'x')
    monkeypatch.setattr('sys.argv', ['prog','build','--ticker','AAPL','--output',str(tmp_path/'x.txt')])
    with pytest.raises(ValueError):
        cli.main()
