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
const RADIUS := 0.22
const LENGTH := 1.1
## Generous relative to the visual: a bolt that visibly clips a body and does
## nothing feels broken, and being slightly forgiving costs nothing here.
const HIT_RADIUS := 0.85

var spell: Spell
var stats: StatBlock
var rng: Rng
var direction := Vector3.FORWARD
## Behaviour ids from the build's inscriptions, e.g. "bolt_forks".
var behaviours: Array = []
## How many further bodies this may fork to. Set from behaviours at spawn.
var forks_left: int = 0

var _life := 0.0
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
	_mesh = MeshInstance3D.new()
	var body := CapsuleMesh.new()
	body.radius = RADIUS
	body.height = LENGTH
	body.radial_segments = 8
	body.rings = 4
	_mesh.mesh = body
	_material = Shapes.glow(_tint())
	_mesh.material_override = _material
	# Capsules stand up the Y axis; lay it along the direction of travel.
	_mesh.basis = Basis(Vector3.UP, atan2(direction.x, direction.z)) * Basis(
		Vector3.RIGHT, deg_to_rad(90.0)
	)
	add_child(_mesh)
	position.y = 1.0


## Bolts take the colour of whatever the build has committed to, so you can read
## someone's element off the screen without a UI.
func _tint() -> Color:
	if behaviours.has("bolt_ignites"):
		return Color(1.0, 0.55, 0.22)
	if behaviours.has("bolt_chills"):
		return Color(0.55, 0.85, 1.0)
	if behaviours.has("bolt_forks") or behaviours.has("bolt_chains_three"):
		return Color(0.78, 0.62, 1.0)
	# Deliberately cool: the default bolt must not read as either the warm white
	# player body or the orange enemy telegraph.
	return Color(0.62, 0.86, 1.0)


func _process(delta: float) -> void:
	_life += delta
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
		var result := Damage.resolve(stats, enemy.stats, rng)
		result.total *= spell.damage_scale
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
