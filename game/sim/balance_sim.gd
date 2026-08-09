extends SceneTree

## Headless balance simulator.
##
##   godot --headless --script res://sim/balance_sim.gd
##   godot --headless --script res://sim/balance_sim.gd -- 5000 0.55
##
## Args: [runs] [dodge_rate]. Plays whole runs through the same core code the
## real game uses, then reports how deep they got and what they picked.
##
## This exists because the numbers in data/*.json and RunState.enemy_for_depth
## are guesses. Guesses are fine as long as something checks them — and a
## thousand simulated runs answer "does anything survive act 2" and "is one
## boon in every winning build" far faster than playtesting can.
##
## What it deliberately does NOT tell you: whether any of this is fun. Time to
## kill and build diversity are proxies. A human still has to play it.


## Attacks per second, used to turn per-hit damage into a rate.
const PLAYER_ATTACK_RATE := 1.7
const ENEMY_ATTACK_RATE := 0.8

## Fraction of incoming damage a competent player avoids by dashing. This is the
## single biggest unknown in the model — it stands in for skill, and the game's
## real difficulty curve is far more sensitive to it than to any table below.
const DEFAULT_DODGE := 0.5

## Healing between areas, and the larger restore for clearing an act. Both
## mirror scenes/main.gd — if they drift, the simulator stops measuring the game.
const AREA_HEAL := 0.12
const BOSS_HEAL := 0.35
const RESPITE_HEAL := 0.5

const ITEMS_PATH := "res://data/items.json"
const BOONS_PATH := "res://data/boons.json"

## Pick policies, standing in for kinds of player.
##
## `greedy_damage` always takes the biggest immediate number; `committed` picks
## a direction early and then scales it; `random` is the floor.
##
## The expectation when `committed` was added was that it would beat greedy,
## since a typed multiplier is worth nothing until you have the damage type it
## multiplies and greedy cannot see one move ahead. It does not. At 200 runs it
## is slightly *worse* (median depth 3 vs 4), and both sit level with `random`.
## That spread — or rather the lack of one — is the most useful number this
## simulator currently produces: it says boon choice is not what decides a run.
## See the README for where the pressure is actually coming from.
const POLICIES: Array[String] = ["greedy_damage", "committed", "random"]


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var runs := int(args[0]) if args.size() > 0 else 1000
	var dodge := float(args[1]) if args.size() > 1 else DEFAULT_DODGE

	var gen := ItemGenerator.from_json(ITEMS_PATH)
	var pool := BoonPool.from_json(BOONS_PATH)

	print("")
	print("Ashfall balance simulation")
	print("==========================")
	print("runs=%d  dodge=%.2f  areas=%d (%d acts x %d)" %
		[runs, dodge, Progression.total_areas(), Progression.ACTS, Progression.AREAS_PER_ACT])

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
	var ttk_by_area := {}

	for i in runs:
		var outcome := _simulate_one(gen, pool, i * 7919 + 13, dodge, policy)
		depths.append(outcome["depth"])
		for id in outcome["boons"]:
			boon_picks[id] = boon_picks.get(id, 0) + 1
		for t in outcome["tags"]:
			tag_counts[t] = tag_counts.get(t, 0) + 1
		for f in outcome["ttk"]:
			if not ttk_by_area.has(f):
				ttk_by_area[f] = []
			ttk_by_area[f].append(outcome["ttk"][f])

	depths.sort()
	return {
		"depths": depths,
		"boon_picks": boon_picks,
		"tag_counts": tag_counts,
		"ttk_by_area": ttk_by_area,
	}


func _simulate_one(
	gen: ItemGenerator, pool: BoonPool, seed_v: int, dodge: float, policy: String
) -> Dictionary:
	var run := RunState.start(seed_v)
	var picked_ids: Array = []
	var ttk := {}
	var depth := 0

	while true:
		var area := run.area_number
		var kind := Progression.kind_of(area)
		var here := run.depth()
		var stats := run.build_stats()
		# Stats are rebuilt at the top of each area, so a boon taken last area is
		# live now — matching what the real game does in _next_area.

		if kind == Progression.AreaKind.RESPITE:
			run.health = minf(stats.max_health, run.health + stats.max_health * RESPITE_HEAL)
			depth = here
			if not run.advance_area():
				break
			continue

		var count := Progression.enemy_count(run.act_number, area)
		var area_ttk := 0.0
		var boss_here := kind == Progression.AreaKind.BOSS

		for e in count:
			var lead := e == 0
			var elite := lead and Progression.has_elite(area)
			var enemy: StatBlock = (
				RunState.boss_for_act(run.act_number) if (lead and boss_here)
				else RunState.enemy_for_depth(here, elite)
			)

			var player_dps := stats.expected_hit(enemy) * PLAYER_ATTACK_RATE
			var seconds := enemy.max_health / maxf(player_dps, 0.01)
			area_ttk += seconds

			var enemy_dps := enemy.expected_hit(stats) * ENEMY_ATTACK_RATE * (1.0 - dodge)
			run.health -= seconds * enemy_dps

			if run.health <= 0.0:
				break

		ttk[here] = area_ttk / float(count)
		if run.health <= 0.0:
			break

		depth = here

		# Reward cadence comes from Progression, so the simulator cannot drift
		# into measuring a more generous game than the one being played.
		match Progression.reward_of(area):
			Progression.Reward.ITEM:
				_maybe_equip(gen, run, here, 3, 0.5)
			Progression.Reward.BOON:
				_take_boon(pool, run, policy, picked_ids)
			Progression.Reward.ACT_PRIZE:
				_maybe_equip(gen, run, here, 7, 0.85)
				_take_boon(pool, run, policy, picked_ids)

		var heal := BOSS_HEAL if boss_here else AREA_HEAL
		var full := run.build_stats().max_health
		run.health = minf(full, run.health + full * heal)

		if not run.advance_area():
			break

	return {"depth": depth, "boons": picked_ids, "tags": run.active_tags(), "ttk": ttk}


