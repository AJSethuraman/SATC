extends SceneTree

## Records a gameplay demo as a PNG sequence, for CI to encode into a video.
##
##   xvfb-run -a godot --path game --rendering-driver opengl3 --fixed-fps 30 \
##     --script res://tools/record_demo.gd
##
## `--fixed-fps 30` is load-bearing: it pins delta to 1/30 regardless of how slow
## the software rasteriser actually is, so the recording plays back at real speed
## instead of in slow motion. It is also why hit-stop is counted in frames rather
## than seconds — a wall-clock freeze would swallow half the footage here.
##
## The game is driven by tools/demo_pilot.gd rather than by input, and boons are
## auto-accepted, so the demo keeps moving through floors instead of stalling on
## a menu nobody is there to click.

const FPS := 30
## Hard ceiling, not a target. The recording now ends when the *run* reaches a
## natural stopping point — the act is cleared or the player dies — because a
## clip that stops mid-area shows a fight without showing what it was for. This
## only exists so a pilot that somehow survives forever cannot render until the
## job times out.
## Measured, not guessed: the pilot clears roughly one area every sixteen
## seconds, so eight areas plus a boss needs about two and a half minutes. At
## 100 the recording stopped in The Last Furnace, one area short of the fight
## the whole act builds to — which is precisely the ending the old
## fixed-length clip kept missing.
const MAX_SECONDS := 155
const OUTPUT_DIR := "res://recording"

## Keep rolling for a moment after the run ends, so the last kill and the act
## banner are on screen rather than cut off by the final frame.
const TAIL_FRAMES := 45

## Skip the first moments: the camera is still settling and the first wave has
## not closed yet, which makes for a limp opening shot.
const WARMUP_FRAMES := 20

var _pilot := DemoPilot.new()
var _main: Node
var _frame := 0
var _saved := 0

## Census of what was actually alive while recording.
##
## Reading a recording back for evidence that a system works is a trap: I spent
## three rounds deciding bolts were missing because a colour probe kept matching
## something else on screen, when the question — did a Projectile exist and where
## — is one the engine can answer directly. Anything hard to see in the footage
## gets counted here instead of eyeballed.
var _bolt_frames := 0
var _bolt_peak := 0
var _nova_frames := 0
## The run's story, for the log: which areas were reached and when it ended.
var _areas_seen: Array[String] = []
var _tail := -1
var _ending := "still going"


func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT_DIR))

	var packed: PackedScene = load("res://scenes/main.tscn")
	if packed == null:
		push_error("record_demo: could not load res://scenes/main.tscn")
		quit(1)
		return
	_main = packed.instantiate()
	root.add_child(_main)
	print("record_demo: recording until the act ends, at most %d frames" % [MAX_SECONDS * FPS])


func _process(delta: float) -> bool:
	_frame += 1

	var player := get_first_node_in_group("player") as Player
	if player != null and player.health > 0.0:
		_pilot.drive(player, _enemies(), delta)
	_auto_accept_boon()

	if _frame <= WARMUP_FRAMES:
		return false
	_census()

	var image := root.get_texture().get_image()
	if image != null:
		image.save_png("%s/frame_%05d.png" % [OUTPUT_DIR, _saved])
		_saved += 1

	if _saved >= MAX_SECONDS * FPS or _run_over():
		_report()
		quit(0)
		return true
	return false


## Has the run reached a natural stopping point?
##
## The act being cleared or the player dying are both endings; a fixed sixteen
## seconds is neither. A clip that stops in the middle of area three shows a
## fight without showing what the fight was for, which is most of why the demo
## never communicated that this game has a structure.
##
## Returns true only after the tail has played out, so the last kill and the act
## banner are on screen instead of being cut off by the final frame.
func _run_over() -> bool:
	if _tail >= 0:
		_tail -= 1
		return _tail <= 0

	var run: RunState = _main.get("run")
	if run == null:
		return false

	var here := "%s %d/%d" % [
		Progression.area_name(run.act_number, run.area_number),
		run.area_number,
		Progression.AREAS_PER_ACT,
	]
	if not _areas_seen.has(here):
		_areas_seen.append(here)
		print("record_demo: entered %s" % here)

	var player := get_first_node_in_group("player") as Player
	if player != null and player.health <= 0.0:
		_ending = "died in %s" % here
		_tail = TAIL_FRAMES
		return false

	if run.act_number > 1:
		_ending = "cleared %s" % Progression.act_label(1)
		_tail = TAIL_FRAMES
		return false

	return false


func _report() -> void:
	print("record_demo: wrote %d frames to %s" % [_saved, OUTPUT_DIR])
	print("record_demo: run %s after %d areas" % [_ending, _areas_seen.size()])
	print(
		"record_demo: bolts on screen in %d/%d frames (peak %d), nova ring in %d"
		% [_bolt_frames, _saved, _bolt_peak, _nova_frames]
	)


## Count the spell effects alive this frame. A zero here means casts are not
## spawning; a healthy count with nothing in the footage means they are spawning
## and not being drawn. Those are different bugs and the log should say which.
func _census() -> void:
	var holder := _main.get_node_or_null("Enemies")
	if holder == null:
		return
	var bolts := 0
	for child in holder.get_children():
		if child is Projectile:
			bolts += 1
	if bolts > 0:
		_bolt_frames += 1
	_bolt_peak = maxi(_bolt_peak, bolts)

	for child in _main.get_children():
		if child is NovaBurst:
			_nova_frames += 1
			break


func _enemies() -> Array:
	var holder := _main.get_node_or_null("Enemies")
	if holder == null:
		return []
	# Projectiles share this parent, so filter rather than handing the pilot
	# bolts to chase.
	return holder.get_children().filter(func(n): return n is Enemy)


## Click the first boon on offer. Without this the run stops dead at the reward
## panel, which is not what the demo is meant to show.
func _auto_accept_boon() -> void:
	var button := _first_button(_main)
	if button != null:
		button.pressed.emit()


func _first_button(node: Node) -> Button:
	for child in node.get_children():
		var button := child as Button
		if button != null:
			return button
		var found := _first_button(child)
		if found != null:
			return found
	return null
