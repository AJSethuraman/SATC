"""The README is a claim about this package, so it is checked against it.

A document that describes software drifts the moment the software moves, and a
README that has been wrong once is still the first thing a new reader trusts.
These tests do not review the prose -- they check the falsifiable parts: that
every path it points at exists, every command it tells you to run is real, and
the engine module list it prints is the engine's actual module list.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from credit_suite import conformance
from credit_suite.parity import repo_root

PACKAGE = Path(__file__).resolve().parents[1]
README = PACKAGE / "README.md"


@pytest.fixture(scope="module")
def text():
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def flowed(text):
    """The README with line wrapping removed.

    Prose wraps, so a phrase can be split across a newline while reading
    perfectly. Searching the raw text for it fails on a document that is right,
    which is the kind of false positive that gets a check switched off.
    """
    return " ".join(text.split())


def test_the_readme_exists_and_says_what_the_package_is(text, flowed):
    assert text.startswith("# credit-suite")
    assert "provider adapter plus a config seed" in flowed


def test_every_linked_path_exists(text):
    """Markdown links, relative to the README."""
    missing = []
    for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (README.parent / target).resolve()
        if not candidate.exists():
            missing.append(target)
    assert not missing, "README links to paths that do not exist: %s" % missing


def test_every_backticked_repo_path_exists(text):
    """Paths named in backticks, e.g. `tests/goldens/`."""
    missing = []
    for token in re.findall(r"`([^`]+)`", text):
        token = token.strip()
        if not re.match(r"^[\w./-]+$", token):
            continue
        leaf = token.rsplit("/", 1)[-1]
        if not (token.endswith("/") or "." in leaf):
            continue
        if leaf.startswith("."):
            continue                      # a bare extension like `.xlsm`
        if token.startswith(("http", "0.", "1.")) or token.endswith("()"):
            continue
        for base in (PACKAGE, PACKAGE / "src" / "credit_suite", repo_root()):
            if (base / token).exists():
                break
        else:
            missing.append(token)
    assert not missing, "README names paths that do not exist: %s" % missing


def test_every_command_it_tells_you_to_run_is_real(text):
    """`python tools/x.py` must name a file, or the instruction is a dead end."""
    missing = []
    for script in re.findall(r"python (tools/[\w./-]+\.py)", text):
        if not (PACKAGE / script).is_file():
            missing.append(script)
    assert not missing, "README documents scripts that do not exist: %s" % missing
    assert "python -m pytest" in text, "the README must say how to run the suite"


def test_the_engine_module_list_matches_the_engine(text):
    """The tree block lists engine modules by name. If one is added or removed
    and the README is not updated, this is the thing that notices."""
    engine = PACKAGE / "src" / "credit_suite" / "engine"
    real = {p.name for p in engine.glob("*.py")} - {"__init__.py"}
    listed = set(re.findall(r"^    (\w+\.py)", text, re.M))
    assert listed, "no engine modules listed in the README at all"
    assert real - listed == set(), \
        "engine modules missing from the README: %s" % sorted(real - listed)
    assert listed - real == set(), \
        "README lists engine modules that do not exist: %s" % sorted(listed - real)


def test_the_seam_is_documented_with_its_real_signature(text):
    from credit_suite.engine.provider import NormalizedRow

    assert "fetch_series(spec, secret=None) -> list[NormalizedRow]" in text
    documented = set(re.findall(r"NormalizedRow = \{([^}]+)\}", text)[0].split(", "))
    actual = set(NormalizedRow.__dataclass_fields__)
    assert documented == actual, \
        "README's NormalizedRow fields %s do not match %s" % (documented, actual)


def test_the_add_a_source_steps_name_files_a_real_source_has(text):
    """The instructions must describe the shape FDIC actually has, or the first
    person to follow them builds something that does not fit."""
    fdic = PACKAGE / "src" / "credit_suite" / "sources" / "fdic"
    for step in ("spec.py", "fields.py", "adapter.py", "layout.py", "runner.py"):
        assert "sources/<name>/%s" % step in text, "%s not in the steps" % step
        assert (fdic / step).is_file(), "FDIC has no %s to copy the shape from" % step
    assert "bundles.py" in text
    assert (PACKAGE / "src" / "credit_suite" / "bundles.py").is_file()


def test_it_names_the_monitors_that_have_not_migrated(text):
    """The README must not read as though the whole suite is done."""
    for folder in conformance.UNMIGRATED_FOLDERS:
        stem = folder.split("-")[0]
        assert stem in text.lower(), "%s not mentioned as outstanding" % folder
    assert "M2" in text


def test_it_does_not_promise_a_recapture_shortcut(text):
    """Recapturing a golden to make parity pass would destroy the whole point,
    so the README has to say so."""
    assert "Do not recapture a golden" in text


def test_the_backlog_section_it_points_at_exists():
    backlog = (repo_root() / "BACKLOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## 6 . credit-suite", backlog, re.M), \
        "BACKLOG.md has no section 6 for the roadmap the README links to"
