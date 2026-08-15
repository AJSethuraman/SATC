class_name CharacterRig
extends Node3D

## A jointed humanoid built from primitives, animated procedurally.
##
## A capsule cannot read as a character no matter how well it is lit, because a
## character is legible through its *articulation* — you read a person from the
## swing of their legs, the counter-swing of their arms, the twist of a torso
## into a swing. None of that is available to a single blob.
##
## So this is a small skeleton: hips, torso, head, two arms, two legs, and a
## weapon, each a box hanging off a pivot at its joint. Nothing here is authored
## art — every pose is computed each frame from a handful of inputs the owning
## body sets (how fast it is moving, whether it is mid-swing, whether it is
## dashing). That is the honest ceiling of what can be built without an artist,
## but a figure with a walk cycle clears a capsule by a wide margin.
##
## Proportions are expressed as fractions of total height so the same rig serves
## the player, a regular enemy and a scaled-up elite.
##
## The demon kinds exist because "five bodies in slightly different reds" is not
## a bestiary. A silhouette is the only thing readable at this camera distance
## and this body size — you cannot see a face, a texture or a costume, so
## whatever tells you what you are fighting has to be in the outline. Horns,
## hunch, limb length and a tail are cheap, and between them they are the whole
## difference between "enemy" and "imp".
##
## The player stays human-shaped on purpose: it is the only upright, unhorned,
## weapon-carrying figure on the screen, so the thing you most need to find is
## the thing least like everything else.

enum Kind {
	HUMAN,
	## Small, hunched, oversized head, long arms. The chaff.
	IMP,
	## Heavy and wide, tiny head, huge arms, big horns. Reads slow and it is.
	BRUTE,
	## Tall and thin, long legs, whipping tail. Reads fast and it is.
	STALKER,
	## The player. Robed, hooded, carrying a staff rather than a sword — the
	## Diablo II Sorceress silhouette, which is almost entirely skirt and hood.
	SORCERESS,
}

const LEG_FRACTION := 0.44
const TORSO_FRACTION := 0.32
const HEAD_FRACTION := 0.18
const ARM_FRACTION := 0.34
const WIDTH_FRACTION := 0.30

## Peak leg swing at full running speed, in degrees.
const LEG_SWING := 42.0
## Arms counter-swing a little less than the legs do.
const ARM_SWING := 30.0
## Strides per second at full speed. Too high reads as a scurry.
const STRIDE_RATE := 1.5
const IDLE_RATE := 0.9
## How far the torso twists into a swing.
const TORSO_TWIST := 34.0

# --- inputs, written by the owning body each frame ----------------------
## 0 at a standstill, 1 at full move speed.
var speed_ratio := 0.0
## -1 when not attacking, otherwise 0..1 across the whole swing.
var attack_phase := -1.0
var dashing := false
## Forward tip of the whole body, in radians. Negative leans into the facing
## direction. Squash-and-stretch works on a blob but not on a figure with legs —
## stretching a standing humanoid along its facing axis reads as it lying down,
## so a dash leans the body instead of scaling it.
var lean := 0.0
## Extra silhouette scale, for hit reactions and telegraphs.
var shape := Vector3.ONE
var tint := Color.WHITE

var _height := 1.7
## The leg fraction this particular body was built with — the hips ride on it
## every frame, and a stalker's hips are nowhere near a brute's.
var _leg_fraction := LEG_FRACTION
## Forward pitch of the torso, in radians. The cheapest "not human" signal
## available: an upright figure reads as a person whatever else you hang on it.
var _hunch := 0.0
var _phase := 0.0
var _twist := 0.0
## Tracked rather than read back from the node: assigning a scaled Basis makes
## rotation.y a lossy round-trip, and the facing would slowly drift.
var _yaw := 0.0

var _hips: Node3D
var _torso: Node3D
var _head: MeshInstance3D
var _arm_l: Node3D
var _arm_r: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _weapon: MeshInstance3D

var _skin: StandardMaterial3D
var _head_material: StandardMaterial3D
var _tail_joints: Array[Node3D] = []
var _accent: StandardMaterial3D


