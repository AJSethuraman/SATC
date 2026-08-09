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


# --- item tiers ---------------------------------------------------------
#
# The ladder from docs/difficulty-and-loot.md: plain in Normal, exceptional in
# Nightmare, elite in Hell, each allowing one more socket than the last. These
# tests exist because that is the mechanism the whole difficulty axis was added
# for — if a base leaks a pass early, a three-sigil inscription becomes a matter
# of luck again and the change bought nothing.


func test_a_base_above_the_current_difficulty_never_rolls() -> void:
	var g := _gen()
	for i in Progression.DIFFICULTIES:
		var difficulty := i + 1
		var rng := Rng.new(3100 + difficulty)
		for n in 900:
			var item := g.roll_item(_ilvl_in(difficulty), rng, 3.0, "", difficulty)
			assert_true(
				Item.min_difficulty(item.tier) <= difficulty,
				"%s base '%s' dropped in %s"
					% [
						Item.TIER_NAMES[item.tier],
						item.base_name,
						Progression.difficulty_name(difficulty),
					]
			)


func test_sockets_never_exceed_the_tier_ceiling() -> void:
	var g := _gen()
	for i in Progression.DIFFICULTIES:
		var difficulty := i + 1
		var rng := Rng.new(6400 + difficulty)
		for n in 1200:
			var item := g.roll_item(_ilvl_in(difficulty), rng, 0.0, "", difficulty)
			assert_true(
				item.sockets <= Item.max_sockets(item.tier),
				"%s '%s' rolled %d sockets, ceiling is %d"
					% [
						Item.TIER_NAMES[item.tier],
						item.base_name,
						item.sockets,
						Item.max_sockets(item.tier),
					]
			)


## The consequence the design is actually buying: a socket count you cannot
## reach is an inscription length you cannot assemble. Sampled against the real
## generator rather than read off the table, so it keeps holding however the
## socket weights are next retuned.
func test_each_pass_unlocks_exactly_one_more_socket() -> void:
	var g := _gen()
	var deepest: Array[int] = [0, 0, 0]
	for i in Progression.DIFFICULTIES:
		var difficulty := i + 1
		var rng := Rng.new(8800 + difficulty)
		for n in 5000:
			var item := g.roll_item(_ilvl_in(difficulty), rng, 0.0, "", difficulty)
			var top: int = deepest[i]
			deepest[i] = maxi(top, item.sockets)

	assert_eq(deepest[0], 2, "Normal must top out at a two-socket vessel")
	assert_eq(deepest[1], 3, "three-sigil words must become assemblable in Nightmare")
	assert_eq(deepest[2], 4, "four-sigil words must become assemblable in Hell")


func test_every_plain_base_has_higher_tier_counterparts() -> void:
	var g := _gen()
	for entry in g.bases:
		var base: Dictionary = entry
		if ItemGenerator.tier_of_base(base) != Item.Tier.PLAIN:
			continue
		assert_false(
			_counterpart(g, base, Item.Tier.EXCEPTIONAL).is_empty(),
			"'%s' has no %s counterpart; every base must return each pass"
				% [base.get("name"), Item.TIER_NAMES[Item.Tier.EXCEPTIONAL]]
		)
		assert_false(
			_counterpart(g, base, Item.Tier.ELITE).is_empty(),
			"'%s' has no %s counterpart; every base must return each pass"
				% [base.get("name"), Item.TIER_NAMES[Item.Tier.ELITE]]
		)


## Higher tiers are the same item met again, so the numbers may only go up and
## the stat lines may not change. A tier that gained or lost a line would be a
## different base wearing a familiar name, and the naming convention would stop
## telling the player anything true.
func test_a_higher_tier_base_is_strictly_better_than_the_one_below_it() -> void:
	var g := _gen()
	for entry in g.bases:
		var base: Dictionary = entry
		if ItemGenerator.tier_of_base(base) != Item.Tier.PLAIN:
			continue
		var exceptional := _counterpart(g, base, Item.Tier.EXCEPTIONAL)
		var elite := _counterpart(g, base, Item.Tier.ELITE)
		if exceptional.is_empty() or elite.is_empty():
			continue  # already reported by the counterpart test
		_assert_upgrade(base, exceptional)
		_assert_upgrade(exceptional, elite)


