"""The scratch-directory choice, and the two ways it has already gone wrong.

`conftest.py` carries the incidents. These are the guards: each one fails if the
reasoning in that file is removed, which is the only thing that makes the
reasoning worth writing down.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import conftest as C  # noqa: E402


@pytest.fixture
def short_tmp():
    """A real, writable directory with a SHORT path.

    `tmp_path` cannot be used where length is part of what is under test: its
    own path is long enough to fail the budget, so a test handing it to
    `choose_root` would be asserting the refusal it is trying to disprove.
    """
    root = Path(tempfile.gettempdir()) / "cpt-t"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    assert len(str(root)) + len(C.DIRNAME) + 1 <= C.MAX_ROOT_LEN
    yield root
    shutil.rmtree(root, ignore_errors=True)


def test_a_root_the_operator_chose_is_left_alone(short_tmp):
    """Somebody who sets the variable has a reason, and it outranks ours.

    The directory must be a SHORT one that would otherwise be accepted. Written
    with `tmp_path`, this test survived deleting the check it exists for: the
    long path failed the length budget instead, and `None` came back for a
    reason that had nothing to do with the operator.
    """
    chosen = str(short_tmp / "theirs")
    assert C.choose_root({}, short_tmp, CANON) is not None,         "the directory must be acceptable, or this proves nothing"
    assert C.choose_root({C.VAR: chosen}, short_tmp, CANON) is None


def test_an_empty_variable_is_not_a_choice(short_tmp):
    """An exported-but-blank variable is the shell's leftovers, not an
    instruction -- and treating it as one would leave the broken default in
    force, which is the whole failure this exists to prevent."""
    root = C.choose_root({C.VAR: ""}, short_tmp, CANON)
    assert root is not None


def test_a_root_inside_the_record_is_refused():
    """4 September 2026: a scratch root inside `canon/` made the no-client-data
    check read the fixtures the fix had just written, and report the record as
    carrying a taxpayer identifier, an employer identifier and a private key.
    It carried none of them."""
    inside = CANON / "does-not-need-to-exist"
    assert C.choose_root({}, inside, CANON) is None


def test_the_tree_itself_counts_as_inside_it():
    """The boundary case the `==` in `is_inside` exists for."""
    assert C.is_inside(CANON, CANON)


def test_a_sibling_of_the_record_is_not_inside_it(short_tmp):
    """The refusal has to be `inside`, not `shares a prefix` -- a directory
    named `canon-pt` next to one named `canon` starts with its whole name."""
    assert not C.is_inside(short_tmp / "canon-pt", short_tmp / "canon")


def test_a_root_too_long_for_windows_is_refused():
    """Windows refuses paths past ~260 characters and says so nowhere useful:
    the observed symptom was `git init` exiting 128 under a deep pytest path,
    naming neither length nor git."""
    long_temp = "C:\\" + "\\".join(["a-fairly-long-directory-name"] * 5)
    assert len(long_temp) > C.MAX_ROOT_LEN
    assert C.choose_root({}, long_temp, CANON) is None


def test_an_ordinary_temp_directory_is_accepted(short_tmp):
    """The happy path, which the three refusals above would otherwise let rot:
    a plain temp directory yields a root, under our own name."""
    root = C.choose_root({}, short_tmp, CANON)
    assert root is not None
    assert root.name == C.DIRNAME
    assert root.parent == short_tmp


def test_install_leaves_the_variable_pointing_at_the_root(short_tmp):
    """The decision is worth nothing unless it reaches the environment pytest
    actually reads."""
    env = {}
    root = C.install(env=env, tempdir=short_tmp, tree=CANON)
    assert root is not None
    assert env[C.VAR] == str(root)
    assert root.is_dir()


def test_a_root_that_cannot_be_written_leaves_the_default_standing(short_tmp):
    """The locked directory is the whole reason this file exists, so this file
    must not itself fall over when it meets one. A file where the root should
    go makes `mkdir` raise, which stands in for the ACL that cannot be
    reproduced in a test."""
    (short_tmp / C.DIRNAME).write_text("not a directory", encoding="utf-8")
    env = {}
    assert C.install(env=env, tempdir=short_tmp, tree=CANON) is None
    assert C.VAR not in env


def test_the_root_in_force_is_outside_the_record():
    """End to end, in this very run: whatever pytest is using for `tmp_path`,
    it is not inside canon. `IN_FORCE` is None when an operator set the
    variable themselves -- then the guard is theirs to keep, not ours."""
    if C.IN_FORCE is None:
        return
    assert not C.is_inside(C.IN_FORCE, CANON)
    assert len(str(C.IN_FORCE)) <= C.MAX_ROOT_LEN


def test_the_scratch_root_is_not_written_into_this_tree(tmp_path):
    """`tmp_path` is the fixture every erroring test asked for. Where it lands
    is the observable behaviour, and it must land outside the record."""
    assert not C.is_inside(tmp_path, CANON)
