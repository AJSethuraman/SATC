class_name Progression
extends RefCounted

## The shape of a run: acts made of areas, rather than a flat stack of floors.
##
## The prototype's original unit was the "floor" — one arena, one clear, one
## item, one boon, repeat. That is a Hades *chamber* wearing the name of a
## Diablo *act*, and it is why the run had no shape: every encounter was the
## same size, worth the same reward, with nothing to arrive at.
##
## Both reference games agree on the real unit. Hades' Tartarus is 15 chambers
## ending at Megaera, Asphodel 10 and Elysium 11; Diablo II gives each act nine
## waypoints (Act IV excepted, at three) before its act boss. So an act is
## somewhere between eight and fifteen discrete spaces, a mix of kinds, ending
## in a named fight. Eight is the low end of that range, chosen because an
## Ashfall area is a full arena clear rather than a Hades chamber's handful of
## bodies — the same wall-clock, fewer doors.
##
## Everything here is static and free of scene state, so the balance simulator
## walks exactly the structure the game does.

enum AreaKind {
	COMBAT,
	## No fight. Heal, and the one place in a run you may bank to the reliquary.
	RESPITE,
	## The act boss. One body worth the whole act's tension.
	BOSS,
}

## What an area hands over when it is cleared. Combat areas alternate rather
## than granting both: the old floor gave an item *and* a boon every single
## clear, which made power arrive faster than the run could pace it. There are
## eight times as many encounters now, so each one is worth proportionally less.
enum Reward {
	NONE,
	ITEM,
	BOON,
	## Boss only: an item rolled deeper than the act would normally offer, plus
	## a boon. Arriving somewhere should pay differently from passing through.
	ACT_PRIZE,
}

## Difficulty passes. A run walks every act three times, harder each pass — the
## same places, not new ones, which is why this is an axis rather than more acts
## bolted on the end. See docs/difficulty-and-loot.md.
##
## The names are Diablo II's because they are instantly legible. Nothing
## structural depends on them.
enum Difficulty { NORMAL, NIGHTMARE, HELL }

const DIFFICULTY_NAMES: Array[String] = ["Normal", "Nightmare", "Hell"]
const DIFFICULTIES := 3

const AREAS_PER_ACT := 8
const ACTS := 5
const RESPITE_AREA := 4
const BOSS_AREA := AREAS_PER_ACT

## The region each act crosses.
const ACT_NAMES: Array[String] = [
	"The Cinderwaste",
	"The Sunken Works",
	"The Glass Reach",
	"The Rive",
	"Ashfall",
]

## Every area, by name.
##
## This is the whole reason the unit is called an area rather than a floor.
## "Floor 11" is a coordinate: it tells you how far you have counted, and
## nothing else. Diablo II never says floor — you are in the Blood Moor, then
## the Cold Plains, then the Stony Field, and the names are how you know both
## where you are and that you are going somewhere. A numbered stack of identical
## rungs cannot do that no matter how many of them there are.
##
## Ordered to describe a crossing: each act opens at its edge, passes its
## respite, and arrives somewhere named after the act itself.
const AREA_NAMES := [
	[
		"The Ashen Verge",
		"Cold Kilns",
		"The Slagfields",
		"Emberwatch",  # respite
		"The Clinker Road",
		"Bonemeal Yard",  # elite
		"The Last Furnace",
		"The Great Kiln",  # boss
	],
	[
		"The Drowned Gate",
		"Pumphouse Nine",
		"The Silt Galleries",
		"The Dry Dock",
		"Turbine Hollow",
		"The Weir",
		"The Black Sluice",
		"The Deep Works",
	],
	[
		"The Fulgurite Flats",
		"The Shivering Span",
		"Mirrorscour",
		"The Lens Camp",
		"The Singing Dunes",
		"Cullet Field",
		"The Annealing Walk",
		"The Furnace Heart",
	],
	[
		"The Split Stair",
		"Hangman's Ledge",
		"The Undercut",
		"Ropewalk",
		"The Falling Dark",
		"Gravewater",
		"The Long Drop",
		"The Rive",
	],
	[
		"The Grey Descent",
		"Cinderfall",
		"The Quiet Mile",
		"Last Light",
		"The Unmaking",
		"The Choir of Ash",
		"Under the Fall",
		"Ashfall",
	],
]


## Areas in one pass through every act.
static func areas_per_difficulty() -> int:
	return ACTS * AREAS_PER_ACT


static func total_areas() -> int:
	return DIFFICULTIES * areas_per_difficulty()


