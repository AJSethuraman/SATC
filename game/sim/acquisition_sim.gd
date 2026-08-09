extends SceneTree

## How many runs until your first inscription?
##
##   godot --headless --path game --script res://sim/acquisition_sim.gd
##   godot --headless --path game --script res://sim/acquisition_sim.gd -- 2000 5
##
## Args: [players] [areas_cleared_per_run].
##
## This exists to answer the one question the runeword design lives or dies on
## before any of it is built into the game. Too slow and the chase is a grind
## wall; too fast and there is no chase. That number is not a matter of taste —
## it is a consequence of drop rates, socket rates and one deposit per run, and
## it can be measured rather than guessed at.
##
## What it deliberately does NOT tell you: whether chasing a specific recipe is
## *fun*. It reports how long the chase takes. Whether that length feels like
## anticipation or like homework is a question for a person.

const ITEMS_PATH := "res://data/items.json"
const SIGILS_PATH := "res://data/sigils.json"

const MAX_RUNS := 60

## The specific recipe the second pass chases. A three-sigil word needing a
## top-tier sigil is the far end of the curve, so it bounds the chase.
const CHASE_TARGET := "conflagrant"
## And the deliberate long chase, for contrast.
const DEEP_CHASE_TARGET := "ruin"
const CHASE_MAX_RUNS := 400

## Chance a floor's reward is a sigil rather than an item. The other big lever
## besides socket rates — turn this first if the answer comes back too slow.
const SIGIL_DROP_CHANCE := 0.34


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var players := int(args[0]) if args.size() > 0 else 1000
	var areas_deep := int(args[1]) if args.size() > 1 else 15

	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var book := InscriptionBook.from_json(SIGILS_PATH)

	print("")
	print("Ashfall acquisition simulation")
	print("==============================")
	print("players=%d  areas cleared per run=%d  sigil drop chance=%.2f"
		% [players, areas_deep, SIGIL_DROP_CHANCE])
	print("reliquary: %d capacity, %d deposit at start + %d per act cleared"
		% [Reliquary.DEFAULT_CAPACITY, Reliquary.DEPOSITS_AT_START, Reliquary.DEPOSITS_PER_ACT])

	# Pass one: any inscription at all. This is the on-ramp — how long before the
	# system first does anything for you.
	_run_pass(
		"ANY inscription (the on-ramp)", gen, book, players, areas_deep,
		book.by_ascending_cost(), MAX_RUNS
	)

	# Pass two: one specific deep recipe. This is the actual chase the design is
	# built around — "you are after specific things" — and it is a different
	# question with a very different answer.
	for target_id in [CHASE_TARGET, DEEP_CHASE_TARGET]:
		var chased := book.inscription_by_id(str(target_id))
		if chased != null:
			_run_pass(
				"'%s' specifically (%d sigils)" % [chased.display_name, chased.pattern.size()],
				gen, book, players, areas_deep, [chased], CHASE_MAX_RUNS
			)
	print("")
	quit(0)


