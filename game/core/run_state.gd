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
var difficulty_number: int = 1
var act_number: int = 1
var area_number: int = 1
var health: float = 100.0
## Which of the Sorceress' three trees this run was dealt. Set by the scene
## layer at run start; core/ only carries it so the HUD and the log agree.
var school: String = "fire"

var gear: Dictionary = {}  # slot -> Item
var boons: Array = []  # of Boon.Rolled

## The named-item table this run reads set bonuses from. Null means the shared
## one — see UniquePool.shared(); assign only to test against a specific table.
var uniques: UniquePool = null

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


## The damage type a school deals.
const SCHOOL_ELEMENT := {
	"fire": Damage.Type.FIRE,
	"cold": Damage.Type.COLD,
	"lightning": Damage.Type.LIGHTNING,
}


static func element_of(school_name: String) -> int:
	return SCHOOL_ELEMENT.get(school_name, Damage.Type.FIRE)


## The player's base line before any gear or boons. Deliberately unarmed-weak:
## the whole power curve is supposed to come from what the run gives you.
##
## The split is the run's element, not physical. That looks like a detail and is
## not: expected_hit() drives every "is this an upgrade?" decision the loot log
## and the balance simulator make, and while the base was physical those were
## all computed for a character who deals no physical damage at all. Enemy
## elemental resistances were invisible to them, and a `more.fire` boon looked
## worth exactly nothing. A caster's baseline is the element she casts.
static func base_stats(school_name: String = "fire") -> StatBlock:
	var s := StatBlock.new()
	s.weapon_min = 6.0
	s.weapon_max = 10.0
	s.weapon_split = {element_of(school_name): 1.0}
	s.crit_chance = 0.05
	s.crit_mult = 1.5
	s.max_health = 100.0
	s.move_speed = 220.0
	s.max_mana = 100.0
	s.mana_regen = 14.0
	s.cast_speed = 1.0
	return s


func unique_pool() -> UniquePool:
	return uniques if uniques != null else UniquePool.shared()


func gear_tags() -> Array[String]:
	var out: Array[String] = []
	for slot in gear:
		for t in gear[slot].tags():
			if not out.has(t):
				out.append(t)
	# A set bonus that grants a tag widens the boon pool exactly as an affix that
	# grants one does. Leaving it out would have made the tag a stat-sheet line
	# with no consequence, which is not what a tag is for anywhere else.
	for t in unique_pool().set_bonus_tags(gear):
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
	return _stats_from(gear, boons)


## The stat block for an arbitrary gear/boon combination.
##
## Split out of build_stats so that "what would this be worth if I took it?" is
## answered by the same code as "what am I actually fighting with". Anything
## that hand-rolls a hypothetical instead will drift — and did: the balance
## simulator built its own trial block, which meant it evaluated every candidate
## without synergies and could not see the mechanic at all.
func _stats_from(gear_set: Dictionary, boon_set: Array) -> StatBlock:
	var s := RunState.base_stats(school)
	for slot in gear_set:
		gear_set[slot].apply_to(s)
	# Set bonuses are a consequence of what is worn, so they land with the gear
	# and — because this is the only pipeline — they land in the hypotheticals
	# too. That is the part that matters: without it, the second piece of a set
	# reads as a downgrade in stats_with_item() and the loot log would tell the
	# player not to complete the set.
	unique_pool().apply_set_bonuses(gear_set, s)
	for b in boon_set:
		s.apply_all(b.mods)
	# Synergies last, and computed against the finished set rather than folded
	# in as each boon is taken — otherwise the order you were offered things in
	# would change what they are worth, and two identical builds could disagree.
	for b in boon_set:
		s.apply_all(b.synergy_with(boon_set))
	return s


## Stats as they would be with this boon taken. Includes what the boon does to
## every synergy already in the build, and what the build does to its synergy —
## which is the whole reason a committed pick is worth more than its own numbers.
func stats_with_boon(candidate: Boon.Rolled) -> StatBlock:
	var hypothetical := boons.duplicate()
	hypothetical.append(candidate)
	return _stats_from(gear, hypothetical)


## Stats as they would be with this item equipped, replacing whatever occupies
## its slot.
func stats_with_item(drop: Item) -> StatBlock:
	var hypothetical := gear.duplicate()
	hypothetical[drop.slot] = drop
	return _stats_from(hypothetical, boons)


