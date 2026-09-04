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
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import check_record  # noqa: E402


# ── the record is a record ────────────────────────────────────────────────

def test_every_skill_is_one_the_harness_can_load():
    """Written over the whole directory rather than over `bassy` alone. It was
    `bassy` alone, and three skills were added afterwards -- any one of which
    could have shipped with no frontmatter and loaded nowhere, silently, with
    a green test beside it. A guard aimed at one instance of a thing is a guard
    that stops covering it the moment there are two.
    """
    skills = sorted(p for p in (CANON / "skills").iterdir() if p.is_dir())
    assert {p.name for p in skills} == {"bassy", "canon-adopt", "canon-mine", "docket", "how-we-work"}
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


# ── the manifest, checked by the thing that decides ───────────────────────

def _claude_cli() -> str | None:
    return shutil.which("claude")


def test_the_manifest_says_valid_by_our_own_reading():
    """Always runs, even where the CLI is absent, so this file never becomes a
    check that examined nothing (S2).

    The specific shape below is not decoration: `author` was a plain string and
    the real installer rejected it -- `expected object, received string` -- on
    the first attempt to install canon anywhere. The test beside it asserted
    the manifest was "valid" and had only ever checked that the JSON parsed.
    """
    got = json.loads((CANON / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert got["name"] == "canon"
    assert got["description"].strip()
    assert isinstance(got.get("author"), dict), \
        "author is an object in the manifest schema, not a string"
    assert got["author"].get("name"), "an author object with no name"
    assert re.fullmatch(r"\d+\.\d+\.\d+", got.get("version", "")), \
        "version must be semver for a marketplace entry"


def test_the_installer_itself_accepts_the_manifest():
    """The real validator, not our reading of it. Skipped where the CLI is not
    installed -- and the skip says so out loud rather than passing quietly."""
    cli = _claude_cli()
    if not cli:
        pytest.skip("the `claude` CLI is not on PATH, so the REAL validator did "
                    "not run here; only our own reading of the schema did")
    got = subprocess.run([cli, "plugin", "validate", str(CANON)],
                         capture_output=True, text=True, timeout=120)
    assert got.returncode == 0, got.stdout + got.stderr
    assert "Validation passed" in got.stdout


def test_the_marketplace_lists_canon_and_the_installer_accepts_it():
    """The marketplace lives one level up, outside `canon/`, which is the one
    place that is allowed to know canon exists: it is what makes the plugin
    installable from any other repository. canon still reaches nothing above
    itself.
    """
    market = CANON.parent / ".claude-plugin" / "marketplace.json"
    if not market.is_file():
        # canon has been lifted out, which is what it is built for. The
        # marketplace belongs to whatever repository is now offering it, and
        # this copy is in no position to check one it does not own.
        pytest.skip("no marketplace above this copy — canon has been lifted "
                    "out, and the marketplace belongs to its new home")
    got = json.loads(market.read_text(encoding="utf-8"))
    entry = next(p for p in got["plugins"] if p["name"] == "canon")
    assert entry["source"] == "./canon"
    assert isinstance(got["owner"], dict)

    cli = _claude_cli()
    if not cli:
        pytest.skip("the `claude` CLI is not on PATH, so the REAL validator did "
                    "not run over the marketplace")
    ran = subprocess.run([cli, "plugin", "validate", str(CANON.parent)],
                         capture_output=True, text=True, timeout=120)
    assert ran.returncode == 0, ran.stdout + ran.stderr


# ── what is installed is what is written ─────────────────────────────────────

def test_the_marketplace_and_the_manifest_agree_on_the_version():
    """THE BUG THIS CLOSES, which happened twice in one day.

    C11 was recorded and merged with no bump at all. A later commit bumped
    `plugin.json` to 1.5.0 for three behaviours and left the marketplace entry
    at 1.4.0. The plugin cache is keyed by the version the MARKETPLACE declares,
    so there was nothing new to fetch either time: every installed session kept
    reading a record that stopped at C10 while the repository had eleven.

    Nothing failed. Bassy simply could not challenge from a conviction the firm
    had given, and no test here could tell — the only version check asserted the
    string matched semver.
    """
    market = CANON.parent / ".claude-plugin" / "marketplace.json"
    if not market.is_file():
        pytest.skip("no marketplace above this copy — canon has been lifted out")
    entry = next(p for p in json.loads(market.read_text(encoding="utf-8"))["plugins"]
                 if p["name"] == "canon")
    manifest = json.loads(
        (CANON / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert entry["version"] == manifest["version"], (
        f"the marketplace offers canon {entry['version']} while the plugin is "
        f"{manifest['version']}; the cache is keyed by the marketplace's number, "
        f"so installed sessions would never see the difference"
    )


def test_the_version_says_what_the_record_actually_contains():
    """A digest of the record, written beside the version it belongs to.

    WHAT THIS CANNOT DO, said rather than implied: it cannot force anyone to
    bump a version. No test can. What it does is make the omission loud —
    change `CONVICTIONS.md` and this goes red until the digest is rewritten,
    and the line you rewrite sits directly beside the version number, so
    "should this be 1.6.0?" appears in the diff a reviewer is reading instead
    of being a thing nobody thought about.
    """
    import release
    stated = json.loads(release.RELEASED.read_text(encoding="utf-8"))
    assert stated["version"] == release.version(), (
        f"RELEASED.json describes {stated['version']} and the manifest says "
        f"{release.version()}"
    )
    assert stated["record_sha256"] == release.digest(), (
        "the record has changed since this version was released. Run "
        "`python canon/release.py`, then decide whether the version should move "
        "— an installed session reads whatever the marketplace's number fetches"
    )


def test_a_count_stated_in_a_manifest_is_a_count_somebody_made():
    """Both manifests describe canon in prose, and the prose carries a number.
    The marketplace said "fifteen standing behaviours" while the file held
    eighteen — a claim about the product, drifting where nothing compared it."""
    words = {"fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
             "nineteen": 19, "twenty": 20}
    real = len(re.findall(r"^## \d+ · ",
                          (CANON / "skills" / "how-we-work" / "SKILL.md")
                          .read_text(encoding="utf-8"), re.M))
    assert real, "no behaviours found; this check would pass vacuously"

    texts = {"plugin.json": json.loads(
        (CANON / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["description"]}
    market = CANON.parent / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        texts["marketplace.json"] = next(
            p for p in json.loads(market.read_text(encoding="utf-8"))["plugins"]
            if p["name"] == "canon")["description"]

    for where, text in texts.items():
        for word, n in words.items():
            if re.search(rf"\b{word} standing behaviours\b", text, re.I):
                assert n == real, (
                    f"{where} claims {word} standing behaviours; there are {real}"
                )
