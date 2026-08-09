extends TestCase

## Sigils, sockets and inscription matching.

const SIGILS_PATH := "res://data/sigils.json"
const ITEMS_PATH := "res://data/items.json"


func _book() -> InscriptionBook:
	return InscriptionBook.from_json(SIGILS_PATH)


func _vessel(slot: String, sockets: int) -> Item:
	var item := Item.new()
	item.slot = slot
	item.base_name = "Test Vessel"
	item.sockets = sockets
	return item


func _fill(item: Item, book: InscriptionBook, ids: Array) -> Item:
	for id in ids:
		item.insert(book.sigil_by_id(str(id)))
	item.reappraise(book)
	return item


func test_tables_load() -> void:
	var book := _book()
	assert_gt(float(book.sigils.size()), 0.0)
	assert_gt(float(book.inscriptions.size()), 0.0)


func test_the_exact_pattern_forms_the_inscription() -> void:
	var book := _book()
	var word: Inscription = book.inscription_by_id("kindling")
	assert_not_null(word)

	var item := _fill(_vessel(word.slot, 2), book, word.pattern)
	assert_true(item.is_inscribed(), "the exact pattern should have formed '%s'" % word.id)
	assert_eq(item.inscription.id, word.id)


func test_order_matters() -> void:
	# The whole reason these are recipes rather than collections. Same sigils,
	# wrong order, nothing happens.
	var book := _book()
	var word: Inscription = book.inscription_by_id("kindling")
	var reversed_pattern := word.pattern.duplicate()
	reversed_pattern.reverse()
	assert_ne(reversed_pattern, word.pattern, "test needs an asymmetric pattern")

	var item := _fill(_vessel(word.slot, 2), book, reversed_pattern)
	assert_false(item.is_inscribed(), "a reversed pattern must not form the inscription")


func test_wrong_slot_does_not_match() -> void:
	var book := _book()
	var word: Inscription = book.inscription_by_id("kindling")
	var item := _fill(_vessel("trinket", word.pattern.size()), book, word.pattern)
	assert_false(item.is_inscribed(), "a weapon inscription must not form in a trinket")


func test_a_partial_sequence_forms_nothing() -> void:
	var book := _book()
	var word: Inscription = book.inscription_by_id("conflagrant")
	var item := _fill(_vessel(word.slot, 3), book, [word.pattern[0]])
	assert_false(item.is_inscribed(), "one sigil of three must not complete the word")


func test_the_socket_count_must_match_exactly() -> void:
	# D2's rule: a four-socket item will not carry a three-socket formula. Without
	# it, a large vessel does everything a small one does and 2-socket vessels
	# stop being worth banking. See docs/d2-rune-economy.md.
	var book := _book()
	var word: Inscription = book.inscription_by_id("kindling")
	assert_eq(word.pattern.size(), 2, "test assumes a two-sigil word")

	var oversized := _vessel(word.slot, 3)
	for id in word.pattern:
		oversized.insert(book.sigil_by_id(str(id)))
	oversized.reappraise(book)
	assert_false(oversized.is_inscribed(), "a three-socket vessel must not form a two-sigil word")

	var exact := _fill(_vessel(word.slot, 2), book, word.pattern)
	assert_true(exact.is_inscribed(), "the correctly-sized vessel should still work")


func test_transmutation_follows_d2s_tightening_ratio() -> void:
	# Three-for-one through the low bands, two-for-one at the top. The tightening
	# is the point: the hardest steps are proportionally cheaper, so the ladder
	# stays reachable instead of receding. See docs/d2-rune-economy.md.
	assert_eq(InscriptionBook.transmute_cost(1), 3)
	assert_eq(InscriptionBook.transmute_cost(3), 3)
	assert_eq(InscriptionBook.transmute_cost(4), 2)
	assert_eq(InscriptionBook.transmute_cost(5), 2)


