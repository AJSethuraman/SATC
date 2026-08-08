extends SceneTree

## Boots the real game, lets it settle, and writes one rendered frame to a PNG.
##
##   xvfb-run -a godot --path game --rendering-driver opengl3 \
##     --script res://tools/capture_frame.gd
##
## Exists because the test suite can prove a hit deals 237 damage but cannot
## notice that nothing is on screen. A boot smoke test catches a _ready() that
## throws; it does not catch a camera pointed at empty space, a Control sized to
## nothing, or a z_index that buries the world. Those fail silently and look
## exactly like a working build from CI's point of view.
##
## So CI renders a frame and uploads it as an artifact, and the image can then be
## looked at directly. It is the closest thing to eyes on the game that a
## headless pipeline can offer.

const CAPTURE_AT_FRAME := 90
const OUTPUT := "res://frame.png"

var _frames := 0


func _initialize() -> void:
	var packed: PackedScene = load("res://scenes/main.tscn")
	if packed == null:
		push_error("capture_frame: could not load res://scenes/main.tscn")
		quit(1)
		return
	root.add_child(packed.instantiate())


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < CAPTURE_AT_FRAME:
		return false

	var image := root.get_texture().get_image()
	if image == null:
		push_error("capture_frame: viewport produced no image")
		quit(1)
		return true

	var err := image.save_png(OUTPUT)
	if err != OK:
		push_error("capture_frame: save_png failed with error %d" % err)
		quit(1)
		return true

	print("capture_frame: wrote %s (%dx%d)" % [OUTPUT, image.get_width(), image.get_height()])
	quit(0)
	return true
