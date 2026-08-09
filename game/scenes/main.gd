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
const SIGILS_PATH := "res://data/sigils.json"
const SPELLS_PATH := "res://data/spells.json"

const SPAWN_MARGIN := 2.5
const MIN_SPAWN_DISTANCE := 5.0

var run: RunState
var generator: ItemGenerator
var boon_pool: BoonPool
var book: InscriptionBook
var all_spells: Array = []
var bolt: Spell
var nova: Spell

var player: Player
var enemies_root: Node3D
var camera: IsoCamera

var _awaiting_reward := false
var _hitstop_frames := 0
var _hitstop_gap := 0
var _hud: Label
var _log: Label
var _build_panel: Label
var _card_slot: VBoxContainer
var _reward_layer: CanvasLayer


func _ready() -> void:
	randomize()
	generator = ItemGenerator.from_json(ITEMS_PATH)
	boon_pool = BoonPool.from_json(BOONS_PATH)
	book = InscriptionBook.from_json(SIGILS_PATH)
	all_spells = Spell.from_json(SPELLS_PATH)

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
	_attune(seed_v)

	if is_instance_valid(player):
		player.queue_free()
	player = Player.new()
	player.add_to_group("player")
	player.setup(run.build_stats(), camera)
	player.equip_spells(bolt, nova, run.active_behaviours())
	player.cast.connect(_on_player_cast)
	player.died.connect(_on_player_died)
	add_child(player)
	# Position after add_child: global_position on a node outside the tree logs
	# an error and returns identity. Harmless at the origin, which is exactly why
	# it sat in the log unnoticed.
	player.global_position = Vector3.ZERO

	camera.snap_to(Vector3.ZERO)
	_say("You wake attuned to %s. Descend." % run.school)
	_start_area()


## Pick the run's school and bind its two spells.
##
## Diablo II's Sorceress owns all three trees at once and specialises by where
## she spends points. There is no skill screen here and only two cast buttons,
## so the run is dealt a school instead — which keeps the thing that actually
## mattered about the choice: you are one element this run, and the boons and
## gear you find either flatter it or do not.
func _attune(seed_v: int) -> void:
	var schools := ["fire", "cold", "lightning"]
	run.school = schools[absi(seed_v) % schools.size()]
	var kit := Spell.of_school(all_spells, run.school)
	for s in kit:
		var spell := s as Spell
		if spell == null:
			continue
		if spell.shape == Spell.Shape.NOVA:
			nova = spell
		else:
			bolt = spell


func _start_area() -> void:
	_awaiting_reward = false
	for child in enemies_root.get_children():
		child.queue_free()

	var kind := Progression.kind_of(run.area_number)
	if kind == Progression.AreaKind.RESPITE:
		_open_respite()
		return

	var count := Progression.enemy_count(run.act_number, run.area_number)
	var boss_here := kind == Progression.AreaKind.BOSS
	for i in count:
		# The act's one elite leads its area; in a boss area the lead body is the
		# boss itself and the rest are escort.
		var lead := i == 0
		var elite := lead and Progression.has_elite(run.area_number)
		var e := Enemy.new()
		var stats: StatBlock = (
			RunState.boss_for_act(run.act_number) if (lead and boss_here)
			else RunState.enemy_for_depth(run.depth(), elite)
		)
		e.setup(stats, elite or (lead and boss_here), run.combat_rng.randi_range(0, 0x7FFFFFFF))
		e.died.connect(_on_enemy_died)
		enemies_root.add_child(e)
		e.global_position = _spawn_point()

	if boss_here:
		_say("%s. The way out is through." % _here())
	else:
		_say("%s — %d foes." % [_here(), count])
	_refresh_hud()


## An area with nothing in it. The act's only breathing space: it pays no reward
## and simply hands back health, which is what makes the areas either side of it
## worth pushing through at low health.
##
## This is where a reliquary deposit belongs once it has a UI — banking one item
## per run is a decision that wants somewhere the player is not being hit. The
## reliquary rules exist in core/ already; nothing here calls them yet.
func _open_respite() -> void:
	var stats := run.build_stats()
	run.health = minf(stats.max_health, run.health + stats.max_health * 0.5)
	player.health = run.health
	_say("%s. You catch your breath." % _here())
	_refresh_hud()
	_next_area()