func build(height: float, colour: Color, with_weapon: bool, kind: Kind = Kind.HUMAN) -> void:
	_height = height
	# Outline width scales with the body so an elite is not hairline-thin and
	# a bolt-sized prop is not drawn in marker pen. At 0.011 the line came out
	# under two pixels at this camera distance — present in the buffer, absent
	# to the eye. An outline either states the silhouette or it is not worth
	# drawing.
	var line := height * 0.038
	_skin = Shapes.body(colour, line)
	_accent = Shapes.body(colour.darkened(0.28), line)

	# Proportions per kind. These are the whole bestiary: nothing below this
	# point knows which creature it is building.
	var leg_f := LEG_FRACTION
	var torso_f := TORSO_FRACTION
	var head_f := HEAD_FRACTION
	var arm_f := ARM_FRACTION
	var width_f := WIDTH_FRACTION
	var horn := 0.0
	var tail := 0.0
	var clawed := false

	match kind:
		Kind.IMP:
			leg_f = 0.32
			torso_f = 0.30
			head_f = 0.27
			arm_f = 0.42
			width_f = 0.31
			horn = 0.46
			tail = 0.52
			clawed = true
			_hunch = deg_to_rad(22.0)
		Kind.BRUTE:
			leg_f = 0.38
			torso_f = 0.40
			head_f = 0.14
			arm_f = 0.48
			width_f = 0.48
			horn = 0.62
			clawed = true
			_hunch = deg_to_rad(26.0)
		Kind.SORCERESS:
			# A robe reads as one tapering mass from the shoulders down, so the
			# legs shrink to almost nothing and the skirt does the work. This is
			# why the Sorceress is recognisable at Diablo II's zoom while a
			# figure in trousers is not: her silhouette is a triangle.
			leg_f = 0.30
			torso_f = 0.36
			head_f = 0.15
			arm_f = 0.34
			width_f = 0.24
		Kind.STALKER:
			leg_f = 0.54
			torso_f = 0.26
			head_f = 0.16
			arm_f = 0.46
			width_f = 0.19
			horn = 0.34
			tail = 0.8
			clawed = true
			_hunch = deg_to_rad(14.0)

	_leg_fraction = leg_f
	var leg_len := height * leg_f
	var torso_h := height * torso_f
	var head_size := height * head_f
	var arm_len := height * arm_f
	var width := height * width_f

	_hips = Node3D.new()
	_hips.position = Vector3(0.0, leg_len, 0.0)
	add_child(_hips)

	_torso = Node3D.new()
	_hips.add_child(_torso)
	var torso_mesh := _box(Vector3(width, torso_h, width * 0.62), _skin)
	torso_mesh.position = Vector3(0.0, torso_h * 0.5, 0.0)
	_torso.add_child(torso_mesh)

	_head_material = Shapes.body(colour.lightened(0.18), line)
	_head = _box(Vector3(head_size * 0.86, head_size, head_size * 0.86), _head_material)
	_head.position = Vector3(0.0, torso_h + head_size * 0.55, 0.0)
	_torso.add_child(_head)

	# Arms hang from the shoulders; legs from the hips. Each limb is a box
	# offset below its pivot so rotating the pivot swings it from the joint.
	var shoulder_y := torso_h * 0.86
	var shoulder_x := width * 0.5 + arm_len * 0.09
	_arm_l = _limb(Vector3(-shoulder_x, shoulder_y, 0.0), arm_len, arm_len * 0.17, _accent)
	_arm_r = _limb(Vector3(shoulder_x, shoulder_y, 0.0), arm_len, arm_len * 0.17, _accent)
	_torso.add_child(_arm_l)
	_torso.add_child(_arm_r)

	var hip_x := width * 0.30
	_leg_l = _limb(Vector3(-hip_x, 0.0, 0.0), leg_len, leg_len * 0.21, _accent)
	_leg_r = _limb(Vector3(hip_x, 0.0, 0.0), leg_len, leg_len * 0.21, _accent)
	_hips.add_child(_leg_l)
	_hips.add_child(_leg_r)

	if horn > 0.0:
		_add_horns(head_size, horn, line, colour)
	if kind != Kind.HUMAN:
		_add_eyes(head_size)
	if tail > 0.0:
		_add_tail(height * tail, width, line, colour)
	if clawed:
		_add_claws(_arm_l, arm_len, line, colour)
		_add_claws(_arm_r, arm_len, line, colour)

	if kind == Kind.SORCERESS:
		_add_robe(height, leg_len, width, line, colour)
		_add_hood(head_size, line, colour)
		_add_staff(height, arm_len, line, colour)
	elif with_weapon:
		var blade_len := height * 0.5
		_weapon = _box(Vector3(height * 0.05, blade_len, height * 0.1), Shapes.body(
			Color(0.78, 0.80, 0.86)
		))
		# Held out from the fist at the end of the right arm, angled forward.
		_weapon.position = Vector3(0.0, -arm_len * 0.92, -blade_len * 0.34)
		_weapon.basis = Basis(Vector3.RIGHT, deg_to_rad(-78.0))
		_arm_r.add_child(_weapon)


