extends SceneTree

## Headless test entry point.
##
##   godot --headless --script res://tests/run_tests.gd
##   godot --headless --script res://tests/run_tests.gd -- damage
##
## Anything after `--` is a substring filter on the test-file name. Exits
## non-zero on failure so CI fails the build.

const TEST_SCRIPTS: Array[String] = [
	"res://tests/test_rng.gd",
	"res://tests/test_damage.gd",
	"res://tests/test_items.gd",
	"res://tests/test_boons.gd",
	"res://tests/test_run_state.gd",
	"res://tests/test_progression.gd",
	"res://tests/test_inscriptions.gd",
	"res://tests/test_reliquary.gd",
	"res://tests/test_spells.gd",
	"res://tests/test_projectile.gd",
	"res://tests/test_data.gd",
]


var _ran := false


## The suite runs on the first frame rather than in _initialize.
##
## Anything scene-level needs a live tree: inside _initialize the root window is
## not yet inside the tree, so add_child gives you a node whose global_transform
## is silently the identity — tests/test_projectile.gd looked like a bolt that
## refused to move. By the first idle frame the tree is real. Pure core/ tests do
## not care either way.
func _process(_delta: float) -> bool:
	if _ran:
		return true
	_ran = true
	_run()
	return true


func _run() -> void:
	var filter := ""
	var user_args := OS.get_cmdline_user_args()
	if user_args.size() > 0:
		filter = user_args[0]

	var total_assertions := 0
	var total_tests := 0
	var all_failures: Array[String] = []
	var files_run := 0

	print("")
	print("Ashfall test suite")
	print("==================")

	for path in TEST_SCRIPTS:
		if filter != "" and not path.contains(filter):
			continue
		files_run += 1

		var script: Script = load(path)
		if script == null:
			all_failures.append("%s\n      could not be loaded" % path)
			print("  ??  %s (failed to load)" % path)
			continue

		var suite: TestCase = script.new()
		var short_name: String = path.get_file()

		var methods: Array[String] = []
		for m in suite.get_method_list():
			var n: String = m["name"]
			if n.begins_with("test_") and not methods.has(n):
				methods.append(n)
		methods.sort()

		var before := suite.failures().size()
		for m in methods:
			suite.begin("%s::%s" % [short_name, m])
			suite.call(m)
			total_tests += 1

		var failed := suite.failures().size() - before
		total_assertions += suite.assertion_count()
		all_failures.append_array(suite.failures())

		var mark := "ok  " if failed == 0 else "FAIL"
		print("  %s %-24s %2d tests, %4d assertions" % [mark, short_name, methods.size(), suite.assertion_count()])

	print("")
	if all_failures.is_empty():
		print("PASSED — %d tests, %d assertions across %d files" % [total_tests, total_assertions, files_run])
		print("")
		quit(0)
		return

	print("FAILURES (%d):" % all_failures.size())
	for f in all_failures:
		print("  - %s" % f)
	print("")
	print("FAILED — %d of %d tests had failures" % [all_failures.size(), total_tests])
	print("")
	quit(1)
