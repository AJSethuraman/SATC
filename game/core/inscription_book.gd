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
func match_pattern(sigil_ids: Array, item_slot: String) -> Inscription:
	for i in inscriptions:
		if i.matches(sigil_ids, item_slot):
			return i
	return null


## Weighted sigil drop. Higher tiers carry lower weight, which is what makes a
## specific late-tier sigil worth banking a slot for.
func roll_sigil(rng: Rng, ilvl: int = 99) -> Sigil:
	var eligible: Array = []
	var weights: Array = []
	for s in sigils:
		# Tier gates roughly on depth, so floor one cannot hand you a Doom.
		if s.tier * 4 > ilvl + 4:
			continue
		eligible.append(s)
		weights.append(s.weight)
	if eligible.is_empty():
		return sigils[0]
	return rng.weighted_pick(eligible, weights)


## Inscriptions ordered by how few components they need, cheapest first. The
## acquisition simulator uses this to model a player who chases the nearest
## achievable recipe rather than the flashiest one.
func by_ascending_cost() -> Array:
	var sorted := inscriptions.duplicate()
	sorted.sort_custom(func(a: Inscription, b: Inscription): return a.pattern.size() < b.pattern.size())
	return sorted