## Would equipping this raise expected damage against a same-depth enemy?
##
## Lives here rather than in whichever caller needs it because three of them do
## — the balance simulator, the scene's drop handler, and the demo's warm-up —
## and the first version of it lived in the simulator, which is how the scene
## ended up with no upgrade test at all and simply wore whatever fell last.
## Judged through the real stat pipeline, so an item trading damage for
## resistance is weighed the way combat will actually weigh it.
func is_upgrade(drop: Item) -> bool:
	var enemy := RunState.enemy_for_depth(depth())
	return stats_with_item(drop).expected_hit(enemy) > build_stats().expected_hit(enemy)


## Stats as they would be with this slot empty — "what is this item worth?" for
## something already worn, which is a different question from stats_with_item
## and the only honest one to ask about gear that is already on.
func stats_without(slot: String) -> StatBlock:
	var hypothetical := gear.duplicate()
	hypothetical.erase(slot)
	return _stats_from(hypothetical, boons)


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
## Retuned for a 120-area run. The old rates were set for 32 and compound to
## absurdity over four times the distance — 1.09 per area across 119 of them is
## a factor of twenty-eight thousand. Target is roughly 60x health and 8x damage
## from the first area of Normal to the last of Hell.
## Enemy health follows the player's power curve, which is not a straight line.
##
## Measured, and the measurement is the whole reason these numbers changed. The
## balance simulator reports average seconds-to-kill by depth, and it read 1.6s
## in area 1, 0.3s by area 17, and then 0.1s from area 33 to area 77 — a fifth
## of one attack cycle, for nearly half the game. Working backwards from that
## curve, enemy health grew about 12x between areas 1 and 77 while player damage
## grew about 190x.
##
## No single boon is responsible; that was the first suspicion and it was wrong.
## The player's damage is the product of four independent axes — multiplicative
## boons (~8x), additive increases (~5x), flat damage from gear (~4x), and crit
## — each defensible alone and jointly enormous. Stacking like that is the point
## of the itemisation, so the enemy curve is what has to move.
##
## And it has to move in the right *shape*. The boon pool holds thirty boons and
## a run is offered three or four an act, so somewhere around the eighth act
## there is nothing left to take and the build stops compounding; after that it
## grows only from gear. A single exponential fitted to the compounding phase
## makes the end of Hell absurd, and one fitted to the whole run leaves the
## middle at 0.1s. So there are two rates with a knee between them.
##
## The consequence to watch for: longer fights mean more time under fire, so
## this is a difficulty change as well as a pacing one, and the clear rate is
## expected to come down from the 103-of-120 median the simulator last reported.
const POWER_SATURATION_AREAS := 64.0
const AREA_HEALTH_GROWTH := 1.047
## After the knee, where only gear is still adding to the player's damage.
const LATE_HEALTH_GROWTH := 1.012
const AREA_DAMAGE_GROWTH := 1.0079
const ACT_HEALTH_STEP := 1.10
const ACT_DAMAGE_STEP := 1.04

## The step between difficulty passes.
##
## Deliberately much larger than an act boundary. The point of replaying the
## same five acts is that they are a different game the second time — Nightmare
## has to invalidate a Normal build outright, or a banked runeword carries all
## the way and the run collapses into "farm one good weapon" again. That failure
## mode is the reason the old reliquary refused to store finished items, and the
## difficulty step is what replaces the rule.
const DIFFICULTY_HEALTH_STEP := 2.0
const DIFFICULTY_DAMAGE_STEP := 1.35

## How fast enemy elemental resistance climbs, and where it stops.
##
## Named rather than inline because they are now a balance dial rather than
## flavour, and because a test that asserts on a literal has to be edited every
## time the dial moves — which teaches you to edit tests to match code instead
## of the other way round.
##
## Must stay at or under Damage.RESIST_CAP; past that the clamp silently eats
## the difference and raising the number does nothing at all.
const ENEMY_RESIST_PER_AREA := 0.026
const ENEMY_RESIST_MAX := 0.6


## How deep the run is, counted in areas cleared. Every curve is written against
## this rather than against act/area, so difficulty never depends on how the run
## happens to be chopped up.
func depth() -> int:
	return Progression.depth(difficulty_number, act_number, area_number)


