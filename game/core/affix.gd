class_name Affix
extends RefCounted

## A rollable modifier template, loaded from data/affixes.json.
##
## Affixes are D2-shaped: each belongs to an exclusion `group` (an item never
## gets two affixes from the same group), is gated by `ilvl_req`, and is picked
## by `weight` within the eligible set. Tiers exist purely so the same concept
## ("Added Fire Damage") can appear at several power levels — a higher tier is
## a distinct affix with a stricter ilvl requirement.

var id: String = ""
var name_template: String = ""
var group: String = ""
var tier: int = 1
var ilvl_req: int = 1
var weight: float = 1.0

## Modifier key (StatBlock grammar) -> [min, max] roll range.
var ranges: Dictionary = {}

## Tags this affix contributes to the wearer, gating which boons can appear.
var grants_tags: Array[String] = []

## Slots this affix may roll on. Empty means any slot.
var slots: Array[String] = []


func allows_slot(slot: String) -> bool:
	return slots.is_empty() or slots.has(slot)


static func from_dict(d: Dictionary) -> Affix:
	var a := Affix.new()
	a.id = str(d.get("id", ""))
	a.name_template = str(d.get("name", a.id))
	a.group = str(d.get("group", a.id))
	a.tier = int(d.get("tier", 1))
	a.ilvl_req = int(d.get("ilvl_req", 1))
	a.weight = float(d.get("weight", 1.0))
	a.ranges = d.get("ranges", {})
	for t in d.get("grants_tags", []):
		a.grants_tags.append(str(t))
	for s in d.get("slots", []):
		a.slots.append(str(s))
	return a


## One concrete roll of an affix, as it sits on an item.
class Rolled extends RefCounted:
	var id: String = ""
	var display_name: String = ""
	var tier: int = 1
	var mods: Dictionary = {}  # StatBlock key -> rolled value
	var tags: Array[String] = []

	func _to_string() -> String:
		return display_name


## Roll this affix into a concrete instance. Consumes one rng value per
## modifier range, in the dictionary's iteration order.
func roll(rng: Rng) -> Rolled:
	var r := Rolled.new()
	r.id = id
	r.tier = tier
	r.tags = grants_tags.duplicate()

	var first_value := 0.0
	var have_value := false
	for key in ranges:
		var span: Array = ranges[key]
		var lo := float(span[0])
		var hi := float(span[1])
		var v := rng.randf_range(lo, hi)
		# Integer-feeling stats stay whole numbers; percentages keep precision.
		if _is_integral(str(key)):
			v = roundf(v)
		r.mods[str(key)] = v
		if not have_value:
			first_value = v
			have_value = true

	r.display_name = _format_name(first_value)
	return r


func _format_name(value: float) -> String:
	if not name_template.contains("{}"):
		return name_template
	var shown := ""
	if absf(value) < 1.0 and value != 0.0:
		shown = "%d%%" % roundi(value * 100.0)
	else:
		shown = "%d" % roundi(value)
	return name_template.replace("{}", shown)


static func _is_integral(key: String) -> bool:
	return (
		key.begins_with("flat.")
		or key == "armor"
		or key == "max_health"
		or key == "move_speed"
		or key == "weapon_min"
		or key == "weapon_max"
	)
