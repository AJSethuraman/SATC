class_name Player
extends CharacterBody2D

## The player avatar. Owns movement, dash and the attack state machine; asks
## core/ for every number that matters and Feel for every number that feels.

signal attacked(origin: Vector2, facing: Vector2)
signal died

const RADIUS := 14.0

enum State { FREE, WINDUP, ACTIVE, RECOVERY }

var stats: StatBlock
var health: float = 100.0
var facing := Vector2.RIGHT

var _state: State = State.FREE
var _state_timer := 0.0
var _dash_timer := 0.0
var _dash_cooldown := 0.0
var _iframes := 0.0
var _buffered_attack := 0.0
var _hit_flash := 0.0


func _ready() -> void:
	var shape := CircleShape2D.new()
	shape.radius = RADIUS
	var col := CollisionShape2D.new()
	col.shape = shape
	add_child(col)

	# Layer 2, collides with walls (layer 1) only. Contact with enemies is
	# resolved by distance so bodies never shove each other around.
	collision_layer = 2
	collision_mask = 1


func setup(s: StatBlock) -> void:
	stats = s
	health = s.max_health


func is_invulnerable() -> bool:
	return _iframes > 0.0


func _physics_process(delta: float) -> void:
	_tick_timers(delta)
	_read_input()

	var target := Vector2.ZERO
	if _dash_timer > 0.0:
		target = facing * Feel.DASH_SPEED
	elif _state == State.FREE or _state == State.RECOVERY:
		target = _move_input() * stats.move_speed
	elif _state == State.WINDUP:
		target = facing * Feel.ATTACK_LUNGE

	var rate := Feel.MOVE_ACCEL if target.length() > 0.0 else Feel.MOVE_FRICTION
	velocity = velocity.lerp(target, clampf(rate * delta, 0.0, 1.0))
	move_and_slide()
	queue_redraw()


func _tick_timers(delta: float) -> void:
	_dash_timer = maxf(0.0, _dash_timer - delta)
	_dash_cooldown = maxf(0.0, _dash_cooldown - delta)
	_iframes = maxf(0.0, _iframes - delta)
	_buffered_attack = maxf(0.0, _buffered_attack - delta)
	_hit_flash = maxf(0.0, _hit_flash - delta)

	if _state == State.FREE:
		return
	_state_timer -= delta
	if _state_timer > 0.0:
		return

	match _state:
		State.WINDUP:
			_state = State.ACTIVE
			_state_timer = Feel.ATTACK_ACTIVE
			attacked.emit(global_position, facing)
		State.ACTIVE:
			_state = State.RECOVERY
			_state_timer = Feel.ATTACK_RECOVERY
		State.RECOVERY:
			_state = State.FREE
			if _buffered_attack > 0.0:
				_start_attack()


func _read_input() -> void:
	var aim := (get_global_mouse_position() - global_position)
	if aim.length() > 1.0:
		facing = aim.normalized()

	if Input.is_key_pressed(KEY_SPACE) or Input.is_key_pressed(KEY_SHIFT):
		_try_dash()

	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) or Input.is_key_pressed(KEY_J):
		if _state == State.FREE:
			_start_attack()
		else:
			_buffered_attack = Feel.ATTACK_BUFFER


func _move_input() -> Vector2:
	var v := Vector2.ZERO
	if Input.is_key_pressed(KEY_A):
		v.x -= 1.0
	if Input.is_key_pressed(KEY_D):
		v.x += 1.0
	if Input.is_key_pressed(KEY_W):
		v.y -= 1.0
	if Input.is_key_pressed(KEY_S):
		v.y += 1.0
	return v.normalized()


func _try_dash() -> void:
	if _dash_cooldown > 0.0 or _dash_timer > 0.0:
		return
	var dir := _move_input()
	if dir == Vector2.ZERO:
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
	_hit_flash = 0.15
	if health <= 0.0:
		health = 0.0
		died.emit()


## Placeholder rendering — a wedge so facing is readable. Art is the other half
## of this genre and it is not something this file is pretending to solve.
func _draw() -> void:
	var body := Color(0.85, 0.86, 0.9)
	if _hit_flash > 0.0:
		body = Color(1, 0.4, 0.4)
	elif is_invulnerable():
		body = Color(0.5, 0.8, 1.0, 0.7)
	draw_circle(Vector2.ZERO, RADIUS, body)

	var tip := facing * (RADIUS + 8.0)
	var side := facing.orthogonal() * (RADIUS * 0.55)
	draw_colored_polygon(PackedVector2Array([tip, side, -side]), body.darkened(0.25))

	if _state == State.ACTIVE:
		var arc := deg_to_rad(Feel.ATTACK_ARC)
		var mid := facing.angle()
		draw_arc(Vector2.ZERO, Feel.ATTACK_RANGE, mid - arc, mid + arc, 24, Color(1, 0.95, 0.75, 0.55), 4.0)
