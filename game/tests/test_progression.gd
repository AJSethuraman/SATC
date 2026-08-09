extends TestCase

## The shape of a run.
##
## These are mostly structural assertions rather than balance ones — balance is
## the simulator's job. What they pin is that the act model stays coherent: that
## depth and act_of_depth are actually inverses, that every act has exactly one
## boss and one respite, and that a run cannot advance past its last act.


func test_depth_counts_areas_across_acts_and_passes() -> void:
	assert_eq(Progression.depth(1, 1, 1), 1)
	assert_eq(Progression.depth(1, 1, Progression.AREAS_PER_ACT), Progression.AREAS_PER_ACT)
	assert_eq(Progression.depth(1, 2, 1), Progression.AREAS_PER_ACT + 1)
	assert_eq(Progression.depth(2, 1, 1), Progression.areas_per_difficulty() + 1)
	assert_eq(
		Progression.depth(Progression.DIFFICULTIES, Progression.ACTS, Progression.AREAS_PER_ACT),
		Progression.total_areas()
	)


## depth() and its inverses must agree, or scaling and structure disagree about
## where the run is. The Cinderwaste is act 1 in Hell exactly as in Normal, so
## act_of_depth wraps within a pass rather than counting globally.
func test_depth_inverts_across_every_pass() -> void:
	for difficulty in range(1, Progression.DIFFICULTIES + 1):
		for act in range(1, Progression.ACTS + 1):
			for area in range(1, Progression.AREAS_PER_ACT + 1):
				var d := Progression.depth(difficulty, act, area)
				assert_eq(Progression.difficulty_of_depth(d), difficulty,
					"depth %d should be in pass %d" % [d, difficulty])
				assert_eq(Progression.act_of_depth(d), act,
					"depth %d should be in act %d" % [d, act])


## Every pass covers the same places. If a pass ever had a different act count
## the whole point — that Hell *is* the Cinderwaste again, harder — would be
## quietly gone.
func test_every_pass_walks_the_same_acts() -> void:
	assert_eq(Progression.areas_per_difficulty(), Progression.ACTS * Progression.AREAS_PER_ACT)
	assert_eq(
		Progression.total_areas(), Progression.DIFFICULTIES * Progression.areas_per_difficulty()
	)
	for difficulty in range(1, Progression.DIFFICULTIES + 1):
		assert_eq(
			Progression.area_name(1, 1), "The Ashen Verge",
			"the first area is the same place on every pass"
		)


## A pass boundary must dwarf an act boundary. Nightmare has to invalidate a
## Normal build outright, or a banked runeword carries the whole run and the
## design collapses back into "farm one good weapon".
func test_a_new_pass_is_a_bigger_step_than_a_new_act() -> void:
	var across_act := (
		RunState.enemy_for_depth(Progression.AREAS_PER_ACT + 1).max_health
		/ RunState.enemy_for_depth(Progression.AREAS_PER_ACT).max_health
	)
	var per_area := Progression.areas_per_difficulty()
	var across_pass := (
		RunState.enemy_for_depth(per_area + 1).max_health
		/ RunState.enemy_for_depth(per_area).max_health
	)
	assert_gt(across_pass, across_act * 1.5,
		"a pass boundary (%.2fx) is not meaningfully harder than an act one (%.2fx)"
			% [across_pass, across_act])


func test_each_act_has_exactly_one_boss_and_one_respite() -> void:
	var bosses := 0
	var respites := 0
	var combats := 0
	for area in range(1, Progression.AREAS_PER_ACT + 1):
		match Progression.kind_of(area):
			Progression.AreaKind.BOSS:
				bosses += 1
			Progression.AreaKind.RESPITE:
				respites += 1
			_:
				combats += 1
	assert_eq(bosses, 1)
	assert_eq(respites, 1)
	assert_eq(combats, Progression.AREAS_PER_ACT - 2)


## The act must end on the boss, not merely contain one.
func test_the_boss_is_the_last_area() -> void:
	assert_eq(Progression.kind_of(Progression.AREAS_PER_ACT), Progression.AreaKind.BOSS)


## An act should pay in both currencies. A rhythm that handed out only gear
## would leave the boon pool — and every tag gate built on it — unused.
func test_an_act_grants_both_items_and_boons() -> void:
	var items := 0
	var boons := 0
	for area in range(1, Progression.AREAS_PER_ACT + 1):
		match Progression.reward_of(area):
			Progression.Reward.ITEM:
				items += 1
			Progression.Reward.BOON:
				boons += 1
	# Gear and boons gate each other — an item's tags widen the boon pool — so a
	# lopsided act starves one of the two systems.
	assert_eq(items, boons, "an act pays %d items against %d boons" % [items, boons])
	assert_gt(items, 0, "an act grants no rewards at all")
	assert_eq(Progression.reward_of(Progression.BOSS_AREA), Progression.Reward.ACT_PRIZE)
	assert_eq(Progression.reward_of(Progression.RESPITE_AREA), Progression.Reward.NONE)


func test_respite_areas_are_empty_and_boss_areas_are_not() -> void:
	assert_eq(Progression.enemy_count(1, Progression.RESPITE_AREA), 0)
	assert_gt(Progression.enemy_count(1, Progression.BOSS_AREA), 0)
	# Later acts field more bodies than the first.
	assert_gt(
		float(Progression.enemy_count(Progression.ACTS, 1)),
		float(Progression.enemy_count(1, 1))
	)


