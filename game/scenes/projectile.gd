class_name Projectile
extends Node3D

## A cast bolt in flight.
##
## Carries the caster's resolved stat block rather than a damage number, so
## everything core/ knows — affixes, sigils, inscriptions, boons, resistances —
## applies at the moment of impact rather than at the moment of casting.
##
## Hit detection is a distance check rather than an Area3D. At these speeds and
## sizes physics callbacks would need continuous collision to not tunnel through
## a body, and a sphere test done in _process is both simpler and easier to
## reason about when something does not connect.

signal hit_enemy(enemy: Node3D, result: Damage.Result, at: Vector3)

## A sphere this small is unreadable at the camera's distance, so the bolt is a
## capsule stretched along travel — which also reads as motion rather than as a
## floating ball.
## Sized against the body, not against the arena. The camera shows roughly 11m
## across a 1280px frame, so a 0.26m-wide bolt is still ~30px on screen — plenty
## to read — while a bolt the length of the player reads as a thrown log.
const RADIUS := 0.13
const LENGTH := 0.55
## Generous relative to the visual: a bolt that visibly clips a body and does
## nothing feels broken, and being slightly forgiving costs nothing here.
const HIT_RADIUS := 0.85
## Frames of travel before the bolt is allowed to connect.
##
## Without this, a bolt cast into a body already leaning on you resolves on the
## frame it spawns: mana drains, damage lands, an enemy dies, and the spell is
## never drawn once. Two frames guarantees every cast is visibly a cast, and
## costs almost nothing in reach — after two frames the bolt has travelled
## about 1.1m, so a body inside HIT_RADIUS + ENEMY_RADIUS is still in contact.
const ARM_FRAMES := 2

var spell: Spell
var stats: StatBlock
var rng: Rng
var direction := Vector3.FORWARD
## Behaviour ids from the build's inscriptions, e.g. "bolt_forks".
var behaviours: Array = []
## How many further bodies this may fork to. Set from behaviours at spawn.
var forks_left: int = 0

var _life := 0.0
var _frames: int = 0
var _pierced: int = 0
var _already_hit: Array = []
var _mesh: MeshInstance3D
var _material: StandardMaterial3D


func setup(s: Spell, caster_stats: StatBlock, dir: Vector3, r: Rng, active: Array) -> void:
	spell = s
	stats = caster_stats
	direction = Vector3(dir.x, 0.0, dir.z).normalized()
	rng = r
	behaviours = active
	if behaviours.has("bolt_chains_three"):
		forks_left = 3
	elif behaviours.has("bolt_forks"):
		forks_left = 1


func _ready() -> void:
	# Capsules stand up the Y axis; lay both meshes along the direction of travel.
	var lie_down := Basis(Vector3.UP, atan2(direction.x, direction.z)) * Basis(
		Vector3.RIGHT, deg_to_rad(90.0)
	)
	var colour := tint_for_spell(spell, behaviours)

	# A smear behind the core, additive and translucent. At 17 m/s a bolt covers
	# most of its own length per frame, so without something trailing it reads as
	# a stuttering dash rather than as a thing moving through space.
	var smear := MeshInstance3D.new()
	var tail := CapsuleMesh.new()
	tail.radius = RADIUS * 0.6
	tail.height = LENGTH * 2.2
	tail.radial_segments = 6
	tail.rings = 2
	smear.mesh = tail
	var faint := colour
	faint.a = 0.3
	smear.material_override = Shapes.glow(faint)
	smear.basis = lie_down
	smear.position = -direction * LENGTH * 0.8
	smear.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(smear)

	_mesh = MeshInstance3D.new()
	var body := CapsuleMesh.new()
	body.radius = RADIUS
	body.height = LENGTH
	body.radial_segments = 8
	body.rings = 4
	_mesh.mesh = body
	_material = Shapes.unlit(colour)
	_mesh.material_override = _material
	_mesh.basis = lie_down
	# See the smear above: light passes through a spell rather than being
	# stopped by it.
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_mesh)

	position.y = 1.0


