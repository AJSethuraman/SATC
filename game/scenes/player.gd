class_name Player
extends CharacterBody3D

## The player avatar. Owns movement, dash and the attack state machine; asks
## core/ for every number that matters and Feel for every number that feels.
##
## There are no animation frames, so all of this character's life comes from
## deforming a capsule in code: leaning into movement, stretching along a dash,
## crouching before a swing, popping on release. That is the cheapest convincing
## substitute for animation, and it lives in _animate().

signal attacked(origin: Vector3, facing: Vector3)
signal died

enum State { FREE, WINDUP, ACTIVE, RECOVERY }

var stats: StatBlock
var health: float = 100.0
## Horizontal facing on the ground plane. Never vertical.
var facing := Vector3.FORWARD

## Scripted-input hook. When `scripted` is true these fields replace the
## keyboard and mouse entirely. Deliberately plain values rather than a
## controller object, so nothing in the game depends on the thing driving it —
## tools/demo_pilot.gd writes them to record a demo, and the same seam would
## serve an autoplay soak test.
var scripted := false
var scripted_move := Vector3.ZERO
var scripted_aim := Vector3.ZERO
var scripted_attack := false
var scripted_dash := false

var _state: State = State.FREE
var _state_timer := 0.0
var _dash_timer := 0.0
var _dash_cooldown := 0.0
var _iframes := 0.0
var _buffered_attack := 0.0
var _flash := 0.0
var _bob := 0.0
var _aim_point := Vector3.ZERO

## Current animated silhouette and lean, eased toward their targets each frame
## rather than snapped, and tracked here because assigning a Basis discards scale.
var _shape := Vector3.ONE
var _lean := 0.0

var _body: MeshInstance3D
var _body_material: StandardMaterial3D
var _slash: MeshInstance3D
var _slash_material: StandardMaterial3D
var _camera: IsoCamera


func setup(s: StatBlock, camera: IsoCamera) -> void:
	stats = s
	health = s.max_health
	_camera = camera


func _ready() -> void:
	# Floating mode: this is a top-down game on a flat plane, so the body should
	# never try to resolve floors, slopes or gravity.
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	up_direction = Vector3.UP

	var shape := CapsuleShape3D.new()
	shape.radius = Feel.PLAYER_RADIUS
	shape.height = Feel.PLAYER_HEIGHT
	var col := CollisionShape3D.new()
	col.shape = shape
	col.position = Vector3(0.0, Feel.PLAYER_HEIGHT * 0.5, 0.0)
	add_child(col)

	# Layer 2, colliding with walls (layer 1) only. Contact with enemies is
	# resolved by distance so bodies never shove each other around.
	collision_layer = 2
	collision_mask = 1

	_body = MeshInstance3D.new()
	_body.mesh = Shapes.body_capsule(Feel.PLAYER_RADIUS, Feel.PLAYER_HEIGHT)
	_body_material = Shapes.solid(Feel.COLOUR_PLAYER)
	_body.material_override = _body_material
	_body.position = Vector3(0.0, Feel.PLAYER_HEIGHT * 0.5, 0.0)
	add_child(_body)

	_slash = MeshInstance3D.new()
	_slash.mesh = Shapes.arc_band(
		Feel.ATTACK_RANGE * Feel.SLASH_INNER_RATIO,
		Feel.ATTACK_RANGE,
		Feel.ATTACK_ARC,
		Feel.SLASH_SEGMENTS
	)
	_slash_material = Shapes.glow(Feel.COLOUR_SLASH)
	_slash_material.albedo_color.a = 0.0
	_slash.material_override = _slash_material
	_slash.position = Vector3(0.0, Feel.SLASH_HEIGHT, 0.0)
	add_child(_slash)


func is_invulnerable() -> bool:
	return _iframes > 0.0


func aim_point() -> Vector3:
	return _aim_point


func _physics_process(delta: float) -> void:
	_tick_timers(delta)
	_read_input()

	var target := Vector3.ZERO
	if _dash_timer > 0.0:
		target = facing * Feel.DASH_SPEED
	elif _state == State.FREE or _state == State.RECOVERY:
		target = _move_input() * stats.move_speed * Feel.UNITS_PER_PIXEL
	elif _state == State.WINDUP:
		target = facing * Feel.ATTACK_LUNGE

	var rate := Feel.MOVE_ACCEL if target.length() > 0.0 else Feel.MOVE_FRICTION
	velocity = velocity.lerp(target, clampf(rate * delta, 0.0, 1.0))
	velocity.y = 0.0
	move_and_slide()

	_animate(delta)


func _tick_timers(delta: float) -> void:
	_dash_timer = maxf(0.0, _dash_timer - delta)
	_dash_cooldown = maxf(0.0, _dash_cooldown - delta)
	_iframes = maxf(0.0, _iframes - delta)
	_buffered_attack = maxf(0.0, _buffered_attack - delta)
	_flash = maxf(0.0, _flash - delta)

	if _state == State.FREE:
		return
	_state_timer -= delta
	if _state_timer > 0.0:
		return

	match _state:
		State.WINDUP:
			_state = State.ACTIVE
			_state_timer = Feel.ATTACK_ACTIVE
			_slash_material.albedo_color.a = Feel.SLASH_ALPHA
			attacked.emit(global_position, facing)
		State.ACTIVE:
			_state = State.RECOVERY
			_state_timer = Feel.ATTACK_RECOVERY
		State.RECOVERY:
			_state = State.FREE
			if _buffered_attack > 0.0:
				_start_attack()


