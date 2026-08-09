extends TestCase

## Run assembly: how base + gear + boons become the stat block combat uses,
## and how enemies scale with depth.

const ITEMS_PATH := "res://data/items.json"
const BOONS_PATH := "res://data/boons.json"


func test_a_fresh_run_starts_at_full_health() -> void:
	var run := RunState.start(1234)
	assert_almost_eq(run.health, run.build_stats().max_health, 0.01)
	assert_eq(run.act_number, 1)
	assert_eq(run.area_number, 1)
	assert_eq(run.depth(), 1)


func test_streams_are_derived_from_the_seed() -> void:
	var a := RunState.start(4321)
	var b := RunState.start(4321)
	assert_eq(a.loot_rng.seed_value, b.loot_rng.seed_value)
	assert_eq(a.boon_rng.seed_value, b.boon_rng.seed_value)
	assert_ne(a.loot_rng.seed_value, a.boon_rng.seed_value)
	assert_ne(a.boon_rng.seed_value, a.combat_rng.seed_value)


func test_gear_and_boons_both_reach_the_stat_block() -> void:
	var run := RunState.start(7)
	var bare := run.build_stats().expected_hit(StatBlock.new())

	var gen := ItemGenerator.from_json(ITEMS_PATH)
	run.equip(_weapon_with_affixes(gen))
	var geared := run.build_stats().expected_hit(StatBlock.new())
	assert_gt(geared, bare, "equipping a weapon must raise expected damage")

	var pool := BoonPool.from_json(BOONS_PATH)
	run.take_boon(_boon_by_id(pool, "odrin_weight").at_rarity(Boon.Rarity.HEROIC))
	assert_gt(run.build_stats().expected_hit(StatBlock.new()), geared, "boons must stack on top of gear")


func test_stats_are_rebuilt_not_accumulated() -> void:
	# Calling build_stats twice must not double-apply anything.
	var run := RunState.start(9)
	var gen := ItemGenerator.from_json(ITEMS_PATH)
	run.equip(_weapon_with_affixes(gen))
	var first := run.build_stats()
	var second := run.build_stats()
	assert_almost_eq(second.max_health, first.max_health, 0.0001)
	assert_almost_eq(second.weapon_max, first.weapon_max, 0.0001)
	assert_eq(second.more_mults.size(), first.more_mults.size())


func test_replacing_gear_leaves_nothing_behind() -> void:
	var run := RunState.start(11)
	var gen := ItemGenerator.from_json(ITEMS_PATH)

	var heavy := _weapon_with_affixes(gen)
	run.equip(heavy)
	var with_heavy := run.build_stats()

	# Swap in a bare base of the same slot; the old affixes must vanish entirely.
	var bare := Item.new()
	bare.slot = heavy.slot
	bare.base_name = "Bare"
	run.equip(bare)
	var after := run.build_stats()

	var baseline := RunState.base_stats()
	assert_almost_eq(after.max_health, baseline.max_health, 0.0001, "old gear's life persisted")
	assert_almost_eq(after.weapon_max, baseline.weapon_max, 0.0001, "old gear's damage persisted")
	assert_lt(after.expected_hit(StatBlock.new()), with_heavy.expected_hit(StatBlock.new()))


func test_gear_tags_are_collected_across_slots() -> void:
	var run := RunState.start(13)
	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var tagged := _weapon_with_tags(gen)
	run.equip(tagged)
	for t in tagged.tags():
		assert_has(run.gear_tags(), t)


