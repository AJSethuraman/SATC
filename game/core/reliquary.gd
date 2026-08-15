class_name Reliquary
extends RefCounted

## The bank: the only thing that survives a death.
##
## A store that persists, fed by deposits a run earns. That is what turns a pile
## of unrelated runs into a campaign — what you set aside is the only decision in
## the game that outlives the character making it.
##
## THE LOAD-BEARING RULE: you may bank a finished item. You must assemble it
## inside a single run. What the bank refuses is the half-built thing — a vessel
## with sigils in it that do not yet spell anything — and the merely lucky one: a
## rare is a roll, and banking rolls makes the slot a ratchet rather than a
## choice. Uniques and set pieces bank freely, because a named item is the same
## item every time and keeping one is a decision about which item you want.
##
## That inverts the rule this system shipped with — "only raw sigils and empty
## vessels may be deposited, never a completed item" — and the inversion is
## deliberate rather than a relaxation. The old rule existed for exactly one
## reason: to stop the game collapsing into "farm one good weapon, then every
## subsequent run opens easy", a failure mode the balance simulator identified
## directly. It is superseded because the difficulty passes now do that job, and
## do it better. A run is three passes over the same acts, and enemy health steps
## about 2.2x across a pass boundary (RunState.DIFFICULTY_HEALTH_STEP, on top of
## the act step landing at the same moment). A runeword assembled in Normal is
## outscaled by Nightmare, so a banked item is not a permanent win — it is a leg
## up for the *next* run's early game, which gets you deeper faster, which is the
## only way to farm the components that exist only deeper. That ladder is the
## progression, and it is worth more than the old prohibition was.
##
## So the constraint moved rather than vanished. It used to be about what you may
## keep; it is now about what you must do in one sitting. Assembly is the part
## that has to happen inside a run, because holding a vessel and every sigil of a
## recipe at the same time is precisely what depth buys you. test_reliquary.gd
## enforces the new shape of it, and it is still a design invariant rather than a
## preference.
##
## The old rule had a pleasant side effect that is now paid for. Only inert
## components were storable, so a save was ids and counts with no item state to
## serialise. A banked item now stores its base, socket count and sigil order,
## and is rebuilt through the book by item_from_entry() — which re-derives the
## inscription from the *current* book instead of trusting the stored id, so
## editing content can never resurrect a word that no longer exists.

const DEFAULT_CAPACITY := 8

## Deposits are earned by getting deeper, not handed out flat.
##
## One per run was the original rule and it made the whole system arithmetic
## rather than a game. A specific three-sigil inscription came out at a median
## of forty-nine runs with 62% of players never seeing one in four hundred,
## because income was capped at one component per attempt no matter how well the
## attempt went. That is not a chase, it is a queue — and no amount of tuning
## the drop rate fixes a cap.
##
## So: one for showing up, and one more for each act cleared. A run that dies in
## the Cinderwaste banks one; a full clear banks five. That ties the bank to
## how the run actually went, gives the difficulty curve something to pay out,
## and makes the answer to "why push deeper" a concrete one.
##
## It also matches what this was always for. The bank is a ramp into the next
## run, not a vault you fill toward one endgame item.
const DEPOSITS_AT_START := 1
const DEPOSITS_PER_ACT := 1

var capacity: int = DEFAULT_CAPACITY

## What is stored. Each entry is one of
##   {"kind": "sigil",  "id": ...}
##   {"kind": "vessel", "base": ..., "slot": ..., "sockets": n}
##   {"kind": "item",   "base": ..., "slot": ..., "sockets": n,
##                      "sigils": [id, ...], "inscription": id}
##   {"kind": "named",  "base": ..., "slot": ..., "ilvl": n, "piece": name}
## A finished item keeps its sigils in socket order because order is what makes
## the inscription; a bag of the same three sigils is a different thing.
var contents: Array = []

var _deposits_earned: int = DEPOSITS_AT_START
var _deposits_used: int = 0


func begin_run() -> void:
	_deposits_earned = DEPOSITS_AT_START
	_deposits_used = 0


