extends TestCase

## The bank, and the one rule the whole persistence design rests on.

const SIGILS_PATH := "res://data/sigils.json"


func _vessel(sockets: int, slot: String = "weapon") -> Item:
	var item := Item.new()
	item.slot = slot
	item.base_name = "Plain Rod"
	item.sockets = sockets
	return item


func _fresh() -> Reliquary:
	var r := Reliquary.new()
	r.begin_run()
	return r


# --- the load-bearing rule ---------------------------------------------


func test_a_completed_inscription_can_never_be_banked() -> void:
	# If this ever passes, the design has collapsed into "keep your best gear",
	# which the balance simulator already showed trivialises every later run.
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var word: Inscription = book.inscription_by_id("kindling")
	var item := _vessel(2)
	for id in word.pattern:
		item.insert(book.sigil_by_id(str(id)))
	item.reappraise(book)
	assert_true(item.is_inscribed(), "test setup should have produced an inscription")

	var bank := _fresh()
	assert_false(bank.can_deposit(item), "a completed inscription must be unbankable")
	assert_false(bank.deposit_vessel(item))
	assert_eq(bank.contents.size(), 0)


func test_a_vessel_holding_any_sigil_cannot_be_banked() -> void:
	# Even one sigil short of a word. Otherwise you could bank most of the work
	# and finish it trivially next run.
	var book := InscriptionBook.from_json(SIGILS_PATH)
	var item := _vessel(3)
	item.insert(book.sigils[0])

	var bank := _fresh()
	assert_false(bank.can_deposit(item))
	assert_true(bank.rejection_reason(item).contains("already holds"))


func test_an_affixed_item_cannot_be_banked() -> void:
	var item := _vessel(2)
	var rolled := Affix.Rolled.new()
	rolled.id = "test"
	rolled.mods = {"max_health": 10.0}
	item.affixes.append(rolled)
	assert_false(_fresh().can_deposit(item), "only plain vessels are bankable")


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