## The skirt of the robe: a wide cone from the waist to the floor.
##
## Hides the legs entirely, which is the point — a walking robe should read as
## a body gliding rather than as two sticks alternating, and hiding the legs is
## far cheaper than animating a cloth simulation nobody asked for.
func _add_robe(height: float, leg_len: float, width: float, line: float, colour: Color) -> void:
	var skirt := CylinderMesh.new()
	skirt.height = leg_len + height * 0.16
	skirt.top_radius = width * 0.52
	skirt.bottom_radius = width * 1.15
	skirt.radial_segments = 8
	skirt.rings = 1

	var inst := MeshInstance3D.new()
	inst.mesh = skirt
	inst.material_override = Shapes.body(colour.darkened(0.18), line)
	# Hangs from the hips down; the hips sit at leg_len, so centre it below them.
	inst.position = Vector3(0.0, -(leg_len + height * 0.16) * 0.5 + height * 0.05, 0.0)
	_hips.add_child(inst)


## A hood: a slightly larger, darker box sitting over the skull and back of the
## head, open at the front so the face still catches the light.
func _add_hood(head_size: float, line: float, colour: Color) -> void:
	var hood := _box(
		Vector3(head_size * 1.12, head_size * 0.78, head_size * 1.02),
		Shapes.body(colour.darkened(0.42), line)
	)
	hood.position = Vector3(0.0, head_size * 0.26, head_size * 0.1)
	_head.add_child(hood)


## A staff, held out from the off hand, with a lit stone at the head of it.
##
## The stone is above the bloom threshold, so a Sorceress standing in a dark
## arena is lit by the one thing she is carrying. It is also the only part of
## the player that glows, which makes the staff head a second place to find her
## when the body is behind something.
func _add_staff(height: float, arm_len: float, line: float, colour: Color) -> void:
	var shaft_len := height * 0.82
	_weapon = _box(
		Vector3(height * 0.028, shaft_len, height * 0.028),
		Shapes.body(Color(0.42, 0.31, 0.26), line)
	)
	_weapon.position = Vector3(0.0, -arm_len * 0.95 + shaft_len * 0.28, 0.0)
	_arm_l.add_child(_weapon)

	var stone := SphereMesh.new()
	stone.radius = height * 0.045
	stone.height = height * 0.09
	stone.radial_segments = 8
	stone.rings = 4
	var lit := MeshInstance3D.new()
	lit.mesh = stone
	lit.material_override = Shapes.glow(Color(0.72, 0.86, 1.0))
	lit.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	lit.position = Vector3(0.0, shaft_len * 0.55, 0.0)
	_weapon.add_child(lit)


