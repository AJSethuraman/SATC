class_name ItemCard
extends PanelContainer

## The item you just found, held on screen long enough to read.
##
## Loot has existed in this prototype since the beginning and has never been
## *visible*. A drop produced one line in a scrolling log — "Found Ashen Band
## (+7% dmg)" — which tells you an item happened and nothing about what it is.
## Every affix, every rarity tier, the whole socket and inscription system,
## all of it resolved into a percentage and vanished.
##
## So this is a Diablo item tooltip: rarity-coloured name, base and item level,
## one line per affix, sockets if any. It is the only place the itemisation
## systems are ever shown to the player, which is why it holds for a few seconds
## rather than flashing.

## Rarity colours, following the convention every ARPG since Diablo has used —
## grey/blue/yellow/orange — because a player who has met one of those games
## already knows what a blue name means and does not need to be taught.
const RARITY_COLOUR := {
	Item.Rarity.NORMAL: Color(0.78, 0.78, 0.82),
	Item.Rarity.MAGIC: Color(0.45, 0.62, 1.0),
	Item.Rarity.RARE: Color(1.0, 0.92, 0.35),
	Item.Rarity.UNIQUE: Color(1.0, 0.62, 0.22),
}

const HOLD := 3.4
const FADE := 0.6

var _life := 0.0


func setup(item: Item, damage_delta: float) -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.06, 0.05, 0.09, 0.9)
	style.border_color = RARITY_COLOUR.get(item.rarity, Color.WHITE)
	style.set_border_width_all(2)
	style.set_corner_radius_all(3)
	style.set_content_margin_all(10)
	add_theme_stylebox_override("panel", style)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 2)
	add_child(box)

	box.add_child(_line(item.display_name(), 19, RARITY_COLOUR.get(item.rarity, Color.WHITE)))
	box.add_child(_line(
		"%s · ilvl %d" % [item.base_name, item.ilvl], 13, Color(0.62, 0.60, 0.66)
	))

	for a in item.affixes:
		box.add_child(_line(a.display_name, 15, Color(0.55, 0.72, 1.0)))

	if item.sockets > 0:
		box.add_child(_line(
			"sockets: %d (%d free)" % [item.sockets, item.free_sockets()],
			13, Color(0.72, 0.66, 0.52)
		))
	if item.inscription != null:
		box.add_child(_line("— %s —" % item.inscription.display_name, 15, Color(1.0, 0.72, 0.26)))

	# The number the old log line carried, kept because it is the one thing a
	# card of affixes does not answer: is this actually better than what I have?
	var better := damage_delta >= 0.0
	box.add_child(_line(
		"%+.0f%% damage" % (damage_delta * 100.0), 15,
		Color(0.5, 0.9, 0.55) if better else Color(0.9, 0.45, 0.45)
	))


func _line(text: String, size: int, colour: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", colour)
	return label


func _process(delta: float) -> void:
	_life += delta
	if _life < HOLD:
		return
	var t := (_life - HOLD) / FADE
	if t >= 1.0:
		queue_free()
		return
	modulate.a = 1.0 - t
