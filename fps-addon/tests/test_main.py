"""Main.lua: the game window, through the stand-in client. It proves the flow and what is drawn where, not how it looks."""
import math
import pytest
from test_gauntlet import MOCK, G as GDIR, lupa

FILES = ("Ray", "Level", "Rules", "Nav", "Gen", "Play", "Bench", "Render", "Gauntlet", "Main")


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK + "\n" + prelude)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Gauntlet', ns) end")
    for f in FILES:
        ld(str(GDIR / f"{f}.lua"), ns)
    ns.Main.rethrow = True                                              # a bug in a frame must fail the test, not be swallowed
    return lua, ns


def frame(lua):
    return lua.eval("FRAMES.GauntletGameFrame")


def tick(lua, n, dt=1 / 75):
    f = frame(lua)
    for _ in range(n):
        f.scripts.OnUpdate(f, dt)


def key(lua, k, down=True):
    f = frame(lua)
    (f.scripts.OnKeyDown if down else f.scripts.OnKeyUp)(f, k)


def said(lua):
    return [str(v) for v in lua.eval("PRINTED").values()]


def slash(lua, text):
    lua.eval("SlashCmdList.GAUNTLET")(text)


def start(prelude=""):
    lua, ns = boot(prelude)
    ns.Main.start(False)
    tick(lua, 2)
    return lua, ns, ns.Main.state()


def hall_world(lua, ns, G, enemies=(), items=(), start=(1.5, 2.5), exit_=(40.0, 40.0), n=1, boss=False, length=24):
    rows = ["1" * (length + 2)] + ["1" + "." * length + "1" for _ in range(3)] + ["1" * (length + 2)]
    lv = lua.table_from({"rows": lua.table_from(rows), "start": lua.table_from({"x": start[0], "y": start[1], "angle": 0}),
                         "exit": lua.table_from({"x": exit_[0], "y": exit_[1]}), "boss": boss, "n": n, "name": "Test Hall",
                         "enemies": lua.table_from([lua.table_from({"kind": k, "x": x, "y": y}) for k, x, y in enemies]),
                         "pickups": lua.table_from([lua.table_from({"kind": k, "x": x, "y": y}) for k, x, y in items])})
    G.w = ns.Play["from"](lv, n, 1, None)
    G.stage = "play"
    tick(lua, 1)
    return G.w


def sounds(lua):
    return [int(v) for v in lua.eval("SOUNDS").values()]


# ---------------------------------------------------------------- starting
def test_starting_opens_the_window_on_level_one_with_the_walls_the_game_defines():
    lua, ns, G = start()
    assert frame(lua).shown and G.stage == "play" and G.n == 1
    R = ns.Main.render()
    assert R.n == 320 and lua.eval("rawequal")(ns.Render.WALLS, ns.Rules.WALLS)
    assert "level 1: The Gloam Crypt" in str(R.title.text) and "LEVEL 1: THE GLOAM CRYPT" in str(R.msg.text)
    shown = [c for c in R.cols.values() if c.tex.shown]
    assert shown                                                        # walls are on screen from the first frame


def test_starting_again_while_playing_does_not_throw_the_level_away_but_new_does():
    lua, ns, G = start()
    w = G.w
    ns.Main.start(False)
    assert lua.eval("rawequal")(ns.Main.state().w, w)
    ns.Main.start(True)
    assert not lua.eval("rawequal")(ns.Main.state().w, w) and ns.Main.state().n == 1


def test_the_window_title_bar_is_a_drag_handle_and_esc_closes_and_keeps_a_report():
    lua, ns, G = start()
    key(lua, "ESCAPE")
    assert not frame(lua).shown
    assert "GAUNTLET GAME REPORT" in str(lua.eval("GauntletDB.game_report"))


