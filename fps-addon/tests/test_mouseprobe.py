"""MouseProbe.lua: the mouse test. The tallies and the verdict are plain maths; the window is driven through the stand-in client."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_main import boot, slash, said, frame  # noqa: E402


def run_phases(lua, ns, script):
    """Drive the probe window frame by frame. script(phase, frame_no) sets the stand-in's readings before each frame."""
    f = lua.eval("FRAMES.GauntletMouseProbe")
    for _ in range(100000):
        P = ns.MouseProbe.state()
        if P.done:
            break
        script(int(P.phase), int(P.stats[int(P.phase)].frames))
        f.scripts.OnUpdate(f, 1 / 60)
    return ns.MouseProbe.state()


API = """
FACING = 1.0; CX = 500; DX = 0; LOCKED = false; RIGHT = false
function GetPlayerFacing() return FACING end
function GetCursorPosition() return CX, 300 end
function GetCursorDelta() local d = DX; DX = 0; return d, 0 end
function MouselookStart() LOCKED = true end
function MouselookStop() LOCKED = false end
function IsMouselooking() return LOCKED end
function IsMouseButtonDown(b) return RIGHT and b == "RightButton" end
function GetBuildInfo() return "1.15.0", "99999", "Jan 1 2026", 11500 end
"""


def test_a_signal_counts_only_if_it_moved_enough_frames_and_the_verdict_follows_the_locked_step():
    lua, ns = boot()
    P = ns.MouseProbe.new()
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"facing": 1.0, "cx": 500 + (i if i < 2 else 0), "dx": 0}))
    assert list(ns.MouseProbe.working(P.stats[1]).values()) == []           # two changes of the cursor are not enough
    P.phase = 2
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"facing": 1.0 + i * 0.01, "cx": 500, "dx": 0}))
    assert list(ns.MouseProbe.working(P.stats[2]).values()) == ["facing"]
    mode, sig = ns.MouseProbe.verdict(P)
    assert mode == "look" and list(sig.values()) == ["facing"]


def test_nothing_while_locked_but_the_cursor_moves_free_gives_free_and_nothing_at_all_gives_edge():
    lua, ns = boot()
    P = ns.MouseProbe.new()
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"cx": 500 + i}))
    mode, _ = ns.MouseProbe.verdict(P)
    assert mode == "free"
    Q = ns.MouseProbe.new()
    for i in range(10):
        ns.MouseProbe.sample(Q, lua.table_from({"cx": 500}))
    assert ns.MouseProbe.verdict(Q)[0] == "edge"


def test_the_whole_test_runs_three_steps_locks_only_in_the_second_and_saves_the_choice_and_the_report():
    lua, ns = boot(API)
    slash(lua, "mousetest")
    f = lua.eval("FRAMES.GauntletMouseProbe")
    assert f.shown
    locks = {}

    def script(phase, n):
        locks.setdefault(phase, set()).add(bool(lua.eval("LOCKED")))
        if phase == 1:
            lua.execute("CX = 500 + %d" % (n * 5))                                  # the free cursor moves
        elif phase == 2:
            lua.execute("DX = 7")                                                   # locked: the delta reports
        else:
            lua.execute("RIGHT = true; FACING = FACING + 0.01")                      # right button held: facing moves

    P = run_phases(lua, ns, script)
    assert P.done and not f.shown
    assert locks[1] == {False} and locks[3] == {False} and True in locks[2]         # locked in step 2 only
    assert lua.eval("LOCKED") is False                                              # and released at the end
    assert str(lua.eval("GauntletDB.mouse_mode")) == "look"
    rep = str(lua.eval("GauntletDB.mouse_probe"))
    assert "CHOICE: look (using delta)" in rep and "GetCursorDelta=yes" in rep and "1.15.0" in rep
    assert "right button down on" in rep
    assert ns.Main.look is True and ns.Main.edge is False


def test_a_client_that_gives_nothing_while_locked_is_set_to_free_and_the_game_then_starts_that_way():
    lua, ns = boot(API)
    slash(lua, "mousetest")

    def script(phase, n):
        if phase == 1:
            lua.execute("CX = 500 + %d" % (n * 5))                                  # only the free cursor moves

    run_phases(lua, ns, script)
    assert str(lua.eval("GauntletDB.mouse_mode")) == "free"
    assert ns.Main.look is False
    lua2, ns2 = boot(API + "GauntletDB = { mouse_mode = 'free', mouse_mode_v = 2 }")                  # a later session reads the saved choice
    ns2.Main.start(False)
    assert ns2.Main.look is False


def test_escape_cancels_the_test_and_lets_go_of_the_mouse():
    lua, ns = boot(API)
    slash(lua, "mousetest")
    f = lua.eval("FRAMES.GauntletMouseProbe")
    for _ in range(7 * 60):
        f.scripts.OnUpdate(f, 1 / 60)                                               # into the locked step
        if lua.eval("LOCKED"):
            break
    assert lua.eval("LOCKED") is True
    f.scripts.OnKeyDown(f, "ESCAPE")
    assert lua.eval("LOCKED") is False and not f.shown


def test_free_is_chosen_only_if_the_cursor_position_itself_moved_since_that_is_what_the_game_reads():
    lua, ns = boot()
    P = ns.MouseProbe.new()
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"cx": 500, "dx": 5}))          # only the delta moved with the cursor free
    assert ns.MouseProbe.verdict(P)[0] == "edge"


def test_only_the_cursor_position_moving_while_locked_is_its_own_choice_and_delta_or_facing_is_look():
    lua, ns = boot()
    P = ns.MouseProbe.new()
    P.phase = 2
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"cx": 500 + i}))
    assert ns.MouseProbe.verdict(P)[0] == "lockpos"
    Q = ns.MouseProbe.new()
    Q.phase = 2
    for i in range(10):
        ns.MouseProbe.sample(Q, lua.table_from({"cx": 500 + i, "dx": 3}))
    assert ns.MouseProbe.verdict(Q)[0] == "look"


def test_the_lock_the_test_started_is_always_stopped_even_if_the_client_never_says_it_is_locked():
    lua, ns = boot(API + "function IsMouselooking() return false end")
    slash(lua, "mousetest")
    f = lua.eval("FRAMES.GauntletMouseProbe")
    for _ in range(7 * 60):
        f.scripts.OnUpdate(f, 1 / 60)
        if lua.eval("LOCKED"):
            break
    assert lua.eval("LOCKED") is True
    f.scripts.OnKeyDown(f, "ESCAPE")
    assert lua.eval("LOCKED") is False                              # stopped although IsMouselooking never said so


def test_facing_alone_while_locked_is_not_trusted_when_the_free_cursor_works_but_a_locked_delta_is():
    lua, ns = boot()
    P = ns.MouseProbe.new()
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"cx": 500 + i * 7, "dx": 7, "facing": 1.0 + i * 0.01}))   # free step: everything moves
    P.phase = 2
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"cx": 500, "facing": 1.0 + i * 0.01}))                  # locked: only the facing, like the real client
    assert ns.MouseProbe.verdict(P)[0] == "free"
    for i in range(10):
        ns.MouseProbe.sample(P, lua.table_from({"cx": 500, "dx": 5, "facing": 1.0}))                    # now the locked delta reports too
    assert ns.MouseProbe.verdict(P)[0] == "look"


def test_a_choice_saved_by_the_older_test_is_ignored_so_the_new_default_applies():
    lua, ns = boot(API + "GauntletDB = { mouse_mode = 'look' }")                    # no version: saved when facing alone chose the lock
    ns.Main.start(False)
    assert ns.Main.look is False
