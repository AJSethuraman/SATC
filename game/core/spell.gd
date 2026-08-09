class_name Spell
extends RefCounted

## A castable ability, loaded from data/spells.json.
##
## This is the piece the prototype was missing. Diablo II does not feel like
## Diablo II because of its loot tables — it feels that way because you press a
## button and a Blizzard happens. A single melee swing that boons make bigger is
## a Hades combat model wearing ARPG numbers; a spell you spend a resource on,
## at a rate you can improve, is the ARPG itself.
##
## Damage is expressed as a multiplier on the caster's stat block rather than as
## its own numbers, so every affix, sigil, inscription and boon already built
## flows into every spell for free. A spell decides *shape and cost*; core/damage
## still decides how much.

enum Shape { PROJECTILE, NOVA }

const SHAPE_NAMES := {
	Shape.PROJECTILE: "projectile",
	Shape.NOVA: "nova",
}

var id: String = ""
var display_name: String = ""
## Which of the three trees this belongs to: "fire", "cold" or "lightning".
var school: String = "fire"
var description: String = ""
var shape: Shape = Shape.PROJECTILE

## The school this spell belongs to, and the damage type it deals regardless of
## what the caster is wearing.
##
## This is the change that makes a Sorceress possible. Until now a spell scaled
## the caster's own weapon split, which is physical by default — so an
## "Emberbolt" dealt physical damage and every resistance in the game was
## decorative. A Frozen Orb is cold because it is a Frozen Orb.
var element: int = Damage.Type.FIRE

## Asymmetric roll multiplier, low and high.
##
## Diablo II's lightning spells roll from 1 to a very large number: Chain
## Lightning at high level might read "1-500", and the average is nowhere near
## the middle of the bar you are reading. That variance is the identity of the
## school — lightning is the gamble, fire is steady, cold is steady but slows.
## Defaults to no variance at all, so only spells that opt in are noisy.
var roll_low: float = 1.0
var roll_high: float = 1.0

## Mana spent per cast. Zero would make the resource decorative.
var cost: float = 0.0
## Seconds between casts before cast_speed is applied.
var base_cast_time: float = 0.4
## Extra seconds this specific spell must wait, independent of cast speed. The
## heavy skill needs a floor that attack speed cannot erase.
var cooldown: float = 0.0

## Multiplier on the caster's resolved hit.
var damage_scale: float = 1.0

## PROJECTILE: metres per second, and how many bodies it passes through.
var speed: float = 22.0
var pierce: int = 0
## NOVA: radius in metres.
var radius: float = 4.5

## Lifetime in seconds, so nothing lives forever if it misses.
var lifetime: float = 2.0


static func from_dict(d: Dictionary) -> Spell:
	var s := Spell.new()
	s.id = str(d.get("id", ""))
	s.display_name = str(d.get("name", s.id))
	s.school = str(d.get("school", "fire"))
	s.description = str(d.get("description", ""))
	s.shape = Shape.NOVA if str(d.get("shape", "projectile")) == "nova" else Shape.PROJECTILE
	s.element = Damage.type_from_name(str(d.get("element", "fire")))
	s.roll_low = float(d.get("roll_low", 1.0))
	s.roll_high = float(d.get("roll_high", 1.0))
	s.cost = float(d.get("cost", 0.0))
	s.base_cast_time = float(d.get("cast_time", 0.4))
	s.cooldown = float(d.get("cooldown", 0.0))
	s.damage_scale = float(d.get("damage_scale", 1.0))
	s.speed = float(d.get("speed", 22.0))
	s.pierce = int(d.get("pierce", 0))
	s.radius = float(d.get("radius", 4.5))
	s.lifetime = float(d.get("lifetime", 2.0))
	return s


## Seconds between casts for a given caster. Faster casting shortens the gap but
## can never drive it to zero, which is what stops a cast-speed stacking build
## from becoming a continuous beam.
func cast_time(stats: StatBlock) -> float:
	return maxf(0.05, base_cast_time / maxf(0.1, stats.cast_speed))


func can_afford(mana: float) -> bool:
	return mana >= cost


## The damage split to resolve this spell with: all of its own element.
func split() -> Dictionary:
	return {element: 1.0}


## One roll of this spell's variance. Averages 1.0 when roll_low and roll_high
## are symmetric about it, so widening the spread makes a spell swingier without
## quietly making it stronger.
func roll_variance(rng: Rng) -> float:
	if is_equal_approx(roll_low, roll_high):
		return roll_low
	return rng.randf_range(roll_low, roll_high)


## Every spell of one school, so a run can be handed a complete kit.
static func of_school(all: Array, name: String) -> Array:
	var out: Array = []
	for s in all:
		var spell := s as Spell
		if spell != null and spell.school == name:
			out.append(spell)
	return out


static func from_json(path: String) -> Array:
	var f := FileAccess.open(path, FileAccess.READ)
	assert(f != null, "Spell: cannot open %s" % path)
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	assert(parsed is Dictionary, "Spell: %s must contain a JSON object" % path)

	var out: Array = []
	for d in parsed.get("spells", []):
		out.append(Spell.from_dict(d))
	assert(not out.is_empty(), "Spell: no spells in %s" % path)
	return out