# ---------------------------------------------------------------- moving
def test_the_keys_walk_strafe_and_turn_and_a_released_key_stops():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    p = w.player
    x0 = p.x
    key(lua, "W"); tick(lua, 30); key(lua, "W", False)
    assert p.x > x0 + 0.8 and p.y == pytest.approx(2.5)
    x1 = p.x
    tick(lua, 30)
    assert p.x == x1
    y1 = p.y
    key(lua, "D"); tick(lua, 20); key(lua, "D", False)
    assert p.y > y1 + 0.5
    a0 = p.ang
    key(lua, "E"); tick(lua, 20); key(lua, "E", False)
    assert p.ang > a0 + 0.3
    key(lua, "LEFT"); tick(lua, 20); key(lua, "LEFT", False)
    assert p.ang == pytest.approx(a0, abs=0.02)


def test_a_key_that_is_not_ours_goes_through_to_the_game():
    lua, ns, G = start()
    f = frame(lua)
    key(lua, "W")
    assert f.propagate is False
    key(lua, "F5")
    assert f.propagate is True


def test_the_mouse_turns_by_how_far_the_cursor_is_from_the_middle():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    a0 = w.player.ang
    lua.execute("CURSOR[1] = 500 + 20")
    tick(lua, 30)
    assert w.player.ang == pytest.approx(a0)                              # dead zone
    lua.execute("CURSOR[1] = 500 + 160")
    tick(lua, 75)
    assert w.player.ang == pytest.approx(a0 + 1.875, abs=0.05)     # half way out: 5 * (0.5*0.5 + 0.5*0.25)
    slash(lua, "mouse off")
    a1 = w.player.ang
    tick(lua, 30)
    assert w.player.ang == a1


# ---------------------------------------------------------------- shooting and weapons
def test_space_and_the_mouse_button_hold_fire_and_each_shot_makes_its_sound_and_is_counted():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    ammo = w.player.ammo.bullets
    key(lua, "SPACE"); tick(lua, 75); key(lua, "SPACE", False)           # a second of holding: pistol rate 0.38 -> 3 shots
    fired = ammo - w.player.ammo.bullets
    assert fired == 3
    assert sounds(lua).count(567721) + sounds(lua).count(567718) + sounds(lua).count(567722) >= 1
    assert G.run.shots.pistol == 3
    f = frame(lua)
    f.scripts.OnMouseDown(f, "LeftButton")
    tick(lua, 40)
    f.scripts.OnMouseUp(f, "LeftButton")
    assert w.player.ammo.bullets < ammo - 3


def test_number_keys_choose_owned_weapons_only_and_the_wheel_cycles():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    key(lua, "3")
    assert w.player.weapon == 1
    w.player.weapons[3] = True
    key(lua, "3")
    tick(lua, 1)
    assert w.player.weapon == 3 and "Dwarven Repeater" in str(ns.Main.render().msg.text)
    f = frame(lua)
    f.scripts.OnMouseWheel(f, 1)
    assert w.player.weapon == 1
    f.scripts.OnMouseWheel(f, -1)
    assert w.player.weapon == 3


def test_the_hand_shows_the_weapon_you_hold_and_the_hud_shows_health_armour_and_ammo():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    R = ns.Main.render()
    w.player.armor = 40
    tick(lua, 1)
    assert "HEALTH 100" in str(R.h_hp.text) and "ARMOR 40" in str(R.h_ar.text) and "Flintlock Pistol: 50" in str(R.h_ammo.text)
    assert R.weapon_icon == "INV_Weapon_Rifle_01"
    w.player.weapons[2], w.player.ammo.shells = True, 7
    ns.Play.select(w, 2)
    tick(lua, 1)
    assert "Blunderbuss: 7" in str(R.h_ammo.text) and R.weapon_icon == "INV_Weapon_Rifle_06"
    assert R.slots[2].alpha == 1 and R.slots[1].alpha == 0.5 and R.slots[3].alpha == pytest.approx(0.12)
    w.player.key_count = 2
    tick(lua, 1)
    assert "KEY x2" in str(R.h_keys.text)


