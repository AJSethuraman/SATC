extends TestCase

## Spells, mana and cast speed.

const SPELLS_PATH := "res://data/spells.json"


func _spells() -> Dictionary:
	var out := {}
	for s in Spell.from_json(SPELLS_PATH):
		out[s.id] = s
	return out


func test_the_table_loads_both_spells() -> void:
	var s := _spells()
	assert_true(s.has("bolt"), "a basic attack is required")
	assert_true(s.has("nova"), "a heavy skill is required")


func test_every_spell_costs_mana() -> void:
	# A free spell makes the resource decorative and removes the spend-and-coast
	# rhythm that separates an ARPG from a stream of damage.
	for id in _spells():
		assert_gt(_spells()[id].cost, 0.0, "'%s' must cost mana" % id)


func test_the_heavy_spell_costs_more_and_hits_harder() -> void:
	var s := _spells()
	var bolt: Spell = s["bolt"]
	var nova: Spell = s["nova"]
	assert_gt(nova.cost, bolt.cost, "the heavy spell must cost more")
	assert_gt(nova.damage_scale, bolt.damage_scale, "and hit harder")
	assert_gt(nova.cooldown, 0.0, "and have a floor cast speed cannot erase")


func test_cast_speed_shortens_the_gap() -> void:
	var bolt: Spell = _spells()["bolt"]
	var slow := RunState.base_stats()
	var fast := RunState.base_stats()
	fast.apply("cast_speed", 1.0)
	assert_lt(bolt.cast_time(fast), bolt.cast_time(slow), "faster casting must fire sooner")
	assert_almost_eq(bolt.cast_time(fast), bolt.cast_time(slow) * 0.5, 0.001)


func test_cast_time_can_never_reach_zero() -> void:
	# Otherwise a cast-speed stacking build becomes a continuous beam.
	var bolt: Spell = _spells()["bolt"]
	var absurd := RunState.base_stats()
	absurd.apply("cast_speed", 500.0)
	assert_gt(bolt.cast_time(absurd), 0.0)
	assert_almost_eq(bolt.cast_time(absurd), 0.05, 0.001)


func test_affordability_gates_on_the_pool() -> void:
	var nova: Spell = _spells()["nova"]
	assert_false(nova.can_afford(nova.cost - 0.01))
	assert_true(nova.can_afford(nova.cost))


func test_a_fresh_run_can_afford_its_own_spells() -> void:
	# A class that starts unable to cast is not a class.
	var stats := RunState.base_stats()
	for id in _spells():
		assert_true(
			_spells()[id].can_afford(stats.max_mana),
			"'%s' must be castable from a full starting pool" % id
		)


func test_mana_and_cast_speed_are_part_of_the_grammar() -> void:
	for key in ["max_mana", "mana_regen", "cast_speed"]:
		assert_true(StatBlock.is_valid_key(key), "'%s' should be a valid modifier key" % key)


func test_inscriptions_expose_their_behaviour_to_the_run() -> void:
	# The `behaviour` vocabulary written into the sigil table ahead of time has to
	# actually reach the scene layer, or the loot has no mechanical consequence.
	var book := InscriptionBook.from_json("res://data/sigils.json")
	var word: Inscription = book.inscription_by_id("arcwork")
	assert_not_null(word)
	assert_ne(word.behaviour, "", "this inscription should name a behaviour")

	var item := Item.new()
	item.slot = word.slot
	item.sockets = word.pattern.size()
	for id in word.pattern:
		item.insert(book.sigil_by_id(str(id)))
	item.reappraise(book)
	assert_true(item.is_inscribed())

	var run := RunState.start(5)
	assert_true(run.active_behaviours().is_empty(), "a bare run has no behaviours")
	run.equip(item)
	assert_has(run.active_behaviours(), word.behaviour)