## Spawn away from the player so an area never opens with a free hit.
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

	# A body that simply stops existing gives the kill no weight — you register
	# that the crowd is smaller, not that you killed something. A burst at the
	# spot costs one node and makes the kill the event.
	var pop := NovaBurst.new()
	pop.setup(1.7 if was_elite else 1.15, Feel.COLOUR_ELITE if was_elite else Feel.COLOUR_ENEMY)
	add_child(pop)
	pop.global_position = Vector3(at.x, 0.0, at.z)

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


## What clearing this area pays out. Combat areas alternate gear and blessings
## rather than granting both — see core/progression.gd for why.
func _offer_rewards() -> void:
	match Progression.reward_of(run.area_number):
		Progression.Reward.ITEM:
			_grant_item(0.5)
			_next_area()
		Progression.Reward.BOON:
			_offer_boon()
		Progression.Reward.ACT_PRIZE:
			# Arriving somewhere pays differently from passing through: gear
			# rolled deeper than the act would otherwise offer, and a blessing.
			_grant_item(0.85, 4)
			_offer_boon()
		_:
			_next_area()


func _grant_item(magic_chance: float, bonus_depth: int = 0) -> void:
	# Loot first, so a tag it grants can widen the boon offer immediately — this
	# ordering is the whole gear-gates-boons loop in one line.
	var drop := generator.roll_item(run.depth() + 3 + bonus_depth, run.loot_rng, magic_chance)
	var enemy := RunState.enemy_for_depth(run.depth())
	var before := run.build_stats().expected_hit(enemy)
	run.equip(drop)
	var after := run.build_stats().expected_hit(enemy)
	_show_item_card(drop, after / maxf(before, 0.01) - 1.0)


## Hold the drop on screen. See scenes/item_card.gd — every affix, socket and
## inscription in the game used to collapse into one line of scrolling log.
func _show_item_card(drop: Item, damage_delta: float) -> void:
	if _card_slot == null:
		return
	# Never stack more than two; a boss area grants gear and a boon at once and
	# a column of cards would cover the fight.
	while _card_slot.get_child_count() >= 2:
		_card_slot.get_child(0).free()
	var card := ItemCard.new()
	_card_slot.add_child(card)
	card.setup(drop, damage_delta)


func _offer_boon() -> void:
	var offer := boon_pool.offer(
		run.boon_rng, run.owned_boon_ids(), run.owned_boon_groups(), run.active_tags(), 3
	)
	if offer.is_empty():
		_next_area()
		return
	_show_reward_ui(offer)


func _next_area() -> void:
	var was_boss := Progression.kind_of(run.area_number) == Progression.AreaKind.BOSS
	if not run.advance_area():
		_say("Ashfall is behind you. The run is over — press R.")
		return
	var stats := run.build_stats()
	# Clearing a boss restores more than passing through an area does; the act
	# boundary is where a run gets to breathe.
	var heal := 0.35 if was_boss else 0.22
	run.health = minf(stats.max_health, run.health + stats.max_health * heal)
	player.setup(stats, camera)
	player.equip_spells(bolt, nova, run.active_behaviours())
	player.health = run.health
	if was_boss:
		_say("%s." % Progression.act_label(run.act_number))
	_start_area()


func _on_player_died() -> void:
	_say("You died in %s, %s. Press R." % [_here(), Progression.act_label(run.act_number)])


## Where the run is, in words rather than in coordinates. Every message that
## names a place goes through here so they cannot disagree.
func _here() -> String:
	return Progression.area_name(run.act_number, run.area_number)


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_R:
		if is_instance_valid(player) and player.health <= 0.0:
			_clear_reward_ui()
			_start_run(randi())


# --- combat -------------------------------------------------------------


func _on_player_cast(spell: Spell, origin: Vector3, facing: Vector3) -> void:
	match spell.shape:
		Spell.Shape.PROJECTILE:
			_fire_projectile(spell, origin, facing)
		Spell.Shape.NOVA:
			_detonate_nova(spell, origin)


func _fire_projectile(spell: Spell, origin: Vector3, facing: Vector3) -> void:
	var shot := Projectile.new()
	shot.setup(spell, player.stats, facing, run.combat_rng, player.behaviours)
	shot.hit_enemy.connect(_on_projectile_hit)
	enemies_root.add_child(shot)
	shot.global_position = origin + Vector3(0.0, 1.0, 0.0) + facing * 0.7


