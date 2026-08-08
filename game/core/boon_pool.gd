class_name BoonPool
extends RefCounted

## Builds the three-way choice the player gets after clearing a room.
##
## The offer is always distinct by group, always legal given owned boons and
## gear tags, and never empty unless the pool is genuinely exhausted.

## Typed so that `for b in boons` yields a Boon rather than a Variant.
var boons: Array[Boon] = []


static func from_json(path: String) -> BoonPool:
	var p := BoonPool.new()
	var f := FileAccess.open(path, FileAccess.READ)
	assert(f != null, "BoonPool: cannot open %s" % path)
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	assert(parsed is Dictionary, "BoonPool: %s must contain a JSON object" % path)
	for d in parsed.get("boons", []):
		p.boons.append(Boon.from_dict(d))
	assert(not p.boons.is_empty(), "BoonPool: no boons in %s" % path)
	return p


func roll_rarity(rng: Rng, luck: float = 0.0) -> Boon.Rarity:
	var kinds: Array = []
	var weights: Array = []
	for r in Boon.RARITY_WEIGHTS:
		kinds.append(r)
		var w: float = Boon.RARITY_WEIGHTS[r]
		if r != Boon.Rarity.COMMON:
			w *= 1.0 + maxf(0.0, luck)
		weights.append(w)
	return rng.weighted_pick(kinds, weights)


## Everything legal right now, in table order.
func candidates(owned_ids: Array, owned_groups: Array, gear_tags: Array) -> Array:
	return boons.filter(
		func(b: Boon): return b.available_to(owned_ids, owned_groups, gear_tags)
	)


## The player-facing choice. Returns up to `count` distinct-group offers.
func offer(
	rng: Rng,
	owned_ids: Array,
	owned_groups: Array,
	gear_tags: Array,
	count: int = 3,
	luck: float = 0.0
) -> Array:
	var pool := candidates(owned_ids, owned_groups, gear_tags)
	var taken_groups: Array = []
	var out: Array = []

	while out.size() < count:
		var legal := pool.filter(func(b: Boon): return not taken_groups.has(b.group))
		if legal.is_empty():
			break
		var weights: Array = []
		for b in legal:
			weights.append(b.weight)
		var picked: Boon = rng.weighted_pick(legal, weights)
		if picked == null:
			break
		taken_groups.append(picked.group)
		out.append(picked.at_rarity(roll_rarity(rng, luck)))

	return out
