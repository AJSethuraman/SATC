class_name Enemy
extends CharacterBody3D

## A chaser with a telegraphed contact attack. Its stat line comes from
## RunState.enemy_for_depth, so buffing depth scaling is a core/ change and never
## a scene change.
##
## Uses the same jointed rig as the player. The swell before it commits, the arm
## visibly cocking through the telegraph and the recoil when struck are its whole
## body language, and they are what make its attacks readable in a crowd.

signal died(at: Vector3, was_elite: bool)

var stats: StatBlock
var health: float = 10.0
var is_elite := false

var _rng: Rng
var _base_colour := Feel.COLOUR_ENEMY
var _radius := Feel.ENEMY_RADIUS
var _height := Feel.ENEMY_HEIGHT
var _hitstun := 0.0
var _attack_cooldown := 0.0
var _windup := -1.0
var _knockback := Vector3.ZERO
var _flash := 0.0
var _shape := Vector3.ONE

var _rig: CharacterRig
var _health_bar: MeshInstance3D
var _health_material: StandardMaterial3D


func setup(s: StatBlock, elite: bool, seed_v: int) -> void:
	stats = s
	health = s.max_health
	is_elite = elite
	_rng = Rng.new(seed_v)

	var scale_up := Feel.ELITE_SCALE if elite else 1.0
	_radius = Feel.ENEMY_RADIUS * scale_up
	_height = Feel.ENEMY_HEIGHT * scale_up

	# Stagger the first swing so a pack does not attack in lockstep.
	_attack_cooldown = _rng.randf() * Feel.ENEMY_ATTACK_COOLDOWN


func _ready() -> void:
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	up_direction = Vector3.UP

	var shape := CapsuleShape3D.new()
	shape.radius = _radius
	shape.height = _height
	var col := CollisionShape3D.new()
	col.shape = shape
	col.position = Vector3(0.0, _height * 0.5, 0.0)
	add_child(col)

	collision_layer = 4
	collision_mask = 1

	_rig = CharacterRig.new()
	# Elites carry a weapon; the rank and file come at you bare-handed, which
	# also makes the dangerous one findable at a glance in a crowd.
	# Vary the hue per body. Eleven identically-coloured figures read as one
	# mass of copies rather than as a crowd of things — and once they all look
	# the same, you stop tracking any of them individually and the fight becomes
	# a blur to be survived rather than one to be picked apart.
	_base_colour = Feel.COLOUR_ELITE if is_elite else Feel.COLOUR_ENEMY
	# Vary the hue per body, through reds into ember. Bodies that are all one
	# colour read as a mass of copies rather than a crowd of things, and once
	# they do you stop tracking any of them individually.
	_base_colour = _base_colour.lerp(
		Color.from_hsv(fmod(_rng.randf_range(0.97, 1.09), 1.0), 0.62, 0.56),
		_rng.randf_range(0.0, 0.4)
	)
	_rig.build(_height, _base_colour, is_elite, _kind())


## Which demon this body is.
##
## Elites are always brutes, so the one thing in the area worth being afraid of
## is also the one with the heaviest silhouette — you should be able to pick it
## out of a crowd before it reaches you, without a health bar or a colour code.
## The rest split between imps and stalkers off the seeded stream, so a area is
## a mixed pack rather than a row of the same creature.
func _kind() -> CharacterRig.Kind:
	if is_elite:
		return CharacterRig.Kind.BRUTE
	return CharacterRig.Kind.STALKER if _rng.randf() < 0.38 else CharacterRig.Kind.IMP
	add_child(_rig)

	# A floating slab above the head, scaled on the X axis to show health. Reads
	# at a glance from a fixed camera angle without needing a UI layer per enemy.
	_health_bar = MeshInstance3D.new()
	var bar := BoxMesh.new()
	bar.size = Vector3(_radius * 2.2, 0.09, 0.09)
	_health_bar.mesh = bar
	_health_material = Shapes.glow(Color(0.95, 0.32, 0.32))
	_health_material.albedo_color.a = 0.0
	_health_bar.material_override = _health_material
	_health_bar.position = Vector3(0.0, _height + 0.35, 0.0)
	add_child(_health_bar)


