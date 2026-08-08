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


## Sigils of a given tier, for transmutation.
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


## The cheapest sigil of `to_tier` obtainable by transmuting `from_id`, or null
## when nothing of the next tier exists.
func transmute_target(from_id: String) -> Sigil:
	var from := sigil_by_id(from_id)
	if from == null:
		return null
	var up := of_tier(from.tier + 1)
	if up.is_empty():
		return null
	# Prefer the most common sigil of the next tier: converting surplus should
	# feel like a floor under bad luck, not a second lottery.
	var best: Sigil = up[0]
	for s in up:
		if s.weight > best.weight:
			best = s
	return best


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
