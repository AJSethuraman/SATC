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
    ("British spelling", "Behaviour first. Organise the file."),
    ("British spelling", "It was behaviourally odd; the organiser's enrolment lapsed."),
    ("saying you're being honest", "This is, to be\nhonest, the right call."),
    ("a sentence about how open we are", "We\u2019re upfront about the fee."),
    ("ceremonial courtesy", "Please don\u2019t hesitate\nto call."),
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
    "Pass-through entities are transparent for tax purposes.",
    "Fees are upfront and the cancellation is free.",
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


#: SHA-256 of the employer's names, lowercased. Hashed so that the test which
#: keeps the name out of this plugin does not itself carry it into every
#: repository canon is installed in.
_KEPT_OUT = {
    "d9efbc5cf78207796c6cab21e53fbc13baa12924294fe27cd28c5cfa5c9ad3ca",
    "da4fd7e81f2723c5ece785a094142ec0ba2426e00b8b9685097d0a13a419612e",
}


def test_the_record_keeps_out_what_it_promised_to():
    """VOICE.md says the employer's documents stay with the employer. The
    employer's name is the cheapest proof that promise was kept."""
    import hashlib
    words = set(re.findall(r"[a-z]+", VOICE.lower()))
    leaked = [w for w in words if hashlib.sha256(w.encode()).hexdigest() in _KEPT_OUT]
    assert not leaked, "VOICE.md carries the employer's name"
    assert "internal use" not in VOICE.lower()


def test_the_profile_is_labeled_as_another_ais_reading():
    """Behaviour 22: a summary is not the firm's words, and must not inherit
    their attribution."""
    profile = " ".join(_section("Copilot's profile, as handed over").split())
    assert "another AI's reading, not the firm's words" in profile
    assert "the sentence wins" in profile


def test_a_sessions_own_reading_is_labeled_as_one():
    talking = " ".join(_section("Talking to the firm").split())
    assert "A session's reading, 14 October 2026, not the firm's words" in talking


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
    assert ("A session's reading of that, written on 14 October 2026 and confirmed "
            'by the firm the same day with one word: "Right"') in bassy
    assert "The firm's voice is not one of these rules" in bassy


# ── canon holds itself to the spelling the firm asked for ────────────────

#: What sessions read, and what the firm reads in a plugin listing.
PROSE = (["CONVICTIONS.md", "TENETS.md", "README.md", "VOICE.md"]
         + sorted(str(p.relative_to(CANON)) for p in CANON.glob("skills/*/SKILL.md")))

