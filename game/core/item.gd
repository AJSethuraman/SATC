class_name Item
extends RefCounted

## A generated piece of gear.
##
## Gear is deliberately *build-defining rather than power-defining*: its numbers
## live in the flat/increased buckets, which sum and therefore flatten out, and
## its real leverage is the tags it grants, which decide what boons a run can
## even offer. Boons own the multiplicative bucket and so own the power curve.
## See core/damage.gd for why that split holds.

enum Rarity { NORMAL, MAGIC, RARE, UNIQUE }

const RARITY_NAMES := {
	Rarity.NORMAL: "Normal",
	Rarity.MAGIC: "Magic",
	Rarity.RARE: "Rare",
	Rarity.UNIQUE: "Unique",
}

## How many affixes each rarity rolls, as [min, max].
const AFFIX_COUNTS := {
	Rarity.NORMAL: [0, 0],
	Rarity.MAGIC: [1, 2],
	Rarity.RARE: [3, 4],
	Rarity.UNIQUE: [4, 4],
}

var base_name: String = "Item"
var slot: String = "weapon"
var rarity: Rarity = Rarity.NORMAL
var ilvl: int = 1
var affixes: Array = []  # of Affix.Rolled

## Modifiers inherent to the base type, before any affix rolls.
var implicit: Dictionary = {}


func display_name() -> String:
	if rarity == Rarity.NORMAL or affixes.is_empty():
		return base_name
	if rarity == Rarity.MAGIC:
		return "%s %s" % [affixes[0].display_name, base_name]
	return "%s %s" % [RARITY_NAMES[rarity], base_name]


## Every tag this item contributes, deduplicated.
func tags() -> Array[String]:
	var out: Array[String] = []
	for a in affixes:
		for t in a.tags:
			if not out.has(t):
				out.append(t)
	return out


## Fold this item's implicit and rolled modifiers into a stat block.
func apply_to(stats: StatBlock) -> void:
	stats.apply_all(implicit)
	for a in affixes:
		stats.apply_all(a.mods)
	stats.add_tags(tags())


func describe() -> String:
	var lines: Array[String] = ["%s (ilvl %d)" % [display_name(), ilvl]]
	for a in affixes:
		lines.append("  " + a.display_name)
	var t := tags()
	if not t.is_empty():
		lines.append("  tags: " + ", ".join(t))
	return "\n".join(lines)