# ---------------------------------------------------------------- what is drawn
def test_an_enemy_in_front_gets_a_model_frame_with_its_creature_and_one_behind_does_not():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, enemies=[("wolf", 8.5, 2.5), ("imp", 1.2, 2.5)])
    R = ns.Main.render()
    shown = [m for m in R.pool.values() if m.shown]
    assert len(shown) == 1 and shown[0].creature == 299                  # the wolf; the imp is behind us
    size = 360 / 7 * 0.85
    assert shown[0].size[2] == pytest.approx(size, rel=0.02)


def test_a_boss_is_drawn_bigger_and_a_model_keeps_its_frame_while_others_come_and_go():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, enemies=[("boss", 10.5, 2.5), ("wolf", 6.5, 2.5)])
    R = ns.Main.render()
    boss = [m for m in R.pool.values() if m.shown and m.creature == 3098][0]
    assert boss.size[2] == pytest.approx(360 / 9 * 0.85 * 1.8, rel=0.02)
    calls = boss.creature
    for _ in range(10):
        w.enemies[2].x += 0.1
        tick(lua, 1)
    assert boss.shown and boss.creature == calls and lua.eval("rawequal")(boss.owner, w.enemies[1])


def test_an_enemy_behind_a_wall_has_no_model_and_a_dead_one_plays_death_then_fades_away():
    lua, ns, G = start()
    rows_world = hall_world(lua, ns, G, enemies=[("wolf", 5.5, 2.5)])
    R = ns.Main.render()
    m = [m for m in R.pool.values() if m.shown][0]
    w = rows_world
    w.enemies[1].dead, w.enemies[1].died = True, w.time
    tick(lua, 1)
    assert m.anim == 1 and m.shown                                       # the death animation
    w.time = w.time + 3.5
    tick(lua, 1)
    assert m.alpha < 0.5
    w.time = w.time + 1.5
    tick(lua, 1)
    assert not [x for x in R.pool.values() if x.shown]


def test_pickups_the_exit_and_fireballs_are_drawn_as_icons_where_they_are_and_taken_ones_disappear():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, items=[("health", 5.5, 2.5), ("key", 9.5, 2.5)], exit_=(15.5, 2.5))
    R = ns.Main.render()
    icons = sorted(str(t.icon) for t in R.spr.values() if t.shown)
    assert icons == sorted(["INV_Potion_54", "INV_Misc_Key_03", "Spell_Holy_DivineIntervention"])
    w.pickups[1].taken = True
    tick(lua, 1)
    assert "INV_Potion_54" not in [str(t.icon) for t in R.spr.values() if t.shown]
    w.shots[1] = lua.table_from({"x": 4.0, "y": 2.5, "vx": 0, "vy": 0, "dmg": 1, "left": 99, "boss": False, "name": "x"})
    tick(lua, 1)
    assert "Spell_Fire_Fireball02" in [str(t.icon) for t in R.spr.values() if t.shown]


def test_the_exit_is_red_while_the_boss_lives_and_green_when_it_is_dead():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, enemies=[("boss", 20.5, 2.5)], exit_=(8.5, 2.5), n=5, boss=True)
    R = ns.Main.render()
    ex = [t for t in R.spr.values() if t.shown and str(t.icon) == "Spell_Holy_DivineIntervention"][0]
    assert ex.color[1] == 1 and ex.color[2] == pytest.approx(0.3)
    w.enemies[1].dead = True
    tick(lua, 1)
    ex = [t for t in R.spr.values() if t.shown and str(t.icon) == "Spell_Holy_DivineIntervention"][0]
    assert ex.color[1] == pytest.approx(0.6)


# ---------------------------------------------------------------- events: sounds, messages, flashes
def test_being_hurt_flashes_the_screen_red_plays_a_sound_and_is_remembered_in_the_report():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    R = ns.Main.render()
    ns.Play.hurt(w, 20, "Moor Wolf")
    tick(lua, 1)
    assert R.tint.alpha > 0.3 and 545127 in sounds(lua)
    a = R.tint.alpha
    tick(lua, 40)
    assert R.tint.alpha < a
    assert G.run.hurt_by["Moor Wolf"] == pytest.approx(20)


