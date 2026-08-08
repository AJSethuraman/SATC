class_name Rng
extends RefCounted

## Deterministic, seedable random source.
##
## Every random decision in the simulation goes through one of these. That is
## what makes runs reproducible from a seed, which in turn is what makes the
## balance simulator (sim/balance_sim.gd) and the regression tests possible.
##
## Subsystems take *derived* streams rather than sharing one, so that adding a
## combat roll does not shift every subsequent loot roll and invalidate the
## tests.

var seed_value: int

var _rng := RandomNumberGenerator.new()


func _init(seed_v: int = 0) -> void:
	seed_value = seed_v
	_rng.seed = seed_v


func randf() -> float:
	return _rng.randf()


func randi_range(lo: int, hi: int) -> int:
	return _rng.randi_range(lo, hi)


func randf_range(lo: float, hi: float) -> float:
	return _rng.randf_range(lo, hi)


## True with probability `p` (clamped to 0..1).
func chance(p: float) -> bool:
	return _rng.randf() < clampf(p, 0.0, 1.0)


## An independent stream derived from this one. Same parent seed + same salt
## always yields the same child stream.
func derive(salt: int) -> Rng:
	return Rng.new(mix(seed_value, salt))


## 64-bit mix, masked to stay positive so it is a valid RandomNumberGenerator
## seed on every platform.
static func mix(a: int, b: int) -> int:
	var h := a * 1099511628211 + b * 2654435761
	h ^= h >> 33
	h *= -49064778989728563  # 0xff51afd7ed558ccd as a signed 64-bit literal
	h ^= h >> 29
	return h & 0x7FFFFFFFFFFFFFF


## Weighted selection. `weights` must be parallel to `items` and sum above zero.
## Returns `null` for an empty pool so callers can detect exhaustion.
func weighted_pick(items: Array, weights: Array) -> Variant:
	assert(items.size() == weights.size(), "weighted_pick: parallel arrays required")
	if items.is_empty():
		return null

	var total := 0.0
	for w in weights:
		total += maxf(0.0, float(w))
	if total <= 0.0:
		return null

	var roll := _rng.randf() * total
	var cursor := 0.0
	for i in items.size():
		cursor += maxf(0.0, float(weights[i]))
		if roll < cursor:
			return items[i]
	return items[items.size() - 1]  # float drift guard


## Pick `count` distinct items by weight, without replacement. Returns fewer
## than `count` only if the pool is smaller than that.
func weighted_sample(items: Array, weights: Array, count: int) -> Array:
	var pool := items.duplicate()
	var w := weights.duplicate()
	var out: Array = []
	while out.size() < count and not pool.is_empty():
		var picked: Variant = weighted_pick(pool, w)
		if picked == null:
			break
		var idx := pool.find(picked)
		pool.remove_at(idx)
		w.remove_at(idx)
		out.append(picked)
	return out
