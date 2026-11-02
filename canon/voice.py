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
# "realistically" and "programmer" are left alone. A CLOSED LIST, said rather
# than implied: a British word with no entry here passes. The families were
# widened once, after a review found "behaviourally", "organiser" and
# "enrolment" walking straight past the first version.
_IZE_STEMS = (
    "organ|recogn|real|summar|priorit|apolog|emphas|minim|maxim|categor|standard"
    "|final|util|amort|optim|mechan|item|general|parameter|capital|normal|canonical"
    "|author|character|special|critic|visual|memor|custom|initial|serial|sanit|token"
    "|digit|synthes|formal|central|local|stabil|neutral|legal|familiar|subsid"
    "|rational|penal|legitim|monet|harmon|modern|scrutin|econom|equal|privat|jeopard"
    "|symbol|personal|marginal|commercial|popular|sympath|agon|antagon|patron|terror"
    "|fertil|hospital|energ|vandal|revolution|motor|human|civil|global|vocal|western"
)
_OUR_STEMS = (
    "behavio|colo|favo|hono|labo|neighbo|rigo|humo|endeavo|flavo|rumo|harbo|armo"
    "|odo|savo|valo|vigo|clamo|parlo|splendo|tumo"
)
_DOUBLED_L = (
    "travel|cancel|model|label|signal|total|fuel|counsel|level|marvel|channel|tunnel"
    "|dial|duel|jewel|quarrel|rival|shovel|worship|equal|pencil|program"
)
_BRITISH = (
    rf"(?:{_IZE_STEMS})is(?:e|ed|es|ing|ation|ations|er|ers|able)"
    rf"|(?:{_OUR_STEMS})ur(?:s|ed|ing|al|ally|ful|able|ably|ite|ites|hood|er|ers|less)?"
    rf"|(?:{_DOUBLED_L})l(?:ed|ing|er|ers)"
    r"|analys(?:e|ed|ing|er|ers)|paralys(?:e|ed|ing)|catalys(?:e|ed|ing)"
    r"|centre[sd]?|metres?|theatres?|fibres?|litres?|calibre|manoeuvre[sd]?"
    r"|licence[sd]?|defence|offence|pretence"
    r"|judgements?|acknowledgements?|ageing|practis(?:e|es|ed|ing)|cheques?|grey|programmes?"
    r"|catalogues?|analogue|marvellous|jewellery|tyres?|aluminium|sceptic(?:al|ism)?"
    r"|fulfil|fulfils|fulfilment|enrol|enrols|enrolment|instil|instils"
    r"|whilst|amongst|learnt|spelt"
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
        re.compile(r"\b(?:honestly|to\s+be\s+honest|in\s+all\s+honesty)\b", re.I),
        "don't say things like 'honestly' randomly",
    ),
    # SAID ABOUT OURSELVES, NOT ABOUT ANYTHING. "Pass-through entities are
    # transparent for tax purposes" and "fees are upfront" are ordinary
    # sentences at a tax firm, and the first version flagged both.
    Tell(
        "a sentence about how open we are",
        re.compile(r"\b(?:we're|we\s+are|i'm|i\s+am|to\s+be|being)\s+(?:upfront|transparent)\b", re.I),
        "we dont need to be claiming how upfront we are about stuff",
    ),
    Tell(
        "padding before the point",
        re.compile(r"\bI\s+wanted\s+to\s+take\s+a\s+moment\b"
                   r"|\bI\s+hope\s+this\s+(?:email\s+|message\s+|note\s+)?finds\s+you\s+well\b", re.I),
        "I wanted to take a moment to raise a potential consideration.",
    ),
    Tell(
        "ceremonial courtesy",
        re.compile(r"\b(?:please\s+)?(?:don't|do\s+not)\s+hesitate\s+to\b"
                   r"|\bthank\s+you\s+(?:so\s+much\s+)?for\s+your\s+patience\b", re.I),
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
    """Every tell in the text, with the line it starts on.

    THE TEXT IS SEARCHED WHOLE, NOT LINE BY LINE. Markdown here is wrapped at
    about eighty columns, so "to be" ends one line and "honest" starts the
    next, and a per-line search never saw it. Curly apostrophes are read as
    straight ones, because a draft pasted from Outlook or Word has them.
    Both substitutions keep every character where it was, so the line number
    of a match is still the line it starts on.
    """
    flat = text.replace("’", "'").replace("‘", "'")
    found = []
    for tell in TELLS:
        for m in tell.pattern.finditer(flat):
            line = flat.count("\n", 0, m.start()) + 1
            found.append(Finding(where, line, tell.label, " ".join(m.group(0).split())))
    return sorted(found, key=lambda f: f.line)


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
        'like me"*. This is the *Talking to the firm* section of canon\'s `VOICE.md`, '
        "and it applies to every reply. For anything the firm will send, `/canon:voice` "
        "reads the rest of that file.\n\n"
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
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv:
        raw = []
        for a in argv:
            try:
                raw.append((a, Path(a).read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError) as e:
                raw.append((a, None, f"could not be read ({type(e).__name__})"))
    else:
        raw = [("<stdin>", sys.stdin.read())]

    # UNKNOWN IS A THIRD ANSWER, PER SOURCE. Summing words across sources let an
    # empty draft hide beside a full one and the run came back clean.
    read, unread = [], []
    for item in raw:
        where, text = item[0], item[1]
        if text is None:
            unread.append((where, item[2]))
        elif not _words(text):
            unread.append((where, "has 0 words"))
        else:
            read.append((where, text))

    found = [f for where, text in read for f in check(text, where)]
    for f in found:
        print(f"{f.where}:{f.line}: {f.label}: {f.text!r}")
    for where, why in unread:
        print(f"{where}: {why}. Nothing was checked there; this is not a clean result.")
    words = sum(_words(text) for _, text in read)
    print(f"{len(found)} tell(s) in {words:,} words across {len(read)} of {len(raw)} "
          f"source(s); {len(TELLS)} kinds of tell checked.")
    if found:
        return 1
    if unread:
        return 2
    print("Clean on these tells only. Read it next to a sentence of theirs before it goes out.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
