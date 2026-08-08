extends Node3D

## Game orchestration: arena, lighting, waves, rewards, HUD, death and restart.
##
## Every node here is built in code rather than authored as a .tscn. That is a
## deliberate prototype choice — the whole presentation is procedural primitives,
## and keeping it in script means the interesting parts stay reviewable as text
## instead of hiding in editor state.
##
## Nothing in this file knows how damage, loot or boons work. That all lives in
## core/, which never imports a scene node — which is why swapping this layer
## from flat 2D to a lit isometric 3D scene touched none of it.

const ITEMS_PATH := "res://data/items.json"
const BOONS_PATH := "res://data/boons.json"

const ENEMIES_BASE := 5
const ELITE_EVERY := 3
const SPAWN_MARGIN := 2.5
const MIN_SPAWN_DISTANCE := 7.0

var run: RunState
var generator: ItemGenerator
var boon_pool: BoonPool

var player: Player
var enemies_root: Node3D
var camera: IsoCamera

var _awaiting_reward := false
var _hitstop_frames := 0
var _hud: Label
var _log: Label
var _reward_layer: CanvasLayer


func _ready() -> void:
	randomize()
	generator = ItemGenerator.from_json(ITEMS_PATH)
	boon_pool = BoonPool.from_json(BOONS_PATH)

	_build_environment()
	_build_arena()
	_build_hud()

	enemies_root = Node3D.new()
	enemies_root.name = "Enemies"
	add_child(enemies_root)

	camera = IsoCamera.new()
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
	player.setup(run.build_stats(), camera)
	player.global_position = Vector3.ZERO
	player.attacked.connect(_on_player_attacked)
	player.died.connect(_on_player_died)
	add_child(player)

	camera.snap_to(Vector3.ZERO)
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
		e.died.connect(_on_enemy_died)
		enemies_root.add_child(e)
		e.global_position = _spawn_point()

	_say("Floor %d — %d foes." % [run.floor_number, count])
	_refresh_hud()


## Spawn away from the player so a floor never opens with a free hit.
func _spawn_point() -> Vector3:
	var half := Feel.ARENA * 0.5
	for _attempt in 40:
		var p := Vector3(
			randf_range(-half.x + SPAWN_MARGIN, half.x - SPAWN_MARGIN),
			0.0,
			randf_range(-half.y + SPAWN_MARGIN, half.y - SPAWN_MARGIN)
		)
		if not is_instance_valid(player) or p.distance_to(player.global_position) > MIN_SPAWN_DISTANCE:
			return p
	return Vector3(half.x - SPAWN_MARGIN, 0.0, half.y - SPAWN_MARGIN)


func _on_enemy_died(at: Vector3, was_elite: bool) -> void:
	camera.add_shake(Feel.SHAKE_CRIT if was_elite else Feel.SHAKE_NORMAL)
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
	# Loot first, so a tag it grants can widen the boon offer immediately — this
	# ordering is the whole gear-gates-boons loop in one line.
	var drop := generator.roll_item(run.floor_number + 3, run.loot_rng, 0.5)
	var enemy := RunState.enemy_for_floor(run.floor_number)
	var before := run.build_stats().expected_hit(enemy)
	run.equip(drop)
	var after := run.build_stats().expected_hit(enemy)
	_say("Found %s  (%+.0f%% dmg)" % [drop.display_name(), 100.0 * (after / maxf(before, 0.01) - 1.0)])

	var offer := boon_pool.offer(
		run.boon_rng, run.owned_boon_ids(), run.owned_boon_groups(), run.active_tags(), 3
	)
	if offer.is_empty():
		_next_floor()
		return
	_show_reward_ui(offer)


func _next_floor() -> void:
	run.advance_floor()
	var stats := run.build_stats()
	run.health = minf(stats.max_health, run.health + stats.max_health * 0.25)
	player.setup(stats, camera)
	player.health = run.health
	_start_floor()


func _on_player_died() -> void:
	_say("You died on floor %d. Press R." % run.floor_number)


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_R:
		if is_instance_valid(player) and player.health <= 0.0:
			_clear_reward_ui()
			_start_run(randi())


# --- combat -------------------------------------------------------------


func _on_player_attacked(origin: Vector3, facing: Vector3) -> void:
	var arc := deg_to_rad(Feel.ATTACK_ARC)
	var hit_any := false
	var any_crit := false

	for node in enemies_root.get_children():
		# Cast rather than `is`-check: get_children() is typed Array[Node], and
		# GDScript does not narrow through a branch, so member access needs this.
		var e := node as Enemy
		if e == null or e.is_queued_for_deletion():
			continue

		var to_enemy: Vector3 = e.global_position - origin
		to_enemy.y = 0.0
		if to_enemy.length() > Feel.ATTACK_RANGE + Feel.ENEMY_RADIUS:
			continue
		# Angle on the ground plane only — height must not affect whether a swing
		# connects, or standing on a slope would change your reach.
		if absf(facing.signed_angle_to(to_enemy, Vector3.UP)) > arc:
			continue

		var result := Damage.resolve(player.stats, e.stats, run.combat_rng)
		e.take_hit(result, origin)
		hit_any = true
		any_crit = any_crit or result.was_crit

	if hit_any:
		_impact(any_crit)