# QUOTED TEXT IS LEFT AS IT WAS WRITTEN. A blockquote, anything in double
# quotes and inline code are somebody's words or a literal, and respelling them
# is paraphrase. "Fires on" lines are selectors: they carry both spellings on
# purpose, so a decision written either way still brings the entry into play.
_PROTECTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`')


def _prose_hits(text: str) -> list[str]:
    hits = []
    for line in text.splitlines():
        if line.lstrip().startswith(">") or line.startswith("**Fires on:**"):
            continue
        hits += [f.text for f in voice.check(_PROTECTED.sub("", line))
                 if f.label == "British spelling"]
    return hits


def test_canons_own_prose_is_spelled_the_way_the_firm_asked():
    """The firm asked for American spelling in August 2026, and on 14 October
    canon's own prose still carried 82 British spellings that every session
    read and copied. They said yes to fixing it; this keeps it fixed."""
    assert len(PROSE) >= 12, "the skills moved; this check would cover less than it claims"
    for name in PROSE:
        hits = _prose_hits((CANON / name).read_text(encoding="utf-8"))
        assert not hits, f"{name} spells {sorted(set(hits))} the British way"


def test_the_spelling_guard_still_sees_a_british_word():
    """Check the checker: the exemptions must not swallow ordinary prose."""
    assert _prose_hits("The behaviour was recognised.") == ["behaviour", "recognised"]
    assert _prose_hits('He wrote "the behaviour" and left.') == []
    assert _prose_hits("> the behaviour, quoted") == []


def test_the_manifests_are_spelled_the_way_the_firm_asked():
    import json
    texts = [json.loads((CANON / ".claude-plugin" / "plugin.json")
                        .read_text(encoding="utf-8"))["description"]]
    market = CANON.parent / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        texts += [p["description"] for p in json.loads(market.read_text(encoding="utf-8"))["plugins"]
                  if p["name"] == "canon"]
    for text in texts:
        assert not [f for f in voice.check(text) if f.label == "British spelling"], text[:80]


# ── the talking rules reach every session ────────────────────────────────

HOOKS = CANON / "hooks" / "hooks.json"


def test_the_session_start_text_is_generated_from_voice_md():
    """One source. A hand-kept copy of the talking rules is a second account of
    them, and the two would disagree within a release."""
    assert voice.HOOK_TEXT.read_text(encoding="utf-8") == voice.session_start_text(), \
        "hooks/session-start.md is stale. Run: python voice.py --write-hook"


def test_the_session_start_text_fits_under_the_cap():
    """Over 10,000 characters, Claude Code saves the output to a file and shows
    only a preview, and nothing asks the session to read the rest."""
    assert len(voice.session_start_text()) < 10_000


def test_the_plugin_declares_the_hook_the_way_the_loader_reads_it():
    """A hooks file without the top-level "hooks" wrapper fails to load, and
    an unquoted plugin root breaks on a path with a space in it. `cat` rather
    than Python, because which Python name exists differs by machine and `cat`
    works in sh, Git Bash and PowerShell alike."""
    import json
    spec = json.loads(HOOKS.read_text(encoding="utf-8"))
    entries = spec["hooks"]["SessionStart"]
    commands = [h["command"] for e in entries for h in e["hooks"] if h["type"] == "command"]
    assert commands == ['cat "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.md"']
    # NO MATCHER, SO EVERY SOURCE FIRES: startup, resume, clear, compact, fork.
    # It was "startup|clear|compact" to keep a resumed chat from seeing the
    # text twice. Codex on #439: a chat begun before canon was installed or
    # updated then never sees it at all. Twice is cheaper than never.
    assert all("matcher" not in e for e in entries), \
        "a matcher narrows which sessions are told how to talk to the firm"


def test_a_stale_hook_text_is_caught(tmp_path, monkeypatch):
    """Check the checker: --check-hook has to fail when the file drifts."""
    stale = tmp_path / "session-start.md"
    stale.write_text("an old copy\n", encoding="utf-8")
    monkeypatch.setattr(voice, "HOOK_TEXT", stale)
    assert voice.main(["--check-hook"]) == 1
    stale.write_text(voice.session_start_text(), encoding="utf-8")
    assert voice.main(["--check-hook"]) == 0



def test_a_source_that_could_not_be_read_is_not_a_finding_or_a_pass(tmp_path):
    """A wrong path came back as exit 1, "tells found", with a traceback, and a
    UTF-16 file from PowerShell's `>` did the same. Neither was checked."""
    missing = tmp_path / "nope.md"
    utf16 = tmp_path / "ps.md"
    utf16.write_text("Honestly, fine.", encoding="utf-16")
    for path in (missing, utf16):
        got = subprocess.run([sys.executable, str(CANON / "voice.py"), str(path)],
                             capture_output=True, text=True, cwd=CANON)
        assert got.returncode == 2, got.stdout + got.stderr
        assert "not a clean result" in got.stdout
        assert "Traceback" not in got.stderr


def test_an_empty_draft_beside_a_clean_one_is_not_clean(tmp_path):
    """Words were summed across sources, so an empty file hid behind a full one."""
    empty, clean = tmp_path / "empty.md", tmp_path / "clean.md"
    empty.write_text("", encoding="utf-8")
    clean.write_text("Please try again, this should be fixed.", encoding="utf-8")
    got = subprocess.run([sys.executable, str(CANON / "voice.py"), str(empty), str(clean)],
                         capture_output=True, text=True, cwd=CANON)
    assert got.returncode == 2, got.stdout
    assert "empty.md: has 0 words" in got.stdout
    assert "across 1 of 2 source(s)" in got.stdout


def test_help_is_help():
    got = subprocess.run([sys.executable, str(CANON / "voice.py"), "--help"],
                         capture_output=True, text=True, cwd=CANON)
    assert got.returncode == 0 and "Run:" in got.stdout
