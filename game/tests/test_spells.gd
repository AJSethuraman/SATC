extends TestCase

## Spells, mana and cast speed.

const SPELLS_PATH := "res://data/spells.json"


func _spells() -> Dictionary:
	var out := {}
	for s in Spell.from_json(SPELLS_PATH):
		out[s.id] = s
	return out


## Every school must be a complete kit. A school missing its bolt or its nova
## would be dealt to a run by _attune() and leave that run with a null spell and
## a button that does nothing.
func test_every_school_has_a_bolt_and_a_nova() -> void:
	var all := Spell.from_json(SPELLS_PATH)
	for school in ["fire", "cold", "lightning"]:
		var kit := Spell.of_school(all, school)
		assert_eq(kit.size(), 2, "school '%s' does not have exactly two spells" % school)
		var shapes: Array = []
		for entry in kit:
			var spell := entry as Spell
			shapes.append(spell.shape)
			assert_eq(
				spell.element, RunState.element_of(school),
				"'%s' is in the %s school but deals another element" % [spell.id, school]
			)
		assert_true(shapes.has(Spell.Shape.PROJECTILE), "%s has no basic attack" % school)
		assert_true(shapes.has(Spell.Shape.NOVA), "%s has no heavy skill" % school)


## Lightning is the gamble and the other two are not. If every school rolled the
## same spread the three would differ only by a colour.
func test_only_lightning_rolls_wild() -> void:
	var all := Spell.from_json(SPELLS_PATH)
	for entry in all:
		var spell := entry as Spell
		var spread := spell.roll_high - spell.roll_low
		if spell.school == "lightning":
			assert_gt(spread, 0.8, "'%s' is lightning but rolls flat" % spell.id)
		else:
			assert_almost_eq(spread, 0.0, 0.0001, "'%s' should not roll wild" % spell.id)


## Variance must not smuggle in extra damage: a wider spread makes a school
## swingier, not stronger. Averaged over many rolls it has to land on 1.0.
func test_variance_averages_out() -> void:
	var all := Spell.from_json(SPELLS_PATH)
	var rng := Rng.new(99)
	for entry in all:
		var spell := entry as Spell
		var total := 0.0
		for _i in 4000:
			total += spell.roll_variance(rng)
		assert_almost_eq(total / 4000.0, 1.0, 0.05, "'%s' variance is not centred" % spell.id)


func test_every_spell_costs_mana() -> void:
	# A free spell makes the resource decorative and removes the spend-and-coast
	# rhythm that separates an ARPG from a stream of damage.
	for id in _spells():
		assert_gt(_spells()[id].cost, 0.0, "'%s' must cost mana" % id)


func test_the_heavy_spell_costs_more_and_hits_harder() -> void:
	var s := _spells()
	var bolt: Spell = s["bolt_fire"]
	var nova: Spell = s["nova_fire"]
	assert_gt(nova.cost, bolt.cost, "the heavy spell must cost more")
	assert_gt(nova.damage_scale, bolt.damage_scale, "and hit harder")
	assert_gt(nova.cooldown, 0.0, "and have a floor cast speed cannot erase")


func test_cast_speed_shortens_the_gap() -> void:
	var bolt: Spell = _spells()["bolt_fire"]
	var slow := RunState.base_stats()
	var fast := RunState.base_stats()
	fast.apply("cast_speed", 1.0)
	assert_lt(bolt.cast_time(fast), bolt.cast_time(slow), "faster casting must fire sooner")
	assert_almost_eq(bolt.cast_time(fast), bolt.cast_time(slow) * 0.5, 0.001)


func test_cast_time_can_never_reach_zero() -> void:
	# Otherwise a cast-speed stacking build becomes a continuous beam.
	var bolt: Spell = _spells()["bolt_fire"]
	var absurd := RunState.base_stats()
	absurd.apply("cast_speed", 500.0)
	assert_gt(bolt.cast_time(absurd), 0.0)
	assert_almost_eq(bolt.cast_time(absurd), 0.05, 0.001)


func test_affordability_gates_on_the_pool() -> void:
	var nova: Spell = _spells()["nova_fire"]
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