func test_each_pass_opens_more_of_the_base_table() -> void:
	var g := _gen()
	assert_lt(float(g.bases_for(1).size()), float(g.bases_for(2).size()))
	assert_lt(float(g.bases_for(2).size()), float(g.bases_for(3).size()))
	assert_eq(g.bases_for(3).size(), g.bases.size(), "Hell should reach the whole table")

	# Every slot needs a plain base or the very first drop of a run has nothing
	# to roll from, which roll_item can only report as a failed assertion.
	for entry in ["weapon", "armor", "trinket"]:
		var slot := str(entry)
		assert_gt(
			float(g.bases_for(1, slot).size()), 0.0,
			"slot '%s' has no base available in Normal" % slot
		)


func test_item_level_maps_onto_the_difficulty_pass() -> void:
	var per := Progression.areas_per_difficulty()
	assert_eq(ItemGenerator.difficulty_of_ilvl(1), 1)
	assert_eq(ItemGenerator.difficulty_of_ilvl(per), 1)
	assert_eq(ItemGenerator.difficulty_of_ilvl(per + 1), 2)
	assert_eq(ItemGenerator.difficulty_of_ilvl(2 * per), 2)
	assert_eq(ItemGenerator.difficulty_of_ilvl(2 * per + 1), 3)
	assert_eq(ItemGenerator.difficulty_of_ilvl(Progression.total_areas()), 3)


## A caller that does not name its difficulty gets it inferred from ilvl, which
## is the path scenes/main.gd and the simulators take today.
func test_item_level_alone_gates_the_tier() -> void:
	var g := _gen()
	var per := Progression.areas_per_difficulty()
	var rng := Rng.new(1717)
	for i in 500:
		var shallow := g.roll_item(per, rng, 2.0)
		assert_eq(
			shallow.tier, Item.Tier.PLAIN,
			"'%s' dropped at an ilvl still inside Normal" % shallow.base_name
		)
	for i in 500:
		var middle := g.roll_item(per + 1, rng, 2.0)
		assert_ne(
			middle.tier, Item.Tier.ELITE,
			"'%s' dropped at an ilvl still inside Nightmare" % middle.base_name
		)


# --- uniques and sets ---------------------------------------------------
#
# The other two ways to be powerful, from docs/difficulty-and-loot.md. Runewords
# are the assembled one and must stay the strongest on average, so most of what
# these tests pin is a *ceiling*: a named line may only use a modifier key the
# affix table already rolls, may never exceed the best roll of that key, and may
# never reach into the multiplicative bucket. A unique is therefore at most a
# rare that always rolled perfectly, and an inscription's multiplier still sits
# on top of it. See core/unique_pool.gd for the argument in full.

const UNIQUES_PATH := "res://data/uniques.json"


func _pool() -> UniquePool:
	return UniquePool.from_json(UNIQUES_PATH)


func test_a_unique_carries_the_modifiers_the_table_declares() -> void:
	var g := _gen()
	var pool := _pool()
	var found := 0
	for entry in _named_drops(g, 3, Item.Rarity.UNIQUE, 4000):
		var item := entry as Item
		if item == null:
			continue
		var piece := pool.piece_by_name(item.unique_name)
		assert_not_null(piece, "dropped unique '%s' is not in the table" % item.unique_name)
		if piece == null:
			continue
		found += 1
		assert_eq(
			item.affixes.size(), piece.mods.size(),
			"'%s' dropped with %d lines; the table declares %d"
				% [piece.display_name, item.affixes.size(), piece.mods.size()]
		)
		for a in item.affixes:
			for key in a.mods:
				var k := str(key)
				assert_true(
					piece.mods.has(k),
					"'%s' dropped with a line '%s' the table never declared" % [piece.display_name, k]
				)
				if not piece.mods.has(k):
					continue
				var declared := float(piece.mods[k])
				var got: float = a.mods[key]
				assert_almost_eq(
					got, declared, 0.0001,
					"'%s' rolled '%s' instead of taking its fixed value" % [piece.display_name, k]
				)
	assert_gt(float(found), 0.0, "no unique dropped in 4000 rolls; the generator hook is not firing")