func test_gear_tags_unlock_boons_for_the_run() -> void:
	# The whole gear-is-build-defining claim, end to end: the same boon pool
	# offers a different candidate set depending only on what is equipped.
	var pool := BoonPool.from_json(BOONS_PATH)
	var run := RunState.start(17)
	var bare_count := pool.candidates(run.owned_boon_ids(), run.owned_boon_groups(), run.gear_tags()).size()

	var gen := ItemGenerator.from_json(ITEMS_PATH)
	# Pin the tag rather than taking whatever drops: 'ignite' is known to gate
	# boons, so a failure here means the gate broke, not that the roll was dull.
	run.equip(_weapon_granting(gen, "ignite"))
	assert_has(run.gear_tags(), "ignite")
	var geared_count := pool.candidates(
		run.owned_boon_ids(), run.owned_boon_groups(), run.gear_tags()
	).size()
	assert_gt(float(geared_count), float(bare_count), "tagged gear must widen the boon pool")


func test_boon_granted_tags_join_the_active_set() -> void:
	var pool := BoonPool.from_json(BOONS_PATH)
	var run := RunState.start(29)
	assert_true(run.active_tags().is_empty(), "a fresh run should carry no tags")

	run.take_boon(_boon_by_id(pool, "morrow_ember").at_rarity(Boon.Rarity.COMMON))
	assert_has(run.boon_tags(), "ignite")
	assert_has(run.active_tags(), "ignite")
	assert_false(run.gear_tags().has("ignite"), "a boon tag must not masquerade as a gear tag")


func test_active_tags_unions_both_sources_without_duplicates() -> void:
	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var pool := BoonPool.from_json(BOONS_PATH)
	var run := RunState.start(31)

	run.equip(_weapon_granting(gen, "ignite"))
	run.take_boon(_boon_by_id(pool, "morrow_ember").at_rarity(Boon.Rarity.COMMON))

	var active := run.active_tags()
	assert_has(active, "ignite")
	var ignite_count := 0
	for t in active:
		if t == "ignite":
			ignite_count += 1
	assert_eq(ignite_count, 1, "a tag from both gear and a boon must appear once")


func test_a_typed_multiplier_only_pays_off_once_committed() -> void:
	# End to end: Morrow's amplifier is dead weight on a bare physical build and
	# live only after the entry boon has seeded fire damage.
	var pool := BoonPool.from_json(BOONS_PATH)
	var dummy := StatBlock.new()

	var uncommitted := RunState.start(37)
	var before := uncommitted.build_stats().expected_hit(dummy)
	uncommitted.take_boon(_boon_by_id(pool, "morrow_pyre").at_rarity(Boon.Rarity.HEROIC))
	assert_almost_eq(
		uncommitted.build_stats().expected_hit(dummy), before, 0.01,
		"a fire multiplier paid out on a build with no fire damage"
	)

	var committed := RunState.start(37)
	committed.take_boon(_boon_by_id(pool, "morrow_ember").at_rarity(Boon.Rarity.COMMON))
	var seeded := committed.build_stats().expected_hit(dummy)
	committed.take_boon(_boon_by_id(pool, "morrow_pyre").at_rarity(Boon.Rarity.HEROIC))
	assert_gt(
		committed.build_stats().expected_hit(dummy), seeded,
		"the same multiplier should pay out once fire damage exists"
	)


func test_owned_boons_report_ids_and_groups() -> void:
	var pool := BoonPool.from_json(BOONS_PATH)
	var run := RunState.start(19)
	var b := _boon_by_id(pool, "odrin_weight").at_rarity(Boon.Rarity.COMMON)
	run.take_boon(b)
	assert_has(run.owned_boon_ids(), "odrin_weight")
	assert_has(run.owned_boon_groups(), b.group)


func test_enemies_get_harder_with_depth() -> void:
	var previous := RunState.enemy_for_depth(1)
	for n in range(2, Progression.total_areas() + 1):
		var current := RunState.enemy_for_depth(n)
		assert_gt(current.max_health, previous.max_health, "area %d health did not rise" % n)
		assert_gt(current.weapon_max, previous.weapon_max, "area %d damage did not rise" % n)
		previous = current


