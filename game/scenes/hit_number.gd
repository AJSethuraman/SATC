class_name HitNumber
extends Node3D

## A damage number that floats off a body and fades.
##
## Diablo II has no floating numbers and Hades has none either, so this is not
## imitation — it is here because of a specific problem this prototype has that
## neither of those games does. Every affix, boon, sigil and inscription in
## core/ resolves into one figure at the moment of impact, and until now that
## figure was visible nowhere. You could take a boon promising "+40% ignite
## damage" and have no way at all to tell whether it did anything.
##
## So this is instrumentation that happens to be diegetic: the shortest path
## between the numbers the build is made of and the player's eyes. A crit is
## larger and warmer, because the single most useful thing to be able to read
## mid-fight is whether the big hits are landing.

const RISE := 1.9
const LIFETIME := 0.75
const DRIFT := 0.7

var _life := 0.0
var _label: Label3D
var _velocity := Vector3.ZERO


func setup(amount: float, crit: bool, sideways: float) -> void:
	_label = Label3D.new()
	_label.text = str(roundi(amount))
	_label.font_size = 68 if crit else 46
	_label.outline_size = 18
	_label.outline_modulate = Color(0.03, 0.02, 0.05, 0.85)
	_label.modulate = Color(1.0, 0.82, 0.42) if crit else Color(0.94, 0.93, 0.96)
	# Billboarded and depth-tested off: a number that disappears behind the body
	# it belongs to is worse than useless, because you notice it flicker and
	# learn to stop looking.
	_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_label.no_depth_test = true
	_label.fixed_size = true
	_label.pixel_size = 0.0016
	add_child(_label)

	# Fan sideways so a crowd of simultaneous hits does not stack into one
	# unreadable smear.
	_velocity = Vector3(sideways * DRIFT, RISE, 0.0)


func _process(delta: float) -> void:
	_life += delta
	if _life >= LIFETIME:
		queue_free()
		return

	var t := _life / LIFETIME
	position += _velocity * delta
	# Decelerate as it rises, so it settles rather than sailing off.
	_velocity.y = RISE * (1.0 - t)
	# Hold full opacity for the first third; a number that starts fading
	# immediately is hard to read at the moment it matters most.
	_label.modulate.a = clampf((1.0 - t) * 1.5, 0.0, 1.0)