## A pair of cones off the top of the skull, swept out and back.
##
## Cones rather than boxes because this is the one place the extra primitive
## earns itself: a tapered horn reads as a horn at any size, and a rectangular
## one reads as a block glued to a head.
func _add_horns(head_size: float, scale_v: float, line: float, colour: Color) -> void:
	var material := Shapes.body(colour.darkened(0.42), line)
	for side in [-1.0, 1.0]:
		var cone := CylinderMesh.new()
		cone.height = head_size * scale_v * 1.5
		cone.bottom_radius = head_size * 0.17
		cone.top_radius = 0.0
		# Faceted, to sit with the rest of the low-poly silhouette.
		cone.radial_segments = 6
		cone.rings = 1

		var inst := MeshInstance3D.new()
		inst.mesh = cone
		inst.material_override = material
		inst.position = Vector3(side * head_size * 0.34, head_size * 0.46, 0.0)
		inst.basis = Basis(Vector3.FORWARD, deg_to_rad(-26.0 * side)) * Basis(
			Vector3.RIGHT, deg_to_rad(-18.0)
		)
		_head.add_child(inst)


## Two hot points on the front of the skull.
##
## Additive and above the bloom threshold, so they are the only part of a body
## that glows. Worth more than their size suggests: a dark silhouette with two
## lit eyes reads as something looking at you, and the same silhouette without
## them reads as furniture.
func _add_eyes(head_size: float) -> void:
	var material := Shapes.glow(Color(1.0, 0.62, 0.22))
	material.no_depth_test = false
	for side in [-1.0, 1.0]:
		var mesh := BoxMesh.new()
		mesh.size = Vector3(head_size * 0.2, head_size * 0.11, head_size * 0.06)
		var inst := MeshInstance3D.new()
		inst.mesh = mesh
		inst.material_override = material
		inst.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# Forward is -Z; sit them just proud of the face so they never z-fight.
		inst.position = Vector3(side * head_size * 0.21, head_size * 0.06, -head_size * 0.46)
		_head.add_child(inst)


## A jointed tail hanging off the hips, tapering to a point.
##
## Built as a chain so it can whip rather than swing as one rigid rod — each
## joint lags the one before it, which is what makes it read as attached to a
## creature rather than bolted to a prop.
func _add_tail(length: float, width: float, line: float, colour: Color) -> void:
	var material := Shapes.body(colour.darkened(0.34), line)
	var segments := 4
	var parent := _hips
	for i in segments:
		var t := float(i) / float(segments)
		var seg_len := length / float(segments)
		var thick := width * lerpf(0.24, 0.06, t)

		var joint := Node3D.new()
		joint.position = Vector3(0.0, 0.0, width * 0.28) if i == 0 else Vector3(0.0, 0.0, seg_len)
		var mesh := _box(Vector3(thick, thick, seg_len), material)
		mesh.position = Vector3(0.0, 0.0, seg_len * 0.5)
		joint.add_child(mesh)
		parent.add_child(joint)

		_tail_joints.append(joint)
		parent = joint


## Three short cones at the end of a limb.
func _add_claws(arm: Node3D, arm_len: float, line: float, colour: Color) -> void:
	var material := Shapes.body(colour.lightened(0.3), line)
	for i in 3:
		var cone := CylinderMesh.new()
		cone.height = arm_len * 0.24
		cone.bottom_radius = arm_len * 0.035
		cone.top_radius = 0.0
		cone.radial_segments = 4
		cone.rings = 1

		var inst := MeshInstance3D.new()
		inst.mesh = cone
		inst.material_override = material
		inst.position = Vector3((float(i) - 1.0) * arm_len * 0.07, -arm_len * 1.02, 0.0)
		inst.basis = Basis(Vector3.RIGHT, deg_to_rad(168.0))
		arm.add_child(inst)


func _limb(joint: Vector3, length: float, thickness: float, material: StandardMaterial3D) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = joint
	var mesh := _box(Vector3(thickness, length, thickness), material)
	mesh.position = Vector3(0.0, -length * 0.5, 0.0)
	pivot.add_child(mesh)
	return pivot


func _box(size: Vector3, material: StandardMaterial3D) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var inst := MeshInstance3D.new()
	inst.mesh = mesh
	inst.material_override = material
	return inst