## One player, run after run, until they complete any inscription.
##
## The modelled player is deliberately simple: they pursue the cheapest recipe
## they can still finish, bank whichever single piece most advances it, and
## complete the word the moment the last component is in hand mid-run.
func _play_until_inscribed(
	gen: ItemGenerator, book: InscriptionBook, seed_v: int, areas_deep: int, targets: Array,
	max_runs: int
) -> Dictionary:
	var rng := Rng.new(seed_v)
	var bank := Reliquary.new()
	var blocked := {}

	for run in range(1, max_runs + 1):
		bank.begin_run()

		# Components in hand this run: everything banked, plus what drops now.
		var held_sigils := bank.sigil_ids().duplicate()
		# slot -> set of socket counts held, since matching is now exact.
		var held_vessels := {}
		for v in bank.vessels():
			var slot := str(v.get("slot", ""))
			if not held_vessels.has(slot):
				held_vessels[slot] = {}
			held_vessels[slot][int(v.get("sockets", 0))] = true

		# What is this run waiting on, before anything drops? Aggregated across
		# every run of every player, this answers the question a median cannot:
		# a long chase caused by missing sigils and a long chase caused by a
		# missing vessel look identical in the summary and want opposite fixes.
		# Transmutation already puts a floor under sigil luck; nothing does that
		# for a vessel, so if the wait is mostly vessels then no amount of sigil
		# tuning will move it.
		var reason := _blocked_by(targets, held_sigils, held_vessels)
		blocked[reason] = int(blocked.get(reason, 0)) + 1

		var loose_sigils: Array = []
		var loose_vessels: Array = []

		# Walk the real structure rather than a flat stack of floors. Areas pay
		# gear on the cadence Progression sets, and clearing an act earns a
		# deposit — so how deep a run gets is what decides how much of it you
		# keep, which is the entire point of tying the bank to depth.
		for area_index in range(1, areas_deep + 1):
			var act := Progression.act_of_depth(area_index)
			var area := ((area_index - 1) % Progression.AREAS_PER_ACT) + 1
			var reward := Progression.reward_of(area)
			if reward == Progression.Reward.BOON:
				continue
			if Progression.kind_of(area) == Progression.AreaKind.BOSS:
				bank.earn_deposit()

			var ilvl := area_index + 3
			if rng.chance(SIGIL_DROP_CHANCE):
				loose_sigils.append(book.roll_sigil(rng, ilvl).id)
			else:
				var drop := gen.roll_item(ilvl, rng, 0.5)
				if drop.is_empty_vessel():
					loose_vessels.append({"slot": drop.slot, "sockets": drop.sockets})

			# Can anything be completed right now?
			var done := _completable(targets, held_sigils + loose_sigils, held_vessels, loose_vessels)
			if done != "":
				return {"run": run, "inscription": done, "blocked": blocked}

		# End of run: keep the single most useful piece, then convert surplus.
		_bank_best(bank, book, targets, held_sigils, held_vessels, loose_sigils, loose_vessels, gen)
		_transmute_surplus(bank, book, targets)

	return {"run": -1, "inscription": "", "blocked": blocked}


## What the cheapest live target is still missing, given only banked components.
##
## "vessel" and "sigils" want different fixes, and the distinction is invisible
## in a median. Reported per run rather than per player so a chase that spends
## thirty runs holding the right sigils and waiting for one three-socket dagger
## is legible as exactly that.
func _blocked_by(targets: Array, sigils: Array, banked_vessels: Dictionary) -> String:
	if targets.is_empty():
		return "none"
	var need: Dictionary = (targets[0] as Inscription).requirements()
	var slot: String = need["slot"]
	var want_sockets: int = need["vessel_sockets"]

	var have_vessel: bool = banked_vessels.has(slot) and banked_vessels[slot].has(want_sockets)

	var pool := sigils.duplicate()
	var have_sigils := true
	for sigil_id in need["sigils"]:
		for _n in int(need["sigils"][sigil_id]):
			var at := pool.find(sigil_id)
			if at < 0:
				have_sigils = false
				break
			pool.remove_at(at)
		if not have_sigils:
			break

	if have_vessel and have_sigils:
		return "ready"
	if have_vessel:
		return "sigils"
	if have_sigils:
		return "vessel"
	return "both"


## The first target whose every component is in hand, or "".
func _completable(
	targets: Array, sigils: Array, banked_vessels: Dictionary, loose_vessels: Array
) -> String:
	for t in targets:
		var need: Dictionary = t.requirements()
		var slot: String = need["slot"]
		var want_sockets: int = need["vessel_sockets"]

		# Exactly, not merely enough — see docs/d2-rune-economy.md.
		var have_vessel: bool = banked_vessels.has(slot) and banked_vessels[slot].has(want_sockets)
		if not have_vessel:
			for v in loose_vessels:
				if (slot == "" or str(v["slot"]) == slot) and int(v["sockets"]) == want_sockets:
					have_vessel = true
					break
		if not have_vessel:
			continue

		var pool := sigils.duplicate()
		var short := false
		for sigil_id in need["sigils"]:
			for _n in int(need["sigils"][sigil_id]):
				var at := pool.find(sigil_id)
				if at < 0:
					short = true
					break
				pool.remove_at(at)
			if short:
				break
		if not short:
			return t.id
	return ""


