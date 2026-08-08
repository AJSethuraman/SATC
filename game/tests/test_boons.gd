extends TestCase

## Boon offers, and the gear-tag gate that makes equipment build-defining.

const BOONS_PATH := "res://data/boons.json"

## Tags this test relies on existing in the boon table. test_data.gd separately
## proves that every required tag is actually reachable from some affix.
const IGNITE := "ignite"


func _pool() -> BoonPool:
	return BoonPool.from_json(BOONS_PATH)


func test_table_loads() -> void:
	assert_gt(float(_pool().boons.size()), 0.0)


func test_offer_returns_three_distinct_groups() -> void:
	var pool := _pool()
	var rng := Rng.new(21)
	for i in 300:
		var offer := pool.offer(rng, [], [], [], 3)
		assert_eq(offer.size(), 3, "offer %d was short" % i)
		var groups: Array = []
		for b in offer:
			assert_false(groups.has(b.group), "offer %d repeated group '%s'" % [i, b.group])
			groups.append(b.group)


func test_offer_is_deterministic() -> void:
	var pool := _pool()
	var a := pool.offer(Rng.new(606), [], [], [], 3)
	var b := pool.offer(Rng.new(606), [], [], [], 3)
	for i in a.size():
		assert_eq(a[i].id, b[i].id)
		assert_eq(a[i].rarity, b[i].rarity)


func test_a_tag_gated_boon_never_appears_without_the_tag() -> void:
	var pool := _pool()
	var gated := _first_requiring_tag(pool, IGNITE)
	assert_not_null(gated, "expected at least one boon gated on '%s'" % IGNITE)

	var rng := Rng.new(88)
	for i in 400:
		for b in pool.offer(rng, [], [], [], 3):
			assert_ne(b.id, gated.id, "'%s' leaked into an offer with no gear tags" % gated.id)


func test_a_tag_gated_boon_becomes_reachable_with_the_tag() -> void:
	var pool := _pool()
	var gated := _first_requiring_tag(pool, IGNITE)
	# Satisfy any boon prerequisites so only the tag gate is under test.
	var owned := gated.requires_boons.duplicate()
	assert_true(
		pool.candidates(owned, [], [IGNITE]).any(func(b: Boon): return b.id == gated.id),
		"'%s' should be offerable once the run has the '%s' tag" % [gated.id, IGNITE]
	)


func test_prerequisite_boons_gate_their_dependents() -> void:
	var pool := _pool()
	var duo := _first_with_prereq(pool)
	assert_not_null(duo, "expected at least one boon with requires_boons")

	var tags := duo.requires_tags.duplicate()
	assert_false(
		pool.candidates([], [], tags).any(func(b: Boon): return b.id == duo.id),
		"'%s' should be locked until its prerequisite is owned" % duo.id
	)
	assert_true(
		pool.candidates(duo.requires_boons, [], tags).any(func(b: Boon): return b.id == duo.id),
		"'%s' should unlock once its prerequisite is owned" % duo.id
	)


func test_an_owned_group_is_never_offered_again() -> void:
	var pool := _pool()
	var owned := ["odrin_attack", "odrin_defense"]
	# Guard against the group names drifting and this test silently passing.
	for g in owned:
		assert_true(
			pool.boons.any(func(b: Boon): return b.group == g),
			"group '%s' no longer exists in the table" % g
		)
	var rng := Rng.new(13)
	for i in 200:
		for b in pool.offer(rng, [], owned, [], 3):
			assert_false(owned.has(b.group), "offered an already-owned group")


func test_an_entry_boon_unlocks_its_god() -> void:
	# Taking an entry boon must open the same doors that finding the gear would
	# — otherwise a run with no elemental drops can never build into anything.
	var pool := _pool()
	var entry := _first_granting_tag(pool, IGNITE)
	assert_not_null(entry, "expected an ungated boon granting '%s'" % IGNITE)
	assert_true(entry.requires_tags.is_empty(), "the entry boon must itself be ungated")

	var before := pool.candidates([], [], []).size()
	var after := pool.candidates([entry.id], [entry.group], entry.grants_tags).size()
	assert_gt(float(after), float(before) - 1.0, "taking the entry boon did not open its god's tree")

	var gated := _first_requiring_tag(pool, IGNITE)
	assert_true(
		pool.candidates([entry.id], [entry.group], entry.grants_tags).any(
			func(b: Boon): return b.id == gated.id
		),
		"'%s' should be reachable once the entry boon is owned" % gated.id
	)


func test_rarity_scales_every_modifier() -> void:
	var pool := _pool()
	var base: Boon = pool.boons[0]
	var common := base.at_rarity(Boon.Rarity.COMMON)
	var heroic := base.at_rarity(Boon.Rarity.HEROIC)
	for k in common.mods:
		assert_almost_eq(
			heroic.mods[k],
			common.mods[k] * Boon.RARITY_SCALE[Boon.Rarity.HEROIC],
			0.0001,
			"modifier '%s' did not scale with rarity" % k
		)


func test_luck_shifts_the_rarity_mix_upward() -> void:
	var pool := _pool()
	assert_gt(_uncommon_rate(pool, 4.0), _uncommon_rate(pool, 0.0) + 0.05)


func test_offer_degrades_gracefully_when_the_pool_runs_dry() -> void:
	var pool := _pool()
	var all_groups: Array = []
	for b in pool.boons:
		if not all_groups.has(b.group):
			all_groups.append(b.group)
	# Every group owned: an empty offer, not a hang and not a crash.
	assert_eq(pool.offer(Rng.new(1), [], all_groups, [], 3).size(), 0)


func _uncommon_rate(pool: BoonPool, luck: float) -> float:
	var rng := Rng.new(4004)
	var hits := 0
	var n := 3000
	for i in n:
		if pool.roll_rarity(rng, luck) != Boon.Rarity.COMMON:
			hits += 1
	return float(hits) / float(n)


func _first_requiring_tag(pool: BoonPool, tag: String) -> Boon:
	for b in pool.boons:
		if b.requires_tags.has(tag):
			return b
	return null


func _first_granting_tag(pool: BoonPool, tag: String) -> Boon:
	for b in pool.boons:
		if b.grants_tags.has(tag) and b.requires_tags.is_empty() and b.requires_boons.is_empty():
			return b
	return null


func _first_with_prereq(pool: BoonPool) -> Boon:
	for b in pool.boons:
		if not b.requires_boons.is_empty():
			return b
	return null