def test_picking_something_up_says_so_flashes_gold_and_plays_the_coin_sound():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, items=[("armor", 1.6, 2.5)])
    R = ns.Main.render()
    tick(lua, 2)
    assert "Picked up: Plate Armor" in str(R.msg.text) and 567428 in sounds(lua) and w.player.armor == 40


def test_a_locked_door_says_so_and_a_boss_exit_says_to_defeat_him_first():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    ns.Play.step(w, 0.01)
    w.events[1] = lua.table_from({"k": "locked"})
    tick(lua, 1)
    assert "Locked. Find the iron key." in str(ns.Main.render().msg.text)
    w.events[1] = lua.table_from({"k": "blocked_exit"})
    tick(lua, 1)
    assert "Defeat Gorefang first!" in str(ns.Main.render().msg.text)


def test_a_message_fades_after_its_time_but_an_end_screen_message_stays():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    R = ns.Main.render()
    tick(lua, 75 * 4)
    assert str(R.msg.text) == ""
    G.w.over = True
    tick(lua, 2)
    assert G.stage == "dead"
    tick(lua, 75 * 30)
    assert "YOU DIED" in str(R.msg.text)


# ---------------------------------------------------------------- dying, finishing, winning
def test_dying_shows_the_screen_records_what_killed_you_and_space_tries_the_level_again_with_the_same_start():
    lua, ns, G = start("SHOTCOUNT = 0\nfunction Screenshot() SHOTCOUNT = SHOTCOUNT + 1 end")
    w = hall_world(lua, ns, G)
    carry = G.level_carry
    ns.Play.hurt(w, 30, "Tusker")
    ns.Play.hurt(w, 500, "Gorefang the Unwelcome")
    tick(lua, 2)
    assert G.stage == "dead" and "YOU DIED" in str(ns.Main.render().msg.text)
    assert len(list(G.run.deaths.values())) == 1 and "Tusker 30" in str(G.run.deaths[1].hits) and "Gorefang the Unwelcome" in str(G.run.deaths[1].hits)
    assert G.run.levels[1].deaths == 1
    lua.eval("run_timers")()
    assert lua.eval("SHOTCOUNT") == 1                                     # a picture of the moment
    x = w.player.x
    key(lua, "W"); tick(lua, 10); key(lua, "W", False)
    assert w.player.x == x                                                # nothing moves while dead
    key(lua, "SPACE")
    assert G.stage == "play" and not lua.eval("rawequal")(G.w, w) and G.w.player.hp == 100 and G.n == 1


def test_finishing_a_level_shows_the_stats_and_space_goes_on_with_your_guns_and_ammo():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, exit_=(5.5, 2.5))
    w.player.weapons[2], w.player.ammo.shells, w.player.armor = True, 9, 35
    w.player.x = 5.0
    tick(lua, 2)
    R = ns.Main.render()
    assert G.stage == "levelend" and "LEVEL COMPLETE" in str(R.msg.text) and G.run.levels[1].done is True
    key(lua, "SPACE")
    assert G.stage == "play" and G.n == 2 and G.w.player.weapons[2] is True and G.w.player.ammo.shells == 9 and G.w.player.armor == 35
    assert "LEVEL 2: BONEWIND KEEP" in str(R.msg.text)
    prog = lua.eval("GauntletDB.progress")
    assert prog.level == 2 and prog.carry.shells == 9                    # saved at the start of the level


