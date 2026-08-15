class_name Sigil
extends RefCounted

## A rune: a component that is nearly worthless alone.
##
## That worthlessness is the entire point. What makes D2's runewords compelling
## is not that runes are strong — it is that a rune is inert until it meets the
## right base, in the right order. The value lives in the *combination*, which is
## why a rune can be banked across runs without making any single run easy.
##
## Socketed into a vessel a sigil still contributes its own small modifier, so a
## combination that forms no inscription is a disappointment rather than a
## complete waste. That is also D2's behaviour and it matters: it means putting a
## rune in a socket is never strictly a mistake, only sometimes a bad trade.

var id: String = ""
var display_name: String = ""
## Higher tiers are rarer. Drop weight falls off sharply with tier, which is what
## makes a specific high sigil something you chase across runs.
var tier: int = 1
## Damage type this sigil is associated with, or "" for the neutral ones.
var element: String = ""
var weight: float = 1.0

## The sigil's own contribution when socketed, independent of any inscription.
var mods: Dictionary = {}


static func from_dict(d: Dictionary) -> Sigil:
	var s := Sigil.new()
	s.id = str(d.get("id", ""))
	s.display_name = str(d.get("name", s.id))
	s.tier = int(d.get("tier", 1))
	s.element = str(d.get("element", ""))
	s.weight = float(d.get("weight", 1.0))
	s.mods = d.get("mods", {})
	return s


func _to_string() -> String:
	return display_name