## Bank the piece that most advances the cheapest live target: the vessel if we
## still lack one big enough, otherwise a sigil the recipe still wants.
## Bank as much as the run earned, best piece first.
##
## Deposits used to be one flat allowance per run, so this kept a single item
## and returned. They are earned by depth now — see Reliquary.DEPOSITS_PER_ACT —
## so a deep run keeps several components and a shallow one keeps one piece,
## which is the whole reason tying the bank to progress is worth doing.
func _bank_best(
	bank: Reliquary,
	book: InscriptionBook,
	targets: Array,
	held_sigils: Array,
	held_vessels: Dictionary,
	loose_sigils: Array,
	loose_vessels: Array,
	gen: ItemGenerator
) -> void:
	while bank.deposits_remaining() > 0 and not bank.is_full():
		if not _bank_one(bank, book, targets, held_sigils, held_vessels, loose_sigils, loose_vessels):
			return


## Bank the single piece that most advances the cheapest live target, and remove
## it from what the run is still carrying. Returns false when nothing left in
## hand is worth a deposit, which is what stops the caller looping.
func _bank_one(
	bank: Reliquary,
	book: InscriptionBook,
	targets: Array,
	held_sigils: Array,
	held_vessels: Dictionary,
	loose_sigils: Array,
	loose_vessels: Array
) -> bool:
	if targets.is_empty():
		return false

	var target: Inscription = targets[0]
	var need: Dictionary = target.requirements()
	var slot: String = need["slot"]
	var want_sockets: int = need["vessel_sockets"]

	var has_exact: bool = held_vessels.has(slot) and held_vessels[slot].has(want_sockets)
	if not has_exact:
		for i in loose_vessels.size():
			var v: Dictionary = loose_vessels[i]
			if (slot == "" or str(v["slot"]) == slot) and int(v["sockets"]) == want_sockets:
				var item := Item.new()
				item.slot = str(v["slot"])
				item.base_name = "Vessel"
				item.sockets = int(v["sockets"])
				if not bank.deposit_vessel(item):
					return false
				loose_vessels.remove_at(i)
				if not held_vessels.has(item.slot):
					held_vessels[item.slot] = {}
				held_vessels[item.slot][item.sockets] = true
				return true

	for sigil_id in need["sigils"]:
		var wanted := int(need["sigils"][sigil_id])
		var have := held_sigils.count(sigil_id)
		var at := loose_sigils.find(sigil_id)
		if have < wanted and at >= 0:
			if not bank.deposit_sigil(book.sigil_by_id(str(sigil_id))):
				return false
			loose_sigils.remove_at(at)
			held_sigils.append(str(sigil_id))
			return true

	# Nothing on the critical path in hand — keep the rarest sigil found, which
	# is what a player hoarding for a later recipe would do.
	var best_sigil := ""
	var best_tier := -1
	var best_at := -1
	for i in loose_sigils.size():
		var sg := book.sigil_by_id(str(loose_sigils[i]))
		if sg != null and sg.tier > best_tier:
			best_tier = sg.tier
			best_sigil = str(loose_sigils[i])
			best_at = i
	if best_sigil == "":
		return false
	if not bank.deposit_sigil(book.sigil_by_id(best_sigil)):
		return false
	loose_sigils.remove_at(best_at)
	held_sigils.append(best_sigil)
	return true


func _run_pass(
	label: String,
	gen: ItemGenerator,
	book: InscriptionBook,
	players: int,
	areas_deep: int,
	targets: Array,
	max_runs: int
) -> void:
	var runs: Array[int] = []
	var never := 0
	var which := {}
	var blocked := {}

	for p in players:
		var outcome := _play_until_inscribed(gen, book, p * 7919 + 17, areas_deep, targets, max_runs)
		for reason in outcome.get("blocked", {}):
			blocked[reason] = int(blocked.get(reason, 0)) + int(outcome["blocked"][reason])
		if outcome["run"] < 0:
			never += 1
		else:
			runs.append(outcome["run"])
			var id: String = outcome["inscription"]
			which[id] = int(which.get(id, 0)) + 1

	runs.sort()
	print("")
	print("-- %s" % label)
	_report(runs, never, which, players, max_runs)
	_report_blockers(blocked)


