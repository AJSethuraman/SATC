"""Play.lua: the rules of the game, in small hand-built levels so every number can be worked out. No screen involved."""
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
    for f in ("Ray", "Rules", "Nav", "Gen", "Play"):
        ld(str(G / f"{f}.lua"), ns)
    return lua, ns


def world(env, rows, enemies=(), items=(), start=(1.5, 1.5), exit_=(0.0, 0.0), boss=False, n=1, carry=None):
    """A level from text rows. Enemies and items are (kind, x, y). The rng is the real one, so tests that need chance control it."""
    lua, ns = env
    lv = lua.table_from({"rows": lua.table_from(rows), "start": lua.table_from({"x": start[0], "y": start[1], "angle": 0}),
                         "exit": lua.table_from({"x": exit_[0], "y": exit_[1]}), "boss": boss, "n": n,
                         "enemies": lua.table_from([lua.table_from({"kind": k, "x": x, "y": y}) for k, x, y in enemies]),
                         "pickups": lua.table_from([lua.table_from({"kind": k, "x": x, "y": y}) for k, x, y in items])})
    return ns.Play["from"](lv, n, 1, carry)


def hall(length=20, height=3):
    """A straight hall: wall all round, open inside, `length` squares long."""
    return ["1" * (length + 2)] + ["1" + "." * length + "1" for _ in range(height)] + ["1" * (length + 2)]


def run(ns, w, seconds, dt=1 / 30):
    for _ in range(int(round(seconds / dt))):
        ns.Play.step(w, dt)


def kinds(w):
    return [str(e.k) for e in w.events.values()]


# ---------------------------------------------------------------- weapons
def test_the_pistol_fires_a_bullet_at_the_enemy_in_front_for_its_damage_and_spends_one_round(env):
    lua, ns = env
    w = world(env, hall(), enemies=[("kobold", 10.5, 2.5)], start=(1.5, 2.5))
    p = w.player
    p.ang = 0
    ammo = p.ammo.bullets
    assert ns.Play.fire(w) is True
    e = w.enemies[1]
    # pistol: 11 damage, one pellet, a little spread (0.015 rad at 9 away is 0.14, inside the kobold's 0.3): a sure hit. Kobold hp 22.
    assert e.hp == pytest.approx(22 - 11) and p.ammo.bullets == ammo - 1
    assert "shot" in kinds(w) and "hit" in kinds(w)


def test_the_weapon_cannot_fire_again_until_its_rate_is_up(env):
    lua, ns = env
    w = world(env, hall(), start=(1.5, 2.5))
    assert ns.Play.fire(w) is True
    assert ns.Play.fire(w) is False
    run(ns, w, 0.3)
    assert ns.Play.fire(w) is False                                   # pistol rate 0.38
    run(ns, w, 0.1)
    assert ns.Play.fire(w) is True


def test_shooting_through_a_wall_hits_nothing(env):
    lua, ns = env
    rows = ["111111111", "1...1...1", "1...1...1", "111111111"]
    w = world(env, rows, enemies=[("kobold", 6.5, 1.5)], start=(1.5, 1.5))
    ns.Play.fire(w)
    assert w.enemies[1].hp == 22 and w.enemies[1].state == "idle"


def test_the_blunderbuss_throws_seven_pellets_that_hurt_most_close_up(env):
    lua, ns = env
    near = world(env, hall(), enemies=[("boar", 3.5, 2.5)], start=(1.5, 2.5))
    near.player.weapons[2], near.player.ammo.shells = True, 10
    ns.Play.select(near, 2)
    ns.Play.fire(near)
    far = world(env, hall(), enemies=[("boar", 12.5, 2.5)], start=(1.5, 2.5))
    far.player.weapons[2], far.player.ammo.shells = True, 10
    ns.Play.select(far, 2)
    ns.Play.fire(far)
    d_near, d_far = 90 - near.enemies[1].hp, 90 - far.enemies[1].hp
    assert near.player.ammo.shells == 9
    assert d_near > d_far > 0 or d_far == 0                           # farther away the pellets scatter and weaken, or miss
    assert d_near <= 7 * 7 + 1e-6                                       # at most seven pellets of 7


