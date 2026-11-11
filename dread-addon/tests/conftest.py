"""Every test in this folder runs twice: on the newer Lua that lupa defaults to, and on Lua 5.1, which is what WoW runs.
Several things behave differently (a function may use at most 60 outside variables, numbers are all doubles, string.format
is stricter or looser), and the first version of the window passed every test on the newer Lua and would not have loaded in the game."""
import pytest

lupa = pytest.importorskip("lupa")


@pytest.fixture(params=["newer-lua", "lua-5.1"], autouse=True)
def lua_version(request, monkeypatch):
    if request.param == "lua-5.1":
        l51 = pytest.importorskip("lupa.lua51")
        monkeypatch.setattr(lupa, "LuaRuntime", l51.LuaRuntime)
    return request.param
