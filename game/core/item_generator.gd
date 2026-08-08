class_name ItemGenerator
extends RefCounted

## Rolls items from the base/affix tables in data/items.json.
##
## Rolling is pure: given the same generator and the same seeded Rng, the same
## item comes out. That is what lets tests pin exact drops and lets the balance
## simulator replay a run.

var bases: Array = []  # of Dictionary, straight from JSON
## Typed so that `for a in affixes` yields an Affix rather than a Variant —
## otherwise every `:=` downstream of a loop over this fails to infer.
var affixes: Array[Affix] = []

## Relative rarity weights before magic find is applied.
const BASE_RARITY_WEIGHTS := {
	Item.Rarity.NORMAL: 60.0,
	Item.Rarity.MAGIC: 28.0,
	Item.Rarity.RARE: 11.0,
	Item.Rarity.UNIQUE: 1.0,
}


static func from_json(path: String) -> ItemGenerator:
	var g := ItemGenerator.new()
	var f := FileAccess.open(path, FileAccess.READ)
	assert(f != null, "ItemGenerator: cannot open %s" % path)
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	assert(parsed is Dictionary, "ItemGenerator: %s must contain a JSON object" % path)

	g.bases = parsed.get("bases", [])
	for d in parsed.get("affixes", []):
		g.affixes.append(Affix.from_dict(d))
	assert(not g.bases.is_empty(), "ItemGenerator: no bases in %s" % path)
	assert(not g.affixes.is_empty(), "ItemGenerator: no affixes in %s" % path)
	return g


## Magic find scales only the non-normal weights, so it raises the odds that a
## drop is interesting without ever changing the drop count.
func roll_rarity(rng: Rng, magic_find: float = 0.0) -> Item.Rarity:
	var kinds: Array = []
	var weights: Array = []
	for r in BASE_RARITY_WEIGHTS:
		kinds.append(r)
		var w: float = BASE_RARITY_WEIGHTS[r]
		if r != Item.Rarity.NORMAL:
			w *= 1.0 + maxf(0.0, magic_find)
		weights.append(w)
	return rng.weighted_pick(kinds, weights)


## Socket count for a plain item.
##
## Three-socket vessels are gated on depth and deliberately scarce: they are the
## only home for a three-sigil inscription, so their rate is the single biggest
## lever on how long the chase takes. sim/acquisition_sim.gd measures exactly
## that, and this is the number to turn if the answer comes back wrong.
const SOCKET_WEIGHTS := {
	0: 26.0,
	1: 34.0,
	2: 26.0,
	3: 14.0,
}
## Depth at which three-socket vessels become possible at all.
const THREE_SOCKET_ILVL := 8


func roll_sockets(rng: Rng, ilvl: int) -> int:
	var counts: Array = []
	var weights: Array = []
	for n in SOCKET_WEIGHTS:
		if n == 3 and ilvl < THREE_SOCKET_ILVL:
			continue
		counts.append(n)
		weights.append(SOCKET_WEIGHTS[n])
	return int(rng.weighted_pick(counts, weights))


## Every affix legal on `slot` at `ilvl` whose group is not already taken.
func eligible(slot: String, ilvl: int, used_groups: Array) -> Array:
	var out: Array = []
	for a in affixes:
		if a.ilvl_req > ilvl:
			continue
		if used_groups.has(a.group):
			continue
		if not a.allows_slot(slot):
			continue
		out.append(a)
	return out


func roll_item(ilvl: int, rng: Rng, magic_find: float = 0.0, slot: String = "") -> Item:
	var candidates := bases
	if slot != "":
		candidates = bases.filter(func(b): return str(b.get("slot", "")) == slot)
	assert(not candidates.is_empty(), "ItemGenerator: no base for slot '%s'" % slot)

	var base: Dictionary = candidates[rng.randi_range(0, candidates.size() - 1)]

	var item := Item.new()
	item.base_name = str(base.get("name", "Item"))
	item.slot = str(base.get("slot", "weapon"))
	item.implicit = base.get("implicit", {})
	item.ilvl = ilvl
	item.rarity = roll_rarity(rng, magic_find)

	# Sockets only on plain items. That is what makes a Normal drop worth
	# looking at — it is the only thing an inscription can be built in, so the
	# usual "grey is trash" instinct inverts.
	if item.rarity == Item.Rarity.NORMAL:
		item.sockets = roll_sockets(rng, ilvl)

	var span: Array = Item.AFFIX_COUNTS[item.rarity]
	var want := rng.randi_range(int(span[0]), int(span[1]))

	var used_groups: Array = []
	while item.affixes.size() < want:
		var pool := eligible(item.slot, ilvl, used_groups)
		if pool.is_empty():
			break  # exhausted the table; a short item is better than a duplicate
		var weights: Array = []
		for a in pool:
			weights.append(a.weight)
		var picked: Affix = rng.weighted_pick(pool, weights)
		if picked == null:
			break
		used_groups.append(picked.group)
		item.affixes.append(picked.roll(rng))

	return item
