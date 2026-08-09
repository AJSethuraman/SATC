extends TestCase

## The bank, and the one rule the whole persistence design rests on: you may keep
## a finished item, but you have to have assembled it inside a single run.

const SIGILS_PATH := "res://data/sigils.json"


func _vessel(sockets: int, slot: String = "weapon") -> Item:
	var item := Item.new()
	item.slot = slot
	item.base_name = "Plain Rod"
	item.sockets = sockets
	return item


## A finished inscription — kindling, ash then cinder in a two-socket weapon.
func _inscribed(book: InscriptionBook) -> Item:
	var word: Inscription = book.inscription_by_id("kindling")
	var item := _vessel(word.socket_count(), word.slot)
	for id in word.pattern:
		item.insert(book.sigil_by_id(str(id)))
	item.reappraise(book)
	return item


func _fresh() -> Reliquary:
	var r := Reliquary.new()
	r.begin_run()
	return r


# --- the load-bearing rule ---------------------------------------------


func test_a_completed_inscription_can_be_banked() -> void:
	# This is the flip, and it used to assert the exact opposite. The refusal
	# existed to stop the game collapsing into "farm one good weapon, then every
	# subsequent run opens easy" — but that job now belongs to the difficulty
	# passes rather than to the bank: RunState.DIFFICULTY_HEALTH_STEP outscales a
	# Normal-made word by Nightmare, so a banked item is a leg up into the next
	# run's early game, not a permanent win. The failure mode is guarded in
	# test_run_state.gd's scaling assertions now, not here.
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var item := _inscribed(book)
	assert_true(item.is_inscribed(), "test setup should have produced an inscription")

	var bank := _fresh()
	assert_true(bank.can_deposit(item), bank.rejection_reason(item))
	assert_true(bank.deposit(item))
	assert_eq(bank.items().size(), 1)

	var entry: Dictionary = bank.items()[0]
	assert_eq(str(entry.get("inscription", "")), "kindling")
	# Socket order, not a bag: the same sigils in the other order spell nothing.
	assert_eq(entry.get("sigils"), ["ash", "cinder"])


func test_a_part_assembled_vessel_cannot_be_banked() -> void:
	# What the flip made *stricter*, and the thing the old "no completed items"
	# rule was protecting all along. You may keep the finished word or you may
	# keep the sigils loose; you may not keep the work in progress, because
	# banking a vessel one sigil short is assembling across runs — precisely the
	# work that has to happen inside a single one.
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var word: Inscription = book.inscription_by_id("kindling")
	var item := _vessel(word.socket_count(), word.slot)
	item.insert(book.sigil_by_id(str(word.pattern[0])))
	item.reappraise(book)
	assert_false(item.is_inscribed(), "one sigil short must not be an inscription")

	var bank := _fresh()
	assert_false(bank.can_deposit(item))
	assert_false(bank.deposit(item))
	assert_eq(bank.contents.size(), 0)
	assert_true(bank.rejection_reason(item).contains("finish"))
	assert_eq(bank.deposits_remaining(), 1, "a refused deposit must not be spent")


func test_a_banked_item_is_not_a_pile_of_loose_components() -> void:
	# Its sigils and its vessel are spoken for. Otherwise banking one runeword
	# would also bank the parts of a second, which is the part-assembly loophole
	# arriving by the back door.
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var bank := _fresh()
	assert_true(bank.deposit(_inscribed(book)))
	assert_eq(bank.sigil_ids().size(), 0)
	assert_eq(bank.vessels().size(), 0)
	assert_eq(bank.best_sockets("weapon"), 0)
	assert_eq(bank.deposits_remaining(), 0, "a finished item costs a deposit like anything else")


func test_an_affixed_item_cannot_be_banked() -> void:
	# Not a component and not something you assembled. The loot that is meant to
	# be worth banking unassembled — uniques and sets — does not exist yet, so
	# this stays refused until it does.
	var item := _vessel(2)
	var rolled := Affix.Rolled.new()
	rolled.id = "test"
	rolled.mods = {"max_health": 10.0}
	item.affixes.append(rolled)
	assert_false(_fresh().can_deposit(item), "only vessels and finished words are bankable")


func test_an_empty_socketed_vessel_is_bankable() -> void:
	var bank := _fresh()
	var item := _vessel(3)
	assert_true(bank.can_deposit(item), bank.rejection_reason(item))
	assert_true(bank.deposit_vessel(item))
	assert_eq(bank.contents.size(), 1)
	assert_eq(bank.best_sockets("weapon"), 3)


