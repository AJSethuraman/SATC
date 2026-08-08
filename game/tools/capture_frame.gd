extends SceneTree

## Boots the real game, lets it settle, writes one rendered frame to a PNG, and
## fails if that frame is essentially blank.
##
##   xvfb-run -a godot --path game --rendering-driver opengl3 \
##     --script res://tools/capture_frame.gd
##
## Exists because the test suite can prove a hit deals 237 damage but cannot
## notice that nothing is on screen. A boot smoke test catches a _ready() that
## throws; it does not catch a camera pointed at empty space, a Control sized to
## nothing, or a z_index that buries the world. Those fail silently and look
## exactly like a working build from CI's point of view — which is precisely how
## an empty grey window reached a human with every check green.
##
## The PNG is uploaded as a CI artifact so the frame can also just be looked at.

const CAPTURE_AT_FRAME := 90
const OUTPUT := "res://frame.png"

## Sample every Nth pixel in both axes. Plenty for "is anything drawing".
const SAMPLE_STEP := 8

## If one colour covers more than this share of sampled pixels, the scene is not
## drawing. A legitimate frame here has walls, a floor, a player and enemies on
## it, so it never comes close.
const MAX_FLAT_SHARE := 0.98

var _frames := 0


var _main: Node


func _initialize() -> void:
	var packed: PackedScene = load("res://scenes/main.tscn")
	if packed == null:
		push_error("capture_frame: could not load res://scenes/main.tscn")
		quit(1)
		return

	_main = packed.instantiate()
	# Diagnostics, because a scene that builds nothing looks identical to a scene
	# that built everything off-camera, and both render a flat frame.
	print("capture_frame: root is %s, script=%s" % [_main.get_class(), _main.get_script()])
	root.add_child(_main)
	print("capture_frame: viewport %s" % str(root.get_visible_rect().size))
	print("capture_frame: %d children after _ready:" % _main.get_child_count())
	for c in _main.get_children():
		var where := ""
		if c is Node2D:
			where = " at %s" % str((c as Node2D).global_position)
		elif c is Control:
			where = " at %s size %s" % [str((c as Control).position), str((c as Control).size)]
		print("   - %s (%s)%s" % [c.name, c.get_class(), where])


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

	var report := _flatness(image)
	print(
		"capture_frame: %s (%dx%d) — %d distinct sampled colours, most common covers %.1f%%"
		% [OUTPUT, image.get_width(), image.get_height(), report["distinct"], report["share"] * 100.0]
	)

	if report["share"] > MAX_FLAT_SHARE:
		push_error(
			"capture_frame: frame is one flat colour (%.1f%% of sampled pixels) — the scene is not drawing"
			% (report["share"] * 100.0)
		)
		quit(1)
		return true

	quit(0)
	return true


## How dominated the frame is by its single most common colour.
func _flatness(image: Image) -> Dictionary:
	var counts := {}
	var total := 0
	var y := 0
	while y < image.get_height():
		var x := 0
		while x < image.get_width():
			var key := image.get_pixel(x, y).to_rgba32()
			counts[key] = counts.get(key, 0) + 1
			total += 1
			x += SAMPLE_STEP
		y += SAMPLE_STEP

	var top := 0
	for k in counts:
		top = maxi(top, int(counts[k]))
	return {
		"distinct": counts.size(),
		"share": float(top) / maxf(1.0, float(total)),
	}
