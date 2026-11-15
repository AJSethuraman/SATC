"""Bench.lua: the pose of the camera on the test route, the frame-time maths, the verdict and the report."""
import math
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
G = Path(__file__).resolve().parents[1] / "Gauntlet"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Gauntlet', ns) end")
    for f in ("Ray", "Level", "Bench"):
        ld(str(G / f"{f}.lua"), ns)
    return lua, ns


def test_the_route_is_the_same_every_time_and_stays_on_open_squares_for_the_whole_run(env):
    lua, ns = env
    m = ns.Ray.parse(ns.Level.ROWS)
    a = ns.Bench.pose(2.5)
    assert a == ns.Bench.pose(2.5)
    for i in range(int(ns.Bench.SECONDS * 30)):
        x, y, ang = ns.Bench.pose(i / 30)
        assert not ns.Ray.blocked(m, x, y)
    x, y, ang = ns.Bench.pose(0)
    r = ns.Level.ROUTE
    assert x == pytest.approx(r.cx + r.r) and y == pytest.approx(r.cy)         # starts at the right-hand point of the circle


def test_the_view_turns_all_the_time_during_the_test(env):
    lua, ns = env
    angs = [ns.Bench.pose(i / 10)[2] for i in range(60)]
    assert all(abs(angs[i + 1] - angs[i]) > 0.01 for i in range(59))


def test_frame_stats_are_averaged_over_time_not_over_frames(env):
    lua, ns = env
    # 99 frames of 1/100 s and one of 0.1 s: 100 frames in 1.09 s -> 91.7 fps average; the worst frame is 10 fps; the worst 1% is that one frame.
    dts = lua.table_from([0.01] * 99 + [0.1])
    s = ns.Bench.stats(dts)
    assert s.n == 100 and s.avg == pytest.approx(100 / 1.09) and s.min == pytest.approx(10) and s.low == pytest.approx(10)


def test_the_slowest_one_percent_is_a_proper_tail_for_a_long_run(env):
    lua, ns = env
    dts = lua.table_from([0.01] * 190 + [0.05, 0.05, 0.03, 0.02] * 0 + [0.04] * 10)   # 200 frames: the worst 1% is 2 frames of 0.04
    s = ns.Bench.stats(dts)
    assert s.n == 200 and s.low == pytest.approx(25)
    assert ns.Bench.stats(lua.table()).avg == 0                                         # no frames: zeros, not an error


def result(lua, columns, avg, low):
    return lua.table_from({"columns": columns, "avg": avg, "min": low, "low": low})


def test_go_needs_two_hundred_forty_columns_to_hold_sixty_maybe_needs_only_some_and_no_go_none(env):
    lua, ns = env
    go = ns.Bench.verdict(lua.table_from([result(lua, 160, 72, 60), result(lua, 240, 66, 45), result(lua, 320, 61, 35)]))
    assert go.word == "GO" and go.best == 320
    maybe = ns.Bench.verdict(lua.table_from([result(lua, 160, 70, 55), result(lua, 240, 52, 40), result(lua, 320, 30, 20)]))
    assert maybe.word == "MAYBE" and maybe.best == 160
    no = ns.Bench.verdict(lua.table_from([result(lua, 160, 41, 30), result(lua, 240, 28, 15), result(lua, 320, 19, 9)]))
    assert no.word == "NO-GO" and no.best is None
    assert ns.Bench.verdict(lua.table()).word == "NO-GO"


def test_a_width_with_good_average_but_stuttering_frames_does_not_pass(env):
    lua, ns = env
    v = ns.Bench.verdict(lua.table_from([result(lua, 240, 80, 12), result(lua, 160, 80, 40)]))
    assert v.word == "MAYBE" and v.best == 160                                 # 240 averaged 80 but its slowest 1% was 12 fps


def test_the_report_says_each_widths_numbers_the_verdict_and_what_failed_to_draw(env):
    lua, ns = env
    results = lua.table_from([result(lua, 160, 71.2, 58), result(lua, 320, 33, 20)])
    assets = lua.table_from({"textures": lua.table_from([lua.table_from({"id": 129765, "name": "uldaman", "ok": True}),
                                                         lua.table_from({"id": 5, "name": "missing", "ok": False})]),
                             "models": lua.table_from([lua.table_from({"name": "wolf", "ok": True, "file": 126487}),
                                                       lua.table_from({"name": "zombie", "ok": False})]),
                             "sounds": lua.table_from([lua.table_from({"id": 567721, "ok": True})])})
    t = str(ns.Bench.report(results, assets, lua.table_from({"build": "13 Nov", "size": "2560x1440", "notes": lua.table_from(["walked: yes"])})))
    for needle in ("GAUNTLET REPORT   build 13 Nov   screen 2560x1440", "160 columns    71 fps average    58 lowest    58 in the slowest 1%   holds 60",
                   "320 columns    33 fps average    20 lowest    20 in the slowest 1%   too slow", "verdict: MAYBE (use 160 columns)",
                   "wall textures that draw: 1 of 2", "no: 5 missing", "model wolf", "ok, file 126487", "zombie", "FAILED", "sound file 567721: will play", "walked: yes"):
        assert needle in t, needle


def test_a_report_with_no_asset_results_yet_still_reads(env):
    lua, ns = env
    t = str(ns.Bench.report(lua.table_from([result(lua, 160, 70, 60)]), None))
    assert "TEST 1" in t and "TEST 2" not in t