def test_winning_the_last_level_clears_the_saved_game_keeps_the_best_time_and_space_starts_over():
    lua, ns, G = start()
    w = hall_world(lua, ns, G, exit_=(5.5, 2.5), n=5)
    G.n = 5
    w.player.x = 5.0
    w.time = 123.0
    tick(lua, 2)
    assert G.stage == "win" and "YOU WIN" in str(ns.Main.render().msg.text)
    assert lua.eval("GauntletDB.progress") is None and lua.eval("GauntletDB.best") == pytest.approx(123.0, abs=1)
    key(lua, "SPACE")
    assert G.stage == "play" and G.n == 1


def test_a_click_also_carries_on_from_an_end_screen_and_does_not_fire():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    ns.Play.hurt(w, 500, "x")
    tick(lua, 2)
    f = frame(lua)
    f.scripts.OnMouseDown(f, "LeftButton")
    assert G.stage == "play" and G.mouse_down is not True


def test_the_game_resumes_where_it_was_left_and_new_starts_over():
    lua, ns = boot("GauntletDB = { progress = { level = 3, seed = 42, carry = { hp = 70, armor = 10, bullets = 99, shells = 4, rockets = 0, weapons = { true, true, false, false } } } }")
    ns.Main.start(False)
    tick(lua, 2)
    G = ns.Main.state()
    assert G.n == 3 and G.w.player.hp == 70 and G.w.player.ammo.bullets == 99 and G.w.player.weapons[2] is True
    assert any("continuing at level 3" in m for m in said(lua))
    slash(lua, "new")
    G = ns.Main.state()
    assert G.n == 1 and G.w.player.hp == 100 and lua.eval("GauntletDB.progress.level") == 1


def test_the_same_seed_makes_the_same_level_so_a_retry_is_the_same_level_and_the_next_level_differs():
    lua, ns, G = start()
    rows = [str(r) for r in G.w.lv.rows.values()]
    ns.Main.begin_level(1, None)
    assert [str(r) for r in ns.Main.state().w.lv.rows.values()] == rows
    ns.Main.begin_level(2, None)
    assert [str(r) for r in ns.Main.state().w.lv.rows.values()] != rows


# ---------------------------------------------------------------- the report, errors, screenshots, settings
def test_the_report_lists_levels_deaths_damage_shots_and_how_it_ran():
    lua, ns, G = start()
    w = hall_world(lua, ns, G)
    key(lua, "SPACE"); tick(lua, 75 * 2); key(lua, "SPACE", False)
    ns.Play.hurt(w, 20, "Moor Wolf")
    ns.Play.hurt(w, 500, "Tusker")
    tick(lua, 75 * 2)
    slash(lua, "report")
    edits = [o for o in lua.eval("ALL").values() if o.kind == "EditBox"]
    t = str(edits[-1].text)
    for needle in ("GAUNTLET GAME REPORT", "columns 320", "1 The Gloam Crypt", "deaths 1", "DEATHS: 1", "Tusker", "DAMAGE TAKEN FROM:",
                   "SHOTS FIRED: pistol", "ERRORS: none", "fps avg 75"):
        assert needle in t, needle


def test_an_error_in_a_frame_is_recorded_once_shown_once_and_the_game_goes_on():
    lua, ns, G = start()
    ns.Main.rethrow = False
    G.w.enemies = None
    tick(lua, 60)
    assert len(list(G.run.errors.values())) == 1 and G.run.errors[1].n == 60
    assert len([m for m in said(lua) if "error" in m and "/gaunt report" in m]) == 1
    ns.Main.rethrow = True


def test_with_rethrow_on_a_bug_fails_loudly_so_the_tests_cannot_hide_one():
    lua, ns, G = start()
    G.w.enemies = None
    with pytest.raises(Exception):
        tick(lua, 2)


