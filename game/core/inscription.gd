class_name Inscription
extends RefCounted

## A runeword: an exact ordered sigil sequence in a vessel of the right size.
##
## Order matters, and that is deliberate. It turns a pile of components into a
## *recipe* — something you can know, plan toward, and be one piece short of.
## A set-based match would let any two fire sigils do, which collapses the chase
## into "collect enough of anything".
##
## What an inscription grants should change how the character *plays*, not how
## big the numbers are. Numbers are what boons and affixes already do; if
## inscriptions were also just numbers there would be no reason for them to
## exist. `behaviour` names the mechanical change for the scene layer to
## implement — it is inert until the caster work lands, and deliberately so:
## pinning the vocabulary now is what stops the content and the code drifting
## apart later.

var id: String = ""
var display_name: String = ""
var description: String = ""

## Sigil ids in the exact order they must occupy the sockets.
var pattern: Array[String] = []

## Item slot this may be inscribed into. Empty means any.
var slot: String = ""

var mods: Dictionary = {}
var grants_tags: Array[String] = []
## Identifier for the behavioural effect, e.g. "bolt_forks". Not yet wired.
var behaviour: String = ""


static func from_dict(d: Dictionary) -> Inscription:
	var i := Inscription.new()
	i.id = str(d.get("id", ""))
	i.display_name = str(d.get("name", i.id))
	i.description = str(d.get("description", ""))
	i.slot = str(d.get("slot", ""))
	i.mods = d.get("mods", {})
	i.behaviour = str(d.get("behaviour", ""))
	for p in d.get("pattern", []):
		i.pattern.append(str(p))
	for t in d.get("grants_tags", []):
		i.grants_tags.append(str(t))
	return i


## How many sockets a vessel needs to carry this.
func socket_count() -> int:
	return pattern.size()


## Does this exact ordered sigil sequence, in this slot, form the inscription?
func matches(sigil_ids: Array, item_slot: String) -> bool:
	if slot != "" and slot != item_slot:
		return false
	if sigil_ids.size() != pattern.size():
		return false
	for i in pattern.size():
		if str(sigil_ids[i]) != pattern[i]:
			return false
	return true


## Every distinct component needed, as {"vessel_sockets": n, "sigils": {id: count}}.
## Used by the acquisition simulator and by any "what am I missing" UI.
func requirements() -> Dictionary:
	var needed := {}
	for p in pattern:
		needed[p] = int(needed.get(p, 0)) + 1
	return {"vessel_sockets": pattern.size(), "slot": slot, "sigils": needed}


func _to_string() -> String:
	return display_name
