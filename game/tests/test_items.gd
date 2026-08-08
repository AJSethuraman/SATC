extends TestCase

## Item generation: roll ranges, group exclusion, ilvl gating, rarity.

const ITEMS_PATH := "res://data/items.json"


func _gen() -> ItemGenerator:
	return ItemGenerator.from_json(ITEMS_PATH)


func test_table_loads() -> void:
	var g := _gen()
	assert_gt(float(g.bases.size()), 0.0)
	assert_gt(float(g.affixes.size()), 0.0)


func test_affix_rolls_land_inside_their_declared_range() -> void:
	var g := _gen()
	var rng := Rng.new(8)
	for a in g.affixes:
		for i in 200:
			var rolled := a.roll(rng)
			for key in a.ranges:
				var span: Array = a.ranges[key]
				var v: float = rolled.mods[str(key)]
				# Integral stats round, so widen by half a unit on each side.
				assert_between(
					v, float(span[0]) - 0.5, float(span[1]) + 0.5,
					"%s rolled %s = %f outside %s" % [a.id, key, v, span]
				)


func test_generation_is_deterministic() -> void:
	var g := _gen()
	var first := g.roll_item(20, Rng.new(555), 1.0)
	var second := g.roll_item(20, Rng.new(555), 1.0)
	assert_eq(first.display_name(), second.display_name())
	assert_eq(first.affixes.size(), second.affixes.size())
	for i in first.affixes.size():
		assert_eq(first.affixes[i].id, second.affixes[i].id)
		assert_eq(first.affixes[i].mods, second.affixes[i].mods)


func test_an_item_never_repeats_an_affix_group() -> void:
	var g := _gen()
	var rng := Rng.new(4242)
	for i in 500:
		var item := g.roll_item(25, rng, 3.0)
		var groups: Array = []
		for a in item.affixes:
			var group := _group_of(g, a.id)
			assert_false(groups.has(group), "item %d repeated group '%s'" % [i, group])
			groups.append(group)


func test_rarity_controls_affix_count() -> void:
	var g := _gen()
	var rng := Rng.new(99)
	for i in 800:
		var item := g.roll_item(25, rng, 2.0)
		var span: Array = Item.AFFIX_COUNTS[item.rarity]
		assert_between(
			float(item.affixes.size()), float(span[0]), float(span[1]),
			"%s item had %d affixes" % [Item.RARITY_NAMES[item.rarity], item.affixes.size()]
		)


func test_ilvl_gates_high_tier_affixes() -> void:
	var g := _gen()
	var rng := Rng.new(17)
	for i in 600:
		var item := g.roll_item(1, rng, 5.0)
		for a in item.affixes:
			assert_true(
				_ilvl_req_of(g, a.id) <= 1,
				"ilvl 1 item rolled '%s' which requires a higher ilvl" % a.id
			)


func test_higher_ilvl_unlocks_more_of_the_table() -> void:
	var g := _gen()
	assert_gt(
		float(g.eligible("weapon", 20, []).size()),
		float(g.eligible("weapon", 1, []).size()),
		"deeper floors must open up the affix table"
	)


func test_used_groups_are_excluded_from_eligibility() -> void:
	var g := _gen()
	var all := g.eligible("weapon", 20, [])
	var without := g.eligible("weapon", 20, ["life"])
	assert_lt(float(without.size()), float(all.size()))
	for a in without:
		assert_ne(a.group, "life")


func test_magic_find_raises_rarity_without_changing_drop_count() -> void:
	var g := _gen()
	var plain := _non_normal_rate(g, 0.0)
	var juiced := _non_normal_rate(g, 3.0)
	assert_gt(juiced, plain + 0.05, "magic find should visibly shift the rarity mix")
	assert_lt(plain, 0.6, "baseline rarity mix should still be mostly normal")


func test_integral_stats_stay_whole_numbers() -> void:
	var g := _gen()
	var rng := Rng.new(63)
	for i in 300:
		var item := g.roll_item(25, rng, 2.0)
		for a in item.affixes:
			for key in a.mods:
				if str(key).begins_with("flat.") or key in ["armor", "max_health", "move_speed"]:
					var v: float = a.mods[key]
					assert_almost_eq(v, roundf(v), 0.0001, "%s.%s = %f is fractional" % [a.id, key, v])


func test_equipping_an_item_moves_the_stat_block() -> void:
	var g := _gen()
	var stats := RunState.base_stats()
	var before := stats.expected_hit(StatBlock.new())

	# Force a heavily-affixed item so the assertion is not at the mercy of a
	# normal-rarity roll.
	var item := _rare_item(g, 25)
	item.apply_to(stats)
	assert_gt(stats.expected_hit(StatBlock.new()), before, "gear must actually do something")


func _rare_item(g: ItemGenerator, ilvl: int) -> Item:
	var rng := Rng.new(1)
	for i in 2000:
		var item := g.roll_item(ilvl, rng, 5.0, "weapon")
		if item.affixes.size() >= 3:
			return item
	fail("could not roll a multi-affix weapon in 2000 tries")
	return g.roll_item(ilvl, rng, 5.0, "weapon")


func _non_normal_rate(g: ItemGenerator, mf: float) -> float:
	var rng := Rng.new(2718)
	var hits := 0
	var n := 3000
	for i in n:
		if g.roll_rarity(rng, mf) != Item.Rarity.NORMAL:
			hits += 1
	return float(hits) / float(n)


func _group_of(g: ItemGenerator, affix_id: String) -> String:
	for a in g.affixes:
		if a.id == affix_id:
			return a.group
	return "<unknown:%s>" % affix_id


func _ilvl_req_of(g: ItemGenerator, affix_id: String) -> int:
	for a in g.affixes:
		if a.id == affix_id:
			return a.ilvl_req
	return 0