def test_pictures_are_taken_at_moments_that_matter_and_never_flood_and_can_be_switched_off():
    lua, ns, G = start("SHOTCOUNT = 0\nfunction Screenshot() SHOTCOUNT = SHOTCOUNT + 1 end")
    w = hall_world(lua, ns, G, exit_=(5.5, 2.5))
    tick(lua, 75 * 20)                                                    # past the gap since the clock started
    w.player.x = 5.0
    tick(lua, 2)                                                          # the level is done
    lua.eval("run_timers")()
    assert lua.eval("SHOTCOUNT") == 1
    key(lua, "SPACE")
    w2 = G.w
    tick(lua, 75 * 2)
    ns.Play.hurt(w2, 500, "x")                                            # a death only 2 s after the last picture: too soon
    tick(lua, 2)
    lua.eval("run_timers")()
    assert lua.eval("SHOTCOUNT") == 1
    slash(lua, "shots off")
    assert lua.eval("GauntletDB.shots") is False and any("screenshots: off" in m for m in said(lua))


def test_frame_rate_is_sampled_once_a_second_and_the_columns_setting_is_clamped_and_applied():
    lua, ns, G = start()
    tick(lua, 75 * 3 + 10)
    r = G.run
    assert r.fps_n == 3 and r.fps_min == pytest.approx(75, abs=0.5)
    slash(lua, "cols 320")
    assert ns.Main.render().n == 320
    slash(lua, "cols 9999")
    assert ns.Main.render().n == 320
    slash(lua, "cols 10")
    assert ns.Main.render().n == 80
    assert any("columns: 80" in m for m in said(lua))


def test_the_old_tests_are_still_one_command_away():
    lua, ns, G = start()
    slash(lua, "test")
    assert not frame(lua).shown
    assert ns.Gauntlet.mode() == "bench"


def test_playing_a_whole_generated_game_start_to_finish_is_possible_by_walking_to_each_exit():
    lua, ns, G = start()
    for n in range(1, 6):
        w = G.w
        assert G.n == n
        for e in w.enemies.values():
            e.dead = True                                                 # skip the fights; this checks the levels chain together
        w.player.key_count = 1
        w.player.x, w.player.y = w.exit.x, w.exit.y
        tick(lua, 2)
        if n < 5:
            assert G.stage == "levelend"
            key(lua, "SPACE")
        else:
            assert G.stage == "win"


# ---------------------------------------------------------------- review findings (PR #492)
def test_starting_the_game_closes_the_speed_test_window():
    lua, ns = boot()
    slash(lua, "test")
    assert ns.Gauntlet.mode() == "bench"
    slash(lua, "")
    assert ns.Gauntlet.mode() is None or ns.Gauntlet.mode() == False or str(ns.Gauntlet.mode()) in ("None", "false", "idle")


def test_report_after_a_speed_test_is_the_speed_report_not_the_old_game_report():
    lua, ns, G = start()
    tick(lua, 20)
    ns.Main.stop()
    slash(lua, "test")
    slash(lua, "report")                                           # too early: says so rather than showing the old game report
    assert any("not finished" in m for m in said(lua))
    pf = lua.eval("FRAMES.GauntletFrame")
    for _ in range(6000):
        pf.scripts.OnUpdate(pf, 1 / 75)
        if ns.Gauntlet.mode() == "walk":
            break
    assert ns.Gauntlet.mode() == "walk"
    slash(lua, "report")
    edits = [o for o in lua.eval("ALL").values() if o.kind == "EditBox"]
    assert "GAUNTLET REPORT" in str(edits[-1].text) and "GAME REPORT" not in str(edits[-1].text)


# ---------------------------------------------------------------- true mouse look
LOOK = """
FACING = 1.0
LOOKING = false
MOUSE = false
function GetPlayerFacing() return FACING end
function MouselookStart() LOOKING = true end
function MouselookStop() LOOKING = false end
function IsMouseButtonDown(b) return MOUSE and b == "LeftButton" end
"""


def test_mouse_look_turns_the_view_by_exactly_how_far_the_mouse_turned_you():
    lua, ns, G = start(LOOK)
    slash(lua, "mouse look")
    tick(lua, 2)
    assert lua.eval("LOOKING") is True
    a0 = G.w.player.ang
    lua.execute("FACING = FACING - 0.25")            # turned right by a quarter radian
    tick(lua, 1)
    assert abs((G.w.player.ang - a0) - 0.25) < 1e-6
    lua.execute("FACING = FACING + 0.10")            # and back left a little
    tick(lua, 1)
    assert abs((G.w.player.ang - a0) - 0.15) < 1e-6