## Bolts take the colour of the school they belong to, so you can read what
## someone is casting off the screen without a UI. Inscriptions can still shift
## it — a build that has committed to chaining reads violet whatever it started
## as.
static func tint_for_spell(spell: Spell, active: Array) -> Color:
	if spell != null:
		match spell.element:
			Damage.Type.COLD:
				return Color(0.55, 0.85, 1.0)
			Damage.Type.LIGHTNING:
				return Color(0.86, 0.78, 1.0)
			_:
				return Color(0.98, 0.46, 0.14)
	return tint_for(active)


static func tint_for(active: Array) -> Color:
	if active.has("bolt_ignites"):
		return Color(1.0, 0.74, 0.24)
	if active.has("bolt_chills"):
		return Color(0.55, 0.85, 1.0)
	if active.has("bolt_forks") or active.has("bolt_chains_three"):
		return Color(0.78, 0.62, 1.0)
	# Ember, because the spell is called Emberbolt.
	#
	# This was green for a while. Not for any design reason — green was the one
	# hue nothing else in the palette used, which made it findable by a pixel
	# probe while I was working out why bolts were not rendering at all. The
	# probe went away and the colour did not, so a spell named after a burning
	# coal spent days firing lime. Debug affordances have to be removed with the
	# same care they were added.
	return Color(0.98, 0.46, 0.14)


func _process(delta: float) -> void:
	_life += delta
	_frames += 1
	if _life > spell.lifetime:
		queue_free()
		return

	global_position += direction * spell.speed * delta

	# Stay inside the arena; a bolt that sails through a wall reads as a bug.
	var half := Feel.ARENA * 0.5
	if absf(global_position.x) > half.x or absf(global_position.z) > half.y:
		queue_free()
		return

	_check_hits()


func _check_hits() -> void:
	if _frames <= ARM_FRAMES:
		return
	var holder := get_parent()
	if holder == null:
		return
	for node in holder.get_children():
		var enemy := node as Enemy
		if enemy == null or enemy.is_queued_for_deletion():
			continue
		if _already_hit.has(enemy.get_instance_id()):
			continue
		var to_enemy := enemy.global_position - global_position
		to_enemy.y = 0.0
		if to_enemy.length() > HIT_RADIUS + Feel.ENEMY_RADIUS:
			continue

		_already_hit.append(enemy.get_instance_id())
		# The spell decides the damage type, not the caster's gear — see
		# Spell.split(). Variance is the school's signature: lightning rolls
		# wild, fire and cold do not.
		var result := Damage.resolve(stats, enemy.stats, rng, spell.split())
		result.total *= spell.damage_scale * spell.roll_variance(rng)
		enemy.take_hit(result, global_position)
		hit_enemy.emit(enemy, result, global_position)

		if forks_left > 0:
			_fork_from(enemy)
			queue_free()
			return

		_pierced += 1
		if _pierced > spell.pierce:
			queue_free()
			return


## Spawn a successor aimed at the nearest untouched body. This is the whole
## point of the Arcwork and Thunderhead inscriptions — a behavioural change
## rather than a bigger number, which is what makes an inscription worth chasing
## over an affix.
func _fork_from(from: Enemy) -> void:
	var holder := get_parent()
	var best: Enemy = null
	var best_distance := 9.0
	for node in holder.get_children():
		var other := node as Enemy
		if other == null or other == from or other.is_queued_for_deletion():
			continue
		if _already_hit.has(other.get_instance_id()):
			continue
		var d: float = other.global_position.distance_to(from.global_position)
		if d < best_distance:
			best_distance = d
			best = other
	if best == null:
		return

	var next := Projectile.new()
	next.setup(spell, stats, best.global_position - from.global_position, rng, behaviours)
	next.forks_left = forks_left - 1
	next._already_hit = _already_hit.duplicate()
	holder.add_child(next)
	next.global_position = from.global_position + Vector3(0.0, 1.0, 0.0)
