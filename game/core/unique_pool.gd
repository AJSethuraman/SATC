class_name UniquePool
extends RefCounted

## The named-item table — uniques and set pieces — loaded from data/uniques.json.
##
## There are three ways to be powerful and only one of them is assembled. The
## assembled one is the inscription system; this file is the other two.
##
## What makes a named item different from a rare is not its size, it is that it
## does not roll. The same Emberfang comes out of the ground every time, so it
## can be known, wanted, recognised on sight, and told to someone else — none of
## which a generated name can do. That is why the mods here are fixed values
## rather than ranges, and why nothing in this file touches the Rng except to
## choose *which* named item drops.
##
## THE POWER BUDGET, and why runewords survive it: a named line may only use a
## modifier key the affix table already rolls, may never exceed the best roll of
## that key, and may never grant a `more` multiplier. A unique is therefore, at
## its absolute best, a rare that always rolls perfectly and always rolls the
## lines you wanted — while an inscription's multiplicative bucket sits on top of
## whatever additive pile the rest of the build has assembled, and multiplies it.
## Additive lines flatten as they stack; a multiplier does not. So the assembly
## loop stays the centre of the game and uniques stay what they are for: the
## thing a run that never lined up its sigils can still bank. The budget is
## enforced by tests/test_items.gd rather than trusted, because a content file is
## exactly where a design invariant goes quietly wrong.
##
## Nothing here touches the scene tree — "how many pieces of this set am I
## wearing" is a static function over a loadout, so the set mechanic is testable
## without a game running.

## Prose for the scalar half of the modifier grammar. The typed keys
## (`flat.fire`, `resist.cold`, …) are read apart in label_for instead.
const SCALAR_LABELS := {
	"weapon_min": "minimum damage",
	"weapon_max": "maximum damage",
	"crit_chance": "critical chance",
	"crit_mult": "critical damage",
	"armor": "armour",
	"max_health": "life",
	"move_speed": "movement speed",
	"max_mana": "mana",
	"mana_regen": "mana regeneration",
	"cast_speed": "cast speed",
	"more": "more damage",
}


## One named item: a unique, or a single piece of a set.
class Piece extends RefCounted:
	var id: String = ""
	var display_name: String = ""
	var slot: String = "weapon"
	## The set this belongs to, or "" for a unique.
	var set_id: String = ""
	## Earliest difficulty pass this can drop in, 1-based, matching
	## Item.min_difficulty rather than the 0-based Difficulty enum.
	var min_difficulty: int = 1
	var weight: float = 1.0
	## Modifier key (StatBlock grammar) -> fixed value. No ranges: see the file
	## comment for why a named item does not roll.
	var mods: Dictionary = {}
	var grants_tags: Array[String] = []
	var description: String = ""

	static func from_dict(d: Dictionary, in_set: String, set_difficulty: int) -> Piece:
		var p := Piece.new()
		p.id = str(d.get("id", ""))
		p.display_name = str(d.get("name", p.id))
		p.slot = str(d.get("slot", "weapon"))
		p.set_id = in_set
		# A set's pieces inherit the set's depth gate unless one says otherwise:
		# half a set that drops a pass earlier than the other half is a set the
		# player cannot finish where they found it.
		p.min_difficulty = int(d.get("min_difficulty", set_difficulty))
		p.weight = float(d.get("weight", 1.0))
		p.mods = d.get("mods", {})
		p.description = str(d.get("description", ""))
		for t in d.get("grants_tags", []):
			p.grants_tags.append(str(t))
		return p

	## Which rarity a drop of this piece is. Set membership is the only thing
	## that decides it, so the two can never disagree.
	func rarity() -> Item.Rarity:
		return Item.Rarity.SET if set_id != "" else Item.Rarity.UNIQUE

	func is_set_piece() -> bool:
		return set_id != ""

	## Write this piece onto a drop, replacing whatever the roll produced.
	##
	## The base underneath is deliberately left alone. A named item binds to a
	## slot rather than to a base name, so the same unique found in Hell sits on
	## an elite base and inherits its better implicit — binding to a base would
	## have meant authoring every unique once per rung of the tier ladder for no
	## design gain.
	##
	## Sockets are cleared, and that is a design statement rather than tidiness:
	## a named item can never also be a vessel, so a unique and a runeword are a
	## choice between two items and never the same one.
	func stamp(item: Item) -> void:
		item.rarity = rarity()
		item.unique_name = display_name
		item.set_id = set_id
		item.slot = slot
		item.sockets = 0
		item.socketed.clear()
		item.inscription = null
		item.affixes.clear()

		var first := true
		for key in mods:
			var value := float(mods[key])
			var line := _line(str(key), value)
			# The tags ride on the first line only. Item.tags() would dedupe them
			# anyway, but repeating a piece's whole tag list on every modifier
			# makes the item look like it grants each tag several times.
			if first:
				var carried: Array[String] = []
				carried.append_array(grants_tags)
				line.tags = carried
				first = false
			item.affixes.append(line)

	## One fixed modifier, in the shape an item already carries rolled ones.
	##
	## Reusing Affix.Rolled rather than adding a parallel container is what keeps
	## everything downstream — apply_to, tags(), the item card — unaware that
	## named items exist at all. The id is per line rather than per piece so an
	## item still never shows two lines sharing an identity.
	func _line(key: String, value: float) -> Affix.Rolled:
		var r := Affix.Rolled.new()
		r.id = "%s:%s" % [id, key]
		r.display_name = UniquePool.line_text(key, value)
		r.mods = {key: value}
		return r