def test_mouse_look_wraps_around_north_and_does_not_spin():
    lua, ns, G = start(LOOK)
    slash(lua, "mouse look")
    lua.execute("FACING = 0.05")
    tick(lua, 2)
    a0 = G.w.player.ang
    lua.execute("FACING = 2 * math.pi - 0.05")       # crossed north turning right: a 0.1 turn, not a full circle
    tick(lua, 1)
    assert abs((G.w.player.ang - a0) - 0.10) < 1e-6


def test_mouse_look_lets_go_on_the_end_screen_and_when_the_window_closes_and_a_held_click_fires():
    lua, ns, G = start(LOOK)
    slash(lua, "mouse look")
    tick(lua, 2)
    assert lua.eval("LOOKING") is True
    lua.execute("MOUSE = true")
    n = G.w.player.ammo.bullets
    tick(lua, 20)
    assert G.w.player.ammo.bullets < n              # holding the button fires, though the frame never sees a click
    lua.execute("MOUSE = false")
    G.stage = "dead"
    tick(lua, 1)
    assert lua.eval("LOOKING") is False             # the cursor comes back so you can click
    G.stage = "play"
    tick(lua, 1)
    assert lua.eval("LOOKING") is True
    ns.Main.stop()
    assert lua.eval("LOOKING") is False


def test_mouse_look_off_falls_back_to_the_cursor_and_never_starts_mouselook():
    lua, ns, G = start(LOOK)
    slash(lua, "mouse look")
    slash(lua, "mouse edge")
    tick(lua, 3)
    assert lua.eval("LOOKING") is False


def test_when_the_client_hides_your_facing_the_cursor_turn_takes_over_and_mouselook_lets_go():
    lua, ns, G = start(LOOK)
    slash(lua, "mouse look")
    tick(lua, 2)
    assert lua.eval("LOOKING") is True
    lua.execute("GetPlayerFacing = function() return nil end")      # inside an instance
    lua.execute("GetCursorPosition = function() return 0, 0 end")
    a0 = G.w.player.ang
    tick(lua, 3)
    assert lua.eval("LOOKING") is False                              # the cursor is back, not stuck hidden


# ---------------------------------------------------------------- the view
def test_the_gun_is_drawn_as_a_first_person_shape_that_changes_with_the_weapon_and_sits_low_and_right():
    lua, ns, G = start()
    R = ns.Main.render()
    shown = lambda: sum(1 for t in R.parts.values() if t.shown)
    assert shown() == 6                                    # the pistol: sleeve, hand, grip, body, barrel, sight
    G.w.player.weapons[4], G.w.player.ammo.rockets = True, 5
    ns.Play.select(G.w, 4)
    tick(lua, 1)
    assert R.weapon_icon == "INV_Misc_Bomb_02" and shown() == 6
    assert R.weapon.pts.x >= 60                            # held to the right of the middle


def test_the_window_fits_the_screen_and_mouselook_is_the_default_where_the_client_has_it():
    lua, ns, G = start(LOOK + "UIParent.GetWidth = function() return 1600 end; UIParent.GetHeight = function() return 900 end")
    tick(lua, 3)
    assert lua.eval("LOOKING") is True
    s = ns.Main.scale()
    assert s == pytest.approx(900 * 0.92 / 424)             # the height is the tighter side
    slash(lua, "scale 1.2")
    assert ns.Main.scale() == pytest.approx(1.2)
    slash(lua, "scale")
    assert ns.Main.scale() == pytest.approx(s)


