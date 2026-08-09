extends TestCase

## The demo's warm start.
##
## This exists because the demo has been the project's main way of *looking* at
## the game, and it was lying by omission. Every recording opened in Normal Act
## I, where exceptional bases cannot drop, so no three-socket vessel could drop,
## so item tiers, long inscriptions and most named items were all invisible —
## and "the demo does not show itemisation" was a true statement about the clip
## rather than about the game.
##
## What is pinned here is that the warm start is a real run rather than a
## handout: it lands where it says it lands, it earns its gear through the same
## roll and the same upgrade test, and it arrives somewhere the loot systems are
## actually on.

const STEP := 1.0 / 30.0


func _main() -> Node:
	var tree := Engine.get_main_loop() as SceneTree
	var packed: PackedScene = load("res://scenes/main.tscn")
	assert_ne(packed, null, "main.tscn does not load")
	var node := packed.instantiate()
	node.set("warm_start_depth", Progression.areas_per_difficulty() + 1)
	tree.root.add_child(node)
	assert_true(node.is_inside_tree(), "scene tests need a live tree")
	return node


## The one the recording depends on. If this lands in Normal the clip is back to
## showing a game with no item ladder in it.
func test_a_warm_start_opens_in_nightmare() -> void:
	var main := _main()
	var run: RunState = main.get("run")
	assert_ne(run, null, "warm start produced no run")
	assert_eq(run.difficulty_number, 2, "warm start did not reach the second pass")
	assert_eq(run.act_number, 1)
	assert_eq(run.area_number, 1)
	assert_eq(run.depth(), Progression.areas_per_difficulty() + 1)
	main.queue_free()


## It has to arrive equipped and blessed, or it is just a deeper character with
## a first-area build, which would die instantly and show nothing.
func test_a_warm_start_arrives_carrying_a_run() -> void:
	var main := _main()
	var run: RunState = main.get("run")
	assert_gt(float(run.gear.size()), 0.0, "warm start arrived wearing nothing")
	assert_gt(float(run.boons.size()), 0.0, "warm start arrived with no blessings")
	# Stronger than a fresh character by a wide margin, since it is about to be
	# hit by enemies with a full difficulty pass of scaling on them.
	var base := RunState.base_stats(run.school)
	var here := run.build_stats()
	assert_gt(here.max_health, base.max_health, "warm start is no tougher than a new character")
	assert_almost_eq(run.health, here.max_health, 0.01)
	main.queue_free()


## And the point of arriving there: bases that only exist past Normal.
func test_nightmare_offers_bases_normal_cannot() -> void:
	var gen := ItemGenerator.from_json("res://data/items.json")
	var in_normal := gen.bases_for(1).size()
	var in_nightmare := gen.bases_for(2).size()
	assert_gt(float(in_nightmare), float(in_normal), "Nightmare adds no bases of its own")

	var best_normal := 0
	for entry in gen.bases_for(1):
		best_normal = maxi(best_normal, Item.max_sockets(ItemGenerator.tier_of_base(entry)))
	var best_nightmare := 0
	for entry in gen.bases_for(2):
		best_nightmare = maxi(best_nightmare, Item.max_sockets(ItemGenerator.tier_of_base(entry)))
	assert_gt(
		float(best_nightmare), float(best_normal),
		"Nightmare grants no more sockets than Normal, so the warm start shows nothing new"
	)


## A zero warm start must still be the ordinary opening, or every normal launch
## quietly starts mid-run.
func test_no_warm_start_opens_at_the_beginning() -> void:
	var tree := Engine.get_main_loop() as SceneTree
	var packed: PackedScene = load("res://scenes/main.tscn")
	var node := packed.instantiate()
	tree.root.add_child(node)
	var run: RunState = node.get("run")
	assert_eq(run.depth(), 1)
	assert_eq(run.difficulty_number, 1)
	node.queue_free()
