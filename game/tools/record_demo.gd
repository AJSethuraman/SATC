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
const SECONDS := 16
const OUTPUT_DIR := "res://recording"

## Skip the first moments: the camera is still settling and the first wave has
## not closed yet, which makes for a limp opening shot.
const WARMUP_FRAMES := 20

var _pilot := DemoPilot.new()
var _main: Node
var _frame := 0
var _saved := 0


func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT_DIR))

	var packed: PackedScene = load("res://scenes/main.tscn")
	if packed == null:
		push_error("record_demo: could not load res://scenes/main.tscn")
		quit(1)
		return
	_main = packed.instantiate()
	root.add_child(_main)
	print("record_demo: recording %d frames at %d fps" % [SECONDS * FPS, FPS])


func _process(delta: float) -> bool:
	_frame += 1

	var player := get_first_node_in_group("player") as Player
	if player != null and player.health > 0.0:
		_pilot.drive(player, _enemies(), delta)
	_auto_accept_boon()

	if _frame <= WARMUP_FRAMES:
		return false

	var image := root.get_texture().get_image()
	if image != null:
		image.save_png("%s/frame_%05d.png" % [OUTPUT_DIR, _saved])
		_saved += 1

	if _saved >= SECONDS * FPS:
		print("record_demo: wrote %d frames to %s" % [_saved, OUTPUT_DIR])
		quit(0)
		return true
	return false


func _enemies() -> Array:
	var holder := _main.get_node_or_null("Enemies")
	return [] if holder == null else holder.get_children()


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