## The fixed-not-rolled claim as the player meets it: two copies of the same
## named item are indistinguishable, where two rares never are.
func test_every_find_of_a_unique_is_the_same_item() -> void:
	var g := _gen()
	var seen := {}
	var repeats := 0
	for entry in _named_drops(g, 3, Item.Rarity.UNIQUE, 4000):
		var item := entry as Item
		if item == null:
			continue
		var lines := _lines_of(item)
		if not seen.has(item.unique_name):
			seen[item.unique_name] = lines
			continue
		repeats += 1
		var before: Dictionary = seen[item.unique_name]
		assert_eq(lines, before, "two finds of '%s' were not the same item" % item.unique_name)
	assert_gt(float(repeats), 0.0, "never found the same unique twice, so nothing was compared")


func test_a_unique_never_carries_a_rolled_affix() -> void:
	var g := _gen()
	var affix_ids: Array = []
	for a in g.affixes:
		affix_ids.append(a.id)

	for entry in _named_drops(g, 3, Item.Rarity.UNIQUE, 3000):
		var item := entry as Item
		if item == null:
			continue
		for a in item.affixes:
			assert_false(
				affix_ids.has(a.id),
				"unique '%s' carries rolled affix '%s'" % [item.unique_name, a.id]
			)
		# A named item is never a vessel, which is what stops a unique and a
		# runeword ever being the same item — you get one or the other.
		assert_eq(item.sockets, 0, "unique '%s' dropped with sockets" % item.unique_name)


func test_a_set_piece_knows_which_set_it_belongs_to() -> void:
	var g := _gen()
	var pool := _pool()
	var found := 0
	for entry in _named_drops(g, 3, Item.Rarity.SET, 4000):
		var item := entry as Item
		if item == null:
			continue
		found += 1
		assert_ne(item.set_id, "", "'%s' dropped as a set piece with no set" % item.unique_name)
		assert_not_null(
			pool.set_by_id(item.set_id),
			"'%s' names set '%s', which is not in the table" % [item.unique_name, item.set_id]
		)
	assert_gt(float(found), 0.0, "no set piece dropped in 4000 rolls")


func test_a_set_bonus_arrives_only_at_its_piece_count() -> void:
	var pool := _pool()
	var definition := _a_full_set(pool)
	if definition == null:
		return
	var members := pool.pieces_of_set(definition.id)

	var worn: Array = [_worn_piece(members[0])]
	assert_eq(int(UniquePool.worn_counts(worn).get(definition.id, 0)), 1)
	assert_true(
		pool.set_bonus_mods(worn).is_empty(),
		"'%s' paid out on one piece; a set is supposed to be weak alone" % definition.display_name
	)

	worn.append(_worn_piece(members[1]))
	assert_eq(int(UniquePool.worn_counts(worn).get(definition.id, 0)), 2)
	var two := pool.set_bonus_mods(worn)
	assert_false(two.is_empty(), "'%s' granted nothing at two pieces" % definition.display_name)

	worn.append(_worn_piece(members[2]))
	assert_eq(int(UniquePool.worn_counts(worn).get(definition.id, 0)), 3)
	var three := pool.set_bonus_mods(worn)

	# Thresholds accumulate rather than replace, so completing a set is a step up
	# and never a swap: nothing the two-piece bonus granted may go backwards.
	for key in two:
		var was: float = two[key]
		var now: float = float(three.get(key, 0.0))
		assert_true(
			now >= was,
			"completing '%s' lost '%s' that two pieces already granted" % [definition.display_name, key]
		)
	assert_true(
		three.size() > two.size() or _any_key_grew(three, two),
		"the last piece of '%s' is worth nothing" % definition.display_name
	)

	var tags_at_three := pool.set_bonus_tags(worn)
	for t in pool.set_bonus_tags([worn[0], worn[1]]):
		assert_has(tags_at_three, t, "completing the set dropped a tag two pieces had granted")