## Areas cleared before this one, across the whole run. The single number every
## scaling curve is expressed in, so difficulty never depends on how the run is
## chopped into passes, acts and areas.
static func depth(difficulty: int, act: int, area: int) -> int:
	return ((difficulty - 1) * ACTS + (act - 1)) * AREAS_PER_ACT + area


## Which difficulty pass a depth falls in.
static func difficulty_of_depth(d: int) -> int:
	return (maxi(1, d) - 1) / areas_per_difficulty() + 1


## Which act *within its pass*, so the Cinderwaste is act 1 in Hell exactly as
## it is in Normal. Together with difficulty_of_depth this inverts depth().
static func act_of_depth(d: int) -> int:
	return ((maxi(1, d) - 1) / AREAS_PER_ACT) % ACTS + 1


static func difficulty_name(difficulty: int) -> String:
	var i := clampi(difficulty - 1, 0, DIFFICULTY_NAMES.size() - 1)
	return DIFFICULTY_NAMES[i]


static func kind_of(area: int) -> AreaKind:
	if area == BOSS_AREA:
		return AreaKind.BOSS
	if area == RESPITE_AREA:
		return AreaKind.RESPITE
	return AreaKind.COMBAT


## The act's payout rhythm, area by area. Fixed rather than rolled, so a player
## can see two areas ahead and decide whether to push on at low health for the
## thing they actually need — the only interesting decision a linear act can
## offer without a door-choice UI.
##
## Spelled out as a table rather than derived from area parity, because parity
## lands four items against two blessings once the respite and boss areas are
## carved out. Gear and boons gate each other (an item's tags widen the boon
## pool), so an act that pays lopsidedly in one currency starves the other.
const REWARD_BY_AREA: Array[Reward] = [
	Reward.ITEM,
	Reward.BOON,
	Reward.ITEM,
	Reward.NONE,  # respite
	Reward.BOON,
	Reward.ITEM,
	Reward.BOON,
	Reward.ACT_PRIZE,  # boss
]


static func reward_of(area: int) -> Reward:
	var i := clampi(area - 1, 0, REWARD_BY_AREA.size() - 1)
	return REWARD_BY_AREA[i]


## Bodies in a combat area. Grows across acts rather than across areas: within
## an act the pressure should come from what the enemies are, not from there
## being more of them each time.
##
## Density went back up once trash health was halved and the attack-token pool
## arrived. Those two changes are what make a crowd affordable: bodies die in
## under a second, and only Feel.ATTACK_TOKENS of them may be mid-swing at once,
## so eight enemies are eight things to position against and two things to
## dodge. Before both, five was already the ceiling — an act-I area cost 57% of
## a health bar and the median run died in area 2, decided before any gear had
## arrived to decide it with.
static func enemy_count(act: int, area: int) -> int:
	match kind_of(area):
		AreaKind.RESPITE:
			return 0
		AreaKind.BOSS:
			# The boss plus a thin escort. Enough that positioning still matters,
			# few enough that the fight reads as being about the one body.
			return 3
		_:
			return 6 + act * 2


## Is this area the act's elite? One per act, two areas before the boss, so an
## act has a recognisable rise rather than a flat run of identical fights.
static func has_elite(area: int) -> bool:
	return area == BOSS_AREA - 2


## Where you are, in words. Typed through a local rather than returned straight
## out of the nested constant, because a nested Array's elements are Variant and
## the parser will not infer a String out of one.
static func area_name(act: int, area: int) -> String:
	var a := clampi(act - 1, 0, AREA_NAMES.size() - 1)
	var names: Array = AREA_NAMES[a]
	var i := clampi(area - 1, 0, names.size() - 1)
	return str(names[i])


static func act_name(act: int) -> String:
	var i := clampi(act - 1, 0, ACT_NAMES.size() - 1)
	return ACT_NAMES[i]


## Roman numerals, because "Act 2" reads as a data field and "Act II" reads as
## a chapter. Four acts, so a table is honest and a general algorithm is not.
const ACT_NUMERALS: Array[String] = ["I", "II", "III", "IV"]


static func act_numeral(act: int) -> String:
	var i := clampi(act - 1, 0, ACT_NUMERALS.size() - 1)
	return ACT_NUMERALS[i]


static func act_label(act: int) -> String:
	return "Act %s — %s" % [act_numeral(act), act_name(act)]


## The full address of a place, pass included. "Act II — The Sunken Works" is
## three different fights depending on which pass you are on, and the label has
## to say which or the HUD is lying by omission.
static func full_label(difficulty: int, act: int) -> String:
	return "%s · %s" % [difficulty_name(difficulty), act_label(act)]
