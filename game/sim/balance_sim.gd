extends SceneTree

## Headless balance simulator.
##
##   godot --headless --script res://sim/balance_sim.gd
##   godot --headless --script res://sim/balance_sim.gd -- 5000 0.55
##
## Args: [runs] [dodge_rate]. Plays whole runs through the same core code the
## real game uses, then reports how deep they got and what they picked.
##
## This exists because the numbers in data/*.json and RunState.enemy_for_floor
## are guesses. Guesses are fine as long as something checks them — and a
## thousand simulated runs answer "does anything survive floor 10" and "is one
## boon in every winning build" far faster than playtesting can.
##
## What it deliberately does NOT tell you: whether any of this is fun. Time to
## kill and build diversity are proxies. A human still has to play it.

const MAX_FLOOR := 15
const ENEMIES_BASE := 5
const ELITE_EVERY := 3

## Attacks per second, used to turn per-hit damage into a rate.
const PLAYER_ATTACK_RATE := 1.7
const ENEMY_ATTACK_RATE := 0.8

## Fraction of incoming damage a competent player avoids by dashing. This is the
## single biggest unknown in the model — it stands in for skill, and the game's
## real difficulty curve is far more sensitive to it than to any table below.
const DEFAULT_DODGE := 0.5

## Healing between floors, as a fraction of max health.
const FLOOR_HEAL := 0.25

const ITEMS_PATH := "res://data/items.json"
const BOONS_PATH := "res://data/boons.json"

## Typed so the loop variable is a String rather than a Variant.
const POLICIES: Array[String] = ["greedy_damage", "random"]


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var runs := int(args[0]) if args.size() > 0 else 1000
	var dodge := float(args[1]) if args.size() > 1 else DEFAULT_DODGE

	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var pool := BoonPool.from_json(BOONS_PATH)

	print("")
	print("Ashfall balance simulation")
	print("==========================")
	print("runs=%d  dodge=%.2f  max_floor=%d" % [runs, dodge, MAX_FLOOR])

	for policy in POLICIES:
		var result := _simulate_many(gen, pool, runs, dodge, policy)
		_report(policy, result, runs)

	print("")
	quit(0)


func _simulate_many(
	gen: ItemGenerator, pool: BoonPool, runs: int, dodge: float, policy: String
) -> Dictionary:
	var depths: Array[int] = []
	var boon_picks := {}
	var tag_counts := {}
	var ttk_by_floor := {}

	for i in runs:
		var outcome := _simulate_one(gen, pool, i * 7919 + 13, dodge, policy)
		depths.append(outcome["depth"])
		for id in outcome["boons"]:
			boon_picks[id] = boon_picks.get(id, 0) + 1
		for t in outcome["tags"]:
			tag_counts[t] = tag_counts.get(t, 0) + 1
		for f in outcome["ttk"]:
			if not ttk_by_floor.has(f):
				ttk_by_floor[f] = []
			ttk_by_floor[f].append(outcome["ttk"][f])

	depths.sort()
	return {
		"depths": depths,
		"boon_picks": boon_picks,
		"tag_counts": tag_counts,
		"ttk_by_floor": ttk_by_floor,
	}


func _simulate_one(
	gen: ItemGenerator, pool: BoonPool, seed_v: int, dodge: float, policy: String
) -> Dictionary:
	var run := RunState.start(seed_v)
	var picked_ids: Array = []
	var ttk := {}
	var depth := 0

	for floor_n in range(1, MAX_FLOOR + 1):
		run.floor_number = floor_n
		var stats := run.build_stats()
		# Stats are rebuilt at the top of each floor, so a boon taken last floor
		# is live now — matching what the real game does in _next_floor.
		var count := ENEMIES_BASE + int(floor_n / 2)
		var floor_ttk := 0.0

		for e in count:
			var elite := (e == 0 and floor_n % ELITE_EVERY == 0)
			var enemy := RunState.enemy_for_floor(floor_n, elite)

			var player_dps := stats.expected_hit(enemy) * PLAYER_ATTACK_RATE
			var seconds := enemy.max_health / maxf(player_dps, 0.01)
			floor_ttk += seconds

			var enemy_dps := enemy.expected_hit(stats) * ENEMY_ATTACK_RATE * (1.0 - dodge)
			run.health -= seconds * enemy_dps

			if run.health <= 0.0:
				break

		ttk[floor_n] = floor_ttk / float(count)
		if run.health <= 0.0:
			break

		depth = floor_n

		# Reward: one drop, equipped if it raises expected damage, plus a boon.
		var drop := gen.roll_item(floor_n + 3, run.loot_rng, 0.5)
		if _is_upgrade(run, drop):
			run.equip(drop)

		var offer := pool.offer(
			run.boon_rng, run.owned_boon_ids(), run.owned_boon_groups(), run.gear_tags(), 3
		)
		if not offer.is_empty():
			var choice := _choose(run, offer, policy)
			run.take_boon(choice)
			picked_ids.append(choice.id)

		var healed := run.build_stats().max_health * FLOOR_HEAL
		run.health = minf(run.build_stats().max_health, run.health + healed)

	return {"depth": depth, "boons": picked_ids, "tags": run.gear_tags(), "ttk": ttk}