## Call when an act boss falls. The deposit is banked as *allowance*, so a run
## that earns three and spends none simply carries nothing over — it is a
## licence to keep something, not a thing.
func earn_deposit() -> void:
	_deposits_earned += DEPOSITS_PER_ACT


func deposits_remaining() -> int:
	return maxi(0, _deposits_earned - _deposits_used)


func is_full() -> bool:
	return contents.size() >= capacity


## Why a deposit would be refused, or "" if it would be accepted. Returns a
## reason rather than a bool so callers can tell the player something useful.
func rejection_reason(item: Item) -> String:
	if not item.is_inscribed() and not item.is_named():
		# The one refusal the whole design now rests on. Banking a vessel with
		# two of the three sigils already in it would let you carry the assembly
		# across runs a piece at a time, which is exactly the work that has to
		# happen in one sitting.
		if not item.socketed.is_empty():
			return "finish the inscription this run or bank the sigils loose"
		# Rolled affixes stay refused, and the line is now drawn somewhere it can
		# be justified: what may be banked is a *fixed* thing — a finished
		# inscription, a unique, a set piece — and what may not is a roll.
		#
		# This is the revisit the previous comment here asked for. Uniques and
		# sets did not exist when the rule was written, so "no affixes" was the
		# only available approximation of it; now that they do, banking one is
		# the entire point of them. A run that never lined up its sigils still
		# has something to keep, which is what makes a bad run worth finishing.
		#
		# Rares remain out, and not arbitrarily: a rare is a roll, so banking
		# rares turns the reliquary into a place you hoard rerolls, and the slot
		# that was meant to be a hard choice becomes a strictly-better ratchet.
		# A unique is the same item every time, so keeping one is a decision
		# about which item you want, not about which roll you got.
		if not item.affixes.is_empty():
			return "only vessels, named items and finished inscriptions can be banked"
		if item.sockets <= 0:
			return "that vessel has no sockets"
	if deposits_remaining() <= 0:
		return "you have already set something aside this run"
	if is_full():
		return "the reliquary is full"
	return ""


func can_deposit(item: Item) -> bool:
	return rejection_reason(item) == ""


## Bank an item — an empty vessel or a finished inscription; the entry written
## depends on which it is.
func deposit(item: Item) -> bool:
	if not can_deposit(item):
		return false
	contents.append(_entry_for(item))
	_deposits_used += 1
	return true


## The name callers had before finished items were bankable. Kept rather than
## renamed because the acquisition simulator banks vessels through it, and
## because "deposit_vessel(a vessel)" still reads correctly at the call site.
func deposit_vessel(item: Item) -> bool:
	return deposit(item)


func _entry_for(item: Item) -> Dictionary:
	# A named item stores its id and nothing else. Every stat it carries is
	# content, so re-stamping it from the current table on load is both smaller
	# and correct by construction: a retuned unique comes back retuned, and one
	# deleted from the table comes back as nothing rather than as a ghost of a
	# balance pass that no longer exists. Same reasoning as the inscription
	# re-derivation below.
	if item.is_named():
		return {
			"kind": "named",
			"base": item.base_name,
			"slot": item.slot,
			"ilvl": item.ilvl,
			"piece": item.unique_name,
		}
	if item.is_inscribed():
		return {
			"kind": "item",
			"base": item.base_name,
			"slot": item.slot,
			"sockets": item.sockets,
			"sigils": item.socketed_ids(),
			"inscription": item.inscription.id,
		}
	return {
		"kind": "vessel",
		"base": item.base_name,
		"slot": item.slot,
		"sockets": item.sockets,
	}


func deposit_sigil(sigil: Sigil) -> bool:
	if deposits_remaining() <= 0 or is_full():
		return false
	contents.append({"kind": "sigil", "id": sigil.id})
	_deposits_used += 1
	return true


func discard_at(index: int) -> void:
	if index >= 0 and index < contents.size():
		contents.remove_at(index)


