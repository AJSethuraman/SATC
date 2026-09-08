"""The year in the header is derived, and no intake door assumes one.

TWO HARDCODED 2024s, FOUND ON 5 SEPTEMBER 2026 -- one by walking the app and one
by re-reading the fix for the first.

`base.html` carried

    <span class="who">A. Sethuraman · TY2024</span>

as a literal, so **every screen of the app** announced tax year 2024 in September
2026, whatever the practice was actually working on. `working_tax_year` has
existed the whole time and its own docstring says exactly why it exists --
*"rather than hardcoded, because a constant here goes stale silently"*. The
header was that constant. It is in the corner of all sixty-five screenshots
taken during the walk and went unnoticed in every one.

AND THE SAME DEFAULT SURVIVED ON THE DOORS A MODEL USES. Removing
`tax_year: int = 2024` from `AppState.run_intake` left it standing in four
signatures on the API and MCP layer:

    api/tools.py       run_intake(...,             tax_year: int = 2024)
    api/tools.py       post_confirmed_intake(...,  tax_year: int = 2024)
    api/mcp_server.py  run_intake(...,             tax_year: int = 2024)
    api/mcp_server.py  post_confirmed_intake(...,  tax_year: int = 2024)

which is precisely the failure the fix's own commit message described -- a guard
on the door that was walked, and none on the doors that were not. Worse here than
on the web path: this is the door an `ai_staff` principal reaches, and a model
that omits the year would have filed a client's documents into the prior year
without anything on any screen to show for it.
"""
from __future__ import annotations

import inspect
import pathlib

import pytest

from satc.app.server import create_app


def test_the_header_carries_no_hardcoded_year():
    """The literal itself, so it cannot come back by copy-paste."""
    base = (pathlib.Path(__file__).resolve().parents[1]
            / "src" / "satc" / "app" / "templates" / "base.html")
    text = base.read_text(encoding="utf-8")
    assert "TY2024" not in text, "the header is a hardcoded year again"
    assert "TY{{ working_year }}" in text


def test_the_header_follows_the_practice_rather_than_the_calendar(monkeypatch):
    """It has to MOVE. Asserting only that the literal is gone would pass against
    a variable wired to something equally fixed."""
    from satc.app import server

    class _Row:
        def __init__(self, year):
            self.tax_year = year

    monkeypatch.setattr(server.STATE, "received_documents", lambda: [_Row(2027)])
    monkeypatch.setattr(server.STATE, "requested_items", lambda: [])

    body = create_app().test_client().get("/").get_data(as_text=True)
    assert "TY2027" in body, "the header did not follow the practice's own year"
    assert "TY2024" not in body


@pytest.mark.parametrize("func_path", [
    ("satc.api.tools", "run_intake"),
    ("satc.api.tools", "post_confirmed_intake"),
])
def test_no_intake_door_defaults_the_tax_year(func_path):
    """The API layer. A year is not a preference with a sensible fallback."""
    import importlib

    module, name = func_path
    func = getattr(importlib.import_module(module), name)
    param = inspect.signature(func).parameters["tax_year"]
    assert param.default is inspect.Parameter.empty, (
        f"{module}.{name} still defaults tax_year to {param.default!r} -- the "
        f"same default that was removed from the engine")


def test_the_mcp_tools_do_not_default_it_either():
    """The MCP tools are defined inside a factory, so read the source rather than
    the signature -- the check has to reach the door an agent actually calls."""
    src = pathlib.Path(inspect.getfile(
        __import__("satc.api.mcp_server", fromlist=["x"]))).read_text(encoding="utf-8")
    assert "tax_year: int = 2024" not in src, (
        "an MCP tool still defaults the tax year to 2024")