## One threshold of a set: what having this many pieces on grants.
class Bonus extends RefCounted:
	var pieces: int = 2
	var mods: Dictionary = {}
	var grants_tags: Array[String] = []

	static func from_dict(d: Dictionary) -> Bonus:
		var b := Bonus.new()
		b.pieces = int(d.get("pieces", 2))
		b.mods = d.get("mods", {})
		for t in d.get("grants_tags", []):
			b.grants_tags.append(str(t))
		return b


## A set and its thresholds.
class SetDefinition extends RefCounted:
	var id: String = ""
	var display_name: String = ""
	var description: String = ""
	var min_difficulty: int = 1
	var bonuses: Array = []  # of Bonus

	static func from_dict(d: Dictionary) -> SetDefinition:
		var s := SetDefinition.new()
		s.id = str(d.get("id", ""))
		s.display_name = str(d.get("name", s.id))
		s.description = str(d.get("description", ""))
		s.min_difficulty = int(d.get("min_difficulty", 1))
		for entry in d.get("bonuses", []):
			s.bonuses.append(Bonus.from_dict(entry))
		return s

	## Every threshold `count` pieces has reached.
	##
	## Thresholds accumulate rather than replace — reaching three keeps the
	## two-piece bonus — which is Diablo II's rule and the reason the last piece
	## of a set reads as a step up rather than a swap.
	func bonuses_at(count: int) -> Array:
		var out: Array = []
		for entry in bonuses:
			var bonus := entry as Bonus
			if bonus != null and count >= bonus.pieces:
				out.append(bonus)
		return out


## Every named item, uniques and set pieces together. Untyped rather than
## Array[Piece] because typed arrays of an inner class are a place GDScript
## inference has bitten this project before; callers narrow with `as Piece`.
var pieces: Array = []
var sets: Array = []  # of SetDefinition


## Where the named-item table lives. ItemGenerator loads the same path.
const DEFAULT_PATH := "res://data/uniques.json"

static var _shared: UniquePool = null


