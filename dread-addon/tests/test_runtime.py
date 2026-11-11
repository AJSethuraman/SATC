"""The two-Lua setup in conftest.py really switches runtimes, so a pass on 'lua-5.1' means it ran on Lua 5.1."""
import lupa


def test_the_runtime_matches_the_fixture(lua_version):
    version = lupa.LuaRuntime().eval("_VERSION")
    if lua_version == "lua-5.1":
        assert version == "Lua 5.1"
    else:
        assert version != "Lua 5.1"