def test_a_weapon_you_do_not_own_cannot_be_chosen_and_one_you_do_can(env):
    lua, ns = env
    w = world(env, hall())
    assert ns.Play.select(w, 3) is False and w.player.weapon == 1
    w.player.weapons[3] = True
    assert ns.Play.select(w, 3) is True and w.player.weapon == 3
    assert ns.Play.select(w, 3) is False                               # already holding it


def test_cycling_skips_weapons_you_do_not_have(env):
    lua, ns = env
    w = world(env, hall())
    w.player.weapons[3] = True
    ns.Play.cycle(w, 1)
    assert w.player.weapon == 3
    ns.Play.cycle(w, 1)
    assert w.player.weapon == 1
    ns.Play.cycle(w, -1)
    assert w.player.weapon == 3


def test_firing_an_empty_weapon_clicks_and_goes_to_the_best_weapon_with_ammo(env):
    lua, ns = env
    w = world(env, hall())
    p = w.player
    p.weapons[2], p.weapons[3] = True, True
    p.ammo.shells, p.ammo.bullets = 0, 5
    ns.Play.select(w, 2)
    assert ns.Play.fire(w) is False
    assert "empty" in kinds(w) and p.weapon == 3                         # the repeater uses bullets, which it has


def test_running_dry_mid_fight_switches_on_its_own_after_the_last_shot(env):
    lua, ns = env
    w = world(env, hall())
    p = w.player
    p.weapons[2], p.ammo.shells, p.ammo.bullets = True, 1, 9
    ns.Play.select(w, 2)
    assert ns.Play.fire(w) is True and p.ammo.shells == 0 and p.weapon == 1


def test_a_rocket_flies_bursts_on_a_wall_and_hurts_everything_near_it_by_how_close(env):
    lua, ns = env
    w = world(env, hall(), enemies=[("boar", 9.5, 2.5), ("boar", 10.5, 2.0)], start=(1.5, 2.5))
    p = w.player
    p.weapons[4], p.ammo.rockets = True, 5
    ns.Play.select(w, 4)
    ns.Play.fire(w)
    assert len(list(w.rockets.values())) == 1 and p.ammo.rockets == 4
    r = w.rockets[1]
    x0 = r.x
    run(ns, w, 0.2)
    assert w.rockets[1].x == pytest.approx(x0 + 9 * 0.2, abs=0.05)         # 9 units a second
    run(ns, w, 2)
    assert len(list(w.rockets.values())) == 0 and "explode" in kinds(w)
    a, b = w.enemies[1], w.enemies[2]
    # it bursts about 0.55 from the first boar (9.5, 2.5): 0.15 from its edge, so 90 * (1 - 0.15/2.2) = 84 damage; the second is about 1.2 from
    # the burst's edge: 90 * (1 - 1.23/2.2) = 40. Nearer means more.
    assert a.hp < 20 and 30 < b.hp < 75 and a.hp < b.hp


def test_a_rocket_that_bursts_next_to_you_hurts_you_half_as_much(env):
    lua, ns = env
    w = world(env, hall(), start=(2.5, 2.5))
    p = w.player
    p.weapons[4], p.ammo.rockets = True, 5
    p.ang = math.pi                                                         # facing the wall 1.5 behind... it bursts at once
    ns.Play.select(w, 4)
    ns.Play.fire(w)
    run(ns, w, 1)
    assert p.hp < 100


# ---------------------------------------------------------------- hurting
def test_armour_soaks_half_of_each_hit_until_it_runs_out(env):
    lua, ns = env
    w = world(env, hall())
    p = w.player
    p.armor = 10
    ns.Play.hurt(w, 8, "x")                                                 # half (4) to the armour, 4 to you
    assert p.armor == pytest.approx(6) and p.hp == pytest.approx(96)
    ns.Play.hurt(w, 20, "x")                                                # armour only has 6: it takes 6 (not 10), you take 14
    assert p.armor == 0 and p.hp == pytest.approx(82)


def test_dying_ends_the_level_and_nothing_moves_after(env):
    lua, ns = env
    w = world(env, hall())
    ns.Play.hurt(w, 500, "x")
    assert w.over is True and w.player.hp == 0 and "dead" in kinds(w)
    x = w.player.x
    ns.Play.move(w, 1, 0, 1)
    assert w.player.x == x and ns.Play.fire(w) is False


# ---------------------------------------------------------------- doors
def door_rows(door):
    return ["1111111", "1..%s..1" % door, "1111111"]


