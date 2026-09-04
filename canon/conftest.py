"""Give pytest a scratch directory it can actually use.

Both of the things that make the default wrong are recorded here, because in
each case the symptom looks nothing like the cause and a session that hits one
of them reads it as broken code.

**The default root can be locked against its own owner.** On the machine canon
was built on, ``<temp>/pytest-of-<user>`` was left with a DACL that denies
everything -- ``icacls`` cannot read it, and granting yourself access is
refused. Every test that asks for ``tmp_path`` then errors at *setup*, so the
run reports thirty-four errors in tests that were never executed. Repairing it
needs an elevated shell, which is not something a test suite may assume.

**Moving the scratch directory into the repository is worse.** Tried on
4 September 2026: canon's own no-client-data check walks this tree, so it read
the fixtures the fix had just written and reported that the record carried a
taxpayer identifier, an employer identifier and a private key. It carried none
of them. A scratch root inside the tree makes every tree-walking guard read its
own leavings, so `choose_root` refuses one and says so.

**Short matters.** Windows still refuses paths past about 260 characters, and
the failure surfaces as a subprocess exit code with no mention of length: a
``git init`` under a long pytest path returns 128 and says nothing useful. The
root therefore has a length budget, asserted by a test rather than hoped for.

Nothing here overrides an operator who set ``PYTEST_DEBUG_TEMPROOT`` themselves.
"""

import os
import tempfile
from pathlib import Path

VAR = "PYTEST_DEBUG_TEMPROOT"

#: Kept short on purpose -- every character here is one pytest cannot spend on
#: the test name and the fixture tree below it.
DIRNAME = "canon-pt"

#: The most any root may occupy, leaving the rest of a 260-character Windows
#: path for `pytest-of-<user>/pytest-<n>/<test name>/` and whatever the test
#: writes underneath it. A generous root today is a mystified `git` tomorrow.
MAX_ROOT_LEN = 100


def is_inside(path: Path, parent: Path) -> bool:
    """Is `path` at or below `parent`? Both are resolved first, so a symlink or
    a `.` in either does not decide the answer."""
    path, parent = Path(path).resolve(), Path(parent).resolve()
    return path == parent or parent in path.parents


def choose_root(env, tempdir, tree: Path):
    """The scratch root to impose, or `None` to leave pytest's own choice alone.

    Pure: it decides, it does not create. `tree` is the directory that must not
    contain the result -- canon itself, here, but the argument is what makes
    this testable without moving the real one.
    """
    if env.get(VAR):
        return None                       # an operator chose one; not ours to override
    root = Path(tempdir) / DIRNAME
    if is_inside(root, tree):
        return None                       # would make every tree walk read its own fixtures
    if len(str(root)) > MAX_ROOT_LEN:
        return None                       # no better than the default, and harder to explain
    return root


def install(env=None, tempdir=None, tree=None) -> Path | None:
    """Choose a root, prove it is writable, and put it in the environment.

    Returns the root now in force, or `None` if the default was left standing.
    A root that cannot be written to is not an error worth failing the run over
    -- it is exactly the condition this exists to survive -- so it falls back to
    pytest's own behaviour and lets the resulting errors speak for themselves.
    """
    env = os.environ if env is None else env
    tempdir = tempfile.gettempdir() if tempdir is None else tempdir
    tree = Path(__file__).resolve().parent if tree is None else tree

    root = choose_root(env, tempdir, tree)
    if root is None:
        return None
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return None
    env[VAR] = str(root)
    return root


IN_FORCE = install()
