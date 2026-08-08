class_name Reliquary
extends RefCounted

## The bank: the only thing that survives a death.
##
## One deposit per run, into a store that persists. That is what turns a pile of
## unrelated runs into a campaign — you are not accumulating power, you are
## accumulating *components*, and the choice of which single piece to keep is the
## only decision in the game that outlives the character making it.
##
## THE LOAD-BEARING RULE: only raw sigils and empty vessels may be deposited.
## Never a completed item, never a vessel with anything already in it.
##
## Everything rests on that. An inscription needs a vessel plus two or three
## specific sigils, so at one deposit per run it is physically impossible to bank
## a finished weapon — you assemble it across runs and complete it *inside* one.
## Relax the rule and the design collapses straight into "keep your best gear",
## which the balance simulator already identified as the failure mode: farm one
## good weapon and every subsequent run opens easy. test_reliquary.gd enforces
## this, and it should be treated as a design invariant rather than a preference.
##
## It has a pleasant side effect too. Because only inert components are storable,
## saving is trivial — a sigil is an id and a vessel is a base name plus a socket
## count. No item state to serialise, no versioning problem.

const DEFAULT_CAPACITY := 8
const DEPOSITS_PER_RUN := 1

var capacity: int = DEFAULT_CAPACITY

## Stored components. Each entry is {"kind": "sigil", "id": ...} or
## {"kind": "vessel", "base": ..., "slot": ..., "sockets": n}.
var contents: Array = []

var _deposits_this_run: int = 0


func begin_run() -> void:
	_deposits_this_run = 0


func deposits_remaining() -> int:
	return maxi(0, DEPOSITS_PER_RUN - _deposits_this_run)


func is_full() -> bool:
	return contents.size() >= capacity


## Why a deposit would be refused, or "" if it would be accepted. Returns a
## reason rather than a bool so callers can tell the player something useful.
func rejection_reason(item: Item) -> String:
	if item.is_inscribed():
		return "a completed inscription cannot be banked"
	if not item.socketed.is_empty():
		return "the vessel already holds sigils"
	if not item.affixes.is_empty():
		return "only plain vessels can be banked"
	if item.sockets <= 0:
		return "that vessel has no sockets"
	if deposits_remaining() <= 0:
		return "you have already set something aside this run"
	if is_full():
		return "the reliquary is full"
	return ""


func can_deposit(item: Item) -> bool:
	return rejection_reason(item) == ""


func deposit_vessel(item: Item) -> bool:
	if not can_deposit(item):
		return false
	contents.append({
		"kind": "vessel",
		"base": item.base_name,
		"slot": item.slot,
		"sockets": item.sockets,
	})
	_deposits_this_run += 1
	return true


func deposit_sigil(sigil: Sigil) -> bool:
	if deposits_remaining() <= 0 or is_full():
		return false
	contents.append({"kind": "sigil", "id": sigil.id})
	_deposits_this_run += 1
	return true


func discard_at(index: int) -> void:
	if index >= 0 and index < contents.size():
		contents.remove_at(index)


func sigil_ids() -> Array:
	var out: Array = []
	for entry in contents:
		if str(entry.get("kind", "")) == "sigil":
			out.append(str(entry.get("id", "")))
	return out


## Vessels held, as {"base", "slot", "sockets"} dictionaries.
func vessels() -> Array:
	return contents.filter(func(e): return str(e.get("kind", "")) == "vessel")


## The largest banked vessel for a slot, or 0 if there is none.
func best_sockets(for_slot: String) -> int:
	var best := 0
	for v in vessels():
		if for_slot == "" or str(v.get("slot", "")) == for_slot:
			best = maxi(best, int(v.get("sockets", 0)))
	return best


# --- persistence --------------------------------------------------------


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
