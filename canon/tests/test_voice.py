"""The firm's voice, checked where a script can reach it.

WHAT THIS CANNOT CHECK, said rather than implied: whether a draft sounds like
the firm. No test reaches that. These hold three narrower things: every tell
rests on a source the firm or their profile gave, no tell fires on the firm's
own writing, and the record keeps out what it promised to keep out.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import voice  # noqa: E402

VOICE = (CANON / "VOICE.md").read_text(encoding="utf-8")
FLAT = " ".join(VOICE.split())


def _section(title: str) -> str:
    start = VOICE.index(f"## {title}\n")
    end = VOICE.find("\n## ", start + 1)
    return VOICE[start:end if end != -1 else len(VOICE)]


def _their_sentences() -> list[str]:
    return [line[2:].strip() for line in _section("Their sentences").splitlines()
            if line.startswith("> ")]


def test_every_tell_rests_on_a_source_quoted_in_the_record():
    """A tell with no source is a session's taste. The source has to be the
    words in VOICE.md, character for character, so it can be read in context."""
    assert voice.TELLS, "no tells; every check below would pass vacuously"
    for tell in voice.TELLS:
        assert tell.source.strip(), f"{tell.label} has no source"
        assert " ".join(tell.source.split()) in FLAT, \
            f"{tell.label}'s source is not quoted in VOICE.md: {tell.source!r}"


def test_no_tell_fires_on_the_firms_own_writing():
    """The guard on the guard. A tell that flags a sentence the firm wrote is
    checking the wrong thing: "frankly" and "upfront" both appear in their own
    writing, and both would have been easy to ban."""
    sentences = _their_sentences()
    assert len(sentences) >= 20, \
        f"only {len(sentences)} of their sentences found; the section moved or emptied"
    for sentence in sentences:
        assert voice.check(sentence) == [], f"a tell fired on the firm: {sentence!r}"


@pytest.mark.parametrize("label, sample", [
    ("British spelling", "The behaviour of the colour grey was analysed."),
    ("saying you're being honest", "Honestly, this is the right call."),
    ("a sentence about how open we are", "We want to be upfront about the fee."),
    ("padding before the point", "I wanted to take a moment to raise this."),
    ("ceremonial courtesy", "Please don't hesitate to reach out."),
])
def test_every_tell_fires_on_what_it_names(label, sample):
    """Check the checker: each tell is watched catching the thing it exists for,
    so a pattern that quietly stopped matching goes red here."""
    assert label in {t.label for t in voice.TELLS}, f"no tell called {label!r}"
    assert label in {f.label for f in voice.check(sample)}, \
        f"{label!r} did not fire on {sample!r}"


@pytest.mark.parametrize("clean", [
    "Realistically the programmer analyses the colors.",
    "I am sure there are holes in that story, frankly.",
    "Doing the work upfront is simpler.",
    "Testers should use their best judgment.",
    "Organize the file and recognize the gap.",
])
def test_american_and_ordinary_words_pass(clean):
    """Whole words only, and American spellings stay clean."""
    assert voice.check(clean) == [], clean


def _run(stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CANON / "voice.py")], input=stdin,
                          capture_output=True, text=True, cwd=CANON)


def test_nothing_read_is_not_a_clean_result():
    """Unknown is a third answer. An empty draft must not come back clean."""
    got = _run("")
    assert got.returncode == 2
    assert "not a clean result" in got.stdout


def test_the_result_carries_its_denominator():
    got = _run("Please try again, this should be fixed.\n")
    assert got.returncode == 0, got.stdout
    assert "0 tell(s) in 7 words" in got.stdout
    assert "Clean on these tells only" in got.stdout
    got = _run("Honestly, it's fixed.\n")
    assert got.returncode == 1
    assert "<stdin>:1: saying you're being honest" in got.stdout


def test_the_record_keeps_out_what_it_promised_to():
    """VOICE.md says the employer's documents stay with the employer. The
    employer's name is the cheapest proof that promise was kept."""
    lowered = VOICE.lower()
    for name in ("keybank", "keycorp", "internal use"):
        assert name not in lowered, f"VOICE.md carries {name!r}"


def test_the_profile_is_labeled_as_another_ais_reading():
    """Behaviour 22: a summary is not the firm's words, and must not inherit
    their attribution."""
    profile = " ".join(_section("Copilot's profile, as handed over").split())
    assert "another AI's reading, not the firm's words" in profile
    assert "the sentence wins" in profile


def test_a_sessions_own_reading_is_labeled_as_one():
    talking = " ".join(_section("Talking to the firm").split())
    assert "This session's reading, 14 October 2026, not the firm's words" in talking


def test_the_standing_role_carries_the_request_in_their_words():
    """Bassy is what the session-start hook prints, so this is the part that
    holds without anybody remembering to load a skill."""
    bassy = " ".join((CANON / "skills" / "bassy" / "SKILL.md")
                     .read_text(encoding="utf-8").split())
    assert ("I want you to talk to me like me and I want things drafted for me "
            "to sound like me") in bassy
    assert "${CLAUDE_PLUGIN_ROOT}/VOICE.md" in bassy
    assert "/canon:voice" in bassy


def test_bassy_holds_the_firms_rules_loosely_outside_the_practice():
    """The firm, 14 October 2026, on projects that are not the practice's own.
    Their words are quoted; the session's reading of them is labeled as one,
    so the next session can tell which part the firm actually said."""
    bassy = " ".join((CANON / "skills" / "bassy" / "SKILL.md")
                     .read_text(encoding="utf-8").split())
    assert ("Also Bassy should understand that if it is not a SATC project we "
            "don't as critically apply our firm's rules") in bassy
    assert "This session's reading of that, 14 October 2026, not the firm's words" in bassy
    assert "The firm's voice is not one of these rules" in bassy
