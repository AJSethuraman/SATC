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
	# ever rolls `more` — global or typed — gear starts competing with boons on
	# the power curve and the two systems stop being distinguishable.
	for a in _items().get("affixes", []):
		for key in a.get("ranges", {}):
			var k := str(key)
			assert_false(
				k == "more" or k.begins_with("more."),
				"affix '%s' grants '%s'; the more bucket belongs to boons" % [a.get("id"), k]
			)


func test_every_typed_more_boon_can_actually_do_something() -> void:
	# A `more.<type>` modifier is worth exactly zero to a build with no damage
	# of that type. Such a boon is therefore only legitimate if it either gates
	# on a tag implying that type, or seeds the type itself. Without this rule
	# it is entirely possible to ship a boon that is legal, offerable, and a
	# guaranteed waste of the player's pick.
	for b in _boons().get("boons", []):
		var mods: Dictionary = b.get("mods", {})
		for key in mods:
			var k := str(key)
			if not k.begins_with("more."):
				continue
			var dmg_type := k.substr(5)

			var seeds_itself := (
				mods.has("flat.%s" % dmg_type) or mods.has("increased.%s" % dmg_type)
			)
			var gated_on_type := false
			for t in b.get("requires_tags", []):
				if Boon.TAG_DAMAGE_TYPE.get(str(t), "") == dmg_type:
					gated_on_type = true

			assert_true(
				seeds_itself or gated_on_type or dmg_type == "physical",
				"boon '%s' grants '%s' but neither seeds %s damage nor gates on a tag that implies it"
					% [b.get("id"), k, dmg_type]
			)


func test_boon_granted_tags_are_known() -> void:
	for b in _boons().get("boons", []):
		for t in b.get("grants_tags", []):
			assert_true(
				Boon.TAG_DAMAGE_TYPE.has(str(t)) or str(t) == "swift",
				"boon '%s' grants unrecognised tag '%s'" % [b.get("id"), t]
			)


func test_each_elemental_god_has_an_ungated_way_in() -> void:
	# If every boon of a god is tag-gated and no affix rolled that tag, the god
	# is unreachable for the whole run. Each tag that gates something must be
	# obtainable from a boon that is itself ungated.
	var gating_tags: Array = []
	for b in _boons().get("boons", []):
		for t in b.get("requires_tags", []):
			if not gating_tags.has(str(t)):
				gating_tags.append(str(t))

	var entry_tags: Array = []
	for b in _boons().get("boons", []):
		if not b.get("requires_tags", []).is_empty():
			continue
		if not b.get("requires_boons", []).is_empty():
			continue
		for t in b.get("grants_tags", []):
			entry_tags.append(str(t))

	for t in gating_tags:
		if t == "brutal" or t == "bleed":
			continue  # gear-only tags, deliberately not offered by any god
		assert_has(entry_tags, t, "tag '%s' gates boons but no ungated boon grants it" % t)


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


func test_every_required_tag_is_reachable() -> void:
	# A boon gated on a tag nothing can ever grant is dead content. Tags now
	# come from two places, so both count as a source.
	var grantable: Array = []
	for a in _items().get("affixes", []):
		for t in a.get("grants_tags", []):
			if not grantable.has(str(t)):
				grantable.append(str(t))
	for b in _boons().get("boons", []):
		for t in b.get("grants_tags", []):
			if not grantable.has(str(t)):
				grantable.append(str(t))

	for b in _boons().get("boons", []):
		for t in b.get("requires_tags", []):
			assert_has(
				grantable, str(t),
				"boon '%s' requires tag '%s', which nothing grants" % [b.get("id"), t]
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
			var own_tags: Array = b.get("requires_tags", [])
			if own_tags.is_empty():
				continue

			# The chain is reachable if one loadout satisfies both gates. The
			# prerequisite either shares a required tag, or grants the tag its
			# dependent needs — which is exactly how the entry boons work.
			var prereq_tags: Array = prereq.get("requires_tags", [])
			var prereq_grants: Array = prereq.get("grants_tags", [])
			var shared := own_tags.any(
				func(t): return prereq_tags.has(t) or prereq_grants.has(t)
			)
			assert_true(
				shared or prereq_tags.is_empty(),
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