## Hit-stop and shake. The durations live in Feel; this just applies them.
##
## Counted down in frames rather than awaited on a timer: a wall-clock wait is
## wrong whenever the engine is not running at real speed, and time_scale left
## stuck at 0.05 because a coroutine never resumed is a spectacular bug.
func _impact(crit: bool) -> void:
	camera.add_shake(Feel.SHAKE_CRIT if crit else Feel.SHAKE_NORMAL)
	_hitstop_frames = maxi(
		_hitstop_frames, Feel.HITSTOP_FRAMES_CRIT if crit else Feel.HITSTOP_FRAMES_NORMAL
	)


func _process(delta: float) -> void:
	if _hitstop_frames > 0:
		_hitstop_frames -= 1
		Engine.time_scale = Feel.HITSTOP_SCALE
	else:
		Engine.time_scale = 1.0

	if is_instance_valid(player):
		var aim := player.aim_point() - player.global_position
		aim.y = 0.0
		camera.follow(player.global_position, aim, delta)
		run.health = player.health
	_refresh_hud()


# --- presentation -------------------------------------------------------


## Ambient fill plus one shadow-casting directional light. The shadows are doing
## most of the work here: they are what tells you a capsule is standing on the
## floor rather than floating in front of it, and they are the single biggest
## reason a scene of primitives reads as a place at all.
func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Feel.FOG_COLOUR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Feel.AMBIENT_COLOUR
	env.ambient_light_energy = Feel.AMBIENT_ENERGY

	var holder := WorldEnvironment.new()
	holder.environment = env
	add_child(holder)

	var light := DirectionalLight3D.new()
	light.light_color = Feel.LIGHT_COLOUR
	light.light_energy = Feel.LIGHT_ENERGY
	light.shadow_enabled = true
	light.directional_shadow_max_distance = 120.0
	# Angled across the camera rather than along it, so bodies cast shadows to
	# the side where they read, instead of hiding directly behind themselves.
	light.rotation = Vector3(deg_to_rad(-52.0), deg_to_rad(Feel.CAMERA_AZIMUTH + 40.0), 0.0)
	add_child(light)


func _build_arena() -> void:
	var half := Feel.ARENA * 0.5

	var floor_mesh := BoxMesh.new()
	floor_mesh.size = Vector3(Feel.ARENA.x, 0.4, Feel.ARENA.y)
	var floor_node := MeshInstance3D.new()
	floor_node.mesh = floor_mesh
	floor_node.material_override = Shapes.tiled_floor(Feel.COLOUR_FLOOR)
	# Top face flush with y = 0, which is the plane everything else stands on.
	floor_node.position = Vector3(0.0, -0.2, 0.0)
	add_child(floor_node)

	_scatter_rubble()

	var t := Feel.WALL_THICKNESS
	var h := Feel.WALL_HEIGHT
	var slabs := [
		[Vector3(0.0, h * 0.5, -half.y - t * 0.5), Vector3(Feel.ARENA.x + t * 2.0, h, t)],
		[Vector3(0.0, h * 0.5, half.y + t * 0.5), Vector3(Feel.ARENA.x + t * 2.0, h, t)],
		[Vector3(-half.x - t * 0.5, h * 0.5, 0.0), Vector3(t, h, Feel.ARENA.y + t * 2.0)],
		[Vector3(half.x + t * 0.5, h * 0.5, 0.0), Vector3(t, h, Feel.ARENA.y + t * 2.0)],
	]
	var wall_material := Shapes.solid(Feel.COLOUR_WALL)

	for slab in slabs:
		var centre: Vector3 = slab[0]
		var size: Vector3 = slab[1]

		var body := StaticBody3D.new()
		body.collision_layer = 1
		body.collision_mask = 0
		body.position = centre
		var shape := BoxShape3D.new()
		shape.size = size
		var col := CollisionShape3D.new()
		col.shape = shape
		body.add_child(col)
		add_child(body)

		var mesh := BoxMesh.new()
		mesh.size = size
		var vis := MeshInstance3D.new()
		vis.mesh = mesh
		vis.material_override = wall_material
		vis.position = centre
		add_child(vis)


## Low blocks scattered across the floor, purely decorative — no collision, so
## they never interfere with a dash. They exist because a flat plane gives the
## eye nothing to measure movement against; a handful of objects casting their
## own small shadows makes the arena read as a place with depth rather than as a
## backdrop. Seeded, so the layout is the same every run rather than flickering
## into a new arrangement each restart.
func _scatter_rubble() -> void:
	var rng := Rng.new(4242)
	var half := Feel.ARENA * 0.5
	var material := Shapes.solid(Feel.COLOUR_WALL.darkened(0.15))

	for i in 26:
		var mesh := BoxMesh.new()
		var w := rng.randf_range(0.3, 1.1)
		mesh.size = Vector3(w, rng.randf_range(0.12, 0.34), rng.randf_range(0.3, 1.1))

		var block := MeshInstance3D.new()
		block.mesh = mesh
		block.material_override = material
		block.position = Vector3(
			rng.randf_range(-half.x + 1.5, half.x - 1.5),
			mesh.size.y * 0.5,
			rng.randf_range(-half.y + 1.5, half.y - 1.5)
		)
		block.basis = Basis(Vector3.UP, rng.randf_range(0.0, TAU))
		add_child(block)


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
	var tags := run.active_tags()
	if not tags.is_empty():
		lines.append("tags: " + ", ".join(tags))
	if not run.boons.is_empty():
		var names: Array[String] = []
		for b in run.boons:
			names.append(b.label())
		lines.append("boons: " + ", ".join(names))
	_hud.text = "\n".join(lines)


func _more_product(stats: StatBlock) -> float:
	return stats.more_multiplier(Damage.Type.PHYSICAL)


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
