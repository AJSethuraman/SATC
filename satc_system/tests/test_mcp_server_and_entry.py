"""The agent's capability surface is decided by which tools get REGISTERED.

These tests pin two guarantees:
  * The MCP server is safe by default — only read/compute tools exist unless
    writes are explicitly enabled. An agent cannot call a tool that was never
    registered, so "safe by default" is a property of the wiring, not a rule we
    ask the model to follow.
  * The frozen entry point routes ``--mcp`` to the MCP server and everything else
    to the GUI app.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

import pytest

SAFE_TOOLS = {"list_clients", "get_client", "estimate_withholding", "read_paystub"}
WRITE_TOOLS = {"create_person_client", "create_business_client", "run_intake",
               "post_confirmed_intake", "set_document_status"}


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    return tmp_path


class _FakeMCP:
    """Stand-in for FastMCP that just records which tools get registered."""

    def __init__(self, name):
        self.name = name
        self.registered: list[str] = []

    def tool(self, *args, **kwargs):
        def deco(fn):
            self.registered.append(fn.__name__)
            return fn
        return deco

    def run(self):  # pragma: no cover - never called in these tests
        raise AssertionError("run() should not be called here")


@pytest.fixture()
def fake_mcp(monkeypatch):
    root = types.ModuleType("mcp")
    server = types.ModuleType("mcp.server")
    fastmcp = types.ModuleType("mcp.server.fastmcp")
    fastmcp.FastMCP = _FakeMCP
    monkeypatch.setitem(sys.modules, "mcp", root)
    monkeypatch.setitem(sys.modules, "mcp.server", server)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp)


def test_mcp_server_is_safe_by_default(data_dir, fake_mcp):
    from satc.api.mcp_server import _build_server
    server = _build_server()                       # default: allow_writes=False
    names = set(server.registered)
    assert names == SAFE_TOOLS                     # ONLY read/compute is exposed
    assert not (names & WRITE_TOOLS)               # no write tool exists to call


def test_mcp_writes_are_opt_in(data_dir, fake_mcp):
    from satc.api.mcp_server import _build_server
    names = set(_build_server(allow_writes=True).registered)
    assert SAFE_TOOLS <= names
    assert WRITE_TOOLS <= names                    # writes appear only when asked for


def test_main_keeps_writes_off_unless_env_set(data_dir, fake_mcp, monkeypatch):
    # main() must not enable writes unless SATC_MCP_ALLOW_WRITES is truthy.
    import satc.api.mcp_server as mcpsrv
    seen = {}

    def _capture(allow_writes=False):
        seen["allow_writes"] = allow_writes
        return types.SimpleNamespace(run=lambda: None)

    monkeypatch.setattr(mcpsrv, "_build_server", _capture)
    monkeypatch.delenv("SATC_MCP_ALLOW_WRITES", raising=False)
    mcpsrv.main()
    assert seen["allow_writes"] is False
    monkeypatch.setenv("SATC_MCP_ALLOW_WRITES", "1")
    mcpsrv.main()
    assert seen["allow_writes"] is True


def _load_entry():
    path = os.path.join(os.path.dirname(__file__), "..", "packaging", "entry.py")
    spec = importlib.util.spec_from_file_location("satc_packaging_entry", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_entry_defaults_to_the_gui_app(data_dir, monkeypatch):
    import satc.api.mcp_server as mcpsrv
    import satc.app.server as appsrv
    calls = []
    monkeypatch.setattr(appsrv, "main", lambda *a, **k: calls.append("app"))
    monkeypatch.setattr(mcpsrv, "main", lambda *a, **k: calls.append("mcp"))
    _load_entry().main([])
    assert calls == ["app"]


def test_entry_mcp_flag_routes_to_the_agent(data_dir, monkeypatch):
    import satc.api.mcp_server as mcpsrv
    import satc.app.server as appsrv
    calls = []
    monkeypatch.setattr(appsrv, "main", lambda *a, **k: calls.append("app"))
    monkeypatch.setattr(mcpsrv, "main", lambda *a, **k: calls.append("mcp"))
    _load_entry().main(["--mcp"])
    assert calls == ["mcp"]
