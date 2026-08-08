extends Node2D

## Game orchestration: arena, waves, rewards, HUD, death and restart.
##
## Every scene node here is built in code rather than authored as a .tscn. That
## is a deliberate prototype choice — the whole playable layer is placeholder
## shapes, and keeping it in script means the interesting parts stay reviewable
## as text instead of hiding in editor state.

const ITEMS_PATH := "res://data/items.json"
const BOONS_PATH := "res://data/boons.json"

const ARENA := Vector2(1600, 1000)
const WALL := 40.0
const ENEMIES_BASE := 5
const ELITE_EVERY := 3

var run: RunState
var generator: ItemGenerator
var boon_pool: BoonPool

var player: Player
var enemies_root: Node2D
var camera: Camera2D

var _shake := 0.0
var _shake_rng := Rng.new(1)
var _awaiting_reward := false
var _hud: Control
var _log: Label
var _reward_layer: CanvasLayer


func _ready() -> void:
	randomize()
	generator = ItemGenerator.from_json(ITEMS_PATH)
	boon_pool = BoonPool.from_json(BOONS_PATH)

	_build_arena()
	_build_hud()

	enemies_root = Node2D.new()
	enemies_root.name = "Enemies"
	add_child(enemies_root)

	camera = Camera2D.new()
	add_child(camera)
	camera.make_current()

	_start_run(randi())


# --- run flow -----------------------------------------------------------


func _start_run(seed_v: int) -> void:
	run = RunState.start(seed_v)

	if is_instance_valid(player):
		player.queue_free()
	player = Player.new()
	player.add_to_group("player")
	player.setup(run.build_stats())
	player.global_position = ARENA * 0.5
	player.attacked.connect(_on_player_attacked)
	player.died.connect(_on_player_died)
	add_child(player)

	_say("Run %d — descend." % seed_v)
	_start_floor()


func _start_floor() -> void:
	_awaiting_reward = false
	for child in enemies_root.get_children():
		child.queue_free()

	var count := ENEMIES_BASE + int(run.floor_number / 2)
	for i in count:
		var elite := (i == 0 and run.floor_number % ELITE_EVERY == 0)
		var e := Enemy.new()
		e.setup(
			RunState.enemy_for_floor(run.floor_number, elite),
			elite,
			run.combat_rng.randi_range(0, 0x7FFFFFFF)
		)
		e.global_position = _spawn_point()
		e.died.connect(_on_enemy_died)
		enemies_root.add_child(e)

	_say("Floor %d — %d foes." % [run.floor_number, count])
	_refresh_hud()


## Spawn away from the player so a floor never opens with a free hit.
func _spawn_point() -> Vector2:
	for attempt in 30:
		var p := Vector2(
			randf_range(WALL + 60.0, ARENA.x - WALL - 60.0),
			randf_range(WALL + 60.0, ARENA.y - WALL - 60.0)
		)
		if not is_instance_valid(player) or p.distance_to(player.global_position) > 320.0:
			return p
	return Vector2(WALL + 80.0, WALL + 80.0)


func _on_enemy_died(at: Vector2, was_elite: bool) -> void:
	_shake = maxf(_shake, Feel.SHAKE_CRIT if was_elite else Feel.SHAKE_NORMAL)
	# The dying enemy is still in the tree for this frame.
	if _living_enemies() > 1 or _awaiting_reward:
		return
	_awaiting_reward = true
	call_deferred("_offer_rewards")


func _living_enemies() -> int:
	var n := 0
	for c in enemies_root.get_children():
		if c is Enemy and not c.is_queued_for_deletion():
			n += 1
	return n


func _offer_rewards() -> void:
	# Loot first, so a tag it grants can widen the boon offer immediately —
	# this ordering is the whole gear-gates-boons loop in one line.
	var drop := generator.roll_item(run.floor_number + 3, run.loot_rng, 0.5)
	var before := run.build_stats().expected_hit(RunState.enemy_for_floor(run.floor_number))
	run.equip(drop)
	var after := run.build_stats().expected_hit(RunState.enemy_for_floor(run.floor_number))
	_say("Found %s  (%+.0f%% dmg)" % [drop.display_name(), 100.0 * (after / maxf(before, 0.01) - 1.0)])

	var offer := boon_pool.offer(
		run.boon_rng, run.owned_boon_ids(), run.owned_boon_groups(), run.gear_tags(), 3
	)
	if offer.is_empty():
		_next_floor()
		return
	_show_reward_ui(offer)


func _next_floor() -> void:
	run.advance_floor()
	var stats := run.build_stats()
	run.health = minf(stats.max_health, run.health + stats.max_health * 0.25)
	player.setup(stats)
	player.health = run.health
	_start_floor()


func _on_player_died() -> void:
	_say("You died on floor %d. Press R." % run.floor_number)
	set_process_input(true)


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_R:
		if is_instance_valid(player) and player.health <= 0.0:
			_clear_reward_ui()
			_start_run(randi())


# --- combat -------------------------------------------------------------