func _read_input() -> void:
	var want_dash := false
	var want_attack := false

	if scripted:
		_aim_point = scripted_aim
		want_dash = scripted_dash
		want_attack = scripted_attack
	else:
		if _camera != null:
			_aim_point = _camera.ground_point(global_position + facing)
		want_dash = Input.is_key_pressed(KEY_SPACE) or Input.is_key_pressed(KEY_SHIFT)
		want_attack = Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) or Input.is_key_pressed(KEY_J)

	var to_aim := _aim_point - global_position
	to_aim.y = 0.0
	if to_aim.length() > 0.15:
		facing = to_aim.normalized()

	if want_dash:
		_try_dash()

	if want_attack:
		if _state == State.FREE:
			_start_attack()
		else:
			_buffered_attack = Feel.ATTACK_BUFFER


## WASD in screen space, rotated into world space by the camera's fixed yaw, so
## "W" means "up the screen" rather than "negative Z".
func _move_input() -> Vector3:
	if scripted:
		if scripted_move.length() < 0.01:
			return Vector3.ZERO
		return Vector3(scripted_move.x, 0.0, scripted_move.z).normalized()

	var screen := Vector2.ZERO
	if Input.is_key_pressed(KEY_A):
		screen.x -= 1.0
	if Input.is_key_pressed(KEY_D):
		screen.x += 1.0
	if Input.is_key_pressed(KEY_W):
		screen.y -= 1.0
	if Input.is_key_pressed(KEY_S):
		screen.y += 1.0
	if screen == Vector2.ZERO:
		return Vector3.ZERO
	screen = screen.normalized()
	return (IsoCamera.input_basis() * Vector3(screen.x, 0.0, screen.y)).normalized()


func _try_dash() -> void:
	if _dash_cooldown > 0.0 or _dash_timer > 0.0:
		return
	var dir := _move_input()
	if dir == Vector3.ZERO:
		dir = facing
	facing = dir
	_dash_timer = Feel.DASH_DURATION
	_dash_cooldown = Feel.DASH_COOLDOWN
	_iframes = Feel.DASH_IFRAMES
	_state = State.FREE


func _start_attack() -> void:
	_state = State.WINDUP
	_state_timer = Feel.ATTACK_WINDUP
	_buffered_attack = 0.0


func take_damage(amount: float) -> void:
	if is_invulnerable():
		return
	health -= amount
	_flash = Feel.FLASH_TIME
	if health <= 0.0:
		health = 0.0
		died.emit()


## All of this character's animation, such as it is. Deforming a capsule is not
## a substitute for a real animator, but a body that leans, stretches and
## recoils reads as alive where a rigid one reads as a placeholder.
func _animate(delta: float) -> void:
	if _body == null:
		return

	var blend := clampf(Feel.SHAPE_RECOVERY * delta, 0.0, 1.0)

	# Yaw that points the capsule's -Z at the aim direction.
	var yaw := atan2(facing.x, facing.z) + PI

	# Lean into travel, proportional to how fast we are actually moving.
	var flat := Vector3(velocity.x, 0.0, velocity.z)
	var speed_ratio := clampf(
		flat.length() / maxf(1.0, stats.move_speed * Feel.UNITS_PER_PIXEL), 0.0, 1.6
	)
	var lean_target := 0.0
	var lean_axis := Vector3.RIGHT
	if flat.length() > 0.05:
		lean_axis = flat.normalized().cross(Vector3.UP)
		lean_target = deg_to_rad(-Feel.LEAN_DEGREES) * speed_ratio
	_lean = lerpf(_lean, lean_target, clampf(Feel.LEAN_RESPONSE * delta, 0.0, 1.0))

	# Target silhouette: stretched along a dash, crouched on windup, popped on
	# release, otherwise resting.
	var want_scale := Vector3.ONE
	if _dash_timer > 0.0:
		want_scale = Vector3(Feel.DASH_SQUASH, Feel.DASH_SQUASH, Feel.DASH_STRETCH)
	elif _state == State.WINDUP:
		want_scale = Vector3(1.06, Feel.ATTACK_CROUCH, 1.06)
	elif _state == State.ACTIVE:
		want_scale = Vector3(0.94, Feel.ATTACK_POP, 1.08)
	_shape = _shape.lerp(want_scale, blend)

	# Compose once, in order: lean around the travel axis, then face, then scale.
	# Assigning basis clears scale, so scale has to be folded into the basis
	# rather than set separately.
	var oriented := Basis(lean_axis, _lean) * Basis(Vector3.UP, yaw)
	_body.basis = oriented.scaled(_shape)
	_slash.basis = Basis(Vector3.UP, yaw)

	_bob += delta * Feel.BOB_SPEED * (1.0 + speed_ratio * 2.0)
	var bob := sin(_bob) * Feel.BOB_HEIGHT * (0.4 + speed_ratio)
	_body.position.y = Feel.PLAYER_HEIGHT * 0.5 + bob

	# Fade the swing arc out.
	if _slash_material.albedo_color.a > 0.0:
		_slash_material.albedo_color.a = maxf(
			0.0, _slash_material.albedo_color.a - Feel.SLASH_FADE * delta
		)

	# Tint: hurt flashes red, dash i-frames read blue.
	var tint := Feel.COLOUR_PLAYER
	if _flash > 0.0:
		tint = Color(1.0, 0.42, 0.42)
	elif is_invulnerable():
		tint = Feel.COLOUR_IFRAME
	_body_material.albedo_color = _body_material.albedo_color.lerp(tint, blend)
