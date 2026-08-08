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

## Lower bound on distinct sampled colours. Placeholder art plus anti-aliased
## HUD text clears this comfortably; a window showing only the engine's own
## overlay does not.
const MIN_DISTINCT_COLOURS := 8

var _frames := 0


var _main: Node


func _initialize() -> void:
	var packed: PackedScene = load("res://scenes/main.tscn")
	if packed == null:
		push_error("capture_frame: could not load res://scenes/main.tscn")
		quit(1)
		return

	_main = packed.instantiate()
	print("capture_frame: root is %s, script=%s" % [_main.get_class(), _main.get_script()])
	root.add_child(_main)
	print("capture_frame: viewport %s" % str(root.get_visible_rect().size))


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < CAPTURE_AT_FRAME:
		return false

	_report_scene()

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
	# Which colour dominates is the whole diagnosis: the engine's default clear
	# colour means nothing drew, the arena floor colour means it drew and the
	# camera is simply looking at empty floor.
	print("capture_frame: dominant colours %s" % str(report["top"]))

	# What "nothing drew" actually looks like is not "one flat colour" — a large
	# arena is legitimately ~99% floor, and an earlier version of this check
	# failed the build over exactly that. It looks like the frame being dominated
	# by the engine's own clear colour, because that is the only thing left when
	# the scene contributes nothing.
	#
	# That failure is not hypothetical either: running the project before it has
	# been imported leaves class_name globals unregistered, main.gd fails to
	# compile, the root node silently loses its script, and the window shows the
	# clear colour and nothing else.
	var clear_colour: Color = ProjectSettings.get_setting(
		"rendering/environment/defaults/default_clear_color", Color(0.3, 0.3, 0.3)
	)
	if report["dominant"] == clear_colour.to_html(false):
		push_error(
			"capture_frame: the frame is mostly the engine clear colour (#%s) — the scene "
			% clear_colour.to_html(false)
			+ "contributed nothing. Usually a script that failed to compile."
		)
		quit(1)
		return true

	if int(report["distinct"]) < MIN_DISTINCT_COLOURS:
		push_error(
			"capture_frame: only %d distinct colours in the frame — nothing but flat background"
			% int(report["distinct"])
		)
		quit(1)
		return true

	quit(0)
	return true


## What the scene actually contains and where the camera is pointing, at the
## moment of capture. A scene that built nothing and a scene that built
## everything just off-camera produce the same flat frame, so both have to be
## ruled out explicitly rather than inferred.
func _report_scene() -> void:
	print("capture_frame: at frame %d, %d children:" % [_frames, _main.get_child_count()])
	for c in _main.get_children():
		var extra := ""
		if c is Node2D:
			var n2 := c as Node2D
			extra = " pos=%s visible=%s z=%d" % [str(n2.global_position), n2.visible, n2.z_index]
		elif c is Control:
			var ct := c as Control
			extra = (
				" pos=%s size=%s visible=%s z=%d"
				% [str(ct.global_position), str(ct.size), ct.visible, ct.z_index]
			)
		elif c is CanvasLayer:
			extra = " layer=%d" % (c as CanvasLayer).layer
		print("   - %s (%s)%s" % [c.name, c.get_class(), extra])

	var cam := _main.get_viewport().get_camera_2d()
	if cam == null:
		print("capture_frame: NO active Camera2D")
	else:
		print("capture_frame: camera pos=%s zoom=%s" % [str(cam.global_position), str(cam.zoom)])
	print("capture_frame: canvas_transform=%s" % str(_main.get_viewport().canvas_transform))


## How dominated the frame is by its single most common colour, plus which
## colours those are.
func _flatness(image: Image) -> Dictionary:
	var counts := {}
	var total := 0
	var y := 0
	while y < image.get_height():
		var x := 0
		while x < image.get_width():
			var key := image.get_pixel(x, y).to_html(false)
			counts[key] = counts.get(key, 0) + 1
			total += 1
			x += SAMPLE_STEP
		y += SAMPLE_STEP

	var ranked := counts.keys()
	ranked.sort_custom(func(a, b): return int(counts[a]) > int(counts[b]))

	var top_list: Array[String] = []
	for i in mini(5, ranked.size()):
		var key: String = ranked[i]
		top_list.append("#%s %.1f%%" % [key, 100.0 * float(counts[key]) / maxf(1.0, float(total))])

	var top := 0 if ranked.is_empty() else int(counts[ranked[0]])
	return {
		"distinct": counts.size(),
		"share": float(top) / maxf(1.0, float(total)),
		"dominant": "" if ranked.is_empty() else str(ranked[0]),
		"top": top_list,
	}
