class_name Enemy
extends CharacterBody2D

## A chaser with a telegraphed contact attack. Its stat line comes from
## RunState.enemy_for_floor, so buffing depth scaling is a core/ change and
## never a scene change.

signal died(at: Vector2, was_elite: bool)

var stats: StatBlock
var health: float = 10.0
var is_elite := false

var _rng: Rng
var _radius := 13.0
var _hitstun := 0.0
var _attack_cooldown := 0.0
var _windup := -1.0
var _knockback := Vector2.ZERO
var _flash := 0.0


func setup(s: StatBlock, elite: bool, seed_v: int) -> void:
	stats = s
	health = s.max_health
	is_elite = elite
	_rng = Rng.new(seed_v)
	_radius = 18.0 if elite else 13.0
	# Stagger the first swing so a pack does not attack in lockstep.
	_attack_cooldown = _rng.randf() * Feel.ENEMY_ATTACK_COOLDOWN

	var shape := CircleShape2D.new()
	shape.radius = _radius
	var col := CollisionShape2D.new()
	col.shape = shape
	add_child(col)

	collision_layer = 4
	collision_mask = 1


func _physics_process(delta: float) -> void:
	var player := _player()
	if player == null:
		return

	_hitstun = maxf(0.0, _hitstun - delta)
	_attack_cooldown = maxf(0.0, _attack_cooldown - delta)
	_flash = maxf(0.0, _flash - delta)
	_knockback = _knockback.lerp(Vector2.ZERO, clampf(Feel.KNOCKBACK_DECAY * delta, 0.0, 1.0))

	var to_player := player.global_position - global_position
	var distance := to_player.length()

	if _windup >= 0.0:
		# Committed. Standing still through the telegraph is what makes the hit
		# dodgeable — moving during windup would make dashing a coin flip.
		_windup -= delta
		if _windup <= 0.0:
			_windup = -1.0
			_attack_cooldown = Feel.ENEMY_ATTACK_COOLDOWN
			if global_position.distance_to(player.global_position) <= Feel.ENEMY_CONTACT_RANGE + _radius:
				player.take_damage(_hit_damage(player))
	elif _hitstun <= 0.0:
		if distance <= Feel.ENEMY_CONTACT_RANGE + _radius and _attack_cooldown <= 0.0:
			_windup = Feel.ENEMY_WINDUP
		elif distance > 1.0:
			var dir := to_player / distance
			velocity = dir * stats.move_speed + _separation()
		else:
			velocity = Vector2.ZERO
	else:
		velocity = Vector2.ZERO

	if _windup >= 0.0 or _hitstun > 0.0:
		velocity = Vector2.ZERO

	velocity += _knockback
	move_and_slide()
	queue_redraw()


## Nudge apart from neighbours so a pack does not stack into one square and
## become a single unavoidable damage source.
func _separation() -> Vector2:
	var push := Vector2.ZERO
	for node in get_parent().get_children():
		var other := node as Enemy
		if other == null or other == self:
			continue
		var away: Vector2 = global_position - other.global_position
		var d := away.length()
		if d > 0.1 and d < Feel.ENEMY_SEPARATION:
			push += away.normalized() * (Feel.ENEMY_SEPARATION - d) * 4.0
	return push


func _hit_damage(player: Player) -> float:
	return Damage.resolve(stats, player.stats, _rng).total


func take_hit(result: Damage.Result, from: Vector2) -> void:
	health -= result.total
	_hitstun = Feel.HITSTUN
	_flash = 0.12
	_windup = -1.0  # interrupted
	var dir := (global_position - from)
	if dir.length() > 0.1:
		_knockback = dir.normalized() * Feel.KNOCKBACK
	if health <= 0.0:
		died.emit(global_position, is_elite)
		queue_free()


func _draw() -> void:
	var body := Color(0.72, 0.28, 0.30) if is_elite else Color(0.45, 0.35, 0.42)
	if _flash > 0.0:
		body = Color(1, 1, 1)
	elif _windup >= 0.0:
		# Telegraph reads as colour so the player can parse a crowd at a glance.
		body = Color(1.0, 0.75, 0.25)
	draw_circle(Vector2.ZERO, _radius, body)

	if stats != null and health < stats.max_health:
		var frac := clampf(health / stats.max_health, 0.0, 1.0)
		var w := _radius * 2.0
		var y := -_radius - 8.0
		draw_rect(Rect2(-_radius, y, w, 3.0), Color(0, 0, 0, 0.6))
		draw_rect(Rect2(-_radius, y, w * frac, 3.0), Color(0.9, 0.3, 0.3))


func _player() -> Player:
	var found := get_tree().get_first_node_in_group("player")
	return found as Player
