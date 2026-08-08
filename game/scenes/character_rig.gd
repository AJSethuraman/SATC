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
var _accent: StandardMaterial3D


func build(height: float, colour: Color, with_weapon: bool) -> void:
	_height = height
	_skin = Shapes.solid(colour)
	_accent = Shapes.solid(colour.darkened(0.28))

	var leg_len := height * LEG_FRACTION
	var torso_h := height * TORSO_FRACTION
	var head_size := height * HEAD_FRACTION
	var arm_len := height * ARM_FRACTION
	var width := height * WIDTH_FRACTION

	_hips = Node3D.new()
	_hips.position = Vector3(0.0, leg_len, 0.0)
	add_child(_hips)

	_torso = Node3D.new()
	_hips.add_child(_torso)
	var torso_mesh := _box(Vector3(width, torso_h, width * 0.62), _skin)
	torso_mesh.position = Vector3(0.0, torso_h * 0.5, 0.0)
	_torso.add_child(torso_mesh)

	_head_material = Shapes.solid(colour.lightened(0.18))
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

	if with_weapon:
		var blade_len := height * 0.5
		_weapon = _box(Vector3(height * 0.05, blade_len, height * 0.1), Shapes.solid(
			Color(0.78, 0.80, 0.86)
		))
		# Held out from the fist at the end of the right arm, angled forward.
		_weapon.position = Vector3(0.0, -arm_len * 0.92, -blade_len * 0.34)
		_weapon.basis = Basis(Vector3.RIGHT, deg_to_rad(-78.0))
		_arm_r.add_child(_weapon)


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
	_hips.position.y = _height * LEG_FRACTION + bob - crouch
	_hips.basis = Basis(Vector3.UP, _twist * 0.35)
	_torso.basis = Basis(Vector3.UP, _twist * 0.65) * Basis(
		Vector3.RIGHT, deg_to_rad(2.0) + deg_to_rad(5.0) * stride
	)
	# Head stays level rather than riding the torso, which reads as attention.
	_head.basis = Basis(Vector3.UP, -_twist * 0.5)

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