func _on_player_attacked(origin: Vector2, facing: Vector2) -> void:
	var arc := deg_to_rad(Feel.ATTACK_ARC)
	var hit_any := false
	var any_crit := false

	for node in enemies_root.get_children():
		# Cast rather than `is`-check: get_children() is typed Array[Node], and
		# GDScript does not narrow through a branch, so member access needs this.
		var e := node as Enemy
		if e == null or e.is_queued_for_deletion():
			continue
		var to_enemy: Vector2 = e.global_position - origin
		if to_enemy.length() > Feel.ATTACK_RANGE + 16.0:
			continue
		if absf(facing.angle_to(to_enemy)) > arc:
			continue

		var result := Damage.resolve(player.stats, e.stats, run.combat_rng)
		e.take_hit(result, origin)
		hit_any = true
		any_crit = any_crit or result.was_crit

	if hit_any:
		_impact(any_crit)


## Hit-stop and shake. The durations live in Feel; this just applies them.
func _impact(crit: bool) -> void:
	_shake = maxf(_shake, Feel.SHAKE_CRIT if crit else Feel.SHAKE_NORMAL)
	var duration := Feel.HITSTOP_CRIT if crit else Feel.HITSTOP_NORMAL
	Engine.time_scale = Feel.HITSTOP_SCALE
	# ignore_time_scale so the freeze lasts a real fraction of a second rather
	# than a scaled one, which would make it twenty times too long.
	await get_tree().create_timer(duration, true, false, true).timeout
	Engine.time_scale = 1.0


func _process(delta: float) -> void:
	if is_instance_valid(player):
		camera.global_position = camera.global_position.lerp(
			player.global_position, clampf(Feel.CAMERA_LAG * delta, 0.0, 1.0)
		)
		run.health = player.health
	if _shake > 0.0:
		_shake = maxf(0.0, _shake - Feel.SHAKE_DECAY * delta)
		camera.offset = Vector2(
			_shake_rng.randf_range(-_shake, _shake), _shake_rng.randf_range(-_shake, _shake)
		)
	else:
		camera.offset = Vector2.ZERO
	_refresh_hud()


# --- presentation -------------------------------------------------------


func _build_arena() -> void:
	var floor_rect := ColorRect.new()
	floor_rect.color = Color(0.10, 0.09, 0.12)
	floor_rect.size = ARENA
	floor_rect.z_index = -10
	add_child(floor_rect)

	var edges := [
		Rect2(0, 0, ARENA.x, WALL),
		Rect2(0, ARENA.y - WALL, ARENA.x, WALL),
		Rect2(0, 0, WALL, ARENA.y),
		Rect2(ARENA.x - WALL, 0, WALL, ARENA.y),
	]
	for r in edges:
		var body := StaticBody2D.new()
		body.collision_layer = 1
		body.collision_mask = 0
		var shape := RectangleShape2D.new()
		shape.size = r.size
		var col := CollisionShape2D.new()
		col.shape = shape
		col.position = r.size * 0.5
		body.position = r.position
		body.add_child(col)
		add_child(body)

		var vis := ColorRect.new()
		vis.color = Color(0.18, 0.16, 0.20)
		vis.position = r.position
		vis.size = r.size
		vis.z_index = -9
		add_child(vis)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	_hud = Label.new()
	_hud.position = Vector2(16, 12)
	_hud.add_theme_font_size_override("font_size", 15)
	layer.add_child(_hud)

	_log = Label.new()
	_log.position = Vector2(16, 132)
	_log.add_theme_font_size_override("font_size", 16)
	_log.modulate = Color(1, 0.93, 0.75)
	layer.add_child(_log)


func _refresh_hud() -> void:
	if _hud == null or run == null or not is_instance_valid(player):
		return
	var stats := player.stats
	var lines := [
		"Floor %d          HP %d / %d" % [run.floor_number, roundi(player.health), roundi(stats.max_health)],
		"dmg %d-%d   crit %.0f%% x%.2f   more x%.2f"
			% [
				roundi(stats.weapon_min), roundi(stats.weapon_max),
				stats.crit_chance * 100.0, stats.crit_mult, _more_product(stats)
			],
	]
	var tags := run.gear_tags()
	if not tags.is_empty():
		lines.append("tags: " + ", ".join(tags))
	if not run.boons.is_empty():
		var names: Array[String] = []
		for b in run.boons:
			names.append(b.label())
		lines.append("boons: " + ", ".join(names))
	_hud.text = "\n".join(lines)


func _more_product(stats: StatBlock) -> float:
	var m := 1.0
	for v in stats.more_mults:
		m *= 1.0 + v
	return m


func _say(msg: String) -> void:
	if _log != null:
		_log.text = msg


func _show_reward_ui(offer: Array) -> void:
	_clear_reward_ui()
	_reward_layer = CanvasLayer.new()
	add_child(_reward_layer)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-260, -140)
	panel.custom_minimum_size = Vector2(520, 0)
	_reward_layer.add_child(panel)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)

	var title := Label.new()
	title.text = "The Court offers:"
	title.add_theme_font_size_override("font_size", 20)
	box.add_child(title)

	for b in offer:
		var button := Button.new()
		button.custom_minimum_size = Vector2(0, 56)
		button.text = "%s  (%s)\n%s" % [b.label(), b.god, b.description]
		button.pressed.connect(_on_boon_chosen.bind(b))
		box.add_child(button)


func _on_boon_chosen(b: Boon.Rolled) -> void:
	run.take_boon(b)
	_say("Taken: %s" % b.label())
	_clear_reward_ui()
	_next_floor()


func _clear_reward_ui() -> void:
	if is_instance_valid(_reward_layer):
		_reward_layer.queue_free()
	_reward_layer = null