## Loose sigils only. The sigils inside a banked inscription are deliberately not
## counted: they are spoken for, and a caller asking "what can I build with?"
## would otherwise be told it owns components it would have to destroy an item to
## get at.
func sigil_ids() -> Array:
	var out: Array = []
	for entry in contents:
		if str(entry.get("kind", "")) == "sigil":
			out.append(str(entry.get("id", "")))
	return out


## Empty vessels held, as {"base", "slot", "sockets"} dictionaries. A banked
## finished item is not one, for the same reason: its sockets are full.
func vessels() -> Array:
	return contents.filter(func(e): return str(e.get("kind", "")) == "vessel")


## Finished inscriptions held, as entry dictionaries. Rebuild one with
## item_from_entry() when you need the Item itself.
func items() -> Array:
	return contents.filter(func(e): return str(e.get("kind", "")) == "item")


## The largest banked vessel for a slot, or 0 if there is none.
func best_sockets(for_slot: String) -> int:
	var best := 0
	for v in vessels():
		if for_slot == "" or str(v.get("slot", "")) == for_slot:
			best = maxi(best, int(v.get("sockets", 0)))
	return best


# --- persistence --------------------------------------------------------


## Rebuild a banked entry into a usable Item, or null if the entry is not a
## finished item.
##
## The inscription is re-derived from the book rather than read back out of the
## entry. A save holds content ids and content moves: a retuned pattern or a
## renamed sigil must produce whatever the *current* book says the sequence
## spells — including nothing — rather than a word the game no longer has rules
## for. The stored "inscription" id is there so a UI can list the bank without
## loading the book, not as the authority on what the item is.
static func item_from_entry(entry: Dictionary, book: InscriptionBook) -> Item:
	if str(entry.get("kind", "")) == "named":
		return _named_from_entry(entry)
	if book == null or str(entry.get("kind", "")) != "item":
		return null
	var item := Item.new()
	item.base_name = str(entry.get("base", "Item"))
	item.slot = str(entry.get("slot", "weapon"))
	item.sockets = int(entry.get("sockets", 0))
	# A save is a file on disk and may be anything by the time it comes back, so
	# a sigil list that is not a list yields an empty vessel rather than a crash.
	var ids: Array = []
	var stored: Variant = entry.get("sigils", [])
	if stored is Array:
		ids = stored
	for sigil_id in ids:
		var sigil := book.sigil_by_id(str(sigil_id))
		# A sigil this book has never heard of is dropped rather than faked, and
		# the reappraisal below then simply finds no inscription.
		if sigil != null:
			item.insert(sigil)
	item.reappraise(book)
	return item


## Re-stamp a banked unique or set piece from the current table, or null if the
## table no longer has it — a piece cut from content should vanish from the bank
## rather than persist with stats nothing can explain.
static func _named_from_entry(entry: Dictionary) -> Item:
	var piece := UniquePool.shared().piece_by_name(str(entry.get("piece", "")))
	if piece == null:
		return null
	var item := Item.new()
	item.base_name = str(entry.get("base", "Item"))
	item.slot = str(entry.get("slot", piece.slot))
	item.ilvl = int(entry.get("ilvl", 1))
	piece.stamp(item)
	return item


## Named items held, as entry dictionaries.
func named_items() -> Array:
	return contents.filter(func(e): return str(e.get("kind", "")) == "named")


func to_dict() -> Dictionary:
	return {"capacity": capacity, "contents": contents}


static func from_dict(d: Dictionary) -> Reliquary:
	var r := Reliquary.new()
	r.capacity = int(d.get("capacity", DEFAULT_CAPACITY))
	r.contents = d.get("contents", [])
	return r


func save_to(path: String) -> Error:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(to_dict(), "\t"))
	f.close()
	return OK


## Load, or an empty reliquary if there is no save yet. A missing file is the
## normal first-launch case, not an error.
static func load_from(path: String) -> Reliquary:
	if not FileAccess.file_exists(path):
		return Reliquary.new()
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return Reliquary.new()
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if not (parsed is Dictionary):
		push_error("Reliquary: %s is corrupt, starting empty" % path)
		return Reliquary.new()
	return Reliquary.from_dict(parsed)
