extends TestCase

## Scene-level tests for the cast bolt.
##
## These exist because of a bug that no core/ test could ever have caught and
## that cost several rounds of reading a recording back frame by frame: bolts
## spawned, resolved against a body already leaning on the player, and freed
## themselves before they were drawn once. Mana drained, damage landed, enemies
## died, and nothing was ever visible. Every symptom said "working"; the screen
## said otherwise.
##
## So the thing under test here is not damage — core/damage.gd owns that — but
## the bolt's *life*: that it survives long enough to be seen, that it travels,
## and that it still connects with something standing right on top of you.

const STEP := 1.0 / 30.0


## Nodes must be in the tree before global_position means anything, so tests
## that touch a scene borrow the running SceneTree's root and clean up after.
func _holder() -> Node3D:
	var tree := Engine.get_main_loop() as SceneTree
	var holder := Node3D.new()
	tree.root.add_child(holder)
	# Tripwire. Outside a live tree, global_position quietly returns the identity
	# and every assertion below passes or fails for the wrong reason — which is
	# exactly how this file failed the first time it ran.
	assert_true(holder.is_inside_tree(), "scene tests need a live tree")
	return holder


func _enemy_at(holder: Node3D, where: Vector3) -> Enemy:
	var e := Enemy.new()
	e.setup(RunState.enemy_for_depth(1), false, 7)
	holder.add_child(e)
	e.global_position = where
	return e


func _bolt(holder: Node3D, at: Vector3, direction: Vector3) -> Projectile:
	var spell := Spell.from_dict(
		{"id": "bolt", "shape": "projectile", "cost": 0, "speed": 17, "lifetime": 2.0}
	)
	var shot := Projectile.new()
	shot.setup(spell, StatBlock.new(), direction, Rng.new(11), [])
	holder.add_child(shot)
	shot.global_position = at
	return shot


## The regression itself. A body in contact at the moment of casting used to eat
## the bolt on its spawn frame; it must now survive to be drawn.
func test_bolt_is_visible_before_it_can_connect() -> void:
	var holder := _holder()
	var origin := Vector3(0.0, 1.0, 0.0)
	_enemy_at(holder, Vector3(0.6, 0.0, 0.0))
	var shot := _bolt(holder, origin, Vector3.RIGHT)

	shot._process(STEP)
	assert_false(shot.is_queued_for_deletion(), "bolt freed on its first frame")
	assert_true(shot.global_position.x > origin.x, "bolt did not move on its first frame")

	holder.free()


## Arming must not cost reach: a body in contact still has to be hit, just a
## frame or two later than it used to be.
func test_a_body_in_contact_is_still_hit() -> void:
	var holder := _holder()
	var enemy := _enemy_at(holder, Vector3(1.0, 0.0, 0.0))
	var before := enemy.health
	var shot := _bolt(holder, Vector3(0.0, 1.0, 0.0), Vector3.RIGHT)

	for _i in Projectile.ARM_FRAMES + 2:
		if is_instance_valid(shot) and not shot.is_queued_for_deletion():
			shot._process(STEP)

	assert_true(enemy.health < before, "adjacent body took no damage from a bolt")

	holder.free()


## A bolt aimed at nothing should expire on its own rather than accumulate.
func test_a_bolt_that_misses_expires() -> void:
	var holder := _holder()
	var shot := _bolt(holder, Vector3(0.0, 1.0, 0.0), Vector3.RIGHT)

	# Past its lifetime, and well past the arena wall it would leave first.
	for _i in 200:
		if shot.is_queued_for_deletion():
			break
		shot._process(STEP)

	assert_true(shot.is_queued_for_deletion(), "bolt never expired")

	holder.free()
