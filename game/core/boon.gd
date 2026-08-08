class_name Boon
extends RefCounted

## A run-scoped blessing, offered three at a time after a cleared room.
##
## Boons own the multiplicative bucket (see core/damage.gd), so they are what
## makes a run's power curve steepen. They are also where gear cashes out: a
## boon can require a tag, and tags come only from affixes, so what you are
## wearing decides which blessings the run is even allowed to offer you.

enum Rarity { COMMON, RARE, EPIC, HEROIC }

const RARITY_NAMES := {
	Rarity.COMMON: "Common",
	Rarity.RARE: "Rare",
	Rarity.EPIC: "Epic",
	Rarity.HEROIC: "Heroic",
}

## Every numeric modifier on a boon scales by its rarity.
const RARITY_SCALE := {
	Rarity.COMMON: 1.0,
	Rarity.RARE: 1.5,
	Rarity.EPIC: 2.0,
	Rarity.HEROIC: 2.5,
}

const RARITY_WEIGHTS := {
	Rarity.COMMON: 70.0,
	Rarity.RARE: 22.0,
	Rarity.EPIC: 7.0,
	Rarity.HEROIC: 1.0,
}

## Which damage type a gear tag implies the wearer has a source of.
##
## Used to check that a `more.<type>` modifier can ever do anything for the
## build it is offered to: a boon carrying one must either gate on a tag that
## implies that type, or seed the type itself. Without that rule it is possible
## to write a boon that is legal, offerable, and worth literally zero.
const TAG_DAMAGE_TYPE := {
	"ignite": "fire",
	"frost": "cold",
	"chain": "lightning",
	"venom": "poison",
	"brutal": "physical",
	"bleed": "physical",
}

var id: String = ""
var display_name: String = ""
var god: String = ""
var group: String = ""
var weight: float = 1.0
var description: String = ""

## Base modifier values, scaled by rarity at offer time.
var mods: Dictionary = {}

## Gear tags that unlock this boon. Empty means always available; otherwise the
## player needs at least one of them.
var requires_tags: Array[String] = []

## Boon ids that must already be owned — this is the duo-boon hook.
var requires_boons: Array[String] = []

## Tags this boon contributes once taken. Each god has one ungated entry boon
## that grants its tag, so a run can commit to an element by choice instead of
## waiting for the right weapon to drop. Gear is still the broader source.
var grants_tags: Array[String] = []


static func from_dict(d: Dictionary) -> Boon:
	var b := Boon.new()
	b.id = str(d.get("id", ""))
	b.display_name = str(d.get("name", b.id))
	b.god = str(d.get("god", ""))
	b.group = str(d.get("group", b.id))
	b.weight = float(d.get("weight", 1.0))
	b.description = str(d.get("description", ""))
	b.mods = d.get("mods", {})
	for t in d.get("requires_tags", []):
		b.requires_tags.append(str(t))
	for r in d.get("requires_boons", []):
		b.requires_boons.append(str(r))
	for t in d.get("grants_tags", []):
		b.grants_tags.append(str(t))
	return b


## Is this boon legal to offer, given what the player owns and wears?
func available_to(owned_ids: Array, owned_groups: Array, gear_tags: Array) -> bool:
	if owned_groups.has(group):
		return false
	for r in requires_boons:
		if not owned_ids.has(r):
			return false
	if requires_tags.is_empty():
		return true
	for t in requires_tags:
		if gear_tags.has(t):
			return true
	return false


## One concrete offer of a boon at a given rarity.
class Rolled extends RefCounted:
	var id: String = ""
	var group: String = ""
	var display_name: String = ""
	var god: String = ""
	var description: String = ""
	var rarity: Rarity = Rarity.COMMON
	var mods: Dictionary = {}  # scaled
	var tags: Array[String] = []

	func label() -> String:
		return "%s %s" % [Boon.RARITY_NAMES[rarity], display_name]

	func _to_string() -> String:
		return label()


func at_rarity(r: Rarity) -> Rolled:
	var out := Rolled.new()
	out.id = id
	out.group = group
	out.display_name = display_name
	out.god = god
	out.description = description
	out.rarity = r
	out.tags = grants_tags.duplicate()
	var scale: float = RARITY_SCALE[r]
	for k in mods:
		out.mods[str(k)] = float(mods[k]) * scale
	return out
