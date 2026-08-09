class_name Progression
extends RefCounted

## The shape of a run: acts made of rooms, rather than a flat stack of floors.
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
## Ashfall room is a full arena clear rather than a Hades chamber's handful of
## bodies — the same wall-clock, fewer doors.
##
## Everything here is static and free of scene state, so the balance simulator
## walks exactly the structure the game does.

enum RoomKind {
	COMBAT,
	## No fight. Heal, and the one place in a run you may bank to the reliquary.
	RESPITE,
	## The act boss. One body worth the whole act's tension.
	BOSS,
}

## What a room hands over when it is cleared. Combat rooms alternate rather
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

const ROOMS_PER_ACT := 8
const ACTS := 4
const RESPITE_ROOM := 4
const BOSS_ROOM := ROOMS_PER_ACT

## Flavour, but load-bearing flavour: "Act II — The Sunken Works, room 3 of 8"
## tells you where you are in a way "Floor 11" never did.
const ACT_NAMES: Array[String] = [
	"The Cinderwaste",
	"The Sunken Works",
	"The Glass Reach",
	"Ashfall",
]


static func total_rooms() -> int:
	return ACTS * ROOMS_PER_ACT


## Rooms cleared before this one, across the whole run. The single number every
## scaling curve is expressed in, so difficulty never depends on how the run is
## chopped into acts.
static func depth(act: int, room: int) -> int:
	return (act - 1) * ROOMS_PER_ACT + room


## Which act a run is in, given how many rooms deep it has got. The inverse of
## depth(), and the reason scaling can be written against one number.
static func act_of_depth(d: int) -> int:
	return (maxi(1, d) - 1) / ROOMS_PER_ACT + 1


static func kind_of(room: int) -> RoomKind:
	if room == BOSS_ROOM:
		return RoomKind.BOSS
	if room == RESPITE_ROOM:
		return RoomKind.RESPITE
	return RoomKind.COMBAT


## The act's payout rhythm, room by room. Fixed rather than rolled, so a player
## can see two rooms ahead and decide whether to push on at low health for the
## thing they actually need — the only interesting decision a linear act can
## offer without a door-choice UI.
##
## Spelled out as a table rather than derived from room parity, because parity
## lands four items against two blessings once the respite and boss rooms are
## carved out. Gear and boons gate each other (an item's tags widen the boon
## pool), so an act that pays lopsidedly in one currency starves the other.
const REWARD_BY_ROOM: Array[Reward] = [
	Reward.ITEM,
	Reward.BOON,
	Reward.ITEM,
	Reward.NONE,  # respite
	Reward.BOON,
	Reward.ITEM,
	Reward.BOON,
	Reward.ACT_PRIZE,  # boss
]


static func reward_of(room: int) -> Reward:
	var i := clampi(room - 1, 0, REWARD_BY_ROOM.size() - 1)
	return REWARD_BY_ROOM[i]


## Bodies in a combat room. Grows across acts rather than across rooms: within
## an act the pressure should come from what the enemies are, not from there
## being more of them each time.
static func enemy_count(act: int, room: int) -> int:
	match kind_of(room):
		RoomKind.RESPITE:
			return 0
		RoomKind.BOSS:
			# The boss plus a thin escort. Enough that positioning still matters,
			# few enough that the fight reads as being about the one body.
			return 3
		_:
			return 6 + act


## Is this room the act's elite? One per act, two rooms before the boss, so an
## act has a recognisable rise rather than a flat run of identical fights.
static func has_elite(room: int) -> bool:
	return room == BOSS_ROOM - 2


static func act_name(act: int) -> String:
	var i := clampi(act - 1, 0, ACT_NAMES.size() - 1)
	return ACT_NAMES[i]


## Roman numerals, because "Act 2" reads as a data field and "Act II" reads as
## a place. Four acts, so a table is honest and a general algorithm is not.
static func act_label(act: int) -> String:
	var numerals: Array[String] = ["I", "II", "III", "IV"]
	var i := clampi(act - 1, 0, numerals.size() - 1)
	return "Act %s — %s" % [numerals[i], act_name(act)]
