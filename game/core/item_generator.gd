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

## The named items — uniques and set pieces. Null means none are loaded, which
## the roll treats as "no named item exists" rather than as an error.
var uniques: UniquePool = null


## Relative rarity weights before magic find is applied.
##
## SET's two points came out of RARE rather than being added on top, so NORMAL
## keeps exactly 60 of 100. That share is the vessel rate — sockets only roll on
## unaffixed items — and sim/acquisition_sim.gd's measurements of how long the
## inscription chase takes are all made against it. Naming a new rarity should
## not silently move the number the chase is tuned on.
const BASE_RARITY_WEIGHTS := {
	Item.Rarity.NORMAL: 60.0,
	Item.Rarity.MAGIC: 28.0,
	Item.Rarity.RARE: 9.0,
	Item.Rarity.SET: 2.0,
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
	# The shared table rather than a fresh parse: RunState reads set bonuses out
	# of the same one, and two copies of a content file is two places for it to be
	# stale. See UniquePool.shared() for why it is shared at all.
	g.uniques = UniquePool.shared()
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


## Socket count for an unaffixed item.
##
## Big vessels are deliberately scarce: they are the only home for a long
## inscription, so their rate is the single biggest lever on how long the chase
## takes. sim/acquisition_sim.gd measures exactly that, and this is the number to
## turn if the answer comes back wrong.
const SOCKET_WEIGHTS := {
	0: 26.0,
	1: 34.0,
	2: 26.0,
	3: 14.0,
	4: 6.0,
}
## Depth at which three-socket vessels become possible at all.
##
## Subsumed in practice by the tier ceiling — an exceptional base cannot drop
## before Nightmare, which is far deeper than this — but kept as the floor it
## always was, so the rule still holds if the tier table is ever retuned.
const THREE_SOCKET_ILVL := 8


## Sockets for one drop. The tier ceiling is the hard gate and ilvl the soft one:
## the tier decides whether a socket count exists in this pass at all, ilvl only
## holds the larger counts back within a pass.
func roll_sockets(rng: Rng, ilvl: int, tier: Item.Tier = Item.Tier.PLAIN) -> int:
	var ceiling := Item.max_sockets(tier)
	var counts: Array = []
	var weights: Array = []
	for n in SOCKET_WEIGHTS:
		var count := int(n)
		if count > ceiling:
			continue
		if count >= 3 and ilvl < THREE_SOCKET_ILVL:
			continue
		counts.append(count)
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


## Which difficulty pass an item level belongs to.
##
## ilvl is depth-shaped — callers roll drops a few areas ahead of where the
## player is standing — so it lands on the same pass boundaries depth does. This
## is the fallback: a caller that knows its own difficulty should hand it to
## roll_item instead, because gear rolled ahead of depth would otherwise leak an
## exceptional base into the last few areas of Normal.
static func difficulty_of_ilvl(ilvl: int) -> int:
	return Progression.difficulty_of_depth(ilvl)


static func tier_of_base(base: Dictionary) -> Item.Tier:
	return Item.tier_from_id(str(base.get("tier", "plain")))


## The bases that exist at `difficulty`, optionally narrowed to one slot.
##
## This filter *is* the difficulty axis as far as loot is concerned: an
## exceptional base simply does not drop in Normal, so neither does the
## three-socket vessel a three-sigil inscription needs. Depth buys the
## component; no amount of repeating Normal does.
func bases_for(difficulty: int, slot: String = "") -> Array:
	var out: Array = []
	for entry in bases:
		var base: Dictionary = entry
		if slot != "" and str(base.get("slot", "")) != slot:
			continue
		if Item.min_difficulty(tier_of_base(base)) > difficulty:
			continue
		out.append(base)
	return out


## Roll one drop. `difficulty` is the 1-based pass; leave it at 0 to infer the
## pass from ilvl.
func roll_item(
	ilvl: int,
	rng: Rng,
	magic_find: float = 0.0,
	slot: String = "",
	difficulty: int = 0
) -> Item:
	var pass_number: int = difficulty if difficulty > 0 else difficulty_of_ilvl(ilvl)
	var candidates := bases_for(pass_number, slot)
	assert(
		not candidates.is_empty(),
		"ItemGenerator: no base for slot '%s' at difficulty %d" % [slot, pass_number]
	)

	var base: Dictionary = candidates[rng.randi_range(0, candidates.size() - 1)]
	var tier := tier_of_base(base)

	var item := Item.new()
	item.base_name = str(base.get("name", "Item"))
	item.slot = str(base.get("slot", "weapon"))
	item.tier = tier
	item.implicit = base.get("implicit", {})
	item.ilvl = ilvl
	item.rarity = roll_rarity(rng, magic_find)

	# Named items are fixed content, so they replace the affix pass entirely
	# rather than feeding it: a unique is a thing you either found or did not.
	#
	# The table is small and depth-gated, so it will often hold nothing for this
	# slot at this pass. That demotes the drop to a rare instead of leaving it
	# empty — a thin content file should cost the player an item they never knew
	# existed, not a wasted drop.
	if item.rarity == Item.Rarity.UNIQUE or item.rarity == Item.Rarity.SET:
		var named: UniquePool.Piece = null
		if uniques != null:
			named = uniques.roll_piece(rng, item.rarity, item.slot, pass_number)
		if named != null:
			named.stamp(item)
			return item
		item.rarity = Item.Rarity.RARE

	# Sockets only on unaffixed items. That is what makes a Normal drop worth
	# looking at — it is the only thing an inscription can be built in, so the
	# usual "grey is trash" instinct inverts.
	if item.rarity == Item.Rarity.NORMAL:
		item.sockets = roll_sockets(rng, ilvl, tier)

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
