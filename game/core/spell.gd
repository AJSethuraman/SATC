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
var description: String = ""
var shape: Shape = Shape.PROJECTILE

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
	s.description = str(d.get("description", ""))
	s.shape = Shape.NOVA if str(d.get("shape", "projectile")) == "nova" else Shape.PROJECTILE
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