func test_a_vessel_without_sockets_is_not_worth_banking() -> void:
	assert_false(_fresh().can_deposit(_vessel(0)))


# --- deposits are earned by depth ---------------------------------------


func test_a_run_starts_with_a_single_deposit() -> void:
	var bank := _fresh()
	assert_true(bank.deposit_vessel(_vessel(2)))
	assert_eq(bank.deposits_remaining(), 0)
	assert_false(bank.deposit_vessel(_vessel(3)), "an unearned deposit must be refused")
	assert_eq(bank.contents.size(), 1)


## Clearing an act earns another. This is the fix for a chase that had a median
## of forty-nine runs and a 62% never-finished rate: income was capped at one
## component per attempt however well the attempt went, which is a queue rather
## than a chase, and no drop-rate tuning fixes a cap.
func test_clearing_an_act_earns_another_deposit() -> void:
	var bank := _fresh()
	assert_true(bank.deposit_vessel(_vessel(2)))
	assert_eq(bank.deposits_remaining(), 0)

	bank.earn_deposit()
	assert_eq(bank.deposits_remaining(), 1)
	assert_true(bank.deposit_vessel(_vessel(3)), "an earned deposit must be spendable")
	assert_eq(bank.contents.size(), 2)


## A full clear of every act should bank meaningfully more than a run that dies
## early — that is the entire reason for tying the allowance to progress.
func test_a_deep_run_banks_more_than_a_shallow_one() -> void:
	var shallow := _fresh()
	var deep := _fresh()
	for _act in Progression.ACTS:
		deep.earn_deposit()
	assert_gt(
		float(deep.deposits_remaining()), float(shallow.deposits_remaining()) + 1.0,
		"clearing four acts is worth no more than dying in the first"
	)


## Earning is not banking. An allowance that is never spent carries nothing into
## the next run, so a deep run still has to choose what to keep.
func test_an_unspent_allowance_does_not_carry_over() -> void:
	var bank := _fresh()
	bank.earn_deposit()
	bank.earn_deposit()
	bank.begin_run()
	assert_eq(bank.deposits_remaining(), Reliquary.DEPOSITS_AT_START)


func test_the_allowance_resets_next_run() -> void:
	var bank := _fresh()
	bank.deposit_vessel(_vessel(2))
	bank.begin_run()
	assert_eq(bank.deposits_remaining(), 1)
	assert_true(bank.deposit_vessel(_vessel(3)))
	assert_eq(bank.contents.size(), 2)


func test_sigils_cost_a_deposit_too() -> void:
	# Sigils and vessels competing for the same single slot is the whole choice.
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var bank := _fresh()
	assert_true(bank.deposit_sigil(book.sigils[0]))
	assert_false(bank.deposit_vessel(_vessel(3)), "the vessel should have lost the slot")
	assert_eq(bank.sigil_ids().size(), 1)


func test_capacity_is_enforced() -> void:
	var bank := Reliquary.new()
	for i in bank.capacity:
		bank.begin_run()
		assert_true(bank.deposit_vessel(_vessel(2)), "deposit %d should fit" % i)
	bank.begin_run()
	assert_true(bank.is_full())
	assert_false(bank.deposit_vessel(_vessel(2)), "a full reliquary must refuse")
	assert_true(bank.rejection_reason(_vessel(2)).contains("full"))


func test_discarding_frees_space() -> void:
	var bank := Reliquary.new()
	for i in bank.capacity:
		bank.begin_run()
		bank.deposit_vessel(_vessel(2))
	bank.discard_at(0)
	bank.begin_run()
	assert_true(bank.deposit_vessel(_vessel(3)))


# --- persistence --------------------------------------------------------


func test_it_survives_a_save_and_load() -> void:
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var bank := _fresh()
	bank.deposit_vessel(_vessel(3))
	bank.begin_run()
	bank.deposit_sigil(book.sigil_by_id("cinder"))

	var path := "user://test_reliquary.json"
	assert_eq(bank.save_to(path), OK)

	var loaded := Reliquary.load_from(path)
	assert_eq(loaded.contents.size(), 2)
	assert_has(loaded.sigil_ids(), "cinder")
	assert_eq(loaded.best_sockets("weapon"), 3)

	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))


