class_name IsoCamera
extends Camera3D

## Fixed isometric-ish camera rig.
##
## The camera never rotates — it only follows. That fixed angle is what makes a
## scene built out of capsules read as a game rather than as a debug view: the
## floor gets foreshortened, bodies have height, and the directional light casts
## shadows that tell you where things are relative to the ground.
##
## Orthographic on purpose. Perspective across an arena this wide makes the far
## corners lean, and depth then has to fight the projection rather than come
## purely from the angle and the shadows.
##
## Also owns the screen-to-ground mapping, since it is the only thing that knows
## the projection: aiming with a mouse in a 3D scene means intersecting a ray
## with the ground plane, not reading a 2D coordinate.

var _shake := 0.0
var _shake_rng := Rng.new(20260808)
var _target := Vector3.ZERO


func _ready() -> void:
	projection = Camera3D.PROJECTION_ORTHOGONAL
	size = Feel.CAMERA_SIZE
	near = 0.05
	far = 400.0
	_target = Vector3.ZERO
	_place(_target)


## Unit vector from the look-at point back toward the camera.
static func offset_direction() -> Vector3:
	var elevation := deg_to_rad(Feel.CAMERA_ELEVATION)
	var azimuth := deg_to_rad(Feel.CAMERA_AZIMUTH)
	return Vector3(
		cos(elevation) * sin(azimuth),
		sin(elevation),
		cos(elevation) * cos(azimuth)
	).normalized()


## The horizontal basis a player's screen-relative input should be rotated by, so
## that "W" means "up the screen" rather than "negative Z in world space".
static func input_basis() -> Basis:
	return Basis(Vector3.UP, deg_to_rad(Feel.CAMERA_AZIMUTH))


func snap_to(point: Vector3) -> void:
	_target = point
	_place(_target)


## Follow `point`, leading slightly toward `aim` so the view feels intentional.
func follow(point: Vector3, aim: Vector3, delta: float) -> void:
	var desired := point + aim.normalized() * Feel.CAMERA_AIM_LEAD
	_target = _target.lerp(desired, clampf(Feel.CAMERA_LAG * delta, 0.0, 1.0))

	if _shake > 0.0:
		_shake = maxf(0.0, _shake - Feel.SHAKE_DECAY * delta)
	_place(_target)


func add_shake(amount: float) -> void:
	_shake = maxf(_shake, amount)


func _place(point: Vector3) -> void:
	var jitter := Vector3.ZERO
	if _shake > 0.0:
		jitter = Vector3(
			_shake_rng.randf_range(-_shake, _shake),
			_shake_rng.randf_range(-_shake, _shake),
			_shake_rng.randf_range(-_shake, _shake)
		)
	global_position = point + offset_direction() * Feel.CAMERA_DISTANCE + jitter
	look_at(point + jitter, Vector3.UP)


## Where the mouse is pointing, on the ground plane. Returns `fallback` when the
## ray runs parallel to the floor, which happens if the rig is ever flattened.
func ground_point(fallback: Vector3) -> Vector3:
	var mouse := get_viewport().get_mouse_position()
	var from := project_ray_origin(mouse)
	var dir := project_ray_normal(mouse)
	var hit: Variant = Plane(Vector3.UP, 0.0).intersects_ray(from, dir)
	if hit == null:
		return fallback
	return hit
