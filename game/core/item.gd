class_name Item
extends RefCounted

## A generated piece of gear.
##
## Gear is deliberately *build-defining rather than power-defining*: its numbers
## live in the flat/increased buckets, which sum and therefore flatten out, and
## its real leverage is the tags it grants, which decide what boons a run can
## even offer. Boons own the multiplicative bucket and so own the power curve.
## See core/damage.gd for why that split holds.

## Ordered by scarcity, not by power. SET sits above RARE because a set piece is
## the rarer drop, while being deliberately *weaker* than a rare on its own — the
## payoff arrives only once enough of the set is worn. Reading this ladder as a
## power ranking is the mistake the design depends on nobody making; see
## core/unique_pool.gd.
enum Rarity { NORMAL, MAGIC, RARE, SET, UNIQUE }

## What difficulty pass a base belongs to. The same base returns each pass as a
## strictly better version of itself with one more socket available, which is
## Diablo II's Normal / Exceptional / Elite ladder and the reason the difficulty
## axis exists at all. See docs/difficulty-and-loot.md.
enum Tier { PLAIN, EXCEPTIONAL, ELITE }

const TIER_NAMES := {
	Tier.PLAIN: "Plain",
	Tier.EXCEPTIONAL: "Exceptional",
	Tier.ELITE: "Elite",
}

## The earliest difficulty pass a tier drops in, 1-based to match
## Progression.difficulty_of_depth rather than the Difficulty enum's 0-based
## ordinals — every other depth-facing number in the codebase counts from one.
const TIER_MIN_DIFFICULTY := {
	Tier.PLAIN: 1,
	Tier.EXCEPTIONAL: 2,
	Tier.ELITE: 3,
}

## The socket ceiling each tier allows.
##
## This table is the entire point of the tier ladder: an inscription needs a
## vessel with exactly as many sockets as it has sigils, so a three-sigil word
## cannot be assembled before Nightmare and a four-sigil one not before Hell.
## Depth gates the component, where previously only luck did — which is what the
## acquisition simulator said was wrong with the chase.
const TIER_MAX_SOCKETS := {
	Tier.PLAIN: 2,
	Tier.EXCEPTIONAL: 3,
	Tier.ELITE: 4,
}

const RARITY_NAMES := {
	Rarity.NORMAL: "Normal",
	Rarity.MAGIC: "Magic",
	Rarity.RARE: "Rare",
	Rarity.SET: "Set",
	Rarity.UNIQUE: "Unique",
}

## How many modifier lines each rarity carries, as [min, max].
##
## The rolled rarities roll a count inside their span. The named ones do not roll
## at all — a unique's lines are fixed content — so for SET and UNIQUE this is
## the budget data/uniques.json must fall inside, and tests/test_items.gd checks
## the content against it. A unique gets a rare's line count, never more: it is
## meant to be a rare that always rolled perfectly, not a bigger thing than a
## rare. A set piece gets less than a rare, because a set is weak alone and pays
## out only when it is assembled.
const AFFIX_COUNTS := {
	Rarity.NORMAL: [0, 0],
	Rarity.MAGIC: [1, 2],
	Rarity.RARE: [3, 4],
	Rarity.SET: [1, 2],
	Rarity.UNIQUE: [3, 4],
}

var base_name: String = "Item"
var slot: String = "weapon"
var rarity: Rarity = Rarity.NORMAL
var tier: Tier = Tier.PLAIN
var ilvl: int = 1
var affixes: Array = []  # of Affix.Rolled

## Modifiers inherent to the base type, before any affix rolls.
var implicit: Dictionary = {}

## The name of the unique or set piece this drop is; empty for a rolled item.
##
## A named item is fixed content rather than a roll, so this — not the base — is
## what it is called, and display_name() shows it in place of the generated name.
## The base is still worth showing, but as provenance rather than identity: a
## named item binds to a slot and is stamped onto whatever base dropped, so the
## same unique is found on a better base each difficulty pass.
var unique_name: String = ""

## The set this piece belongs to; empty for everything else.
##
## Carried on the item rather than looked up from the content table so that "how
## many pieces am I wearing" is answerable from a loadout alone — see
## UniquePool.worn_counts, which is where that question is actually asked.
var set_id: String = ""

## Sockets, and what is currently in them.
##
## Only unaffixed items get sockets, which inverts the usual loot instinct: an
## empty three-socket vessel is one of the most valuable things that can drop,
## because it is the only thing a three-sigil inscription can be built in. That
## inversion is a large part of what made D2's economy interesting.
##
## "Plain" is unfortunately overloaded and the two senses are independent: this
## rule is about *rarity* (Rarity.NORMAL, no affixes), while Tier.PLAIN is about
## the *base* and its difficulty pass. A drop needs both to be a three-socket
## vessel — Normal rarity for sockets at all, exceptional-or-better base for the
## third one.
var sockets: int = 0
var socketed: Array = []  # of Sigil, in socket order
var inscription: Inscription = null


## Read a tier out of its JSON spelling.
##
## Unknown spellings fall back to PLAIN rather than erroring, so a typo in the
## content file costs the player nothing worse than a base that drops one pass
## earlier than intended — and tests/test_items.gd catches it either way.
static func tier_from_id(id: String) -> Tier:
	if id == "exceptional":
		return Tier.EXCEPTIONAL
	if id == "elite":
		return Tier.ELITE
	return Tier.PLAIN


## The earliest difficulty pass this tier can drop in, 1-based.
static func min_difficulty(t: Tier) -> int:
	return int(TIER_MIN_DIFFICULTY.get(t, 1))


static func max_sockets(t: Tier) -> int:
	return int(TIER_MAX_SOCKETS.get(t, TIER_MAX_SOCKETS[Tier.PLAIN]))


## An unaffixed item with sockets and nothing in them — the only shape of item the
## Reliquary will accept. See core/reliquary.gd for why that restriction is the
## load-bearing rule of the whole persistence design.
func is_empty_vessel() -> bool:
	return sockets > 0 and socketed.is_empty() and affixes.is_empty()


func is_inscribed() -> bool:
	return inscription != null


## A unique or a set piece — fixed content rather than a roll. The distinction
## the Reliquary banks on: a named item is the same item every time, so keeping
## one is a choice about which item you want rather than which roll you got.
func is_named() -> bool:
	return unique_name != ""


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


## Re-check whether the current sequence forms an inscription.
##
## The vessel must have exactly as many sockets as the recipe has sigils — a
## three-socket vessel cannot carry a two-sigil word. That is D2's rule and it is
## what keeps small vessels worth banking.
func reappraise(book: InscriptionBook) -> void:
	inscription = book.match_pattern(socketed_ids(), slot, sockets)


func display_name() -> String:
	if inscription != null:
		return "%s %s" % [inscription.display_name, base_name]
	# A named item is simply its name. "Unique Falchion" would throw away the one
	# thing uniques and sets have that a generated item cannot: being the same
	# item every time, and therefore worth telling someone about.
	if unique_name != "":
		return unique_name
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
