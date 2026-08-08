extends TestCase

## The damage pipeline. These tests pin the additive/multiplicative split that
## the whole gear-vs-boons design rests on — if they ever start agreeing with
## each other, the design has quietly collapsed.


## A dummy with a fixed 100-damage physical hit and no crits, so every number
## below is exact rather than sampled.
func _attacker() -> StatBlock:
	var s := StatBlock.new()
	s.weapon_min = 100.0
	s.weapon_max = 100.0
	s.weapon_split = {Damage.Type.PHYSICAL: 1.0}
	s.crit_chance = 0.0
	s.crit_mult = 1.5
	return s


func _dummy() -> StatBlock:
	var s := StatBlock.new()
	s.armor = 0.0
	return s


func test_unmodified_hit_is_weapon_damage() -> void:
	var r := Damage.resolve(_attacker(), _dummy(), Rng.new(1))
	assert_almost_eq(r.total, 100.0, 0.01)
	assert_false(r.was_crit)


func test_increased_modifiers_are_additive() -> void:
	var a := _attacker()
	a.apply("increased.physical", 0.5)
	a.apply("increased.physical", 0.5)
	# 100 * (1 + 0.5 + 0.5) = 200, NOT 225.
	var r := Damage.resolve(a, _dummy(), Rng.new(1))
	assert_almost_eq(r.total, 200.0, 0.01, "increased% must sum into one multiplier")


func test_more_modifiers_are_multiplicative() -> void:
	var a := _attacker()
	a.apply("more", 0.5)
	a.apply("more", 0.5)
	# 100 * 1.5 * 1.5 = 225.
	var r := Damage.resolve(a, _dummy(), Rng.new(1))
	assert_almost_eq(r.total, 225.0, 0.01, "each more% must be its own multiplier")


func test_the_two_buckets_do_not_collapse_into_each_other() -> void:
	var additive := _attacker()
	additive.apply("increased.physical", 0.5)
	additive.apply("increased.physical", 0.5)

	var multiplicative := _attacker()
	multiplicative.apply("more", 0.5)
	multiplicative.apply("more", 0.5)

	var add_hit := Damage.resolve(additive, _dummy(), Rng.new(1)).total
	var mul_hit := Damage.resolve(multiplicative, _dummy(), Rng.new(1)).total
	assert_gt(mul_hit, add_hit, "the same headline % must be stronger as more% than as increased%")


func test_flat_damage_is_amplified_by_increased() -> void:
	var a := _attacker()
	a.apply("flat.physical", 50.0)
	a.apply("increased.physical", 1.0)
	# (100 + 50) * 2 = 300.
	assert_almost_eq(Damage.resolve(a, _dummy(), Rng.new(1)).total, 300.0, 0.01)


func test_flat_of_another_type_is_not_scaled_by_the_wrong_increased() -> void:
	var a := _attacker()
	a.apply("flat.fire", 100.0)
	a.apply("increased.physical", 1.0)
	# physical 100*2 = 200, fire 100*1 = 100 -> 300.
	assert_almost_eq(Damage.resolve(a, _dummy(), Rng.new(1)).total, 300.0, 0.01)


func test_resistance_reduces_the_matching_type_only() -> void:
	var a := _attacker()
	a.apply("flat.fire", 100.0)
	var d := _dummy()
	d.apply("resist.fire", 0.5)
	# physical 100 + fire 100*0.5 = 150.
	assert_almost_eq(Damage.resolve(a, d, Rng.new(1)).total, 150.0, 0.01)


func test_resistance_is_capped() -> void:
	var d := _dummy()
	d.apply("resist.physical", 0.99)
	# Clamped to RESIST_CAP (0.75) -> 100 * 0.25 = 25.
	assert_almost_eq(Damage.resolve(_attacker(), d, Rng.new(1)).total, 25.0, 0.01)
	assert_almost_eq(Damage.RESIST_CAP, 0.75, 0.0001)


func test_negative_resistance_amplifies_but_has_a_floor() -> void:
	var d := _dummy()
	d.apply("resist.physical", -1.0)
	assert_almost_eq(Damage.resolve(_attacker(), d, Rng.new(1)).total, 200.0, 0.01)

	var way_over := _dummy()
	way_over.apply("resist.physical", -9.0)
	assert_almost_eq(
		Damage.resolve(_attacker(), way_over, Rng.new(1)).total, 200.0, 0.01,
		"resistance below the floor must stop scaling"
	)


func test_armor_subtracts_after_mitigation() -> void:
	var d := _dummy()
	d.apply("armor", 30.0)
	assert_almost_eq(Damage.resolve(_attacker(), d, Rng.new(1)).total, 70.0, 0.01)


func test_armor_can_never_fully_negate_a_hit() -> void:
	var d := _dummy()
	d.apply("armor", 100000.0)
	assert_almost_eq(Damage.resolve(_attacker(), d, Rng.new(1)).total, Damage.MIN_HIT, 0.01)


func test_guaranteed_crit_applies_the_multiplier() -> void:
	var a := _attacker()
	a.crit_chance = 1.0
	a.crit_mult = 2.0
	var r := Damage.resolve(a, _dummy(), Rng.new(1))
	assert_true(r.was_crit)
	assert_almost_eq(r.total, 200.0, 0.01)


func test_crit_is_rolled_once_for_the_whole_hit() -> void:
	# With two damage types and a 50% crit chance, a per-type roll would let
	# half a hit crit. Every resolved hit must be all-or-nothing.
	var a := _attacker()
	a.apply("flat.fire", 100.0)
	a.crit_chance = 0.5
	a.crit_mult = 2.0
	var rng := Rng.new(4)
	for i in 200:
		var r := Damage.resolve(a, _dummy(), rng)
		var expected := 400.0 if r.was_crit else 200.0
		assert_almost_eq(r.total, expected, 0.01, "hit %d crit only partially" % i)


func test_resolution_is_deterministic_for_a_seed() -> void:
	var a := _attacker()
	a.weapon_min = 10.0
	a.weapon_max = 200.0
	a.crit_chance = 0.35
	var first: Array[float] = []
	var rng_a := Rng.new(2024)
	for i in 30:
		first.append(Damage.resolve(a, _dummy(), rng_a).total)
	var rng_b := Rng.new(2024)
	for i in 30:
		assert_almost_eq(Damage.resolve(a, _dummy(), rng_b).total, first[i], 0.0, "hit %d" % i)


func test_expected_hit_matches_the_sampled_average() -> void:
	# The balance simulator trusts expected_hit instead of sampling. If the two
	# ever drift apart, every balance conclusion drawn from it becomes wrong.
	var a := _attacker()
	a.weapon_min = 20.0
	a.weapon_max = 180.0
	a.apply("flat.fire", 30.0)
	a.apply("increased.physical", 0.4)
	a.apply("more", 0.25)
	a.crit_chance = 0.3
	a.crit_mult = 2.0

	var d := _dummy()
	d.apply("resist.fire", 0.3)
	d.apply("armor", 5.0)

	var rng := Rng.new(31337)
	var total := 0.0
	var n := 20000
	for i in n:
		total += Damage.resolve(a, d, rng).total
	var sampled := total / float(n)
	var analytic := a.expected_hit(d)
	assert_between(
		sampled / analytic, 0.97, 1.03,
		"expected_hit (%.2f) disagrees with sampling (%.2f)" % [analytic, sampled]
	)