func test_wearing_the_same_piece_twice_does_not_complete_a_set() -> void:
	# A set bonus is exactly the thing worth cheating, and an array of items has
	# none of the one-per-slot discipline a gear dictionary gets for free.
	var pool := _pool()
	var definition := _a_full_set(pool)
	if definition == null:
		return
	var members := pool.pieces_of_set(definition.id)
	var worn: Array = [_worn_piece(members[0]), _worn_piece(members[0]), _worn_piece(members[0])]
	assert_eq(int(UniquePool.worn_counts(worn).get(definition.id, 0)), 1)
	assert_true(pool.set_bonus_mods(worn).is_empty(), "three copies of one piece earned a set bonus")


## The counting seam takes the shape a run actually holds its gear in, so wiring
## it up later cannot need a conversion step that changes the answer.
func test_a_gear_dictionary_counts_the_same_as_a_list() -> void:
	var pool := _pool()
	var definition := _a_full_set(pool)
	if definition == null:
		return
	var members := pool.pieces_of_set(definition.id)

	var worn: Array = []
	var gear := {}
	for entry in members:
		var item := _worn_piece(entry)
		worn.append(item)
		gear[item.slot] = item

	assert_eq(UniquePool.worn_counts(gear), UniquePool.worn_counts(worn))
	assert_eq(pool.set_bonus_mods(gear), pool.set_bonus_mods(worn))


func test_a_completed_set_reaches_the_stat_block() -> void:
	var pool := _pool()
	var definition := _a_full_set(pool)
	if definition == null:
		return

	var worn: Array = []
	for entry in pool.pieces_of_set(definition.id):
		worn.append(_worn_piece(entry))

	var with_bonus := RunState.base_stats()
	var without := RunState.base_stats()
	for entry in worn:
		var item := entry as Item
		item.apply_to(with_bonus)
		item.apply_to(without)
	pool.apply_set_bonuses(worn, with_bonus)

	assert_gt(
		with_bonus.expected_hit(StatBlock.new()) + with_bonus.max_health,
		without.expected_hit(StatBlock.new()) + without.max_health,
		"assembling '%s' changed nothing" % definition.display_name
	)


## Ordered by scarcity, and only by scarcity. Power is deliberately not monotonic
## along this ladder — a set piece is rarer than a rare and weaker than one —
## which is precisely why the ordering has to be pinned rather than assumed.
func test_the_rarity_ladder_stays_coherent() -> void:
	var ladder: Array = [
		Item.Rarity.NORMAL,
		Item.Rarity.MAGIC,
		Item.Rarity.RARE,
		Item.Rarity.SET,
		Item.Rarity.UNIQUE,
	]
	assert_eq(ladder.size(), Item.RARITY_NAMES.size(), "a rarity exists without a name")
	assert_eq(ladder.size(), Item.AFFIX_COUNTS.size(), "a rarity exists without a line budget")
	assert_eq(
		ladder.size(), ItemGenerator.BASE_RARITY_WEIGHTS.size(),
		"a rarity exists without a drop weight, so it can never drop"
	)

	var previous := INF
	for i in ladder.size():
		var r: int = ladder[i]
		assert_eq(r, i, "the Rarity enum is no longer declared in scarcity order")
		assert_true(Item.RARITY_NAMES.has(r), "rarity %d has no name" % r)
		assert_true(Item.AFFIX_COUNTS.has(r), "rarity %d has no line budget" % r)
		assert_true(ItemGenerator.BASE_RARITY_WEIGHTS.has(r), "rarity %d has no drop weight" % r)
		var w: float = float(ItemGenerator.BASE_RARITY_WEIGHTS.get(r, 0.0))
		assert_lt(w, previous, "'%s' is not rarer than the rarity below it" % Item.RARITY_NAMES.get(r, r))
		previous = w