## Enemy stat line at a given depth in areas.
static func enemy_for_depth(d: int, elite: bool = false) -> StatBlock:
	var e := StatBlock.new()
	var areas := maxf(0.0, float(d - 1))
	# Acts and passes *completed*, counted globally rather than within the pass.
	#
	# act_of_depth wraps — the Cinderwaste is act 1 in Hell exactly as in Normal —
	# so using it here would reset the act multiplier at every pass boundary and
	# Nightmare act I would land about where Normal act V did. The scaling curve
	# wants distance travelled; the labels want position.
	var acts_done := floorf(areas / float(Progression.AREAS_PER_ACT))
	var passes_done := floorf(areas / float(Progression.areas_per_difficulty()))

	# Trash dies fast and hits hard.
	#
	# The first full-act recording took about sixteen seconds an area, and almost
	# all of that was chipping: at 40 health against a starting hit of 6-10 a
	# single body took roughly three seconds to kill, five of them fifteen. That
	# is not what an ARPG feels like. Diablo and Hades both delete ordinary
	# enemies in well under a second and put the danger in *how many* arrive and
	# how hard they hit, not in how long each one survives.
	#
	# So health comes down and damage goes up. The product is deliberately close
	# to unchanged — an area should cost about the same health as before and take
	# half the time — which means this is a pacing change rather than a
	# difficulty one, and the simulator should show the clear rate roughly where
	# it was.
	# Two rates with a knee at POWER_SATURATION_AREAS — see the constant for the
	# measurement this shape came from.
	var compounding := minf(areas, POWER_SATURATION_AREAS)
	var after_knee := maxf(0.0, areas - POWER_SATURATION_AREAS)
	e.max_health = (
		22.0
		* pow(AREA_HEALTH_GROWTH, compounding)
		* pow(LATE_HEALTH_GROWTH, after_knee)
		* pow(ACT_HEALTH_STEP, acts_done)
		* pow(DIFFICULTY_HEALTH_STEP, passes_done)
	)
	var damage_scale := (
		pow(AREA_DAMAGE_GROWTH, areas)
		* pow(ACT_DAMAGE_STEP, acts_done)
		* pow(DIFFICULTY_DAMAGE_STEP, passes_done)
	)
	# Halved when kills stopped being instant, and the two numbers are bound
	# together rather than independently tuned. What a fight costs the player is
	# roughly its length times what is hitting them, so raising time-to-kill from
	# a tenth of a second to about one second raised the price of every area by
	# the same factor — the median run went from area 94 to area 7 on that change
	# alone. Enemy damage is the term that pays it back.
	#
	# "Trash dies fast and hits hard" survives as an intent; it just cannot mean
	# both at once at these magnitudes. Danger now comes from how many arrive and
	# from the telegraphed attacks worth dodging, not from chip damage taken
	# while chewing through health bars.
	e.weapon_min = 3.5 * damage_scale
	e.weapon_max = 6.0 * damage_scale
	e.weapon_split = {Damage.Type.PHYSICAL: 1.0}
	e.armor = 0.5 * areas
	# Kept just under the player's 220 at a full clear: enemies that outrun you
	# turn dashing from a decision into a tax.
	e.move_speed = 150.0 + 1.8 * areas

	# Resistances phase in with depth so early areas do not punish a player for
	# being dealt the "wrong" element before they have any say in it.
	#
	# They climb higher and faster than they used to, and that is a direct
	# consequence of the Sorceress. Every hit the player lands is now elemental,
	# where before the baseline was physical and these numbers were decorative —
	# so this is the only dial that pushes back on a caster at all. It is also
	# the dial Cold Mastery and the pierce stat are the answer to, which is the
	# shape Diablo II has: deep enemies resist your element, and the counterplay
	# is penetration rather than simply more damage.
	var res := minf(ENEMY_RESIST_MAX, ENEMY_RESIST_PER_AREA * areas)
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
static func boss_for_act(difficulty: int, act: int) -> StatBlock:
	var e := enemy_for_depth(Progression.depth(difficulty, act, Progression.BOSS_AREA))
	# Raised alongside the trash health cut so a boss stays a wall rather than
	# becoming another body: 6x of the old 40 was 240, 7x of 22 is 154, and the
	# fight would otherwise be over before it read as a fight.
	e.max_health *= 11.0
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
## Move to the next area, rolling into the next act and then the next difficulty
## pass. Returns false only at the very end of Hell — the one way to finish a run
## other than dying.
func advance_area() -> bool:
	if area_number < Progression.AREAS_PER_ACT:
		area_number += 1
		return true
	if act_number < Progression.ACTS:
		act_number += 1
		area_number = 1
		return true
	if difficulty_number >= Progression.DIFFICULTIES:
		return false
	difficulty_number += 1
	act_number = 1
	area_number = 1
	return true
