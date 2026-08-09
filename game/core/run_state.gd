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
## Where the run is, in Progression's terms. A run walks areas 1..8 of an act,
## then starts the next act's area 1 — see core/progression.gd for why the unit
## changed from a flat floor count.
var act_number: int = 1
var area_number: int = 1
var health: float = 100.0
## Which of the Sorceress' three trees this run was dealt. Set by the scene
## layer at run start; core/ only carries it so the HUD and the log agree.
var school: String = "fire"

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
	s.max_mana = 100.0
	s.mana_regen = 14.0
	s.cast_speed = 1.0
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


## Behaviour identifiers granted by inscriptions on equipped gear.
##
## This is where the `behaviour` vocabulary written into data/sigils.json ahead
## of time finally connects: the scene layer asks what the build does
## differently, without needing to know what an inscription is.
func active_behaviours() -> Array[String]:
	var out: Array[String] = []
	for slot in gear:
		var item: Item = gear[slot]
		if item.inscription != null and item.inscription.behaviour != "":
			if not out.has(item.inscription.behaviour):
				out.append(item.inscription.behaviour)
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


## Compounding rates for enemy scaling, per area cleared and per act entered.
##
## Health climbs faster than damage on purpose: going deeper should test whether
## your build actually scales, not whether you can survive a one-shot.
##
## The old constants were per *floor* and there were fifteen of them. A run is
## now thirty-two areas, so applying the same rates per area would have
## compounded damage nearly tenfold. These are the per-area equivalents of a
## gentler curve: about 27x health and 3x damage across a full clear, against
## the ~33x and ~3.8x the floor model reached — and the damage figure is
## deliberately the one that came down, because that is the term the balance
## simulator identified as outrunning the player. Defensive scaling arrives in
## flat lumps from gear and boons; enemy damage compounds, and if it compounds
## faster than the lumps arrive then no choice the player makes matters. That
## showed up measurably: random boon picks performed as well as greedy ones.
##
## The act steps are separate from the area rates so an act boundary is a felt
## event rather than a smooth ramp — arriving in the Sunken Works should be
## noticeably worse than leaving the Cinderwaste.
const AREA_HEALTH_GROWTH := 1.09
const AREA_DAMAGE_GROWTH := 1.028
const ACT_HEALTH_STEP := 1.25
const ACT_DAMAGE_STEP := 1.10


## How deep the run is, counted in areas cleared. Every curve is written against
## this rather than against act/area, so difficulty never depends on how the run
## happens to be chopped up.
func depth() -> int:
	return Progression.depth(act_number, area_number)


## Enemy stat line at a given depth in areas.
static func enemy_for_depth(d: int, elite: bool = false) -> StatBlock:
	var e := StatBlock.new()
	var areas := maxf(0.0, float(d - 1))
	var acts_done := float(Progression.act_of_depth(d) - 1)

	e.max_health = 40.0 * pow(AREA_HEALTH_GROWTH, areas) * pow(ACT_HEALTH_STEP, acts_done)
	var damage_scale := pow(AREA_DAMAGE_GROWTH, areas) * pow(ACT_DAMAGE_STEP, acts_done)
	e.weapon_min = 5.0 * damage_scale
	e.weapon_max = 9.0 * damage_scale
	e.weapon_split = {Damage.Type.PHYSICAL: 1.0}
	e.armor = 0.5 * areas
	# Kept just under the player's 220 at a full clear: enemies that outrun you
	# turn dashing from a decision into a tax.
	e.move_speed = 150.0 + 1.8 * areas

	# Resistances phase in with depth so early areas do not punish a player for
	# picking the "wrong" element before they have any choice about it.
	var res := minf(0.4, 0.018 * areas)
	for t in Damage.Type.values():
		if t != Damage.Type.PHYSICAL:
			e.resistances[t] = res

	if elite:
		e.max_health *= 3.5
		e.weapon_min *= 1.4
		e.weapon_max *= 1.4
		e.armor *= 1.5

	return e


## The act boss. Not an elite with a bigger multiplier bolted on: it has to
## survive long enough for the fight to have phases the player can read, while
## hitting hard enough that the act's whole build-up pays off.
##
## Six times health rather than nine: a boss is time on the clock, and every
## second of it is damage taken. Nine put the act-I boss beyond what three
## items and three boons can answer.
static func boss_for_act(act: int) -> StatBlock:
	var e := enemy_for_depth(Progression.depth(act, Progression.BOSS_AREA))
	e.max_health *= 6.0
	e.weapon_min *= 1.6
	e.weapon_max *= 1.6
	e.armor *= 1.5
	# Slower than its own escort. A boss that can chase you down removes the one
	# tool the player has for reading a long fight.
	e.move_speed *= 0.82
	return e


## Move to the next area, rolling into the next act after the boss. Returns
## false when the run has cleared the last act — the only way to finish one
## other than dying.
func advance_area() -> bool:
	if area_number < Progression.AREAS_PER_ACT:
		area_number += 1
		return true
	if act_number >= Progression.ACTS:
		return false
	act_number += 1
	area_number = 1
	return true