func test_named_drops_stay_the_rarest_things_that_drop() -> void:
	var g := _gen()
	var rng := Rng.new(90210)
	var counts := {}
	var n := 20000
	for i in n:
		var r: int = g.roll_rarity(rng, 0.0)
		counts[r] = int(counts.get(r, 0)) + 1

	var rares := float(counts.get(Item.Rarity.RARE, 0))
	var sets := float(counts.get(Item.Rarity.SET, 0))
	var uniques := float(counts.get(Item.Rarity.UNIQUE, 0))
	assert_gt(rares, sets, "set pieces should be rarer than rares")
	assert_gt(sets, uniques, "uniques should be the rarest named drop")
	assert_lt(uniques / float(n), 0.02, "a unique should stay a story, not a habit")


## The invariant the whole "runewords stay strongest" claim rests on. The
## multiplicative bucket belongs to boons and inscriptions; a unique that reaches
## into it stops being a very good rare and starts competing with the thing the
## player is meant to assemble.
func test_no_named_line_grants_a_more_multiplier() -> void:
	for entry in _named_mod_sets(_pool()):
		var source: Array = entry
		var label := str(source[0])
		var mods: Dictionary = source[1]
		for key in mods:
			var k := str(key)
			assert_false(
				k == "more" or k.begins_with("more."),
				"'%s' grants '%s'; the more bucket belongs to boons and inscriptions" % [label, k]
			)


func test_no_named_line_beats_the_best_roll_of_the_same_affix() -> void:
	var best := _best_affix_values(_gen())
	for entry in _named_mod_sets(_pool()):
		var source: Array = entry
		var label := str(source[0])
		var mods: Dictionary = source[1]
		for key in mods:
			var k := str(key)
			assert_true(
				best.has(k),
				"'%s' grants '%s', which no affix rolls; it is outside the budget" % [label, k]
			)
			if not best.has(k):
				continue
			var ceiling: float = best[k]
			var value := float(mods[key])
			assert_true(
				value <= ceiling + 0.0001,
				"'%s' grants %f of '%s'; the best affix roll of it is %f" % [label, value, k, ceiling]
			)


## A full set occupies every slot it spans, so its ceiling is what those slots
## could have held as perfect rares. Strong assembled, never more than the thing
## it replaced — which is what leaves the runeword room to be the best outcome.
func test_an_assembled_set_is_worth_no_more_than_the_slots_it_fills() -> void:
	var pool := _pool()
	var best := _best_affix_values(_gen())
	for entry in pool.sets:
		var definition := entry as UniquePool.SetDefinition
		if definition == null:
			continue
		var members := pool.pieces_of_set(definition.id)
		var total := {}
		for m in members:
			var piece := m as UniquePool.Piece
			if piece != null:
				_accumulate(total, piece.mods)
		for b in definition.bonuses_at(members.size()):
			var bonus := b as UniquePool.Bonus
			if bonus != null:
				_accumulate(total, bonus.mods)

		for key in total:
			var k := str(key)
			var ceiling: float = float(best.get(k, 0.0)) * float(members.size())
			var value := float(total[key])
			assert_true(
				value <= ceiling + 0.0001,
				"assembled '%s' grants %f of '%s'; %d perfect rares would give %f"
					% [definition.display_name, value, k, members.size(), ceiling]
			)


