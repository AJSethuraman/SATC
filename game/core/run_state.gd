class_name RunState
extends RefCounted

## Everything that defines one attempt: the seed, how deep it got, what it is
## wearing, and what it has been blessed with.
##
## Nothing here touches the scene tree, so a run can be played by a human or
## fast-forwarded ten thousand times by sim/balance_sim.gd through exactly the
## same code path.

## Salts for derived RNG streams. Each subsystem gets its own stream so that
## adding a roll in one place does not shift results everywhere else.
const STREAM_LOOT := 1
const STREAM_BOONS := 2
const STREAM_COMBAT := 3

var seed_value: int = 0
var floor_number: int = 1
var health: float = 100.0

var gear: Dictionary = {}  # slot -> Item
var boons: Array = []  # of Boon.Rolled

var loot_rng: Rng
var boon_rng: Rng
var combat_rng: Rng


static func start(seed_v: int) -> RunState:
	var r := RunState.new()
	r.seed_value = seed_v
	var root := Rng.new(seed_v)
	r.loot_rng = root.derive(STREAM_LOOT)
	r.boon_rng = root.derive(STREAM_BOONS)
	r.combat_rng = root.derive(STREAM_COMBAT)
	r.health = r.build_stats().max_health
	return r


## The player's base line before any gear or boons. Deliberately unarmed-weak:
## the whole power curve is supposed to come from what the run gives you.
static func base_stats() -> StatBlock:
	var s := StatBlock.new()
	s.weapon_min = 6.0
	s.weapon_max = 10.0
	s.weapon_split = {Damage.Type.PHYSICAL: 1.0}
	s.crit_chance = 0.05
	s.crit_mult = 1.5
	s.max_health = 100.0
	s.move_speed = 220.0
	return s


func gear_tags() -> Array[String]:
	var out: Array[String] = []
	for slot in gear:
		for t in gear[slot].tags():
			if not out.has(t):
				out.append(t)
	return out


func boon_tags() -> Array[String]:
	var out: Array[String] = []
	for b in boons:
		for t in b.tags:
			if not out.has(t):
				out.append(t)
	return out


## Everything the boon pool gates on: what you are wearing plus what you have
## already committed to. Gear remains the wider source; entry boons exist so a
## run is never locked out of every god by an unlucky drop sequence.
func active_tags() -> Array[String]:
	var out := gear_tags()
	for t in boon_tags():
		if not out.has(t):
			out.append(t)
	return out


func owned_boon_ids() -> Array:
	return boons.map(func(b): return b.id)


func owned_boon_groups() -> Array:
	return boons.map(func(b): return b.group)


## Resolve base + gear + boons into the stat block combat actually uses.
## Recomputed from scratch rather than mutated in place, so there is no way for
## an unequip to leave a stat behind.
func build_stats() -> StatBlock:
	var s := RunState.base_stats()
	for slot in gear:
		gear[slot].apply_to(s)
	for b in boons:
		s.apply_all(b.mods)
	return s


func equip(item: Item) -> void:
	gear[item.slot] = item


func take_boon(b: Boon.Rolled) -> void:
	boons.append(b)


## Enemy stat line for a given depth.
##
## Health climbs faster than damage on purpose: deeper floors should test
## whether your build actually scales, not whether you can survive a one-shot.
## The exponents here are guesses — sim/balance_sim.gd exists to check them.
static func enemy_for_floor(n: int, elite: bool = false) -> StatBlock:
	var e := StatBlock.new()
	var depth := maxf(0.0, float(n - 1))

	e.max_health = 40.0 * pow(1.28, depth)
	e.weapon_min = 5.0 * pow(1.16, depth)
	e.weapon_max = 9.0 * pow(1.16, depth)
	e.weapon_split = {Damage.Type.PHYSICAL: 1.0}
	e.armor = 1.0 * depth
	e.move_speed = 150.0 + 4.0 * depth

	# Resistances phase in with depth so early floors do not punish a player for
	# picking the "wrong" element before they have any choice about it.
	var res := minf(0.4, 0.05 * depth)
	for t in Damage.Type.values():
		if t != Damage.Type.PHYSICAL:
			e.resistances[t] = res

	if elite:
		e.max_health *= 3.5
		e.weapon_min *= 1.4
		e.weapon_max *= 1.4
		e.armor *= 1.5

	return e


func advance_floor() -> void:
	floor_number += 1