func _physics_process(delta: float) -> void:
	var player := _player()
	if player == null:
		return

	_hitstun = maxf(0.0, _hitstun - delta)
	_attack_cooldown = maxf(0.0, _attack_cooldown - delta)
	_flash = maxf(0.0, _flash - delta)
	_knockback = _knockback.lerp(Vector3.ZERO, clampf(Feel.KNOCKBACK_DECAY * delta, 0.0, 1.0))

	var to_player := player.global_position - global_position
	to_player.y = 0.0
	var distance := to_player.length()
	var reach := Feel.ENEMY_CONTACT_RANGE + _radius

	if _windup >= 0.0:
		# Committed. Standing still through the telegraph is what makes the hit
		# dodgeable — moving during windup would make dashing a coin flip.
		_windup -= delta
		velocity = Vector3.ZERO
		if _windup <= 0.0:
			_windup = -1.0
			_attack_cooldown = Feel.ENEMY_ATTACK_COOLDOWN
			var now := player.global_position - global_position
			now.y = 0.0
			if now.length() <= reach:
				player.take_damage(_hit_damage(player))
	elif _hitstun > 0.0:
		velocity = Vector3.ZERO
	elif distance <= reach and _attack_cooldown <= 0.0:
		_windup = Feel.ENEMY_WINDUP
		velocity = Vector3.ZERO
	elif distance > 0.05:
		velocity = to_player / distance * stats.move_speed * Feel.UNITS_PER_PIXEL + _separation()
	else:
		velocity = Vector3.ZERO

	velocity += _knockback
	velocity.y = 0.0
	move_and_slide()
	_animate(delta, to_player)


## Nudge apart from neighbours so a pack does not stack into one spot and become
## a single unavoidable damage source.
func _separation() -> Vector3:
	var push := Vector3.ZERO
	for node in get_parent().get_children():
		var other := node as Enemy
		if other == null or other == self:
			continue
		var away: Vector3 = global_position - other.global_position
		away.y = 0.0
		var d := away.length()
		if d > 0.05 and d < Feel.ENEMY_SEPARATION:
			# Has to out-push the chase velocity at close range, or a pack simply
			# converges into one overlapping mass and reads as a single blob.
			push += away.normalized() * (Feel.ENEMY_SEPARATION - d) * Feel.SEPARATION_FORCE
	return push


## Mid-telegraph, i.e. committed to a swing that has not landed yet. Public
## because it is the one piece of enemy state a dodging decision depends on.
func is_winding_up() -> bool:
	return _windup >= 0.0


func _hit_damage(player: Player) -> float:
	return Damage.resolve(stats, player.stats, _rng).total


func take_hit(result: Damage.Result, from: Vector3) -> void:
	health -= result.total
	_hitstun = Feel.HITSTUN
	_flash = Feel.FLASH_TIME
	_windup = -1.0  # interrupted
	var dir := global_position - from
	dir.y = 0.0
	if dir.length() > 0.05:
		_knockback = dir.normalized() * Feel.KNOCKBACK
	if health <= 0.0:
		died.emit(global_position, is_elite)
		queue_free()


func _animate(delta: float, to_player: Vector3) -> void:
	if _rig == null:
		return
	var blend := clampf(Feel.SHAPE_RECOVERY * delta, 0.0, 1.0)

	# Swell while winding up, flatten while stunned. Both are readable from the
	# fixed camera angle without any UI.
	var want := Vector3.ONE
	var swing := -1.0
	if _windup >= 0.0:
		var t := 1.0 - clampf(_windup / Feel.ENEMY_WINDUP, 0.0, 1.0)
		var swell := lerpf(1.0, Feel.ENEMY_TELL_SWELL, t)
		want = Vector3(swell, lerpf(1.0, 0.9, t), swell)
		# Drive the rig's swing through the telegraph, so the arm is visibly
		# cocked before the hit rather than the body just changing colour.
		swing = t * 0.3
	elif _hitstun > 0.0:
		want = Vector3(1.12, 0.86, 1.12)
	_shape = _shape.lerp(want, blend)

	var flat := Vector3(velocity.x, 0.0, velocity.z)

	_rig.face(to_player)
	_rig.speed_ratio = clampf(
		flat.length() / maxf(1.0, stats.move_speed * Feel.UNITS_PER_PIXEL), 0.0, 1.4
	)
	_rig.shape = _shape
	_rig.attack_phase = swing

	var tint := _base_colour
	if _flash > 0.0:
		tint = Color(1.0, 1.0, 1.0)
	elif _windup >= 0.0:
		tint = Feel.COLOUR_TELL
	_rig.tint = tint
	_rig.animate(delta)

	if stats != null and health < stats.max_health:
		var frac := clampf(health / stats.max_health, 0.0, 1.0)
		_health_material.albedo_color.a = 0.9
		# Held square to the camera, since it is a flat slab, and shortened along
		# its own X to show the remaining fraction. Folded into the basis because
		# assigning a Basis discards any separately-set scale.
		_health_bar.basis = Basis(Vector3.UP, deg_to_rad(Feel.CAMERA_AZIMUTH)).scaled(
			Vector3(maxf(0.02, frac), 1.0, 1.0)
		)


func _player() -> Player:
	return get_tree().get_first_node_in_group("player") as Player