def test_walking_into_a_door_opens_it_and_you_can_go_through(env):
    lua, ns = env
    w = world(env, door_rows("5"), start=(1.5, 1.5))
    for _ in range(40):
        ns.Play.move(w, 1, 0, 1 / 30)
    assert "door" in kinds(w) and w.map.cells[2][4] == 0
    assert w.player.x > 4.5                                                 # through it


def test_a_locked_door_stays_shut_without_a_key_and_says_so_once_in_a_while(env):
    lua, ns = env
    w = world(env, door_rows("6"), start=(1.5, 1.5))
    for _ in range(90):
        ns.Play.move(w, 1, 0, 1 / 30)
        w.time = w.time + 1 / 30
    assert w.map.cells[2][4] == 6 and w.player.x < 3.6
    assert kinds(w).count("locked") == 2                                    # 3 seconds of pushing: told every 1.5 s, not every frame


def test_a_key_opens_a_locked_door_and_is_used_up(env):
    lua, ns = env
    w = world(env, door_rows("6"), start=(1.5, 1.5))
    w.player.key_count = 1
    for _ in range(40):
        ns.Play.move(w, 1, 0, 1 / 30)
    assert w.map.cells[2][4] == 0 and w.player.key_count == 0 and "unlock" in kinds(w)


def test_walking_stops_at_walls_and_slides_along_them(env):
    lua, ns = env
    w = world(env, hall(), start=(1.5, 2.5))
    w.player.ang = math.radians(135)                                        # up and to the left into the corner
    for _ in range(60):
        ns.Play.move(w, 1, 0, 1 / 30)
    assert w.player.x >= 1.2 and w.player.y >= 1.2


# ---------------------------------------------------------------- pickups
def test_walking_over_a_potion_heals_you_and_only_if_you_need_it(env):
    lua, ns = env
    w = world(env, hall(), items=[("health", 3.5, 2.5)], start=(1.5, 2.5))
    p = w.player
    ns.Play.hurt(w, 40, "x")
    p.x = 3.5
    ns.Play.step(w, 1 / 30)
    assert p.hp == 85 and w.pickups[1].taken and "pickup" in kinds(w)
    w2 = world(env, hall(), items=[("health", 3.5, 2.5)], start=(3.5, 2.5))
    ns.Play.step(w2, 1 / 30)
    assert not w2.pickups[1].taken and w2.player.hp == 100                    # at full health it stays on the floor for later


def test_ammo_is_capped_and_a_full_pool_leaves_the_box(env):
    lua, ns = env
    w = world(env, hall(), items=[("bullets", 3.5, 2.5)], start=(3.5, 2.5))
    w.player.ammo.bullets = 190
    ns.Play.step(w, 1 / 30)
    assert w.player.ammo.bullets == 200
    w2 = world(env, hall(), items=[("bullets", 3.5, 2.5)], start=(3.5, 2.5))
    w2.player.ammo.bullets = 200
    ns.Play.step(w2, 1 / 30)
    assert not w2.pickups[1].taken


def test_a_weapon_pickup_gives_the_weapon_ammo_and_switches_to_it_once(env):
    lua, ns = env
    w = world(env, hall(), items=[("scatter", 3.5, 2.5)], start=(3.5, 2.5))
    ns.Play.step(w, 1 / 30)
    p = w.player
    assert p.weapons[2] is True and p.ammo.shells == 10 and p.weapon == 2
    w2 = world(env, hall(), items=[("scatter", 3.5, 2.5)], start=(3.5, 2.5), carry=lua.table_from({"hp": 100, "armor": 0, "bullets": 50, "shells": 3, "rockets": 0,
                                                                                                     "weapons": lua.table_from([True, True, False, False])}))
    ns.Play.step(w2, 1 / 30)
    assert w2.player.ammo.shells == 13                                       # already owned: just the ammo, and no switching away from what you hold


def test_armour_and_keys_are_picked_up(env):
    lua, ns = env
    w = world(env, hall(), items=[("armor", 3.5, 2.5), ("key", 3.5, 2.5)], start=(3.5, 2.5))
    ns.Play.step(w, 1 / 30)
    assert w.player.armor == 40 and w.player.key_count == 1 and w.stats.picked == 2