func test_named_content_fits_its_rarity_line_budget() -> void:
	for entry in _pool().pieces:
		var piece := entry as UniquePool.Piece
		if piece == null:
			continue
		var span: Array = Item.AFFIX_COUNTS[piece.rarity()]
		assert_between(
			float(piece.mods.size()), float(span[0]), float(span[1]),
			"'%s' carries %d lines; %s allows %s"
				% [
					piece.display_name,
					piece.mods.size(),
					Item.RARITY_NAMES[piece.rarity()],
					span,
				]
		)
		for key in piece.mods:
			var k := str(key)
			if k.begins_with("flat.") or k in ["armor", "max_health", "move_speed"]:
				var v := float(piece.mods[key])
				assert_almost_eq(
					v, roundf(v), 0.0001, "'%s' has a fractional '%s'" % [piece.display_name, k]
				)


## A slot with nothing named to find in Normal silently demotes every unique roll
## there back to a rare, and a whole rarity is invisible for a third of the run.
func test_every_slot_has_something_named_to_find_in_the_first_pass() -> void:
	var pool := _pool()
	for entry in ["weapon", "armor", "trinket"]:
		var slot := str(entry)
		assert_gt(
			float(pool.pieces_for(Item.Rarity.UNIQUE, slot, 1).size()), 0.0,
			"slot '%s' has no unique available in Normal" % slot
		)
		assert_gt(
			float(pool.pieces_for(Item.Rarity.SET, slot, 1).size()), 0.0,
			"slot '%s' has no set piece available in Normal" % slot
		)


## Two pieces sharing a slot, or a bonus needing more pieces than the set has, is
## dead content: the player chases a thing that cannot be completed.
func test_a_set_can_actually_be_completed() -> void:
	var pool := _pool()
	for entry in pool.sets:
		var definition := entry as UniquePool.SetDefinition
		if definition == null:
			continue
		var members := pool.pieces_of_set(definition.id)
		assert_gt(float(members.size()), 1.0, "set '%s' has fewer than two pieces" % definition.id)

		var slots: Array = []
		for m in members:
			var piece := m as UniquePool.Piece
			if piece == null:
				continue
			assert_false(
				slots.has(piece.slot),
				"set '%s' has two pieces for the '%s' slot" % [definition.id, piece.slot]
			)
			slots.append(piece.slot)
			assert_eq(
				piece.min_difficulty, definition.min_difficulty,
				"piece '%s' drops in a different pass from the rest of its set" % piece.id
			)

		for b in definition.bonuses:
			var bonus := b as UniquePool.Bonus
			if bonus == null:
				continue
			assert_gt(float(bonus.pieces), 1.0, "a one-piece 'set bonus' is just an affix")
			assert_true(
				bonus.pieces <= members.size(),
				"set '%s' has a %d-piece bonus and only %d pieces"
					% [definition.id, bonus.pieces, members.size()]
			)


func test_named_ids_and_names_are_distinct() -> void:
	var ids: Array = []
	var names: Array = []
	for entry in _pool().pieces:
		var piece := entry as UniquePool.Piece
		if piece == null:
			continue
		assert_false(ids.has(piece.id), "duplicate named-item id '%s'" % piece.id)
		assert_false(names.has(piece.display_name), "two named items are called '%s'" % piece.display_name)
		ids.append(piece.id)
		names.append(piece.display_name)


## Every drop of one named rarity out of a fixed number of rolls, taken deep
## enough that the whole table is reachable.
func _named_drops(g: ItemGenerator, difficulty: int, rarity: Item.Rarity, tries: int) -> Array:
	var rng := Rng.new(5150 + int(rarity))
	var out: Array = []
	for i in tries:
		var item := g.roll_item(_ilvl_in(difficulty), rng, 4.0, "", difficulty)
		if item.rarity == rarity:
			out.append(item)
	return out


## An item's modifier lines flattened into one key -> value dictionary.
func _lines_of(item: Item) -> Dictionary:
	var out := {}
	for a in item.affixes:
		for key in a.mods:
			var v: float = a.mods[key]
			out[str(key)] = v
	return out