## Walking the whole run must land exactly on the last area of the last act and
## then refuse to go further — a run that can advance forever has no ending.
func test_a_run_walks_every_area_then_stops() -> void:
	var run := RunState.start(4242)
	var visited := 1
	while run.advance_area():
		visited += 1
		assert_lt(float(visited), float(Progression.total_areas() + 1), "run overran its acts")

	assert_eq(visited, Progression.total_areas())
	assert_eq(run.difficulty_number, Progression.DIFFICULTIES)
	assert_eq(run.act_number, Progression.ACTS)
	assert_eq(run.area_number, Progression.AREAS_PER_ACT)
	assert_eq(run.depth(), Progression.total_areas())


## An act boundary should be felt. Entering a new act must be a step up, not a
## continuation of the same slope.
func test_entering_an_act_is_a_step_up() -> void:
	var last_of_act := RunState.enemy_for_depth(Progression.AREAS_PER_ACT)
	var first_of_next := RunState.enemy_for_depth(Progression.AREAS_PER_ACT + 1)
	var within_act := RunState.enemy_for_depth(2).max_health / RunState.enemy_for_depth(1).max_health
	var across := first_of_next.max_health / last_of_act.max_health
	assert_gt(across, within_act, "crossing into a new act is no harder than the area before")


## The curve the simulator flagged: enemy damage must not outrun a player whose
## defences arrive in flat lumps. Across a full clear it may grow, but nothing
## like as fast as health does.
func test_damage_grows_more_slowly_than_health() -> void:
	var first := RunState.enemy_for_depth(1)
	var last := RunState.enemy_for_depth(Progression.total_areas())
	var health_growth := last.max_health / first.max_health
	var damage_growth := last.weapon_max / first.weapon_max
	assert_gt(health_growth, damage_growth * 3.0,
		"health %.1fx vs damage %.1fx — damage is compounding too fast" %
			[health_growth, damage_growth])
	# Bound raised with the run length: this was 4x for a 32-area run and the
	# run is 120 areas across three passes now. The ratio to health is the part
	# that matters and it is asserted above; this only catches runaway.
	assert_lt(damage_growth, 14.0, "damage grows %.1fx across a run" % damage_growth)


func test_a_boss_outlasts_the_area_it_ends() -> void:
	var boss := RunState.boss_for_act(1, 1)
	var mob := RunState.enemy_for_depth(Progression.depth(1, 1, Progression.BOSS_AREA))
	assert_gt(boss.max_health, mob.max_health * 4.0, "boss dies as fast as its escort")
	assert_lt(boss.move_speed, mob.move_speed, "boss can run the player down")


## Every area is a named place, and no name repeats. This is the entire point of
## calling the unit an area rather than a floor: "Floor 11" is a coordinate, and
## a run made of coordinates has no sense of going anywhere. A missing or
## duplicated name silently turns part of the map back into a number.
func test_every_area_is_named_and_no_name_repeats() -> void:
	var seen: Array[String] = []
	for act in range(1, Progression.ACTS + 1):
		for area in range(1, Progression.AREAS_PER_ACT + 1):
			var name_here := Progression.area_name(act, area)
			assert_ne(name_here, "", "act %d area %d has no name" % [act, area])
			assert_false(seen.has(name_here), "duplicate area name: %s" % name_here)
			seen.append(name_here)
	assert_eq(seen.size(), Progression.total_areas())


## The names table must actually cover the structure. A short act would silently
## clamp to its last name, so two areas would share one place.
func test_the_name_table_matches_the_act_shape() -> void:
	assert_eq(Progression.AREA_NAMES.size(), Progression.ACTS)
	for act_names in Progression.AREA_NAMES:
		var names: Array = act_names
		assert_eq(names.size(), Progression.AREAS_PER_ACT)


## The attack-token pool has to be smaller than the smallest crowd, or it never
## binds and the horde goes back to swinging all at once — which is the exact
## failure it exists to prevent, and an invisible one, because nothing looks
## broken. It just stops being dodgeable.
func test_the_attack_token_pool_actually_binds() -> void:
	var smallest := Progression.enemy_count(1, 1)
	for act in range(1, Progression.ACTS + 1):
		for area in range(1, Progression.AREAS_PER_ACT + 1):
			if Progression.kind_of(area) != Progression.AreaKind.COMBAT:
				continue
			smallest = mini(smallest, Progression.enemy_count(act, area))
	assert_gt(
		float(smallest), float(Feel.ATTACK_TOKENS),
		"every body in the smallest area (%d) can swing at once with %d tokens"
			% [smallest, Feel.ATTACK_TOKENS]
	)


## And a crowd has to actually be a crowd. The whole point of pairing tokens
## with density is that the screen can hold a horde; if density drifts back down
## the tokens are solving a problem that no longer exists.
func test_an_area_holds_a_crowd() -> void:
	assert_gt(float(Progression.enemy_count(1, 1)), 6.0, "act I opens too thin to read as a horde")
	assert_gt(
		float(Progression.enemy_count(Progression.ACTS, 1)),
		float(Progression.enemy_count(1, 1)),
		"the last act is no denser than the first"
	)
