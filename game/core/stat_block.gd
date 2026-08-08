class_name StatBlock
extends RefCounted

## The mutable stat state of a combatant, plus the one grammar that affixes and
## boons both speak.
##
## Modifier keys (used verbatim in data/affixes.json and data/boons.json):
##
##   flat.<type>        add flat damage of that type          e.g. "flat.fire"
##   increased.<type>   add to the additive increased% bucket e.g. "increased.physical"
##   more               append a multiplicative modifier, all types  (boons only)
##   more.<type>        append a multiplicative modifier, one type   (boons only)
##   weapon_min         raise the low end of the weapon roll
##   weapon_max         raise the high end of the weapon roll
##   crit_chance        additive, 0..1
##   crit_mult          additive on top of the 1.0 base
##   resist.<type>      add resistance, 0..1 before clamping
##   armor              flat post-mitigation reduction
##   max_health
##   move_speed
##
## `<type>` is any name in Damage.TYPE_NAMES.

var weapon_min: float = 1.0
var weapon_max: float = 2.0

## Fraction of the base weapon roll dealt as each damage type. Should sum to
## 1.0; a weapon that converts damage shifts weight between entries.
var weapon_split: Dictionary = {Damage.Type.PHYSICAL: 1.0}

var flat_damage: Dictionary = {}
var increased_pct: Dictionary = {}

## Multiplicative modifiers that apply to every damage type.
var more_mults: Array[float] = []

## Multiplicative modifiers scoped to one damage type: Type -> Array[float].
## A fire multiplier on a build that deals no fire damage is worth exactly
## nothing, which is the point — it is what stops elemental boons from being
## universally correct picks.
var more_by_type: Dictionary = {}

var crit_chance: float = 0.05
var crit_mult: float = 1.5

var resistances: Dictionary = {}
var armor: float = 0.0

var max_health: float = 100.0
var move_speed: float = 220.0

## Tags contributed by gear. Boon pools filter on these — this is the seam that
## makes gear build-defining rather than just a pile of numbers.
var tags: Array[String] = []


func clone() -> StatBlock:
	var c := StatBlock.new()
	c.weapon_min = weapon_min
	c.weapon_max = weapon_max
	c.weapon_split = weapon_split.duplicate()
	c.flat_damage = flat_damage.duplicate()
	c.increased_pct = increased_pct.duplicate()
	c.more_mults = more_mults.duplicate()
	c.more_by_type = {}
	for t in more_by_type:
		c.more_by_type[t] = (more_by_type[t] as Array).duplicate()
	c.crit_chance = crit_chance
	c.crit_mult = crit_mult
	c.resistances = resistances.duplicate()
	c.armor = armor
	c.max_health = max_health
	c.move_speed = move_speed
	c.tags = tags.duplicate()
	return c


## Apply one modifier from the grammar above. Unknown keys are a hard error
## rather than a silent no-op, so a typo in the data files fails the test suite
## instead of quietly costing the player a stat.
func apply(key: String, value: float) -> void:
	if key.begins_with("flat."):
		var flat_type := Damage.type_from_name(key.substr(5))
		flat_damage[flat_type] = flat_damage.get(flat_type, 0.0) + value
	elif key.begins_with("increased."):
		var inc_type := Damage.type_from_name(key.substr(10))
		increased_pct[inc_type] = increased_pct.get(inc_type, 0.0) + value
	elif key.begins_with("resist."):
		var res_type := Damage.type_from_name(key.substr(7))
		resistances[res_type] = resistances.get(res_type, 0.0) + value
	elif key.begins_with("more."):
		var more_type := Damage.type_from_name(key.substr(5))
		if not more_by_type.has(more_type):
			more_by_type[more_type] = []
		(more_by_type[more_type] as Array).append(value)
	elif key == "more":
		more_mults.append(value)
	elif key == "weapon_min":
		weapon_min += value
	elif key == "weapon_max":
		weapon_max += value
	elif key == "crit_chance":
		crit_chance += value
	elif key == "crit_mult":
		crit_mult += value
	elif key == "armor":
		armor += value
	elif key == "max_health":
		max_health += value
	elif key == "move_speed":
		move_speed += value
	else:
		push_error("StatBlock.apply: unknown modifier key '%s'" % key)


func apply_all(mods: Dictionary) -> void:
	for k in mods:
		apply(str(k), float(mods[k]))


## Scalar modifier keys, i.e. everything that is not `<prefix>.<damage type>`.
const SCALAR_KEYS := [
	"more",
	"weapon_min",
	"weapon_max",
	"crit_chance",
	"crit_mult",
	"armor",
	"max_health",
	"move_speed",
]

const TYPED_PREFIXES := ["flat.", "increased.", "resist.", "more."]


## Product of every multiplicative modifier that applies to damage type `t` —
## the global ones and the ones scoped to that type.
func more_multiplier(t: int) -> float:
	var m := 1.0
	for v in more_mults:
		m *= 1.0 + v
	for v in more_by_type.get(t, []):
		m *= 1.0 + float(v)
	return m


## Whether `key` is part of the modifier grammar. Used by the data validation
## test so a typo in a JSON file fails the suite instead of silently costing the
## player a stat at runtime.
static func is_valid_key(key: String) -> bool:
	if SCALAR_KEYS.has(key):
		return true
	for p in TYPED_PREFIXES:
		if key.begins_with(p):
			return Damage.TYPE_NAMES.values().has(key.substr(p.length()))
	return false


func add_tags(new_tags: Array) -> void:
	for t in new_tags:
		var s := str(t)
		if not tags.has(s):
			tags.append(s)


## Average damage per hit against `defender`, computed analytically rather than
## sampled. The balance simulator uses this for fast build comparison; combat
## itself always goes through Damage.resolve so crits actually feel random.
func expected_hit(defender: StatBlock) -> float:
	var base := (weapon_min + weapon_max) * 0.5
	var avg_crit := 1.0 + clampf(crit_chance, 0.0, 1.0) * (crit_mult - 1.0)

	var total := 0.0
	for t in Damage.Type.values():
		var raw: float = base * weapon_split.get(t, 0.0) + flat_damage.get(t, 0.0)
		if raw <= 0.0:
			continue
		raw *= 1.0 + increased_pct.get(t, 0.0)
		raw *= more_multiplier(t) * avg_crit
		var resist: float = clampf(
			defender.resistances.get(t, 0.0), Damage.RESIST_FLOOR, Damage.RESIST_CAP
		)
		total += raw * (1.0 - resist)
	return maxf(Damage.MIN_HIT, total - defender.armor)
