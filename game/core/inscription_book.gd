class_name InscriptionBook
extends RefCounted

## The sigil and inscription tables, plus matching.
##
## Loaded from data/sigils.json the same way items and boons are, so content is
## data and the rules are code.

var sigils: Array[Sigil] = []
var inscriptions: Array[Inscription] = []


static func from_json(path: String) -> InscriptionBook:
	var b := InscriptionBook.new()
	var f := FileAccess.open(path, FileAccess.READ)
	assert(f != null, "InscriptionBook: cannot open %s" % path)
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	assert(parsed is Dictionary, "InscriptionBook: %s must contain a JSON object" % path)

	for d in parsed.get("sigils", []):
		b.sigils.append(Sigil.from_dict(d))
	for d in parsed.get("inscriptions", []):
		b.inscriptions.append(Inscription.from_dict(d))
	assert(not b.sigils.is_empty(), "InscriptionBook: no sigils in %s" % path)
	assert(not b.inscriptions.is_empty(), "InscriptionBook: no inscriptions in %s" % path)
	return b


func sigil_by_id(id: String) -> Sigil:
	for s in sigils:
		if s.id == id:
			return s
	return null


func inscription_by_id(id: String) -> Inscription:
	for i in inscriptions:
		if i.id == id:
			return i
	return null


## The inscription formed by this exact ordered sequence, or null.
##
## Returns the first match; the data test enforces that no two inscriptions
## share a pattern and slot, so "first" is unambiguous.
func match_pattern(sigil_ids: Array, item_slot: String, item_sockets: int) -> Inscription:
	for i in inscriptions:
		if i.matches(sigil_ids, item_slot, item_sockets):
			return i
	return null


## Sigils of a given tier.
func of_tier(tier: int) -> Array:
	return sigils.filter(func(s: Sigil): return s.tier == tier)


## How many identical sigils transmute into one of the next tier up.
##
## Straight from D2's cube recipes, including the tightening at the top: three
## for one through the low and middle bands, two for one at the high end. That
## tightening is deliberate — the hardest steps are proportionally *cheaper*, so
## the top of the ladder stays reachable rather than receding.
## See docs/d2-rune-economy.md.
const TRANSMUTE_COST_LOW := 3
const TRANSMUTE_COST_HIGH := 2
## Tier at and above which the cheaper ratio applies.
const TRANSMUTE_HIGH_TIER := 4


static func transmute_cost(from_tier: int) -> int:
	return TRANSMUTE_COST_HIGH if from_tier >= TRANSMUTE_HIGH_TIER else TRANSMUTE_COST_LOW


## The transmutation ladder, cheapest sigil first. Cached; see _ensure_ladder.
var _ladder: Array[String] = []


## Ladder order: lower tier first, then commonest first, then declaration order.
##
## The declaration-order tiebreak is load-bearing rather than cosmetic. Three
## tier-1 sigils share a weight and sort_custom is not a stable sort, so without
## a final tiebreak the ladder could come out in a different order between builds
## and the grind cost of a recipe would silently move underneath the player.
func _precedes(a: Sigil, b: Sigil, declared: Dictionary) -> bool:
	if a.tier != b.tier:
		return a.tier < b.tier
	if a.weight != b.weight:
		return a.weight > b.weight
	return int(declared.get(a.id, 0)) < int(declared.get(b.id, 0))


## Build the ladder if it does not already cover the sigil table.
##
## Keyed on size rather than a "built once" flag so a book assembled by hand
## still gets a correct ladder instead of a stale one.
func _ensure_ladder() -> void:
	if _ladder.size() == sigils.size():
		return
	var declared := {}
	for i in sigils.size():
		var s: Sigil = sigils[i]
		declared[s.id] = i
	var ordered: Array = sigils.duplicate()
	ordered.sort_custom(_precedes.bind(declared))
	_ladder.clear()
	for entry in ordered:
		var rung := entry as Sigil
		if rung != null:
			_ladder.append(rung.id)


## Every sigil id from cheapest to rarest — the order transmutation walks.
##
## A total order, the way D2's cube recipe is El -> Eld -> Tir -> ... -> Zod.
## This replaced a jump to "the commonest sigil of the next tier", under which
## tier 2 always produced `pyre` and `rime` and `storm` could not be obtained by
## grinding at any price. The acquisition simulator measured the consequence: a
## chase blocked on sigils rather than vessels, with surplus unable to help.
## A total order means the question is only how much you convert, never whether
## the thing you want is convertible at all. See docs/difficulty-and-loot.md.
func transmute_order() -> Array[String]:
	_ensure_ladder()
	# A copy, so a caller walking the ladder cannot corrupt the cached one.
	var out: Array[String] = []
	out.append_array(_ladder)
	return out


## Position of a sigil on the ladder, or -1 when it is not in the table.
func transmute_rank(id: String) -> int:
	_ensure_ladder()
	return _ladder.find(id)


## The sigil one rung up the ladder from `from_id`, or null at the very top.
##
## One rung, not one tier: within a tier the ladder still climbs (ash -> cinder
## -> hoar -> spark), which is what makes every sigil reachable from every
## cheaper one.
func transmute_target(from_id: String) -> Sigil:
	var at := transmute_rank(from_id)
	if at < 0 or at + 1 >= _ladder.size():
		return null
	var next_id: String = _ladder[at + 1]
	return sigil_by_id(next_id)


## Depth at which a sigil of a given tier reaches its full drop weight.
const TIER_FULL_ILVL := 4
## Floor on the out-of-depth penalty. Deliberately non-zero — see below.
const MIN_DEPTH_FACTOR := 0.03


## Weighted sigil drop. Higher tiers carry lower weight and are further
## suppressed above their intended depth, which is what makes a specific
## late-tier sigil worth banking a slot for.
##
## The suppression is steep but never reaches zero, and that matters. This was
## previously a hard gate — a sigil simply could not drop below its tier's
## depth — which combined with a difficulty curve that ends most runs on floor
## five to make two inscriptions literally unobtainable. Both referenced real
## sigils, both passed every validation, and nobody completed either in four
## hundred simulated runs. A high sigil out of depth should be a story, not an
## impossibility.
func roll_sigil(rng: Rng, ilvl: int = 99) -> Sigil:
	var eligible: Array = []
	var weights: Array = []
	for s in sigils:
		var intended := float(maxi(1, s.tier * TIER_FULL_ILVL))
		var reach := clampf(float(ilvl) / intended, 0.0, 1.0)
		var factor := maxf(MIN_DEPTH_FACTOR, reach * reach)
		eligible.append(s)
		weights.append(s.weight * factor)
	return rng.weighted_pick(eligible, weights)


## Inscriptions ordered by how few components they need, cheapest first. The
## acquisition simulator uses this to model a player who chases the nearest
## achievable recipe rather than the flashiest one.
func by_ascending_cost() -> Array:
	var sorted := inscriptions.duplicate()
	sorted.sort_custom(func(a: Inscription, b: Inscription): return a.pattern.size() < b.pattern.size())
	return sorted