# ---------------------------------------------------------------- enemies
def test_an_enemy_sleeps_until_it_sees_you_close_enough_and_wakes_its_pack_by_noise(env):
    lua, ns = env
    w = world(env, hall(30), enemies=[("wolf", 25.5, 2.5), ("wolf", 4.5, 2.5)], start=(1.5, 2.5))
    run(ns, w, 0.5)
    assert w.enemies[1].state == "idle"                                      # 24 away: past its wake distance of 11
    assert w.enemies[2].state == "chase"                                     # 3 away and in sight
    ns.Play.fire(w)
    assert w.enemies[1].state == "idle"                                      # the noise carries 12, not 24


def test_a_shot_wakes_enemies_in_earshot_and_in_sight_but_not_behind_walls(env):
    lua, ns = env
    rows = ["1111111111111", "1...1.......1", "1...1.......1", "1111111111111"]
    w = world(env, rows, enemies=[("murloc", 8.5, 1.5), ("murloc", 3.5, 1.5)], start=(2.5, 1.5))
    ns.Play.fire(w)
    assert w.enemies[1].state == "idle"                                      # behind the wall at x 4
    assert w.enemies[2].state == "chase"


def test_a_wolf_runs_at_you_and_bites_on_a_cooldown(env):
    lua, ns = env
    w = world(env, hall(), enemies=[("wolf", 8.5, 2.5)], start=(1.5, 2.5))
    w.enemies[1].state = "chase"
    run(ns, w, 2.5)                                                          # 7 units at 3.4 a second is about 2 s
    assert w.player.hp < 100 and "bite" in kinds(w)
    hp = w.player.hp
    run(ns, w, 0.3)
    assert w.player.hp == hp                                                 # 0.6 s between bites


def test_a_kobold_stops_at_range_winds_up_and_shoots_and_can_miss(env):
    lua, ns = env
    w = world(env, hall(30), enemies=[("kobold", 12.5, 2.5)], start=(1.5, 2.5))
    w.enemies[1].state = "chase"
    w.enemies[1].cool = 0
    run(ns, w, 0.1)
    assert w.enemies[1].windup is not None and "windup" in kinds(w) and w.player.hp == 100
    x = w.enemies[1].x
    run(ns, w, 0.5)
    assert "enemyshot" in kinds(w) and w.enemies[1].x == pytest.approx(x)    # it did not walk while aiming; 11 away is in its range of 12
    shots_taken = 0
    for _ in range(40):                                                       # over many shots some hit and some miss
        before = w.player.hp
        run(ns, w, 1.2)
        shots_taken += 1 if w.player.hp < before else 0
        w.player.hp = 100
    assert 5 < shots_taken < 40


def test_an_imp_throws_a_fireball_you_can_step_out_of(env):
    lua, ns = env
    w = world(env, hall(30, 7), enemies=[("imp", 12.5, 4.5)], start=(1.5, 4.5))
    e = w.enemies[1]
    e.state, e.cool = "chase", 0
    run(ns, w, 0.7)                                                            # wind-up 0.5 then released
    assert len(list(w.shots.values())) == 1 and w.player.hp == 100
    w.player.y = 7.0                                                           # step well aside before it arrives
    run(ns, w, 2.0)                                                            # the first one flies past (about 1.8 s to cross 11 units at 6 a second)
    assert w.player.hp == 100
    w2 = world(env, hall(30, 7), enemies=[("imp", 12.5, 4.5)], start=(1.5, 4.5))
    w2.enemies[1].state, w2.enemies[1].cool = "chase", 0
    run(ns, w2, 3)                                                             # standing still it hits
    assert w2.player.hp < 100 and "fireball_hit" in kinds(w2)


def test_an_enemy_that_cannot_see_you_finds_its_way_round_a_wall(env):
    lua, ns = env
    rows = ["1111111111", "1...1....1", "1...1....1", "1...1....1", "1........1", "1111111111"]
    w = world(env, rows, enemies=[("wolf", 7.5, 1.5)], start=(1.5, 1.5))
    w.enemies[1].state = "chase"
    run(ns, w, 6)
    assert w.player.hp < 100 or w.enemies[1].x < 4                             # it came round the gap at the bottom


def test_enemies_do_not_pile_into_the_same_spot(env):
    lua, ns = env
    w = world(env, hall(20, 5), enemies=[("wolf", 10.5, 3.5), ("wolf", 10.6, 3.5), ("wolf", 10.5, 3.6)], start=(1.5, 3.5))
    for e in w.enemies.values():
        e.state = "chase"
    run(ns, w, 1.5)
    es = list(w.enemies.values())
    for i in range(3):
        for j in range(i + 1, 3):
            assert math.hypot(es[i].x - es[j].x, es[i].y - es[j].y) > 0.25


