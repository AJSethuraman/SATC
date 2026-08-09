class_name NovaBurst
extends Node3D

## The visible half of Sunder.
##
## Purely cosmetic — main.gd has already resolved the damage by the time this
## exists. Keeping the two apart means the ring can be retimed, rescaled or
## replaced without any risk of changing what the spell actually does, and the
## damage stays testable without a scene.
##
## It matters more than a cosmetic usually would: a nova is the expensive cast,
## and an expensive cast that produces no image is indistinguishable from a bug.
## The ring is what tells you where the edge of the radius was, so a nova that
## missed reads as a misjudged distance rather than as the game not working.

## Slightly longer than the spell's own lifetime. The ring is allowed to outlive
## the effect because the eye needs the shape to persist a beat after the hit to
## register where it reached.
const DURATION := 0.42

var _life := 0.0
var _radius := 5.0
var _colour := Color.WHITE
var _material: StandardMaterial3D
var _mesh: MeshInstance3D


func setup(radius: float, colour: Color) -> void:
	_radius = radius
	_colour = colour


func _ready() -> void:
	_mesh = MeshInstance3D.new()
	# A band rather than a filled disc: the interior is where the bodies are,
	# and covering them with a flare hides the one thing worth watching.
	_mesh.mesh = Shapes.arc_band(0.86, 1.0, 180.0, 48)
	_material = Shapes.glow(_colour)
	_mesh.material_override = _material
	# Light passes through a spell. Left on, this band floats 16cm above the
	# floor and casts its own stair-stepped shadow onto the floor directly
	# beneath it, which shows straight back through the translucent ring as dark
	# hatching — the artifact that survived two rounds of blaming the shadow map.
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_mesh)
	# Clear of the floor by enough to survive depth precision at this camera's
	# grazing angle — at 0.06 the ring came back striped where it fought the
	# floor plane, which reads as a rendering fault rather than as a spell.
	position.y = 0.16


func _process(delta: float) -> void:
	_life += delta
	var t := clampf(_life / DURATION, 0.0, 1.0)
	if t >= 1.0:
		queue_free()
		return

	# Fast out, slow to settle — an expansion at constant speed reads as a
	# growing circle, whereas a decelerating one reads as a release of force.
	var eased := 1.0 - pow(1.0 - t, 3.0)
	var r := maxf(0.01, _radius * eased)
	scale = Vector3(r, 1.0, r)
	_material.albedo_color.a = (1.0 - t) * 0.75
