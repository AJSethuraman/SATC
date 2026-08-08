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

## Sockets, and what is currently in them.
##
## Only plain items get sockets, which inverts the usual loot instinct: an empty
## three-socket Normal vessel is one of the most valuable things that can drop,
## because it is the only thing a three-sigil inscription can be built in. That
## inversion is a large part of what made D2's economy interesting.
var sockets: int = 0
var socketed: Array = []  # of Sigil, in socket order
var inscription: Inscription = null


## A plain item with sockets and nothing in them — the only shape of item the
## Reliquary will accept. See core/reliquary.gd for why that restriction is the
## load-bearing rule of the whole persistence design.
func is_empty_vessel() -> bool:
	return sockets > 0 and socketed.is_empty() and affixes.is_empty()


func is_inscribed() -> bool:
	return inscription != null


func free_sockets() -> int:
	return sockets - socketed.size()


## Place a sigil in the next free socket. Order is preserved, because order is
## what distinguishes one inscription from another.
func insert(sigil: Sigil) -> bool:
	if free_sockets() <= 0:
		return false
	socketed.append(sigil)
	return true


func socketed_ids() -> Array:
	return socketed.map(func(s): return s.id)


## Re-check whether the current sequence forms an inscription. Called after every
## insert rather than only when full, so a two-sigil word in a three-socket
## vessel still resolves.
func reappraise(book: InscriptionBook) -> void:
	inscription = book.match_pattern(socketed_ids(), slot)


func display_name() -> String:
	if inscription != null:
		return "%s %s" % [inscription.display_name, base_name]
	if rarity == Rarity.NORMAL or affixes.is_empty():
		if sockets > 0:
			return "%s (%d)" % [base_name, sockets]
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
	if inscription != null:
		for t in inscription.grants_tags:
			if not out.has(t):
				out.append(t)
	return out


## Fold this item's implicit and rolled modifiers into a stat block.
##
## Socketed sigils contribute their own modifiers whether or not they form an
## inscription, so a combination that spells nothing is a weak item rather than
## a ruined one.
func apply_to(stats: StatBlock) -> void:
	stats.apply_all(implicit)
	for a in affixes:
		stats.apply_all(a.mods)
	for s in socketed:
		stats.apply_all(s.mods)
	if inscription != null:
		stats.apply_all(inscription.mods)
	stats.add_tags(tags())


func describe() -> String:
	var lines: Array[String] = ["%s (ilvl %d)" % [display_name(), ilvl]]
	for a in affixes:
		lines.append("  " + a.display_name)
	var t := tags()
	if not t.is_empty():
		lines.append("  tags: " + ", ".join(t))
	return "\n".join(lines)
