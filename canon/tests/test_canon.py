"""The guards, and proof each one can fail.

A CHECK THAT HAS NEVER SEEN A REAL HIT is a check tested on the case it cannot
fail. Every test here plants the thing the guard exists to catch and asserts the
guard catches it -- and then asserts the clean case stays clean, because a
scanner that flags everything is as useless as one that flags nothing.

THE FIXTURES ARE BUILT THE WAY THE WRITER WRITES. A fixture assembled by the
same code under test proves only that the code agrees with itself; that failure
survived mutation twice in this operation's other repository in a single week.
Here the planted records are written as literal text, the way a person or an
editor would write them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import check_record  # noqa: E402


# ── the record is a record ────────────────────────────────────────────────

def test_the_plugin_manifest_is_valid_and_names_canon():
    got = json.loads((CANON / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert got["name"] == "canon"
    assert got["description"].strip()


def test_every_skill_is_one_the_harness_can_load():
    """Written over the whole directory rather than over `bassy` alone. It was
    `bassy` alone, and three skills were added afterwards -- any one of which
    could have shipped with no frontmatter and loaded nowhere, silently, with
    a green test beside it. A guard aimed at one instance of a thing is a guard
    that stops covering it the moment there are two.
    """
    skills = sorted(p for p in (CANON / "skills").iterdir() if p.is_dir())
    assert {p.name for p in skills} == {"bassy", "canon-adopt", "canon-mine",
                                        "how-we-work"}
    for skill in skills:
        path = skill / "SKILL.md"
        assert path.is_file(), f"{skill.name} has no SKILL.md"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), \
            f"{skill.name} has no frontmatter, so nothing will load it"
        front = text.split("---", 2)[1]
        assert f"name: {skill.name}" in front, \
            f"{skill.name}'s frontmatter name does not match its directory"
        assert "description:" in front, f"{skill.name} has no description"


def test_every_tenet_carries_evidence():
    """A rule with nothing under it does not belong in this file. The count is
    stated so a bare rule is visible without reading the whole entry."""
    text = (CANON / "TENETS.md").read_text(encoding="utf-8")
    rules = [l for l in text.splitlines() if l.startswith("## S")]
    assert rules, "no tenets at all"
    for rule in rules:
        head = text.split(rule, 1)[1].split("\n## ", 1)[0]
        assert "**Evidence:" in head, f"{rule[:40]} states no evidence count"
        assert "###" in head, f"{rule[:40]} has no evidence entries under it"


def test_every_conviction_carries_the_firms_words_and_a_state():
    text = (CANON / "CONVICTIONS.md").read_text(encoding="utf-8")
    entries = [l for l in text.splitlines() if l.startswith("## C")]
    assert entries, "no convictions at all"
    for entry in entries:
        head = text.split(entry, 1)[1].split("\n## ", 1)[0]
        assert "**State:**" in head, f"{entry[:40]} has no held/retired state"
        assert "> *" in head, f"{entry[:40]} does not quote the firm"
        assert "**Why:**" in head, f"{entry[:40]} records no reason"


# ── canon lifts out whole ─────────────────────────────────────────────────

def test_nothing_in_canon_reaches_outside_canon():
    """The constraint that keeps this movable. `canon` lives inside the SATC
    monorepo today and must be extractable whole -- installing it into an
    unrelated project can never require granting that project access to the
    repository holding the client vault.
    """
    offenders = []
    reach = "parents[" + "2]"          # split so this line is not its own hit
    for path in CANON.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        # THE CHECK CANNOT SCAN ITSELF. Its source necessarily contains the
        # pattern it looks for, which is the same reason `check_record` skips
        # `tests/` -- and the same reason that skip is a single named directory.
        if path.name == Path(__file__).name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and ".." in stripped:
                offenders.append(f"{path.relative_to(CANON)}: {stripped}")
            if reach in stripped:
                offenders.append(f"{path.relative_to(CANON)}: {stripped}")
    assert not offenders, "canon reaches outside itself:\n  " + "\n  ".join(offenders)


# ── the guard can actually fail ───────────────────────────────────────────

PLANTED = [
    ("a taxpayer identifier", "The client's number is 123-45-6789 for the return.\n"),
    ("an employer identifier", "The entity files under 12-3456789 this year.\n"),
    ("a telephone number", "Reach the client on (216) 555-0142 before Friday.\n"),
    ("a payment credential", "export SATC_SQUARE_TOKEN=EAAAlkQ9xZmPq7RtVw3Nc\n"),
    ("a private key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n"),
    ("an access token assignment", 'token: "abcdefghijklmnopqrstuvwx"\n'),
    ("an email address that is not the firm's own", "Write to daniel.reyes@example.com about it.\n"),
]


@pytest.mark.parametrize("what,text", PLANTED, ids=[p[0] for p in PLANTED])
def test_the_guard_catches_what_it_exists_for(tmp_path, what, text):
    """Planted as literal text, the way a person would write it -- not
    generated by the thing being tested."""
    (tmp_path / "CONVICTIONS.md").write_text(
        "# Convictions\n\n## C9 · A conviction\n\n" + text, encoding="utf-8")
    bad, files, size = check_record.scan(tmp_path)
    assert files == 1 and size > 0, "it examined nothing and would have passed"
    assert any(what in line for line in bad), f"{what} got through: {bad}"


def test_the_firms_own_address_is_not_a_finding(tmp_path):
    """A scanner that flags the firm's own billing address flags every real
    file, and a check that fires on everything is one nobody reads."""
    (tmp_path / "README.md").write_text(
        "Invoices go to billing@satcllp.com.\n", encoding="utf-8")
    bad, files, _ = check_record.scan(tmp_path)
    assert files == 1
    assert bad == []


def test_a_clean_record_reports_what_it_examined(tmp_path):
    """S2. A green result from a check that examined nothing is worse than a
    red one, so the denominator is part of the answer."""
    (tmp_path / "TENETS.md").write_text("# Tenets\n\nNothing yet.\n", encoding="utf-8")
    bad, files, size = check_record.scan(tmp_path)
    assert bad == [] and files == 1 and size > 0


def test_tests_is_the_only_thing_the_scanner_skips():
    """The hole is named, so it cannot be widened quietly. `tests/` is excluded
    because it plants fake secrets on purpose; a second exclusion would be a
    place to hide a real one."""
    assert check_record.EXCLUDED == ("tests",)


def test_the_real_record_is_clean():
    bad, files, size = check_record.scan(CANON)
    assert files >= 5, f"it only examined {files} files; something is excluded"
    assert size > 10_000, "it examined almost nothing"
    assert bad == [], f"canon carries something it must not:\n{bad}"