func test_the_transmutation_ladder_is_a_total_order() -> void:
	# Total, so no sigil sits off the ladder unreachable; strict, so a rung never
	# converts into itself or into something already passed.
	var book := _book()
	var order := book.transmute_order()
	assert_eq(order.size(), book.sigils.size(), "every sigil must sit on the ladder")

	var seen := {}
	for id in order:
		assert_false(seen.has(id), "'%s' appears twice on the ladder" % id)
		seen[str(id)] = true
		assert_not_null(book.sigil_by_id(str(id)), "'%s' is not a real sigil" % id)

	for i in order.size() - 1:
		var lower: Sigil = book.sigil_by_id(str(order[i]))
		var upper: Sigil = book.sigil_by_id(str(order[i + 1]))
		assert_true(
			lower.tier <= upper.tier,
			"the ladder must not descend a tier: '%s' then '%s'" % [lower.id, upper.id]
		)
		if lower.tier == upper.tier:
			# Commonest first within a tier, so the cheap end of the ladder is
			# also the end you are most likely to be handed by the drop table.
			var msg := "within tier %d, '%s' should not precede the commoner '%s'" % [
				lower.tier, lower.id, upper.id
			]
			assert_true(lower.weight >= upper.weight, msg)


func test_every_sigil_but_the_last_has_a_successor() -> void:
	var book := _book()
	var order := book.transmute_order()
	assert_gt(float(order.size()), 1.0, "test needs a ladder with more than one rung")

	for i in order.size() - 1:
		var up := book.transmute_target(str(order[i]))
		assert_not_null(up, "'%s' must convert into something" % order[i])
		if up == null:
			continue
		assert_eq(up.id, order[i + 1], "'%s' must convert one rung up" % order[i])

	var last: String = str(order[order.size() - 1])
	assert_eq(book.transmute_target(last), null, "'%s' tops the ladder" % last)


func test_grinding_upward_reaches_every_sigil() -> void:
	# The property the whole change exists to provide, and the one the old rule
	# failed: transmutation jumped to the commonest sigil of the next tier, so
	# tier 2 always produced `pyre` and `rime` and `storm` were unreachable by
	# grinding at any price. A recipe wanting one was pure drop luck forever.
	var book := _book()
	var order := book.transmute_order()
	if order.is_empty():
		fail("the ladder must not be empty")
		return
	var cheapest: String = str(order[0])

	var reached := {}
	var at := book.sigil_by_id(cheapest)
	assert_not_null(at, "the ladder must start at a real sigil")
	# Bounded so a ladder that ever cycles fails the test instead of hanging CI.
	var steps := 0
	while at != null and steps <= order.size():
		reached[at.id] = true
		at = book.transmute_target(at.id)
		steps += 1

	for s in book.sigils:
		assert_true(
			reached.has(s.id),
			"'%s' cannot be reached by grinding up from '%s'" % [s.id, cheapest]
		)


func test_sigils_still_contribute_without_an_inscription() -> void:
	# A combination that spells nothing should be weak, not worthless. Otherwise
	# socketing anything speculatively is strictly a mistake.
	var book := _book()
	var item := _fill(_vessel("weapon", 2), book, ["cinder", "cinder"])
	assert_false(item.is_inscribed())

	var stats := RunState.base_stats()
	var before := stats.expected_hit(StatBlock.new())
	item.apply_to(stats)
	assert_gt(
		stats.expected_hit(StatBlock.new()), before,
		"socketed sigils must apply their own modifiers regardless"
	)


func test_an_inscription_beats_the_same_sigils_loose() -> void:
	var book := _book()
	var word: Inscription = book.inscription_by_id("kindling")

	var plain := RunState.base_stats()
	var loose := _vessel("weapon", word.pattern.size())
	for id in word.pattern:
		loose.insert(book.sigil_by_id(str(id)))
	# Deliberately not reappraised, so only the sigils' own modifiers apply.
	loose.apply_to(plain)

	var worded := RunState.base_stats()
	_fill(_vessel("weapon", 2), book, word.pattern).apply_to(worded)

	var dummy := StatBlock.new()
	assert_gt(
		worded.expected_hit(dummy), plain.expected_hit(dummy),
		"completing the word must be worth more than the parts"
	)


func test_an_inscription_grants_its_tags() -> void:
	var book := _book()
	var word: Inscription = book.inscription_by_id("kindling")
	var item := _fill(_vessel(word.slot, 2), book, word.pattern)
	for t in word.grants_tags:
		assert_has(item.tags(), t)


func test_sockets_cannot_be_overfilled() -> void:
	var book := _book()
	var item := _vessel("weapon", 1)
	assert_true(item.insert(book.sigils[0]))
	assert_false(item.insert(book.sigils[1]), "a one-socket vessel must reject a second sigil")
	assert_eq(item.socketed.size(), 1)


