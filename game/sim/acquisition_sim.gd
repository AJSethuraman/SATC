extends SceneTree

## How many runs until your first inscription?
##
##   godot --headless --path game --script res://sim/acquisition_sim.gd
##   godot --headless --path game --script res://sim/acquisition_sim.gd -- 2000 5
##
## Args: [players] [floors_cleared_per_run].
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
	var floors := int(args[1]) if args.size() > 1 else 5

	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var book := InscriptionBook.from_json(SIGILS_PATH)

	print("")
	print("Ashfall acquisition simulation")
	print("==============================")
	print("players=%d  floors cleared per run=%d  sigil drop chance=%.2f"
		% [players, floors, SIGIL_DROP_CHANCE])
	print("reliquary: %d capacity, %d deposit per run"
		% [Reliquary.DEFAULT_CAPACITY, Reliquary.DEPOSITS_PER_RUN])

	# Pass one: any inscription at all. This is the on-ramp — how long before the
	# system first does anything for you.
	_run_pass(
		"ANY inscription (the on-ramp)", gen, book, players, floors,
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
				gen, book, players, floors, [chased], CHASE_MAX_RUNS
			)
	print("")
	quit(0)


## One player, run after run, until they complete any inscription.
##
## The modelled player is deliberately simple: they pursue the cheapest recipe
## they can still finish, bank whichever single piece most advances it, and
## complete the word the moment the last component is in hand mid-run.
func _play_until_inscribed(
	gen: ItemGenerator, book: InscriptionBook, seed_v: int, floors: int, targets: Array,
	max_runs: int
) -> Dictionary:
	var rng := Rng.new(seed_v)
	var bank := Reliquary.new()

	for run in range(1, max_runs + 1):
		bank.begin_run()

		# Components in hand this run: everything banked, plus what drops now.
		var held_sigils := bank.sigil_ids().duplicate()
		var held_vessels := {}
		for v in bank.vessels():
			var slot := str(v.get("slot", ""))
			held_vessels[slot] = maxi(int(held_vessels.get(slot, 0)), int(v.get("sockets", 0)))

		var loose_sigils: Array = []
		var loose_vessels: Array = []

		for floor_n in range(1, floors + 1):
			var ilvl := floor_n + 3
			if rng.chance(SIGIL_DROP_CHANCE):
				loose_sigils.append(book.roll_sigil(rng, ilvl).id)
			else:
				var drop := gen.roll_item(ilvl, rng, 0.5)
				if drop.is_empty_vessel():
					loose_vessels.append({"slot": drop.slot, "sockets": drop.sockets})

			# Can anything be completed right now?
			var done := _completable(targets, held_sigils + loose_sigils, held_vessels, loose_vessels)
			if done != "":
				return {"run": run, "inscription": done}

		# End of run: keep the single most useful piece.
		_bank_best(bank, book, targets, held_sigils, held_vessels, loose_sigils, loose_vessels, gen)

	return {"run": -1, "inscription": ""}


## The first target whose every component is in hand, or "".
func _completable(
	targets: Array, sigils: Array, banked_vessels: Dictionary, loose_vessels: Array
) -> String:
	for t in targets:
		var need: Dictionary = t.requirements()
		var slot: String = need["slot"]
		var want_sockets: int = need["vessel_sockets"]

		var have_vessel := int(banked_vessels.get(slot, 0)) >= want_sockets
		if not have_vessel:
			for v in loose_vessels:
				if (slot == "" or str(v["slot"]) == slot) and int(v["sockets"]) >= want_sockets:
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
	if bank.is_full() or targets.is_empty():
		return

	var target: Inscription = targets[0]
	var need: Dictionary = target.requirements()
	var slot: String = need["slot"]
	var want_sockets: int = need["vessel_sockets"]

	if int(held_vessels.get(slot, 0)) < want_sockets:
		var best := {}
		for v in loose_vessels:
			if (slot == "" or str(v["slot"]) == slot) and int(v["sockets"]) >= want_sockets:
				best = v
				break
		if not best.is_empty():
			var item := Item.new()
			item.slot = str(best["slot"])
			item.base_name = "Vessel"
			item.sockets = int(best["sockets"])
			bank.deposit_vessel(item)
			return

	for sigil_id in need["sigils"]:
		var wanted := int(need["sigils"][sigil_id])
		var have := held_sigils.count(sigil_id)
		if have < wanted and loose_sigils.has(sigil_id):
			bank.deposit_sigil(book.sigil_by_id(str(sigil_id)))
			return

	# Nothing on the critical path dropped — keep the rarest sigil found, which
	# is what a player hoarding for a later recipe would do.
	var best_sigil := ""
	var best_tier := -1
	for id in loose_sigils:
		var s := book.sigil_by_id(str(id))
		if s != null and s.tier > best_tier:
			best_tier = s.tier
			best_sigil = str(id)
	if best_sigil != "":
		bank.deposit_sigil(book.sigil_by_id(best_sigil))


func _run_pass(
	label: String,
	gen: ItemGenerator,
	book: InscriptionBook,
	players: int,
	floors: int,
	targets: Array,
	max_runs: int
) -> void:
	var runs: Array[int] = []
	var never := 0
	var which := {}

	for p in players:
		var outcome := _play_until_inscribed(gen, book, p * 7919 + 17, floors, targets, max_runs)
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
