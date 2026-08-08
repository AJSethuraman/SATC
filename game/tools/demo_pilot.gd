class_name DemoPilot
extends RefCounted

## A crude bot that plays the game, so a recording shows combat rather than a
## character standing still being eaten.
##
## It is not meant to play well. It is meant to produce footage that shows the
## systems working: closing distance, swinging, dodging a telegraph, moving on.
## Treat its survival time as a stunt, not as a balance signal — the balance
## simulator in sim/ is the thing that measures anything.

## Start backing off inside this range, so it does not just stand in contact.
const COMFORT_RANGE := 1.9
## Dash away when a committed enemy is at least this close.
const PANIC_RANGE := 2.6
## Never dash more often than this, so the footage does not read as a twitch.
const DASH_INTERVAL := 0.9

var _dash_cooldown := 0.0
var _strafe := 1.0
var _strafe_timer := 0.0


## Look at the world and write the player's scripted input fields for this frame.
func drive(player: Player, enemies: Array, delta: float) -> void:
	_dash_cooldown = maxf(0.0, _dash_cooldown - delta)
	_strafe_timer -= delta
	if _strafe_timer <= 0.0:
		_strafe_timer = 1.6
		_strafe = -_strafe

	player.scripted = true
	player.scripted_attack = false
	player.scripted_dash = false
	player.scripted_move = Vector3.ZERO

	var target := _nearest(player, enemies)
	if target == null:
		# Nothing to fight — drift toward the middle so the camera settles.
		player.scripted_aim = player.global_position + player.facing
		player.scripted_move = -player.global_position.normalized() * 0.6
		return

	var to_target: Vector3 = target.global_position - player.global_position
	to_target.y = 0.0
	var distance := to_target.length()
	var forward := to_target.normalized()
	var sideways := forward.cross(Vector3.UP) * _strafe

	player.scripted_aim = target.global_position

	# A committed enemy in your face is the one thing worth spending a dash on.
	var threatened := target.is_winding_up() and distance < PANIC_RANGE
	if threatened and _dash_cooldown <= 0.0:
		player.scripted_dash = true
		player.scripted_move = (-forward + sideways).normalized()
		_dash_cooldown = DASH_INTERVAL
		return

	if distance > Feel.ATTACK_RANGE * 0.75:
		# Close in, but circle rather than walking a straight line at it.
		player.scripted_move = (forward + sideways * 0.45).normalized()
	elif distance < COMFORT_RANGE:
		player.scripted_move = (-forward * 0.6 + sideways).normalized()
		player.scripted_attack = true
	else:
		player.scripted_move = sideways * 0.5
		player.scripted_attack = true


func _nearest(player: Player, enemies: Array) -> Enemy:
	var best: Enemy = null
	var best_distance := INF
	for node in enemies:
		var e := node as Enemy
		if e == null or e.is_queued_for_deletion():
			continue
		var d: float = e.global_position.distance_to(player.global_position)
		if d < best_distance:
			best_distance = d
			best = e
	return best