## Everything within reach, at once. The reason a caster wants a crowd.
func _detonate_nova(spell: Spell, origin: Vector3) -> void:
	var burst := NovaBurst.new()
	burst.setup(spell.radius, Projectile.tint_for_spell(spell, player.behaviours))
	# Parented to the arena rather than to Enemies, which gets cleared wholesale
	# on an area change — a ring is not something to wipe mid-flourish.
	add_child(burst)
	burst.global_position = Vector3(origin.x, 0.0, origin.z)

	var any_crit := false
	var hits := 0
	for node in enemies_root.get_children():
		var e := node as Enemy
		if e == null or e.is_queued_for_deletion():
			continue
		var to_enemy: Vector3 = e.global_position - origin
		to_enemy.y = 0.0
		if to_enemy.length() > spell.radius + Feel.ENEMY_RADIUS:
			continue
		var result := Damage.resolve(player.stats, e.stats, run.combat_rng, spell.split())
		result.total *= spell.damage_scale * spell.roll_variance(run.combat_rng)
		e.take_hit(result, origin)
		_show_hit(e.global_position, result)
		hits += 1
		any_crit = any_crit or result.was_crit
	if hits > 0:
		_impact(any_crit)
	camera.add_shake(Feel.SHAKE_CRIT)


func _on_projectile_hit(enemy: Node3D, result: Damage.Result, at: Vector3) -> void:
	var where := at if enemy == null else enemy.global_position
	_show_hit(where, result)
	_impact(result.was_crit)


## Put the resolved figure on screen. Every modifier in core/ collapses into
## this one number, and it was previously visible nowhere at all — so a boon
## could promise anything and there was no way to tell whether it delivered.
func _show_hit(where: Vector3, result: Damage.Result) -> void:
	var number := HitNumber.new()
	add_child(number)
	number.global_position = where + Vector3(0.0, Feel.ENEMY_HEIGHT * 0.8, 0.0)
	number.setup(result.total, result.was_crit, run.combat_rng.randf_range(-1.0, 1.0))


## Hit-stop and shake. The durations live in Feel; this just applies them.
##
## Counted down in frames rather than awaited on a timer: a wall-clock wait is
## wrong whenever the engine is not running at real speed, and time_scale left
## stuck at 0.05 because a coroutine never resumed is a spectacular bug.
func _impact(crit: bool) -> void:
	camera.add_shake(Feel.SHAKE_CRIT if crit else Feel.SHAKE_NORMAL)
	# Shake always, freeze sparingly — see Feel.HITSTOP_GAP_FRAMES.
	if _hitstop_gap > 0 and not crit:
		return
	_hitstop_frames = maxi(
		_hitstop_frames, Feel.HITSTOP_FRAMES_CRIT if crit else Feel.HITSTOP_FRAMES_NORMAL
	)
	_hitstop_gap = Feel.HITSTOP_GAP_FRAMES