func test_only_plain_items_roll_sockets() -> void:
	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var rng := Rng.new(7)
	var seen_socketed_normal := false
	for i in 1500:
		var item := gen.roll_item(20, rng, 2.0)
		if item.rarity != Item.Rarity.NORMAL:
			assert_eq(item.sockets, 0, "%s item should have no sockets" % Item.RARITY_NAMES[item.rarity])
		elif item.sockets > 0:
			seen_socketed_normal = true
	assert_true(seen_socketed_normal, "plain items should sometimes roll sockets")


func test_three_socket_vessels_are_gated_on_depth() -> void:
	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var rng := Rng.new(11)
	for i in 1200:
		assert_lt(
			float(gen.roll_sockets(rng, 1)), 3.0,
			"three sockets must not be reachable below ilvl %d" % ItemGenerator.THREE_SOCKET_ILVL
		)


func test_depth_suppresses_high_sigils_without_forbidding_them() -> void:
	# Shallow floors should mostly hand out low sigils, but "mostly" is the point.
	# This was a hard gate, and combined with a difficulty curve that ends most
	# runs on floor five it made two inscriptions literally unobtainable.
	var book := _book()
	var rng := Rng.new(13)
	var high := 0
	var n := 3000
	for i in n:
		if book.roll_sigil(rng, 2).tier >= 3:
			high += 1
	assert_lt(float(high) / float(n), 0.06, "shallow floors should rarely give high sigils")


func test_every_inscription_component_can_drop_at_a_reachable_depth() -> void:
	# The guard for the bug the acquisition simulator found: content that
	# referenced only real sigils, passed every other validation, and could never
	# be completed because a component required a depth players do not reach.
	# Nobody finished it in four hundred simulated runs.
	#
	# Empirical rather than analytic on purpose — it exercises the real drop
	# function, so it keeps working however the weighting is next rewritten.
	var reachable_ilvl := 10
	var book := _book()

	var required: Array = []
	for i in book.inscriptions:
		for p in i.pattern:
			if not required.has(p):
				required.append(p)

	var seen := {}
	var rng := Rng.new(99)
	for i in 60000:
		seen[book.roll_sigil(rng, reachable_ilvl).id] = true

	for id in required:
		assert_true(
			seen.has(id),
			"'%s' is required by an inscription but never drops at ilvl %d" % [id, reachable_ilvl]
		)


func test_rare_sigils_are_actually_rare() -> void:
	var book := _book()
	var rng := Rng.new(2718)
	var high := 0
	var n := 4000
	for i in n:
		if book.roll_sigil(rng, 99).tier >= 4:
			high += 1
	var rate := float(high) / float(n)
	assert_between(rate, 0.001, 0.08, "top-tier sigils should be a chase, not a routine drop")


## Every inscription must have somewhere it can be built. A pattern longer than
## the deepest base's socket ceiling is not a hard recipe, it is an impossible
## one — and impossible is invisible: it validates, it displays, it simply never
## happens. This project has shipped that bug twice (a hard tier gate that made
## two words unobtainable, then a socket ceiling that made every three-sigil
## word unobtainable), and both times a simulator found it long after a one-line
## assertion would have.
func test_every_inscription_fits_a_vessel_that_can_exist() -> void:
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var deepest := Item.max_sockets(Item.Tier.ELITE)
	for i in book.inscriptions:
		assert_lt(
			float(i.pattern.size()), float(deepest + 1),
			"'%s' needs %d sockets; the best base in the game has %d"
				% [i.display_name, i.pattern.size(), deepest]
		)


## And the vessel it needs has to be reachable before the run ends. A word whose
## socket count only exists in Hell is fine; one that needs a tier no difficulty
## pass grants is not.
func test_every_socket_count_is_granted_by_some_difficulty() -> void:
	for tier in [Item.Tier.PLAIN, Item.Tier.EXCEPTIONAL, Item.Tier.ELITE]:
		assert_lt(
			float(Item.min_difficulty(tier)), float(Progression.DIFFICULTIES + 1),
			"%s bases require difficulty %d, past the last pass"
				% [Item.TIER_NAMES[tier], Item.min_difficulty(tier)]
		)