func test_enemy_health_outpaces_enemy_damage() -> void:
	# Deep floors should test whether a build scales, not whether the player can
	# survive a one-shot. If damage ever outgrows health, that stops being true.
	var first := RunState.enemy_for_depth(1)
	var deep := RunState.enemy_for_depth(Progression.total_areas())
	var health_growth := deep.max_health / first.max_health
	var damage_growth := deep.weapon_max / first.weapon_max
	assert_gt(health_growth, damage_growth, "enemy damage is outscaling enemy health")


func test_enemy_damage_growth_stays_within_what_a_build_can_answer() -> void:
	# Guards the finding that prompted lowering DAMAGE_GROWTH. Player survival
	# scales roughly 3x across a run — flat armour and health from gear and
	# defensive boons — so enemy damage compounding far past that makes boon
	# choice irrelevant, which the simulator measured directly.
	assert_lt(
		RunState.AREA_DAMAGE_GROWTH, RunState.AREA_HEALTH_GROWTH,
		"damage must not outgrow health"
	)
	var areas := float(Progression.total_areas() - 1)
	var acts := float(Progression.ACTS - 1)
	var across_a_run := pow(RunState.AREA_DAMAGE_GROWTH, areas) * pow(RunState.ACT_DAMAGE_STEP, acts)
	assert_lt(
		across_a_run, 5.0,
		"enemy damage compounds past what a build's survival can answer"
	)


func test_enemy_resistances_phase_in_and_stay_capped() -> void:
	var early := RunState.enemy_for_depth(1)
	assert_almost_eq(early.resistances.get(Damage.Type.FIRE, 0.0), 0.0, 0.0001, "area 1 must be resist-free")
	for n in range(1, Progression.total_areas() + 4):
		var e := RunState.enemy_for_depth(n)
		assert_between(e.resistances.get(Damage.Type.FIRE, 0.0), 0.0, 0.4, "area %d resistance out of band" % n)
		assert_almost_eq(e.resistances.get(Damage.Type.PHYSICAL, 0.0), 0.0, 0.0001, "physical must stay unresisted")


func test_elites_are_strictly_harder() -> void:
	var normal := RunState.enemy_for_depth(6)
	var elite := RunState.enemy_for_depth(6, true)
	assert_gt(elite.max_health, normal.max_health)
	assert_gt(elite.weapon_max, normal.weapon_max)
	assert_gt(elite.armor, normal.armor - 0.0001)


func test_advance_area_walks_into_the_next_act() -> void:
	var run := RunState.start(23)
	for _i in Progression.AREAS_PER_ACT:
		assert_true(run.advance_area(), "run stalled inside act 1")
	assert_eq(run.act_number, 2)
	assert_eq(run.area_number, 1)
	assert_eq(run.depth(), Progression.AREAS_PER_ACT + 1)


func _weapon_with_affixes(gen: ItemGenerator) -> Item:
	var rng := Rng.new(101)
	for i in 3000:
		var item := gen.roll_item(25, rng, 5.0, "weapon")
		if item.affixes.size() >= 3:
			return item
	fail("could not roll a multi-affix weapon")
	return gen.roll_item(25, rng, 5.0, "weapon")


func _weapon_with_tags(gen: ItemGenerator) -> Item:
	var rng := Rng.new(202)
	for i in 3000:
		var item := gen.roll_item(25, rng, 5.0, "weapon")
		if item.tags().size() >= 2:
			return item
	fail("could not roll a weapon granting 2+ tags")
	return gen.roll_item(25, rng, 5.0, "weapon")


func _weapon_granting(gen: ItemGenerator, tag: String) -> Item:
	var rng := Rng.new(303)
	for i in 5000:
		var item := gen.roll_item(25, rng, 5.0, "weapon")
		if item.tags().has(tag):
			return item
	fail("could not roll a weapon granting '%s'" % tag)
	return gen.roll_item(25, rng, 5.0, "weapon")


func _boon_by_id(pool: BoonPool, id: String) -> Boon:
	for b in pool.boons:
		if b.id == id:
			return b
	fail("boon '%s' missing from the table" % id)
	return pool.boons[0]
