extends TestCase

## Validation of the content files themselves.
##
## The runtime treats an unknown modifier key as a push_error and moves on, so
## a typo in JSON would silently cost the player a stat forever. These tests are
## what turn that into a build failure. They also catch content that can never
## be reached, which is a bug the player experiences as "this boon does not
## exist" rather than as an error.

const ITEMS_PATH := "res://data/items.json"
const BOONS_PATH := "res://data/boons.json"


func _items() -> Dictionary:
	return _load(ITEMS_PATH)


func _boons() -> Dictionary:
	return _load(BOONS_PATH)


func _load(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		fail("cannot open %s" % path)
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if not (parsed is Dictionary):
		fail("%s is not a JSON object" % path)
		return {}
	return parsed


func test_every_affix_modifier_key_is_in_the_grammar() -> void:
	for a in _items().get("affixes", []):
		for key in a.get("ranges", {}):
			assert_true(
				StatBlock.is_valid_key(str(key)),
				"affix '%s' uses unknown modifier key '%s'" % [a.get("id"), key]
			)


func test_every_base_implicit_key_is_in_the_grammar() -> void:
	for b in _items().get("bases", []):
		for key in b.get("implicit", {}):
			assert_true(
				StatBlock.is_valid_key(str(key)),
				"base '%s' uses unknown modifier key '%s'" % [b.get("name"), key]
			)


func test_every_boon_modifier_key_is_in_the_grammar() -> void:
	for b in _boons().get("boons", []):
		for key in b.get("mods", {}):
			assert_true(
				StatBlock.is_valid_key(str(key)),
				"boon '%s' uses unknown modifier key '%s'" % [b.get("id"), key]
			)


func test_affixes_never_grant_more_multipliers() -> void:
	# This is the design constraint that keeps gear build-defining. If an affix
	# ever rolls `more`, gear starts competing with boons on the power curve and
	# the two systems stop being distinguishable.
	for a in _items().get("affixes", []):
		assert_false(
			a.get("ranges", {}).has("more"),
			"affix '%s' grants a `more` multiplier; that bucket belongs to boons" % a.get("id")
		)


func test_affix_ranges_are_well_formed() -> void:
	for a in _items().get("affixes", []):
		for key in a.get("ranges", {}):
			var span: Variant = a["ranges"][key]
			assert_true(span is Array, "affix '%s' range '%s' is not an array" % [a.get("id"), key])
			if span is Array:
				assert_eq(span.size(), 2, "affix '%s' range '%s' needs exactly [min, max]" % [a.get("id"), key])
				if span.size() == 2:
					assert_true(
						float(span[0]) <= float(span[1]),
						"affix '%s' range '%s' is inverted" % [a.get("id"), key]
					)


func test_ids_are_unique() -> void:
	_assert_unique_ids(_items().get("affixes", []), "affix")
	_assert_unique_ids(_boons().get("boons", []), "boon")


func test_weights_are_positive() -> void:
	for a in _items().get("affixes", []):
		assert_gt(float(a.get("weight", 1.0)), 0.0, "affix '%s' has a non-positive weight" % a.get("id"))
	for b in _boons().get("boons", []):
		assert_gt(float(b.get("weight", 1.0)), 0.0, "boon '%s' has a non-positive weight" % b.get("id"))


func test_boon_prerequisites_reference_real_boons() -> void:
	var boons: Array = _boons().get("boons", [])
	var ids: Array = boons.map(func(b): return str(b.get("id", "")))
	for b in boons:
		for req in b.get("requires_boons", []):
			assert_has(ids, str(req), "boon '%s' requires unknown boon '%s'" % [b.get("id"), req])


func test_every_required_tag_is_reachable_from_some_affix() -> void:
	# A boon gated on a tag no affix can ever grant is dead content.
	var grantable: Array = []
	for a in _items().get("affixes", []):
		for t in a.get("grants_tags", []):
			if not grantable.has(str(t)):
				grantable.append(str(t))

	for b in _boons().get("boons", []):
		for t in b.get("requires_tags", []):
			assert_has(
				grantable, str(t),
				"boon '%s' requires tag '%s', which no affix grants" % [b.get("id"), t]
			)


func test_a_prerequisite_chain_is_satisfiable_alongside_its_tag_gate() -> void:
	# A duo boon whose prerequisite needs a different, incompatible tag would be
	# unreachable in practice even though every individual reference is valid.
	var boons: Array = _boons().get("boons", [])
	var by_id := {}
	for b in boons:
		by_id[str(b.get("id", ""))] = b

	for b in boons:
		for req_id in b.get("requires_boons", []):
			var prereq: Dictionary = by_id.get(str(req_id), {})
			var prereq_tags: Array = prereq.get("requires_tags", [])
			var own_tags: Array = b.get("requires_tags", [])
			if prereq_tags.is_empty() or own_tags.is_empty():
				continue
			# Both gates are "any of", so a shared tag proves one loadout opens both.
			var shared := own_tags.any(func(t): return prereq_tags.has(t))
			assert_true(
				shared,
				"boon '%s' and its prerequisite '%s' need disjoint tags, so the chain is unreachable"
					% [b.get("id"), req_id]
			)


func test_at_least_three_boon_groups_are_available_with_no_gear() -> void:
	# The offer is always three wide; if fewer than three groups are ungated the
	# player would get a short choice on the very first room.
	var open_groups: Array = []
	for b in _boons().get("boons", []):
		if b.get("requires_tags", []).is_empty() and b.get("requires_boons", []).is_empty():
			var g := str(b.get("group", b.get("id", "")))
			if not open_groups.has(g):
				open_groups.append(g)
	assert_gt(float(open_groups.size()), 2.0, "need 3+ ungated boon groups for a full first offer")


func test_every_base_declares_a_known_slot() -> void:
	var known := ["weapon", "armor", "trinket"]
	for b in _items().get("bases", []):
		assert_has(known, str(b.get("slot", "")), "base '%s' has an unknown slot" % b.get("name"))


func _assert_unique_ids(entries: Array, label: String) -> void:
	var seen: Array = []
	for e in entries:
		var id := str(e.get("id", ""))
		assert_false(seen.has(id), "duplicate %s id '%s'" % [label, id])
		seen.append(id)