## A finished item is the only thing in the bank with real state to serialise,
## which is the price of the flip: the old rule stored nothing but ids and counts
## because nothing storable had ever been assembled.
func test_a_banked_item_comes_back_as_the_item_it_was() -> void:
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var bank := _fresh()
	assert_true(bank.deposit(_inscribed(book)))

	var path := "user://test_reliquary_item.json"
	assert_eq(bank.save_to(path), OK)
	var loaded := Reliquary.load_from(path)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))

	assert_eq(loaded.items().size(), 1)
	var entry: Dictionary = loaded.items()[0]
	var restored := Reliquary.item_from_entry(entry, book)
	assert_not_null(restored, "a banked item must rebuild")
	if restored == null:
		return
	assert_true(restored.is_inscribed(), "and rebuild with its inscription intact")
	assert_eq(restored.inscription.id, "kindling")
	assert_eq(restored.socketed_ids(), ["ash", "cinder"])
	assert_eq(restored.slot, "weapon")


## Content ids move underneath saves. A sequence the current book no longer
## recognises has to come back as the vessel it really is, rather than as a word
## the game has no rules for any more.
func test_a_rebuilt_item_is_re_judged_by_the_current_book() -> void:
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var entry := {
		"kind": "item",
		"base": "Plain Rod",
		"slot": "weapon",
		"sockets": 2,
		"sigils": ["ash", "no_such_sigil"],
		"inscription": "kindling",
	}
	var restored := Reliquary.item_from_entry(entry, book)
	assert_not_null(restored)
	if restored == null:
		return
	assert_false(restored.is_inscribed(), "the stored inscription id must not be taken on trust")


func test_a_missing_save_is_an_empty_reliquary_not_an_error() -> void:
	# First launch is the normal case, not a failure.
	var loaded := Reliquary.load_from("user://definitely_not_written.json")
	assert_eq(loaded.contents.size(), 0)
	assert_eq(loaded.capacity, Reliquary.DEFAULT_CAPACITY)


func test_a_loaded_reliquary_still_owes_a_begin_run() -> void:
	# Loading must not hand back a free deposit for the run already in progress.
	var loaded := Reliquary.from_dict({"capacity": 8, "contents": []})
	loaded.begin_run()
	assert_eq(loaded.deposits_remaining(), 1)


## Uniques and sets are bankable, and that is the revisit the rejection rule
## asked for in writing: "no affixes" was a stand-in for "not a roll", chosen
## when named items did not exist. Now they do, and a run that never lined up
## its sigils still has something to keep.
func test_a_unique_can_be_banked() -> void:
	var bank := Reliquary.new()
	var drop := _named_drop(_any_unique())
	assert_eq(bank.rejection_reason(drop), "", "a unique was refused")
	assert_true(bank.deposit(drop))
	assert_eq(bank.named_items().size(), 1)


## And a rare still cannot, for a reason the design depends on: banking rolls
## turns the one hard choice a run makes into a ratchet.
func test_a_rare_still_cannot_be_banked() -> void:
	var bank := Reliquary.new()
	var rare := Item.new()
	rare.rarity = Item.Rarity.RARE
	var line := Affix.Rolled.new()
	line.id = "test_line"
	line.display_name = "+10 life"
	line.mods = {"max_health": 10.0}
	rare.affixes.append(line)
	assert_ne(bank.rejection_reason(rare), "", "a rolled rare was accepted into the bank")


## A banked unique comes back as itself, re-stamped from the current table
## rather than from stored numbers — so retuning content retunes the bank.
func test_a_banked_unique_survives_a_round_trip() -> void:
	var bank := Reliquary.new()
	var piece := _any_unique()
	assert_true(bank.deposit(_named_drop(piece)))

	var restored := Reliquary.item_from_entry(bank.named_items()[0], null)
	assert_ne(restored, null, "a banked unique did not come back")
	assert_eq(restored.unique_name, piece.display_name)
	assert_eq(restored.rarity, Item.Rarity.UNIQUE)
	assert_eq(restored.affixes.size(), piece.mods.size())


## A piece cut from the content table vanishes rather than persisting as a ghost
## with stats nothing in the game can explain.
func test_a_banked_piece_that_content_removed_comes_back_as_nothing() -> void:
	assert_eq(
		Reliquary.item_from_entry(
			{"kind": "named", "base": "Falchion", "slot": "weapon", "piece": "No Such Thing"}, null
		),
		null
	)


func _any_unique() -> UniquePool.Piece:
	for entry in UniquePool.shared().pieces:
		var piece := entry as UniquePool.Piece
		if piece != null and not piece.is_set_piece():
			return piece
	fail("no uniques in the table")
	return null


func _named_drop(entry: Variant) -> Item:
	var piece := entry as UniquePool.Piece
	var item := Item.new()
	item.base_name = "Test Base"
	item.ilvl = 20
	piece.stamp(item)
	return item
