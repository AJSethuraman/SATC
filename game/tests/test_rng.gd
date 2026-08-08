extends TestCase

## The determinism guarantees everything else in the suite leans on.


func test_same_seed_same_sequence() -> void:
	var a := Rng.new(12345)
	var b := Rng.new(12345)
	for i in 20:
		assert_almost_eq(a.randf(), b.randf(), 0.0, "draw %d diverged" % i)


func test_different_seeds_diverge() -> void:
	var a := Rng.new(1)
	var b := Rng.new(2)
	var same := 0
	for i in 20:
		if is_equal_approx(a.randf(), b.randf()):
			same += 1
	assert_lt(float(same), 3.0, "seeds 1 and 2 produced near-identical streams")


func test_derive_is_deterministic() -> void:
	var parent_a := Rng.new(777)
	var parent_b := Rng.new(777)
	assert_eq(parent_a.derive(5).seed_value, parent_b.derive(5).seed_value)


func test_derived_streams_are_independent() -> void:
	var parent := Rng.new(999)
	var loot := parent.derive(1)
	var boons := parent.derive(2)
	assert_ne(loot.seed_value, boons.seed_value, "salts must produce distinct streams")

	# Draining one stream must not shift the other — this is the property that
	# stops a combat change from re-rolling every item in the regression tests.
	var boons_ref := Rng.new(999).derive(2)
	for i in 50:
		loot.randf()
	for i in 10:
		assert_almost_eq(boons.randf(), boons_ref.randf(), 0.0, "stream %d shifted" % i)


func test_mix_stays_positive() -> void:
	# A negative seed is not portable across platforms, so the mask in Rng.mix
	# is load-bearing rather than cosmetic.
	for seed_v in [0, 1, -1, 2147483647, -2147483648]:
		for salt in [0, 1, 7, 999999]:
			assert_true(Rng.mix(seed_v, salt) >= 0, "mix(%d,%d) went negative" % [seed_v, salt])


func test_mix_spreads_nearby_inputs() -> void:
	# Sequential run seeds must not produce correlated streams, or the balance
	# simulator would be sampling the same run over and over.
	var seen: Array = []
	for i in 200:
		var h := Rng.mix(i, 1)
		assert_false(seen.has(h), "mix collided on seed %d" % i)
		seen.append(h)


func test_weighted_pick_respects_weights() -> void:
	var rng := Rng.new(42)
	var counts := {"a": 0, "b": 0}
	for i in 4000:
		var picked: Variant = rng.weighted_pick(["a", "b"], [9.0, 1.0])
		counts[picked] += 1
	# Expect ~90/10. Generous bounds so this never flakes.
	assert_between(float(counts["a"]) / 4000.0, 0.86, 0.94, "weighting is off")


func test_weighted_pick_never_selects_zero_weight() -> void:
	var rng := Rng.new(7)
	for i in 500:
		assert_eq(rng.weighted_pick(["yes", "no"], [1.0, 0.0]), "yes")


func test_weighted_pick_handles_empty_and_zero_total() -> void:
	var rng := Rng.new(3)
	assert_eq(rng.weighted_pick([], []), null)
	assert_eq(rng.weighted_pick(["a"], [0.0]), null)


func test_weighted_sample_is_distinct_and_bounded() -> void:
	var rng := Rng.new(11)
	var got := rng.weighted_sample(["a", "b", "c"], [1.0, 1.0, 1.0], 3)
	assert_eq(got.size(), 3)
	assert_eq(got.size(), _unique(got).size(), "sample repeated an item")

	# Asking for more than exists yields the whole pool, not a crash.
	assert_eq(rng.weighted_sample(["a", "b"], [1.0, 1.0], 5).size(), 2)


func test_chance_is_clamped() -> void:
	var rng := Rng.new(5)
	for i in 100:
		assert_true(rng.chance(2.0), "p > 1 must always succeed")
		assert_false(rng.chance(-1.0), "p < 0 must always fail")


func _unique(arr: Array) -> Array:
	var out: Array = []
	for v in arr:
		if not out.has(v):
			out.append(v)
	return out
