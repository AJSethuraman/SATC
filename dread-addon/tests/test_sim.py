"""Runs Dread/Sim.lua under plain Lua (lupa). Sim.lua has no WoW calls, so this is all of Test 1's logic
except the drawing, which only the game can check."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")

SIM = Path(__file__).resolve().parents[1] / "Dread" / "Sim.lua"


@pytest.fixture()
def sim():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    lua.eval("function(path, ns) return loadfile(path)('Dread', ns) end")(str(SIM), ns)
    return lua, ns.Sim


def test_same_seed_same_world(sim):
    lua, S = sim
    a, b = S.new(100, 600, 400, 7), S.new(100, 600, 400, 7)
    for _ in range(50):
        S.step(a, 1 / 60); S.step(b, 1 / 60)
    assert all(a.objs[i].x == b.objs[i].x and a.objs[i].y == b.objs[i].y for i in range(1, 101))


def test_objects_never_leave_the_arena(sim):
    lua, S = sim
    w = S.new(100, 600, 400, 3)
    for _ in range(5000):
        S.step(w, 1 / 30)
    assert all(0 <= w.objs[i].x <= 600 and 0 <= w.objs[i].y <= 400 for i in range(1, 101))


def test_a_wall_hit_reverses_the_velocity(sim):
    lua, S = sim
    w = lua.eval("{w=100,h=100,objs={{x=99,y=50,vx=10,vy=0}}}")
    S.step(w, 1)
    o = w.objs[1]
    assert o.x == 91 and o.vx == -10


def test_verdict_pass_and_each_way_to_fail(sim):
    lua, S = sim
    ok = lua.table_from([60] * 300)
    assert S.verdict(ok, 1000, 1050)[0] == "PASS"
    assert S.verdict(lua.table_from([60] * 299 + [25]), 1000, 1000)[0] == "FAIL"   # one dip under 30
    assert S.verdict(ok, 1000, 1200)[0] == "FAIL"                                    # memory grew 20%
    assert S.verdict(lua.table(), 1000, 1000)[0] == "NO DATA"                        # no samples is not a pass
