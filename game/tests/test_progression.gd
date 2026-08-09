extends TestCase

## The shape of a run.
##
## These are mostly structural assertions rather than balance ones — balance is
## the simulator's job. What they pin is that the act model stays coherent: that
## depth and act_of_depth are actually inverses, that every act has exactly one
## boss and one respite, and that a run cannot advance past its last act.


func test_depth_counts_rooms_across_acts() -> void:
	assert_eq(Progression.depth(1, 1), 1)
	assert_eq(Progression.depth(1, Progression.ROOMS_PER_ACT), Progression.ROOMS_PER_ACT)
	assert_eq(Progression.depth(2, 1), Progression.ROOMS_PER_ACT + 1)
	assert_eq(Progression.depth(Progression.ACTS, Progression.ROOMS_PER_ACT),
		Progression.total_rooms())


## depth() and act_of_depth() are inverses, or difficulty and structure disagree
## about where the run is.
func test_act_of_depth_inverts_depth() -> void:
	for act in range(1, Progression.ACTS + 1):
		for room in range(1, Progression.ROOMS_PER_ACT + 1):
			var d := Progression.depth(act, room)
			assert_eq(Progression.act_of_depth(d), act,
				"depth %d should be in act %d" % [d, act])


func test_each_act_has_exactly_one_boss_and_one_respite() -> void:
	var bosses := 0
	var respites := 0
	var combats := 0
	for room in range(1, Progression.ROOMS_PER_ACT + 1):
		match Progression.kind_of(room):
			Progression.RoomKind.BOSS:
				bosses += 1
			Progression.RoomKind.RESPITE:
				respites += 1
			_:
				combats += 1
	assert_eq(bosses, 1)
	assert_eq(respites, 1)
	assert_eq(combats, Progression.ROOMS_PER_ACT - 2)


## The act must end on the boss, not merely contain one.
func test_the_boss_is_the_last_room() -> void:
	assert_eq(Progression.kind_of(Progression.ROOMS_PER_ACT), Progression.RoomKind.BOSS)


## An act should pay in both currencies. A rhythm that handed out only gear
## would leave the boon pool — and every tag gate built on it — unused.
func test_an_act_grants_both_items_and_boons() -> void:
	var items := 0
	var boons := 0
	for room in range(1, Progression.ROOMS_PER_ACT + 1):
		match Progression.reward_of(room):
			Progression.Reward.ITEM:
				items += 1
			Progression.Reward.BOON:
				boons += 1
	# Gear and boons gate each other — an item's tags widen the boon pool — so a
	# lopsided act starves one of the two systems.
	assert_eq(items, boons, "an act pays %d items against %d boons" % [items, boons])
	assert_gt(items, 0, "an act grants no rewards at all")
	assert_eq(Progression.reward_of(Progression.BOSS_ROOM), Progression.Reward.ACT_PRIZE)
	assert_eq(Progression.reward_of(Progression.RESPITE_ROOM), Progression.Reward.NONE)


func test_respite_rooms_are_empty_and_boss_rooms_are_not() -> void:
	assert_eq(Progression.enemy_count(1, Progression.RESPITE_ROOM), 0)
	assert_gt(Progression.enemy_count(1, Progression.BOSS_ROOM), 0)
	# Later acts field more bodies than the first.
	assert_gt(
		float(Progression.enemy_count(Progression.ACTS, 1)),
		float(Progression.enemy_count(1, 1))
	)


## Walking the whole run must land exactly on the last room of the last act and
## then refuse to go further — a run that can advance forever has no ending.
func test_a_run_walks_every_room_then_stops() -> void:
	var run := RunState.start(4242)
	var visited := 1
	while run.advance_room():
		visited += 1
		assert_lt(float(visited), float(Progression.total_rooms() + 1), "run overran its acts")

	assert_eq(visited, Progression.total_rooms())
	assert_eq(run.act_number, Progression.ACTS)
	assert_eq(run.room_number, Progression.ROOMS_PER_ACT)
	assert_eq(run.depth(), Progression.total_rooms())


## An act boundary should be felt. Entering a new act must be a step up, not a
## continuation of the same slope.
func test_entering_an_act_is_a_step_up() -> void:
	var last_of_act := RunState.enemy_for_depth(Progression.ROOMS_PER_ACT)
	var first_of_next := RunState.enemy_for_depth(Progression.ROOMS_PER_ACT + 1)
	var within_act := RunState.enemy_for_depth(2).max_health / RunState.enemy_for_depth(1).max_health
	var across := first_of_next.max_health / last_of_act.max_health
	assert_gt(across, within_act, "crossing into a new act is no harder than the room before")


## The curve the simulator flagged: enemy damage must not outrun a player whose
## defences arrive in flat lumps. Across a full clear it may grow, but nothing
## like as fast as health does.
func test_damage_grows_more_slowly_than_health() -> void:
	var first := RunState.enemy_for_depth(1)
	var last := RunState.enemy_for_depth(Progression.total_rooms())
	var health_growth := last.max_health / first.max_health
	var damage_growth := last.weapon_max / first.weapon_max
	assert_gt(health_growth, damage_growth * 3.0,
		"health %.1fx vs damage %.1fx — damage is compounding too fast" %
			[health_growth, damage_growth])
	assert_lt(damage_growth, 4.0, "damage grows %.1fx across a run" % damage_growth)


func test_a_boss_outlasts_the_room_it_ends() -> void:
	var boss := RunState.boss_for_act(1)
	var mob := RunState.enemy_for_depth(Progression.depth(1, Progression.BOSS_ROOM))
	assert_gt(boss.max_health, mob.max_health * 4.0, "boss dies as fast as its escort")
	assert_lt(boss.move_speed, mob.move_speed, "boss can run the player down")