func _maybe_equip(
	gen: ItemGenerator, run: RunState, here: int, bonus: int, magic: float
) -> void:
	var drop := gen.roll_item(here + bonus, run.loot_rng, magic)
	if _is_upgrade(run, drop):
		run.equip(drop)


func _take_boon(pool: BoonPool, run: RunState, policy: String, picked_ids: Array) -> void:
	var offer := pool.offer(
		run.boon_rng, run.owned_boon_ids(), run.owned_boon_groups(), run.active_tags(), 3
	)
	if offer.is_empty():
		return
	var choice := _choose(run, offer, policy)
	run.take_boon(choice)
	picked_ids.append(choice.id)


## Would equipping this raise expected damage against a same-depth enemy?
## Uses the real stat pipeline rather than a heuristic, so an item that trades
## damage for resistance is judged the way combat will actually judge it.
func _is_upgrade(run: RunState, drop: Item) -> bool:
	var enemy := RunState.enemy_for_depth(run.depth())
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

	if policy == "committed":
		# Take a direction before taking a number: while the build has fewer
		# than two tags, prefer anything that grants one. After that, greedy.
		if run.active_tags().size() < 2:
			for candidate in offer:
				if not candidate.tags.is_empty():
					return candidate

	# greedy_damage: take whatever raises expected damage most right now.
	var enemy := RunState.enemy_for_depth(run.depth())
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

	# Depth is in areas, which is the right unit for a curve and the wrong one
	# for a person. Say where the median run actually dies.
	var median: int = _pct(depths, 0.50)
	print("   median run ends in %s, area %d of %d"
		% [
			Progression.act_label(Progression.act_of_depth(median)),
			((maxi(1, median) - 1) % Progression.AREAS_PER_ACT) + 1,
			Progression.AREAS_PER_ACT,
		])

	var cleared := depths.filter(func(d): return d >= Progression.total_areas()).size()
	print("   cleared all %d acts: %.1f%% of runs" % [Progression.ACTS, 100.0 * cleared / float(runs)])

	var ttk: Dictionary = result["ttk_by_area"]
	var areas := ttk.keys()
	areas.sort()
	# Only runs that reached a area contribute a sample to it, so deep-area
	# figures are survivorship-biased — they describe the builds that got there,
	# not the average build. Printing n alongside keeps that visible instead of
	# letting a flat-looking curve read as "difficulty is fine at depth".
	var line := "   avg seconds-to-kill (n = runs that reached the area):"
	for f in areas:
		if f % 4 == 1:
			var samples: Array = ttk[f]
			line += "  r%d %.1fs/n=%d" % [f, _mean(samples), samples.size()]
	print(line)

	# Build diversity, the metric this whole rebalance was aimed at. A handful
	# of boons appearing in nearly every run means there is one correct build
	# and the choices are decorative.
	var picks: Dictionary = result["boon_picks"]
	var common := 0
	var top_rate := 0.0
	for k in picks:
		var rate := float(picks[k]) / float(runs)
		top_rate = maxf(top_rate, rate)
		if rate >= 0.05:
			common += 1
	print("   diversity: %d boons taken in >=5%% of runs | most-taken appears in %.0f%%"
		% [common, 100.0 * top_rate])

	print("   most-picked boons:")
	for entry in _top(picks, 5):
		print("     %-22s %5d picks (%.0f%% of runs)" % [entry[0], entry[1], 100.0 * entry[1] / float(runs)])

	var tags: Array = _top(result["tag_counts"], 5)
	if not tags.is_empty():
		var tag_line := "   build tags seen:  "
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
