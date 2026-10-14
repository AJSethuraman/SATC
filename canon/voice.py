"""The tells that give a draft away as not the firm's. Checked, with its denominator.

WHAT THIS IS FOR. `VOICE.md` says how the firm writes. Most of it is judgment
and no script reaches it: whether a sentence leads with the point, whether the
example is the right one, whether the ending says what changes. A few things
are mechanical, and the firm has caught every one of them by eye more than once.
This catches those so they never reach the firm to be caught.

EVERY TELL CARRIES ITS SOURCE. A tell is here because the firm objected to it,
or because the writing profile they handed over names it. The source is the
quotation, and a test asserts each one appears verbatim in `VOICE.md`. A tell
with no source is a session's taste, which is the thing this record exists to
keep out.

WHAT IT CANNOT DO, said rather than implied. A draft can pass this clean and
still be what the firm called "literally AI dribble". Clean here means none of
these particular tells were found, not that the draft sounds like them. Reading
it next to a sentence of theirs is still the check that matters.
It also can't tell a word used from a word quoted: a draft that quotes somebody
saying "honestly" is flagged, and that hit is a line to read, not to fix.

Run:  python voice.py DRAFT.md [MORE.md ...]     or pipe a draft on stdin
      python voice.py --write-hook    regenerate hooks/session-start.md from VOICE.md
      python voice.py --check-hook    exit 1 if it has drifted
Exit 0 when nothing is found, 1 when something is, 2 when there was nothing to read.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The British spellings agents keep reaching for. Whole words only, so
# "realistically" and "programmer" are left alone.
_IZE_STEMS = (
    "organ|recogn|real|summar|priorit|apolog|emphas|minim|maxim|categor|standard"
    "|final|util|amort|optim|mechan|item|general|parameter|capital|normal|canonical"
    "|author|character|special|critic|visual|memor|custom|initial|serial|sanit|token"
    "|digit|synthes|formal|central|local|stabil|neutral|legal|emphas|familiar|subsid"
)
_BRITISH = (
    rf"(?:{_IZE_STEMS})is(?:e|ed|es|ing|ation|ations)"
    r"|analys(?:e|ed|ing)|paralys(?:e|ed|ing)|catalys(?:e|ed|ing)"
    r"|behaviours?|colour(?:s|ed|ing)?|favour(?:s|ed|ite|able)?|honour(?:s|ed)?|labour(?:s|ed)?"
    r"|neighbours?|rigour|humour|endeavour(?:s|ed)?|flavour(?:s|ed)?"
    r"|centres?|theatres?|fibres?|litres?|calibre|licence|defence|offence|pretence"
    r"|judgements?|acknowledgements?|ageing|practise[sd]?|cheques?|grey|programmes?|catalogues?|analogue"
    r"|travelled|travelling|cancelled|cancelling|modelled|modelling|labelled|labelling"
    r"|signalled|signalling|totalled|totalling"
    r"|fulfil|enrol|instil|whilst|amongst|learnt|spelt"
)


@dataclass(frozen=True)
class Tell:
    label: str
    pattern: re.Pattern
    source: str   # the words the tell rests on, verbatim from VOICE.md


TELLS = (
    Tell(
        "British spelling",
        re.compile(rf"\b(?:{_BRITISH})\b", re.I),
        "no British spelling this is a totally English American company",
    ),
    Tell(
        "saying you're being honest",
        re.compile(r"\b(?:honestly|to be honest|in all honesty)\b", re.I),
        "don't say things like 'honestly' randomly",
    ),
    Tell(
        "a sentence about how open we are",
        re.compile(r"\b(?:be|being|are|we're|we are|i'm|i am) (?:upfront|transparent)\b", re.I),
        "we dont need to be claiming how upfront we are about stuff",
    ),
    Tell(
        "padding before the point",
        re.compile(r"\bI wanted to take a moment\b|\bI hope this (?:email |message |note )?finds you well\b",
                   re.I),
        "I wanted to take a moment to raise a potential consideration.",
    ),
    Tell(
        "ceremonial courtesy",
        re.compile(r"\b(?:please )?(?:don't|do not) hesitate to\b|\bthank you (?:so much )?for your patience\b",
                   re.I),
        "Avoid ceremonial gratitude, repeated apologies, or excessive reassurance.",
    ),
)


@dataclass(frozen=True)
class Finding:
    where: str
    line: int
    label: str
    text: str


def check(text: str, where: str = "<draft>") -> list[Finding]:
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        for tell in TELLS:
            for m in tell.pattern.finditer(line):
                found.append(Finding(where, number, tell.label, m.group(0)))
    return found


HERE = Path(__file__).resolve().parent
VOICE_MD = HERE / "VOICE.md"
#: Printed at the start of every session by `hooks/hooks.json`. GENERATED from
#: VOICE.md, never edited: a second copy of the talking rules written by hand
#: is a second account that will drift from the first.
HOOK_TEXT = HERE / "hooks" / "session-start.md"


def talking_section(voice_md: str) -> str:
    """The body of VOICE.md's "Talking to the firm" section, without its heading."""
    head = "## Talking to the firm\n"
    if head not in voice_md:
        raise ValueError("VOICE.md has no 'Talking to the firm' section")
    body = voice_md.split(head, 1)[1]
    return body.split("\n## ", 1)[0].strip()


def session_start_text(voice_md: str | None = None) -> str:
    """What every session is told before its first reply."""
    if voice_md is None:
        voice_md = VOICE_MD.read_text(encoding="utf-8")
    return (
        "# Talking to the firm\n\n"
        "Printed by canon at the start of every session. The firm, 14 October 2026: "
        '*"I want you to talk to me like me and I want things drafted for me to sound '
        'like me"*. This is the part of `${CLAUDE_PLUGIN_ROOT}/VOICE.md` that applies '
        "to every reply. The rest of that file, and `/canon:voice`, cover drafting "
        "things the firm will send.\n\n"
        "Generated from VOICE.md by `voice.py --write-hook`. Edit VOICE.md, never this.\n\n"
        + talking_section(voice_md) + "\n"
    )


def _words(text: str) -> int:
    return len(text.split())


def main(argv: list[str]) -> int:
    if argv == ["--write-hook"]:
        HOOK_TEXT.parent.mkdir(exist_ok=True)
        HOOK_TEXT.write_text(session_start_text(), encoding="utf-8")
        print(f"wrote {HOOK_TEXT.name} from VOICE.md")
        return 0
    if argv == ["--check-hook"]:
        current = HOOK_TEXT.read_text(encoding="utf-8") if HOOK_TEXT.is_file() else ""
        if current != session_start_text():
            print(f"{HOOK_TEXT.name} is out of date with VOICE.md. Run: python voice.py --write-hook")
            return 1
        print(f"{HOOK_TEXT.name} matches VOICE.md")
        return 0
    if argv:
        sources = [(a, Path(a).read_text(encoding="utf-8")) for a in argv]
    else:
        sources = [("<stdin>", sys.stdin.read())]
    words = sum(_words(t) for _, t in sources)
    if not words:
        # Unknown is a third answer. Nothing read is not the same as nothing found.
        print("Nothing to read: 0 words. This is not a clean result.")
        return 2
    found = [f for where, text in sources for f in check(text, where)]
    for f in found:
        print(f"{f.where}:{f.line}: {f.label}: {f.text!r}")
    print(f"{len(found)} tell(s) in {words:,} words across {len(sources)} source(s); "
          f"{len(TELLS)} kinds of tell checked.")
    if not found:
        print("Clean on these tells only. Read it next to a sentence of theirs before it goes out.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