## Convert banked duplicates upward, the way D2's cube lets you cash surplus
## commons in on the rune you are chasing.
##
## This is the mechanism the design was missing entirely. Ashfall's rarest sigil
## is about thirty times *more* common than D2's Zod, so rarity was never why the
## chase stalled — it stalled because a miss stayed a miss forever. With this,
## every junk drop is progress toward something.
func _transmute_surplus(bank: Reliquary, book: InscriptionBook, targets: Array) -> void:
	var wanted := {}
	for t in targets:
		for id in t.requirements()["sigils"]:
			wanted[str(id)] = int(t.requirements()["sigils"][id])

	var converted := true
	while converted:
		converted = false
		var counts := {}
		for id in bank.sigil_ids():
			counts[id] = int(counts.get(id, 0)) + 1

		for id in counts:
			var sigil := book.sigil_by_id(str(id))
			if sigil == null:
				continue
			var cost := InscriptionBook.transmute_cost(sigil.tier)
			var spare: int = int(counts[id]) - int(wanted.get(id, 0))
			if spare < cost:
				continue
			var up := book.transmute_target(str(id))
			if up == null:
				continue
			# Spend the duplicates, gain one of the tier above.
			var removed := 0
			while removed < cost:
				var at := _find_sigil(bank, str(id))
				if at < 0:
					break
				bank.discard_at(at)
				removed += 1
			if removed == cost:
				bank.contents.append({"kind": "sigil", "id": up.id})
				converted = true
			break


## Index of the first banked entry holding this sigil, or -1.
func _find_sigil(bank: Reliquary, id: String) -> int:
	for i in bank.contents.size():
		var e: Dictionary = bank.contents[i]
		if str(e.get("kind", "")) == "sigil" and str(e.get("id", "")) == id:
			return i
	return -1


func _report(
	runs: Array[int], never: int, which: Dictionary, players: int, max_runs: int
) -> void:
	print("")
	if runs.is_empty():
		print("   NOBODY completed it within %d runs." % max_runs)
		return

	print("   runs to completion:  p10 %d | median %d | p90 %d | worst %d"
		% [_pct(runs, 0.10), _pct(runs, 0.50), _pct(runs, 0.90), runs[runs.size() - 1]])
	print("   never got one in %d runs: %.1f%%" % [max_runs, 100.0 * never / float(players)])

	var line := "   share inscribed by run:"
	for milestone in [1, 3, 5, 10, 20, 40, 80]:
		var got := runs.filter(func(r): return r <= milestone).size()
		line += "  r%d %.0f%%" % [milestone, 100.0 * got / float(players)]
	print(line)

	print("   first inscription completed:")
	var entries: Array = []
	for k in which:
		entries.append([k, which[k]])
	entries.sort_custom(func(a, b): return a[1] > b[1])
	for e in entries.slice(0, 5):
		print("     %-16s %5d  (%.0f%%)" % [e[0], e[1], 100.0 * e[1] / float(players)])


func _pct(sorted_values: Array, p: float) -> int:
	if sorted_values.is_empty():
		return 0
	var idx := clampi(int(floor(p * (sorted_values.size() - 1))), 0, sorted_values.size() - 1)
	return sorted_values[idx]


## Where the waiting actually goes.
##
## A chase blocked on sigils and a chase blocked on a vessel have the same
## median and opposite fixes: sigil luck already has a floor under it via
## transmutation, and a vessel has none at all, so a wait dominated by vessels
## cannot be tuned away by touching drop rates.
func _report_blockers(blocked: Dictionary) -> void:
	var total := 0
	for k in blocked:
		total += int(blocked[k])
	if total == 0:
		return
	var parts: Array[String] = []
	for reason in ["both", "vessel", "sigils", "ready"]:
		var n := int(blocked.get(reason, 0))
		if n > 0:
			parts.append("%s %.0f%%" % [reason, 100.0 * float(n) / float(total)])
	print("   run-starts blocked on:  " + "  ".join(parts))