func _process(delta: float) -> void:
	_hitstop_gap = maxi(0, _hitstop_gap - 1)
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

	# Bloom. The spell materials have been additive and unlit for a while, which
	# makes them bright — but bright is not the same as luminous, and without
	# glow a bolt is a green shape rather than something giving off light. This
	# is the cheapest line in the project per unit of "that looks like magic".
	#
	# The threshold sits just under 1.0 so only the spell effects cross it: the
	# floor, the walls and the bodies are all far darker than that, so nothing
	# in the arena smears.
	env.glow_enabled = true
	env.glow_intensity = 0.75
	env.glow_strength = 1.0
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	# glow_bloom is a floor applied to every pixel regardless of threshold, so
	# any non-zero value blooms the whole image. At 0.12 it turned a near-black
	# arena into a pale mauve haze and washed the bodies out — the opposite of
	# the problem it was added to solve. Only the threshold should decide what
	# glows.
	env.glow_bloom = 0.0
	# At 1.0 only pixels that clip white cross it, which in this palette means
	# the additive spell effects and nothing else. The scene renders LDR, so a
	# threshold below 1.0 starts catching the grout lines and the player.
	env.glow_hdr_threshold = 1.0

	var holder := WorldEnvironment.new()
	holder.environment = env
	add_child(holder)

	var light := DirectionalLight3D.new()
	light.light_color = Feel.LIGHT_COLOUR
	light.light_energy = Feel.LIGHT_ENERGY
	light.shadow_enabled = true
	# The arena is 26x20m and never moves, so spreading the shadow map over 120m
	# across four cascades wasted almost all of its resolution. The acne that
	# bought was invisible against a near-black floor and then showed up as
	# stripes through the first bright thing ever drawn on it — the nova ring.
	# One cascade over 40m puts every texel where the game actually happens.
	light.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	light.directional_shadow_max_distance = 40.0
	# Enough bias to stop the floor self-shadowing into fine hatching. Only ever
	# visible through something bright drawn on the floor, but the nova ring is
	# exactly that. Kept modest: overshoot detaches the bodies from their own
	# shadows, which costs far more than the acne did.
	light.shadow_bias = 0.16
	light.shadow_normal_bias = 2.5
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

	for i in 16:
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

	# The build, down the right-hand side. Skills, gear and blessings have all
	# existed for a long time and none of them have ever been on screen: a viewer
	# could watch a whole run and not learn that the character has two spells,
	# five equipment slots or a boon list. A panel that is simply always there is
	# the cheapest possible fix and needs no interaction to read.
	_build_panel = Label.new()
	_build_panel.add_theme_font_size_override("font_size", 14)
	_build_panel.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_build_panel.anchor_left = 1.0
	_build_panel.anchor_right = 1.0
	_build_panel.offset_left = -330.0
	_build_panel.offset_right = -16.0
	_build_panel.offset_top = 12.0
	layer.add_child(_build_panel)

	_card_slot = VBoxContainer.new()
	_card_slot.anchor_left = 1.0
	_card_slot.anchor_right = 1.0
	_card_slot.anchor_top = 1.0
	_card_slot.anchor_bottom = 1.0
	_card_slot.offset_left = -340.0
	_card_slot.offset_right = -16.0
	_card_slot.offset_top = -300.0
	_card_slot.offset_bottom = -16.0
	_card_slot.alignment = BoxContainer.ALIGNMENT_END
	_card_slot.add_theme_constant_override("separation", 6)
	layer.add_child(_card_slot)


## The right-hand column: what this character is made of.
##
## Skills first, because the demo has never once shown that the class casts two
## named spells with costs — a viewer could only infer it from watching mana
## move. Then gear by slot, then blessings, so the accumulation over an act is
## visible as a list that grows rather than as numbers that quietly change.
func _refresh_build_panel() -> void:
	if _build_panel == null or run == null:
		return
	var lines: Array[String] = []

	if bolt != null:
		lines.append("%s   %d mp" % [bolt.display_name, roundi(bolt.cost)])
	if nova != null:
		lines.append("%s   %d mp" % [nova.display_name, roundi(nova.cost)])

	lines.append("")
	for slot in ["weapon", "armour", "ring", "amulet", "helm", "boots"]:
		if run.gear.has(slot):
			var item: Item = run.gear[slot]
			var mark := "*" if item.is_inscribed() else ""
			lines.append("%s%s" % [item.display_name(), mark])

	if not run.boons.is_empty():
		lines.append("")
		for b in run.boons:
			lines.append(b.label())

	_build_panel.text = "\n".join(lines)


func _refresh_hud() -> void:
	if _hud == null or run == null or not is_instance_valid(player):
		return
	var stats := player.stats
	var lines := [
		"Act %s · %s   %d/%d     HP %d / %d     MP %d / %d"
			% [
				Progression.act_numeral(run.act_number), _here(), run.area_number,
				Progression.AREAS_PER_ACT, roundi(player.health), roundi(stats.max_health),
				roundi(player.mana), roundi(stats.max_mana)
			],
		"%s   dmg %d-%d   crit %.0f%%   cast x%.2f   more x%.2f"
			% [
				run.school, roundi(stats.weapon_min), roundi(stats.weapon_max),
				stats.crit_chance * 100.0, stats.cast_speed, _more_product(stats)
			],
	]
	var tags := run.active_tags()
	if not tags.is_empty():
		lines.append("tags: " + ", ".join(tags))
	var behaviours := run.active_behaviours()
	if not behaviours.is_empty():
		lines.append("inscribed: " + ", ".join(behaviours))
	_refresh_build_panel()
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
	_next_area()


func _clear_reward_ui() -> void:
	if is_instance_valid(_reward_layer):
		_reward_layer.queue_free()
	_reward_layer = null