## Would equipping this raise expected damage against a same-depth enemy?
## Uses the real stat pipeline rather than a heuristic, so an item that trades
## damage for resistance is judged the way combat will actually judge it.
func _is_upgrade(run: RunState, drop: Item) -> bool:
	var enemy := RunState.enemy_for_floor(run.floor_number)
	var before := run.build_stats().expected_hit(enemy)

	var trial := RunState.base_stats()
	for slot in run.gear:
		if slot != drop.slot:
			run.gear[slot].apply_to(trial)
	drop.apply_to(trial)
	for b in run.boons:
		trial.apply_all(b.mods)

	return trial.expected_hit(enemy) > before


func _choose(run: RunState, offer: Array, policy: String) -> Boon.Rolled:
	if policy == "random":
		return offer[run.boon_rng.randi_range(0, offer.size() - 1)]

	# greedy_damage: take whatever raises expected damage most right now.
	var enemy := RunState.enemy_for_floor(run.floor_number)
	var best: Boon.Rolled = offer[0]
	var best_score := -INF
	for candidate in offer:
		var trial := run.build_stats()
		trial.apply_all(candidate.mods)
		var score := trial.expected_hit(enemy)
		if score > best_score:
			best_score = score
			best = candidate
	return best


func _report(policy: String, result: Dictionary, runs: int) -> void:
	var depths: Array = result["depths"]
	print("")
	print("-- policy: %s" % policy)
	print("   depth   p10 %d | median %d | p90 %d | max %d"
		% [_pct(depths, 0.10), _pct(depths, 0.50), _pct(depths, 0.90), depths[depths.size() - 1]])

	var cleared := depths.filter(func(d): return d >= MAX_FLOOR).size()
	print("   cleared floor %d: %.1f%% of runs" % [MAX_FLOOR, 100.0 * cleared / float(runs)])

	var ttk: Dictionary = result["ttk_by_floor"]
	var floors := ttk.keys()
	floors.sort()
	# Only runs that reached a floor contribute a sample to it, so deep-floor
	# figures are survivorship-biased — they describe the builds that got there,
	# not the average build. Printing n alongside keeps that visible instead of
	# letting a flat-looking curve read as "difficulty is fine at depth".
	var line := "   avg seconds-to-kill (n = runs that reached the floor):"
	for f in floors:
		if f % 3 == 1:
			var samples: Array = ttk[f]
			line += "  f%d %.1fs/n=%d" % [f, _mean(samples), samples.size()]
	print(line)

	print("   most-picked boons:")
	for entry in _top(result["boon_picks"], 5):
		print("     %-22s %5d picks (%.0f%% of runs)" % [entry[0], entry[1], 100.0 * entry[1] / float(runs)])

	var tags: Array = _top(result["tag_counts"], 5)
	if not tags.is_empty():
		var tag_line := "   gear tags seen:  "
		for entry in tags:
			tag_line += "%s %.0f%%  " % [entry[0], 100.0 * entry[1] / float(runs)]
		print(tag_line)


func _pct(sorted_values: Array, p: float) -> int:
	if sorted_values.is_empty():
		return 0
	var idx := clampi(int(floor(p * (sorted_values.size() - 1))), 0, sorted_values.size() - 1)
	return sorted_values[idx]


func _mean(values: Array) -> float:
	if values.is_empty():
		return 0.0
	var t := 0.0
	for v in values:
		t += v
	return t / float(values.size())


func _top(counts: Dictionary, n: int) -> Array:
	var entries: Array = []
	for k in counts:
		entries.append([k, counts[k]])
	entries.sort_custom(func(a, b): return a[1] > b[1])
	return entries.slice(0, n)