## The table every run reads set bonuses out of, loaded once.
##
## A shared instance rather than a parameter threaded through RunState because
## the alternative was worse in a specific way: set bonuses have to be visible to
## stats_with_item(), which is how every "is this an upgrade?" decision in the
## game is made. A caller that forgot to hand over the pool would not crash — it
## would quietly evaluate the second piece of a set as though the set did not
## exist, and recommend against completing it. That is the same class of bug as
## the balance simulator's hand-rolled trial block, and this is the shape that
## makes it unavailable rather than merely discouraged. Tests that want a
## specific table still assign RunState.uniques directly.
static func shared() -> UniquePool:
	if _shared == null:
		_shared = UniquePool.from_json(DEFAULT_PATH)
	return _shared


static func from_json(path: String) -> UniquePool:
	var p := UniquePool.new()
	var f := FileAccess.open(path, FileAccess.READ)
	assert(f != null, "UniquePool: cannot open %s" % path)
	# An empty pool is a survivable state — no named item ever drops — so a
	# missing or malformed file degrades to that rather than taking the run down
	# in a build where the assert above is compiled out.
	if f == null:
		return p
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	assert(parsed is Dictionary, "UniquePool: %s must contain a JSON object" % path)
	if not (parsed is Dictionary):
		return p
	var data: Dictionary = parsed

	for d in data.get("uniques", []):
		p.pieces.append(Piece.from_dict(d, "", 1))

	for entry in data.get("sets", []):
		var definition := SetDefinition.from_dict(entry)
		p.sets.append(definition)
		var set_data: Dictionary = entry
		for piece_data in set_data.get("pieces", []):
			p.pieces.append(Piece.from_dict(piece_data, definition.id, definition.min_difficulty))

	return p


func set_by_id(id: String) -> SetDefinition:
	for entry in sets:
		var definition := entry as SetDefinition
		if definition != null and definition.id == id:
			return definition
	return null


func piece_by_name(name: String) -> Piece:
	for entry in pieces:
		var piece := entry as Piece
		if piece != null and piece.display_name == name:
			return piece
	return null


func pieces_of_set(id: String) -> Array:
	var out: Array = []
	for entry in pieces:
		var piece := entry as Piece
		if piece != null and piece.set_id == id:
			out.append(piece)
	return out


## Every named item that could drop for this rarity, slot and difficulty pass.
## An empty slot means any slot.
func pieces_for(rarity: Item.Rarity, slot: String, difficulty: int) -> Array:
	var out: Array = []
	for entry in pieces:
		var piece := entry as Piece
		if piece == null:
			continue
		if piece.rarity() != rarity:
			continue
		if slot != "" and piece.slot != slot:
			continue
		if piece.min_difficulty > difficulty:
			continue
		out.append(piece)
	return out


## One named item for a drop, or null when the table holds nothing that fits.
##
## Returning null rather than substituting something is deliberate: the caller
## knows what a drop with no named item available should become, and this does
## not.
func roll_piece(rng: Rng, rarity: Item.Rarity, slot: String, difficulty: int) -> Piece:
	# Both arrays are built in the same pass because weighted_pick requires them
	# to stay parallel, and skipping an entry in one but not the other would shift
	# every weight after it onto the wrong item.
	var eligible: Array = []
	var weights: Array = []
	for entry in pieces_for(rarity, slot, difficulty):
		var piece := entry as Piece
		if piece == null:
			continue
		eligible.append(piece)
		weights.append(piece.weight)
	var picked: Variant = rng.weighted_pick(eligible, weights)
	return picked as Piece


# --- set membership -----------------------------------------------------
#
# The question the set mechanic actually turns on is "how many pieces of this am
# I wearing", and it is answered here, statically, over a plain loadout. No
# scene, no run, nothing to stand up: a test can build three items in three lines
# and ask.


