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


## Synergies: the shape that makes a school a tree rather than a menu.


func _syn_boon(tag: String, per: Dictionary, grants: Array) -> Boon.Rolled:
	var b := Boon.from_dict({
		"id": "syn_%s_%d" % [tag, per.size()],
		"name": "Synergy",
		"group": "g_%s" % tag,
		"mods": {},
		"grants_tags": grants,
		"synergy": {"tag": tag, "per": per},
	})
	return b.at_rarity(Boon.Rarity.COMMON)


func _plain_boon(id: String, grants: Array) -> Boon.Rolled:
	return Boon.from_dict({
		"id": id, "name": id, "group": id, "mods": {}, "grants_tags": grants,
	}).at_rarity(Boon.Rarity.COMMON)


## A synergy boon on its own is worth nothing. That is the point — it is payment
## for commitment, not a free bonus, and it must not quietly pay out to a build
## that has not committed.
func test_a_synergy_pays_nothing_alone() -> void:
	var solo := _syn_boon("frost", {"more.cold": 0.05}, ["frost"])
	assert_true(solo.synergy_with([solo]).is_empty(), "a lone synergy boon paid out")


## And it must not count itself: one frost boon plus one frost synergy boon is
## a single companion, not two.
func test_a_synergy_does_not_count_itself() -> void:
	var syn := _syn_boon("frost", {"more.cold": 0.05}, ["frost"])
	var mate := _plain_boon("rime", ["frost"])
	var out := syn.synergy_with([syn, mate])
	assert_almost_eq(float(out.get("more.cold", 0.0)), 0.05, 0.0001)


## Scales linearly with how deep the build is in that school.
func test_a_synergy_scales_with_its_school() -> void:
	var syn := _syn_boon("frost", {"more.cold": 0.05}, ["frost"])
	var build: Array = [syn]
	for i in 4:
		build.append(_plain_boon("frost_%d" % i, ["frost"]))
	assert_almost_eq(float(syn.synergy_with(build).get("more.cold", 0.0)), 0.20, 0.0001)


## Boons of another school are not companions. Without this a synergy would just
## be a bonus for taking any boons at all, and committing would mean nothing.
func test_a_synergy_ignores_other_schools() -> void:
	var syn := _syn_boon("frost", {"more.cold": 0.05}, ["frost"])
	var build: Array = [syn]
	for i in 4:
		build.append(_plain_boon("fire_%d" % i, ["ignite"]))
	assert_true(syn.synergy_with(build).is_empty(), "a cold synergy counted fire boons")


## Rarity scales the synergy too, so a Heroic synergy boon is worth more per
## companion than a Common one — otherwise rarity would be meaningless on
## exactly the boons meant to reward commitment.
func test_rarity_scales_the_synergy() -> void:
	var raw := Boon.from_dict({
		"id": "syn", "name": "syn", "group": "syn", "mods": {},
		"grants_tags": ["frost"], "synergy": {"tag": "frost", "per": {"more.cold": 0.05}},
	})
	var common := raw.at_rarity(Boon.Rarity.COMMON)
	var heroic := raw.at_rarity(Boon.Rarity.HEROIC)
	var mate := _plain_boon("rime", ["frost"])
	assert_gt(
		float(heroic.synergy_with([heroic, mate]).get("more.cold", 0.0)),
		float(common.synergy_with([common, mate]).get("more.cold", 0.0))
	)


## End to end through RunState: committing to a school must beat spreading the
## same number of picks across schools. If it does not, synergies are decoration.
func test_committing_to_a_school_beats_spreading() -> void:
	var dummy := StatBlock.new()

	var committed := RunState.start(5)
	committed.school = "cold"
	committed.take_boon(_syn_boon("frost", {"more.cold": 0.05}, ["frost"]))
	for i in 4:
		committed.take_boon(_plain_boon("frost_%d" % i, ["frost"]))

	var spread := RunState.start(5)
	spread.school = "cold"
	spread.take_boon(_syn_boon("frost", {"more.cold": 0.05}, ["frost"]))
	for i in 4:
		spread.take_boon(_plain_boon("fire_%d" % i, ["ignite"]))

	assert_gt(
		committed.build_stats().expected_hit(dummy),
		spread.build_stats().expected_hit(dummy),
		"five cold picks are worth no more than one cold pick and four fire ones"
	)


## Order of acquisition must not change the result. Synergies are computed
## against the finished build for exactly this reason: if they were folded in as
## each boon arrived, the sequence you were offered things in would silently
## decide what they are worth.
func test_synergy_is_independent_of_pick_order() -> void:
	var dummy := StatBlock.new()
	var syn := _syn_boon("frost", {"more.cold": 0.05}, ["frost"])
	var mates: Array = []
	for i in 3:
		mates.append(_plain_boon("frost_%d" % i, ["frost"]))

	var first := RunState.start(9)
	first.take_boon(syn)
	for m in mates:
		first.take_boon(m)

	var last := RunState.start(9)
	for m in mates:
		last.take_boon(m)
	last.take_boon(syn)

	assert_almost_eq(
		first.build_stats().expected_hit(dummy),
		last.build_stats().expected_hit(dummy),
		0.0001,
		"taking the synergy first is worth more than taking it last"
	)
