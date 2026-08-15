class_name TestCase
extends RefCounted

## Minimal assertion base class.
##
## Deliberately dependency-free — no GUT, no addons, nothing to install. A test
## file extends this and defines methods named `test_*`; tests/run_tests.gd
## finds and runs them. That keeps the whole verification story to one command:
##
##   godot --headless --script res://tests/run_tests.gd

var _failures: Array[String] = []
var _assertions: int = 0
var _current: String = "<none>"


func failures() -> Array[String]:
	return _failures


func assertion_count() -> int:
	return _assertions


func begin(method_name: String) -> void:
	_current = method_name


func fail(msg: String) -> void:
	_failures.append("%s\n      %s" % [_current, msg])


func assert_true(cond: bool, msg: String = "") -> void:
	_assertions += 1
	if not cond:
		fail("expected true. %s" % msg)


func assert_false(cond: bool, msg: String = "") -> void:
	_assertions += 1
	if cond:
		fail("expected false. %s" % msg)


func assert_eq(actual: Variant, expected: Variant, msg: String = "") -> void:
	_assertions += 1
	if actual != expected:
		fail("expected %s, got %s. %s" % [expected, actual, msg])


func assert_ne(actual: Variant, unexpected: Variant, msg: String = "") -> void:
	_assertions += 1
	if actual == unexpected:
		fail("expected anything but %s. %s" % [unexpected, msg])


func assert_almost_eq(actual: float, expected: float, eps: float = 0.0001, msg: String = "") -> void:
	_assertions += 1
	if absf(actual - expected) > eps:
		fail("expected %f (+/- %f), got %f. %s" % [expected, eps, actual, msg])


func assert_gt(actual: float, floor_v: float, msg: String = "") -> void:
	_assertions += 1
	if not (actual > floor_v):
		fail("expected > %f, got %f. %s" % [floor_v, actual, msg])


func assert_lt(actual: float, ceil_v: float, msg: String = "") -> void:
	_assertions += 1
	if not (actual < ceil_v):
		fail("expected < %f, got %f. %s" % [ceil_v, actual, msg])


func assert_between(actual: float, lo: float, hi: float, msg: String = "") -> void:
	_assertions += 1
	if actual < lo or actual > hi:
		fail("expected within [%f, %f], got %f. %s" % [lo, hi, actual, msg])


func assert_has(collection: Variant, needle: Variant, msg: String = "") -> void:
	_assertions += 1
	if not collection.has(needle):
		fail("expected %s to contain %s. %s" % [collection, needle, msg])


func assert_not_null(v: Variant, msg: String = "") -> void:
	_assertions += 1
	if v == null:
		fail("expected non-null. %s" % msg)