## Set membership of a loadout, as set id -> pieces worn.
##
## Accepts either the slot -> Item dictionary a run carries in RunState.gear or a
## plain array of items, because those are the two shapes the real callers hold
## and making one of them convert first would put the counting back in the
## caller, which is precisely what this is for.
static func worn_counts(worn: Variant) -> Dictionary:
	var counts := {}
	var seen: Array[String] = []
	for entry in worn_items(worn):
		var item := entry as Item
		if item == null or item.set_id == "":
			continue
		# One piece per slot, so passing the same item twice cannot inflate a
		# bonus. The gear dictionary already enforces this by construction; an
		# array does not, and a set bonus is exactly the thing worth cheating.
		var key := "%s/%s" % [item.set_id, item.slot]
		if seen.has(key):
			continue
		seen.append(key)
		counts[item.set_id] = int(counts.get(item.set_id, 0)) + 1
	return counts


## Every set bonus this loadout has earned, across every set it is wearing.
func bonuses_active(worn: Variant) -> Array:
	var out: Array = []
	var counts := worn_counts(worn)
	for id in counts:
		var definition := set_by_id(str(id))
		if definition == null:
			continue  # a piece from content that has since been removed
		out.append_array(definition.bonuses_at(int(counts[id])))
	return out


## The modifiers a loadout's set bonuses grant, merged.
##
## Values of the same key are summed rather than overwritten. Two sets both
## granting life is unusual but legal, and silently keeping only one of them
## would be the kind of loss a player never notices and never reports.
func set_bonus_mods(worn: Variant) -> Dictionary:
	var out := {}
	for entry in bonuses_active(worn):
		var bonus := entry as Bonus
		if bonus == null:
			continue
		for key in bonus.mods:
			var k := str(key)
			var value := float(bonus.mods[key])
			out[k] = float(out.get(k, 0.0)) + value
	return out


func set_bonus_tags(worn: Variant) -> Array[String]:
	var out: Array[String] = []
	for entry in bonuses_active(worn):
		var bonus := entry as Bonus
		if bonus == null:
			continue
		for t in bonus.grants_tags:
			if not out.has(t):
				out.append(t)
	return out


## Fold a loadout's set bonuses into a stat block.
##
## The seam a run hooks into: everything a set grants beyond its individual
## pieces arrives through this one call, so wiring it up is one line wherever
## gear is resolved into stats.
func apply_set_bonuses(worn: Variant, stats: StatBlock) -> void:
	stats.apply_all(set_bonus_mods(worn))
	stats.add_tags(set_bonus_tags(worn))


## A loadout as a flat array, whichever of the two shapes it arrived in. Public
## because the item card needs to ask "and what if I also wore this?", which
## means building a loadout rather than only counting one.
static func worn_items(worn: Variant) -> Array:
	if worn is Dictionary:
		return (worn as Dictionary).values()
	if worn is Array:
		return (worn as Array).duplicate()
	return []


# --- presentation -------------------------------------------------------


## Plain-language text for one fixed modifier line.
##
## A rolled affix borrows its wording from the template it came from; a named
## line has no template, so the text is derived from the modifier itself.
## Fractions read as percentages because every fractional key in the grammar is
## one — the same convention Affix._format_name follows, kept identical on
## purpose so a unique's lines and a rare's lines read alike on the item card.
static func line_text(key: String, value: float) -> String:
	var shown := "%d" % roundi(value)
	if absf(value) < 1.0 and value != 0.0:
		shown = "%d%%" % roundi(value * 100.0)
	var sign_prefix := "+" if value >= 0.0 else ""
	return "%s%s %s" % [sign_prefix, shown, label_for(key)]


static func label_for(key: String) -> String:
	if key.begins_with("flat."):
		return "%s damage" % key.substr(5)
	if key.begins_with("increased."):
		return "increased %s damage" % key.substr(10)
	if key.begins_with("resist."):
		return "%s resistance" % key.substr(7)
	if key.begins_with("pierce."):
		return "%s pierce" % key.substr(7)
	if key.begins_with("more."):
		return "more %s damage" % key.substr(5)
	return str(SCALAR_LABELS.get(key, key))
