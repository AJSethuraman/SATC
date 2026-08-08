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
	var item := _fill(_vessel("trinket", 2), book, word.pattern)
	assert_false(item.is_inscribed(), "a weapon inscription must not form in a trinket")


func test_a_partial_sequence_forms_nothing() -> void:
	var book := _book()
	var word: Inscription = book.inscription_by_id("conflagrant")
	var item := _fill(_vessel(word.slot, 3), book, [word.pattern[0]])
	assert_false(item.is_inscribed(), "one sigil of three must not complete the word")


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
	var loose := _vessel("weapon", 2)
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


func test_sigil_drops_are_gated_on_depth() -> void:
	var book := _book()
	var rng := Rng.new(13)
	for i in 800:
		assert_lt(
			float(book.roll_sigil(rng, 1).tier), 3.0,
			"a shallow floor should not hand out high-tier sigils"
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
