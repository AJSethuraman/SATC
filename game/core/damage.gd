class_name Damage
extends RefCounted

## Damage types and the single resolution pipeline every hit goes through.
##
## The order below is load-bearing and deliberately D2-shaped: "increased"
## modifiers sum with each other and apply once, while "more" modifiers each
## apply as their own multiplier. That split is the whole reason gear and boons
## can coexist without one trivialising the other:
##
##   gear  -> flat + increased%   (build-defining, sums, diminishing in feel)
##   boons -> more%               (power-defining, compounds inside one run)
##
## `more%` comes in two forms: global, and scoped to one damage type. The scoped
## form is what gives an elemental god a real identity — a fire multiplier does
## nothing at all for a build with no fire damage, so it is a commitment rather
## than a free upgrade.
##
## Resolution order:
##   1. base weapon roll (min..max)
##   2. + flat added, per damage type
##   3. x (1 + sum of increased%)          <- additive bucket
##   4. x product of (1 + more%), global and this-type
##   5. x crit multiplier, on a crit roll
##   6. x (1 - resistance), resistance clamped to [RESIST_FLOOR, RESIST_CAP]
##   7. - flat armour, floored at MIN_HIT

enum Type { PHYSICAL, FIRE, COLD, LIGHTNING, POISON }

const TYPE_NAMES := {
	Type.PHYSICAL: "physical",
	Type.FIRE: "fire",
	Type.COLD: "cold",
	Type.LIGHTNING: "lightning",
	Type.POISON: "poison",
}

## Resistances above the cap are wasted; below the floor they stop scaling.
## Both mirror D2's 75%/-100% conventions.
const RESIST_CAP := 0.75
const RESIST_FLOOR := -1.0

## Armour can never fully negate a hit.
const MIN_HIT := 1.0


static func type_from_name(n: String) -> Type:
	for t in TYPE_NAMES:
		if TYPE_NAMES[t] == n:
			return t
	push_error("Damage.type_from_name: unknown damage type '%s'" % n)
	return Type.PHYSICAL


## One resolved hit. Kept as a value object so tests and the balance simulator
## can assert on the intermediate stages, not just the final number.
class Result extends RefCounted:
	var total: float = 0.0
	var by_type: Dictionary = {}  # Type -> float, post-mitigation
	var was_crit: bool = false
	var pre_mitigation: float = 0.0

	func _to_string() -> String:
		return "Damage.Result(total=%.2f crit=%s pre=%.2f)" % [total, was_crit, pre_mitigation]


## Resolve a single hit of `attacker` against `defender`.
##
## `rng` is consumed for the base weapon roll and the crit roll, in that order.
static func resolve(attacker: StatBlock, defender: StatBlock, rng: Rng) -> Result:
	var res := Result.new()

	# 1. Base weapon roll, split across the attacker's declared damage types.
	var base := rng.randf_range(attacker.weapon_min, attacker.weapon_max)

	# 5. Crit is rolled once for the hit, not per damage type.
	var crit := rng.chance(attacker.crit_chance)
	res.was_crit = crit
	var crit_mult := attacker.crit_mult if crit else 1.0

	for t in Type.values():
		var portion: float = base * attacker.weapon_split.get(t, 0.0)
		# 2. flat added
		var raw: float = portion + attacker.flat_damage.get(t, 0.0)
		if raw <= 0.0:
			continue
		# 3. additive increased%
		raw *= 1.0 + attacker.increased_pct.get(t, 0.0)
		# 4 + 5. The multiplier is resolved per type, so a fire-only `more`
		# leaves the physical portion of the same hit untouched.
		raw *= attacker.more_multiplier(t) * crit_mult
		res.pre_mitigation += raw

		# 6. resistance
		var resist: float = clampf(defender.resistances.get(t, 0.0), RESIST_FLOOR, RESIST_CAP)
		var mitigated := raw * (1.0 - resist)
		res.by_type[t] = mitigated
		res.total += mitigated

	# 7. flat armour, applied once to the whole hit
	res.total = maxf(MIN_HIT, res.total - defender.armor)
	return res