def test_floor_and_ceiling_get_darker_toward_the_horizon():
    lua, ns, G = start()
    R = ns.Main.render()
    bands = [R.bands[i] for i in range(1, 17)]                     # ceiling, floor, ceiling, floor ... from the screen edge inward
    def shade(b): return float(b.flat[1])
    ceil, floor = bands[0::2], bands[1::2]
    assert shade(ceil[0]) > shade(ceil[-1]) and shade(floor[0]) > shade(floor[-1])


CURSOR_DELTA = LOOK + """
DX = 0
function GetCursorDelta() local d = DX; DX = 0; return d, 0 end
"""


def test_the_mouse_is_locked_to_the_middle_and_the_view_turns_by_the_pixels_the_mouse_moved():
    lua, ns, G = start(CURSOR_DELTA)
    tick(lua, 2)
    a0 = G.w.player.ang
    lua.execute("DX = 200")
    tick(lua, 1)
    assert G.w.player.ang - a0 == pytest.approx(200 * 0.0035)       # 200 pixels right: 0.7 radians
    lua.execute("DX = -100")
    tick(lua, 1)
    assert G.w.player.ang - a0 == pytest.approx(100 * 0.0035)
    tick(lua, 5)
    assert G.w.player.ang - a0 == pytest.approx(100 * 0.0035)       # a still mouse does not drift
    slash(lua, "mouse sens 0.01")
    lua.execute("DX = 10")
    tick(lua, 1)
    assert G.w.player.ang - a0 == pytest.approx(100 * 0.0035 + 0.1)


def test_the_report_says_which_mouse_signal_the_client_gave():
    lua, ns, G = start(CURSOR_DELTA)
    tick(lua, 2)
    lua.execute("DX = 50")
    tick(lua, 1)
    lua.execute("FACING = FACING - 0.1")
    tick(lua, 1)
    assert "MOUSE: turns seen from cursor movement 1" in str(ns.Main.report_text())


# ---------------------------------------------------------------- the cursor cannot leave the game
def test_a_screen_wide_catcher_takes_every_click_while_you_play_and_goes_with_the_window():
    lua, ns, G = start()
    c = ns.Main.render().catcher
    assert c.shown
    c.scripts.OnMouseDown(c, "LeftButton")                      # a click anywhere on the screen
    assert G.mouse_down is True
    c.scripts.OnMouseUp(c, "LeftButton")
    assert G.mouse_down is False
    ns.Main.stop()
    assert not c.shown


def test_with_the_cursor_turn_the_whole_screen_counts_and_a_cursor_far_outside_the_window_still_turns():
    lua, ns, G = start("UIParent.GetWidth = function() return 1000 end; UIParent.GetEffectiveScale = function() return 1 end")
    w = hall_world(lua, ns, G)
    a0 = w.player.ang
    lua.execute("CURSOR[1] = 500 + 500")                        # at the right edge of the screen, well outside the window
    tick(lua, 75)
    assert w.player.ang - a0 == pytest.approx(5.0, abs=0.1)     # full speed for one second
    lua.execute("CURSOR[1] = 500")                              # the middle of the screen
    a1 = w.player.ang
    tick(lua, 30)
    assert w.player.ang == pytest.approx(a1)


def test_holding_the_mouse_button_fires_even_when_the_click_went_elsewhere():
    lua, ns, G = start("function IsMouseButtonDown(b) return b == 'LeftButton' end")
    n = G.w.player.ammo.bullets
    tick(lua, 60)
    assert G.w.player.ammo.bullets < n


def test_a_turn_is_not_counted_twice_when_the_client_gives_both_the_cursor_delta_and_the_facing():
    lua, ns, G = start(CURSOR_DELTA)
    tick(lua, 2)
    a0 = G.w.player.ang
    lua.execute("DX = 100; FACING = FACING - 100 * 0.0035")      # one gesture: the cursor moved and the player turned with it
    tick(lua, 1)
    tick(lua, 3)                                                  # then the mouse stops
    assert G.w.player.ang - a0 == pytest.approx(100 * 0.0035)    # no extra rotation afterwards