## An item wearing one named piece, built without a generator so a test can hold
## an exact loadout rather than fish for one.
func _worn_piece(entry: Variant) -> Item:
	var item := Item.new()
	var piece := entry as UniquePool.Piece
	if piece != null:
		piece.stamp(item)
	return item


func _a_full_set(pool: UniquePool) -> UniquePool.SetDefinition:
	for entry in pool.sets:
		var definition := entry as UniquePool.SetDefinition
		if definition != null and pool.pieces_of_set(definition.id).size() >= 3:
			return definition
	fail("no three-piece set in the table to test against")
	return null


## Every fixed modifier block in the named table, as [label, mods] pairs — the
## pieces themselves and every set bonus.
func _named_mod_sets(pool: UniquePool) -> Array:
	var out: Array = []
	for entry in pool.pieces:
		var piece := entry as UniquePool.Piece
		if piece != null:
			out.append([piece.display_name, piece.mods])
	for entry in pool.sets:
		var definition := entry as UniquePool.SetDefinition
		if definition == null:
			continue
		for b in definition.bonuses:
			var bonus := b as UniquePool.Bonus
			if bonus != null:
				out.append(["%s (%d pieces)" % [definition.display_name, bonus.pieces], bonus.mods])
	return out


## The strongest roll the affix table can produce for each modifier key.
func _best_affix_values(g: ItemGenerator) -> Dictionary:
	var best := {}
	for a in g.affixes:
		for key in a.ranges:
			var span: Array = a.ranges[key]
			var k := str(key)
			best[k] = maxf(float(best.get(k, -INF)), float(span[1]))
	return best


func _accumulate(into: Dictionary, mods: Dictionary) -> void:
	for key in mods:
		var k := str(key)
		var v := float(mods[key])
		into[k] = float(into.get(k, 0.0)) + v


func _any_key_grew(after: Dictionary, before: Dictionary) -> bool:
	for key in after:
		var now: float = after[key]
		var was: float = float(before.get(key, 0.0))
		if now > was:
			return true
	return false


## An item level in the middle of a pass, far enough in that nothing else gates.
func _ilvl_in(difficulty: int) -> int:
	return (difficulty - 1) * Progression.areas_per_difficulty() + 20


## The same base one or two tiers up, by the prefix naming convention, or {} if
## there is none.
func _counterpart(g: ItemGenerator, plain: Dictionary, wanted: Item.Tier) -> Dictionary:
	var plain_name := str(plain.get("name", ""))
	for entry in g.bases:
		var other: Dictionary = entry
		var other_name := str(other.get("name", ""))
		if other_name == plain_name:
			continue
		if ItemGenerator.tier_of_base(other) != wanted:
			continue
		if str(other.get("slot", "")) != str(plain.get("slot", "")):
			continue
		if other_name.ends_with(plain_name):
			return other
	return {}


func _assert_upgrade(lower: Dictionary, higher: Dictionary) -> void:
	var before: Dictionary = lower.get("implicit", {})
	var after: Dictionary = higher.get("implicit", {})
	assert_eq(
		after.keys().size(), before.keys().size(),
		"'%s' and '%s' have different implicit lines" % [lower.get("name"), higher.get("name")]
	)

	var improved := false
	for key in before:
		assert_true(
			after.has(key),
			"'%s' drops implicit '%s' that '%s' has" % [higher.get("name"), key, lower.get("name")]
		)
		var was: float = before[key]
		var now: float = after.get(key, 0.0)
		assert_true(
			now >= was,
			"'%s' has worse '%s' than '%s' (%f vs %f)"
				% [higher.get("name"), key, lower.get("name"), now, was]
		)
		if now > was:
			improved = true
	assert_true(
		improved,
		"'%s' is no better than '%s'" % [higher.get("name"), lower.get("name")]
	)


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