## Recompute the whole pose. Called every frame by the owning body.
func animate(delta: float) -> void:
	if _hips == null:
		return

	# Stride advances with speed, so the legs never scissor faster than the
	# character travels — the single most important thing for not looking like
	# a doll being slid across the floor.
	var rate := lerpf(IDLE_RATE, STRIDE_RATE * TAU, clampf(speed_ratio, 0.0, 1.4))
	_phase += delta * rate

	var swing := sin(_phase)
	var stride := clampf(speed_ratio, 0.0, 1.3)

	var leg_angle := deg_to_rad(LEG_SWING) * swing * stride
	_leg_l.basis = Basis(Vector3.RIGHT, leg_angle)
	_leg_r.basis = Basis(Vector3.RIGHT, -leg_angle)

	# Arms counter-swing the legs, which is what sells a walk as a walk.
	var arm_angle := deg_to_rad(ARM_SWING) * -swing * stride
	var rest := deg_to_rad(6.0)
	_arm_l.basis = Basis(Vector3.RIGHT, arm_angle + rest)

	var right_arm := -arm_angle + rest
	var twist_target := 0.0

	if attack_phase >= 0.0:
		# Wind the sword arm back, then whip it down and across.
		var t := clampf(attack_phase, 0.0, 1.0)
		if t < 0.3:
			var w := t / 0.3
			right_arm = lerpf(rest, deg_to_rad(-125.0), w)
			twist_target = deg_to_rad(TORSO_TWIST) * w
		else:
			var s := (t - 0.3) / 0.7
			right_arm = lerpf(deg_to_rad(-125.0), deg_to_rad(58.0), sqrt(s))
			twist_target = deg_to_rad(TORSO_TWIST) * (1.0 - s) - deg_to_rad(TORSO_TWIST * 0.7) * s
	_arm_r.basis = Basis(Vector3.RIGHT, right_arm)

	_twist = lerpf(_twist, twist_target, clampf(14.0 * delta, 0.0, 1.0))

	# Hips bob twice per stride and dip on the planted foot.
	var bob := absf(sin(_phase)) * _height * 0.022 * stride
	var crouch := 0.0
	if dashing:
		crouch = _height * 0.06
	_hips.position.y = _height * _leg_fraction + bob - crouch
	_hips.basis = Basis(Vector3.UP, _twist * 0.35)
	_torso.basis = Basis(Vector3.UP, _twist * 0.65) * Basis(
		Vector3.RIGHT, _hunch + deg_to_rad(2.0) + deg_to_rad(5.0) * stride
	)
	# Head stays level rather than riding the torso, which reads as attention.
	_head.basis = Basis(Vector3.UP, -_twist * 0.5)

	# Each tail joint lags the one before it, so the whip travels down the tail
	# instead of the whole thing swinging as one rod.
	for i in _tail_joints.size():
		var lag := _phase - float(i) * 0.55
		var sway := sin(lag) * deg_to_rad(11.0 + 5.0 * stride)
		var droop := deg_to_rad(15.0) if i == 0 else deg_to_rad(7.0)
		_tail_joints[i].basis = Basis(Vector3.UP, sway) * Basis(Vector3.RIGHT, droop)

	basis = (Basis(Vector3.UP, _yaw) * Basis(Vector3.RIGHT, lean)).scaled(shape)

	_skin.albedo_color = _skin.albedo_color.lerp(tint, clampf(12.0 * delta, 0.0, 1.0))
	_accent.albedo_color = _accent.albedo_color.lerp(
		tint.darkened(0.28), clampf(12.0 * delta, 0.0, 1.0)
	)
	_head_material.albedo_color = _head_material.albedo_color.lerp(
		tint.lightened(0.18), clampf(12.0 * delta, 0.0, 1.0)
	)


## Face a direction on the ground plane.
func face(direction: Vector3) -> void:
	if direction.length() > 0.01:
		_yaw = atan2(direction.x, direction.z) + PI