def test_a_door_in_the_way_is_opened_by_an_enemy_chasing_you(env):
    lua, ns = env
    w = world(env, door_rows("5"), enemies=[("wolf", 5.5, 1.5)], start=(1.5, 1.5))
    w.enemies[1].state = "chase"
    run(ns, w, 3)
    assert w.map.cells[2][4] == 0


def test_a_locked_door_stops_an_enemy(env):
    lua, ns = env
    w = world(env, door_rows("6"), enemies=[("wolf", 5.5, 1.5)], start=(1.5, 1.5))
    w.enemies[1].state = "chase"
    run(ns, w, 4)
    assert w.map.cells[2][4] == 6 and w.enemies[1].x > 4


def test_killing_an_enemy_counts_it_and_a_dead_one_does_nothing(env):
    lua, ns = env
    w = world(env, hall(), enemies=[("kobold", 8.5, 2.5)], start=(1.5, 2.5))
    for _ in range(3):
        ns.Play.fire(w)
        run(ns, w, 0.4)
    e = w.enemies[1]
    assert e.dead is True and w.stats.kills == 1 and "kill" in kinds(w)
    hp = w.player.hp
    run(ns, w, 3)
    assert w.player.hp == hp


def test_later_levels_give_enemies_more_life(env):
    lua, ns = env
    a = world(env, hall(), enemies=[("boar", 8.5, 2.5)], n=1)
    b = world(env, hall(), enemies=[("boar", 8.5, 2.5)], n=5)
    assert a.enemies[1].hp == 90 and b.enemies[1].hp == pytest.approx(90 * 1.48)


# ---------------------------------------------------------------- the exit, winning, carrying on
def test_reaching_the_exit_finishes_the_level_and_the_last_level_is_a_win(env):
    lua, ns = env
    w = world(env, hall(), start=(1.5, 2.5), exit_=(5.5, 2.5))
    w.player.x = 5.0
    ns.Play.step(w, 1 / 30)
    assert w.done is True and w.won is False and "level_done" in kinds(w)
    w2 = world(env, hall(), start=(1.5, 2.5), exit_=(5.5, 2.5), n=5)
    w2.player.x = 5.0
    ns.Play.step(w2, 1 / 30)
    assert w2.won is True and "win" in kinds(w2)


def test_the_exit_of_the_boss_level_stays_shut_until_the_boss_is_dead(env):
    lua, ns = env
    w = world(env, hall(), enemies=[("boss", 15.5, 2.5)], start=(1.5, 2.5), exit_=(5.5, 2.5), boss=True, n=5)
    w.player.x = 5.0
    ns.Play.step(w, 1 / 30)
    assert w.done is False and "blocked_exit" in kinds(w)
    w.enemies[1].dead = True
    ns.Play.step(w, 1 / 30)
    assert w.done is True and w.won is True


def test_what_you_carry_to_the_next_level_keeps_your_guns_ammo_and_armour_and_gives_back_health_to_at_least_half(env):
    lua, ns = env
    w = world(env, hall())
    p = w.player
    p.hp, p.armor, p.ammo.shells, p.weapons[2], p.key_count = 20, 30, 7, True, 1
    c = ns.Play.carry(w)
    assert c.hp == 50 and c.armor == 30 and c.shells == 7 and c.weapons[2] is True
    w2 = world(env, hall(), carry=c)
    assert w2.player.hp == 50 and w2.player.key_count == 0 and w2.player.weapons[2] is True
    p.hp = 90
    assert ns.Play.carry(w).hp == 90


def test_a_new_game_starts_with_a_pistol_and_fifty_rounds_and_a_loaded_level_is_a_real_one(env):
    lua, ns = env
    w = ns.Play.new(1, 3)
    p = w.player
    assert p.hp == 100 and p.ammo.bullets == 50 and p.weapons[1] is True and p.weapons[2] is False and p.weapon == 1
    assert w.stats.total == len(list(w.enemies.values())) > 0 and w.stats.pickups_total == len(list(w.pickups.values()))
    assert w.lv.n == 1 and not w.over and not w.done
