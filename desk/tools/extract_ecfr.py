"""Turn a section of the eCFR into a desk's problem set and stored authority.

WHY THIS IS A SCRIPT AND NOT PART OF THE ENGINE. This is the one place a live
fetch belongs: building the record. Once built, the engine grades against stored
text and never reaches out, which is what keeps CI deterministic and offline.

WHAT IT REFUSES TO DO. It does not invent a conclusion, and it does not invent a
citation. An example whose outcome is not stated in terms this desk can score,
or whose analysis does not name a single rule it rests on, is left out and
counted, because a problem set that quietly drops what it could not parse
reports a denominator that means nothing -- and that is the first tenet in
`docs/SOFTWARE-TENETS.md`, which exists because a proof artifact once declared
190 documents fine when every one of them was unreadable.

THE RULES ARE THE AUTHORITY; THE EXAMPLES ARE THE PROBLEMS. The first record
this script wrote stored the 21 worked examples it also scored on, and nothing
else: 21 passages for 21 problems, the same citation on each pair, not one
operative rule. Shown to a model the corpus leaked its own conclusions; hidden,
there was nothing to retrieve from, and "cite your authority" degraded into
recalling example numbers from a list of 21 strings. That index was a bijection
a brain could solve as an assignment puzzle, and the frontier row did exactly
that (`runs/2026-09-04/SCOREBOARD.md`). So the stored authority is now every
paragraph of the section OUTSIDE its examples, and a problem's expected citation
is the rule its own analysis names -- see `governing`.

Run:  python tools/extract_ecfr.py <reg.xml> <desk-dir> <YYYY-MM-DD>
      where the date is the day the XML was TAKEN FROM eCFR -- not today.
"""
from __future__ import annotations

import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from record import under as _under                        # noqa: E402

#: HOW THE REGULATION ACTUALLY STATES A CONCLUSION, read off the corpus rather
#: than guessed at. Across § 1.263(a)-3's 117 examples, 112 sentences open with a
#: conclusion connective, and every scorable outcome in them is one of four
#: framings: "must capitalize" (22), "not required to be capitalized" (13), "not
#: required to capitalize" (8), "must be capitalized" (7). Two answers, four
#: spellings. An earlier version knew only the first and third, which is how an
#: example concluding "must be capitalized" was recorded as NOT required to.
CLASSIFY = (
    ("must capitalize", re.compile(r"\bmust capitaliz\w*", re.I)),
    ("must capitalize", re.compile(r"\bmust be capitaliz\w*", re.I)),
    ("not required to capitalize", re.compile(r"\bnot required to capitaliz\w*", re.I)),
    ("not required to capitalize", re.compile(r"\bnot required to be capitaliz\w*", re.I)),
)

#: A CONCLUSION HEDGED ON A CONDITION IS NOT AN ANSWER. Three examples conclude
#: that amounts "must be capitalized IF these amounts result in an improvement" --
#: the regulation is settling that a safe harbour is unavailable, not that
#: capitalisation follows. Their facts do not establish the condition, so the
#: honest answer is conditional and the desk would have marked it wrong. Three of
#: 24 rows, each one punishing the better answer.
CONDITIONAL = re.compile(
    r"\b(?:if|unless|to the extent|provided that|only if)\b", re.I)

#: A conclusion is announced, not merely stated. Requiring the connective is what
#: separates the paragraph that DECIDES from the ones that recite the rule or the
#: taxpayer's own prior treatment -- both of which use the same verbs.
CONNECTIVE = re.compile(
    r"^\(?[ivx]*\)?\s*(?:Therefore|Accordingly|Thus|As a result|Consequently)\b", re.I)

#: WHAT COUNTS AS DISCLOSING THE ANSWER: the words themselves, anywhere in the
#: fact pattern. Not a list of framings -- a TOTAL ban on the two stems this desk
#: reasons about.
#:
#: Three rounds of review were spent widening a list of phrasings, and each round
#: found another the last had missed: first "must be capitalized", then
#: "capitalize these amounts", then the affirmative "is required to capitalize"
#: sitting in three fact patterns after the leak had twice been called fixed. A
#: rule that must enumerate how English can say a thing will always be one
#: phrasing behind, and every gap in it is a silently inflated score.
#:
#: So the rule stops enumerating. A fact pattern may not contain "capitaliz" or
#: "deduct" in ANY form, conclusive or incidental. It costs examples whose facts
#: merely mention the words in passing -- 31 usable became 24 -- and it cannot
#: have a gap, because there is no vocabulary left to be incomplete. The cost
#: bought something too: the surviving set is 12 and 12, so a constant answer
#: scores 50% rather than 58%.
DISCLOSES = re.compile(r"capitaliz|deduct", re.I)

#: An example that leans on one not shown cannot be answered from what the desk
#: is given. Three spellings, because the regulation uses each -- a filter
#: written for only the first missed a real case on this script's first run, and
#: one written for the first two missed "The facts are the same as in Example 30"
#: on the third.
DEPENDENT = re.compile(
    r"same facts as(?: in)? Example|Assume the same facts|the facts are the same as", re.I)

#: A SENTENCE THAT APPLIES A RULE OF THIS SECTION BY NAME IS ANALYSIS, NOT FACT.
#: "A's ESVs are within the routine maintenance safe harbor under paragraph
#: (i)(1)(ii) of this section" carries no connective and no banned stem, so the
#: first boundary let it through as a fact. Once the expected citation IS that
#: paragraph, leaving the sentence in the facts hands the model its citation the
#: way the conclusion used to hand it the answer. So every sentence naming a
#: paragraph of this section is withheld with the conclusion, and the withheld
#: text is where the citation is read from.
ANALYSIS = re.compile(r"\bparagraphs? \(")

#: EXCEPT A STIPULATION. "Assume that none of the exceptions set out in paragraph
#: (i)(3) of this section apply" is the regulation fixing a fact, in its own word,
#: and stripping it would hand the model a problem the regulation did not pose.
#: A stipulation stays in the facts; `build` then refuses any problem whose facts
#: still name its own governing paragraph, so the exception cannot reopen the leak.
STIPULATES = re.compile(r"^\(?[ivx]*\)?\s*Assume\b", re.I)

#: A sentence boundary, kept crude on purpose. Its correctness is NOT what makes
#: the split safe: whatever it does, `DISCLOSES` re-checks what survives.
_SENTENCE = re.compile(r"(?<=\.)\s+(?=[A-Z(])")


def conclusions_in(text: str) -> set:
    """Every DISTINCT answer this text states. Zero, one, or -- fatally -- two."""
    return {a for a, rx in CLASSIFY if rx.search(text)}


def split_conclusion(text: str):
    """Split an example into its fact pattern and the analysis it withholds.

    Returns `(facts, withheld, answer)`, or `(None, None, why)` naming the
    reason this example cannot become a problem. `withheld` is every sentence
    that announces the conclusion or applies a rule of this section by name, in
    the order the regulation wrote them: it is the text `governing` reads the
    expected citation from. Nothing is ever guessed and nothing is ever dropped
    without a reason a reader can count.

    WHY THIS EXISTS, AND WHAT IT NEARLY COST. `build` wrote each example's
    COMPLETE text into `Facts`, and an example was kept precisely BECAUSE that
    text stated a conclusion -- so every problem handed to a model contained its
    own answer, in the regulation's own words. A model had only to copy the
    sentence back, both scoreboard rows would have read near-perfect, and the gap
    between the local brain and the frontier one -- the single finding this
    harness exists to produce -- would have been noise between two ceilings.

    WHY MORE THAN ONE CONCLUSION IS A REFUSAL AND NOT A CHOICE. § 1.263(a)-3(l)(3)
    Example 4 concludes that a cleanup is not an adaptation AND that the regrading
    must be capitalized. Reading only two spellings, an earlier version saw one
    phrase, recorded "not required to capitalize", and would have scored the right
    answer as WRONGLY ABSORBED -- manufacturing the one number that costs
    something. An example stating two outcomes has no single answer to score, so
    it is not a problem, and saying so is the only honest move available.
    """
    facts, withheld, concluded, found = [], [], [], set()
    for sentence in _SENTENCE.split(text.strip()):
        answers = conclusions_in(sentence)
        if answers and CONNECTIVE.search(sentence.strip()):
            concluded.append(sentence)
            withheld.append(sentence)
            found |= answers
        elif ANALYSIS.search(sentence) and not STIPULATES.search(sentence.strip()):
            withheld.append(sentence)
        else:
            facts.append(sentence)
    if not found:
        return None, None, "states no conclusion this desk can score"
    if len(found) > 1:
        return None, None, "states more than one conclusion"
    if CONDITIONAL.search(" ".join(concluded)):
        return None, None, "states its conclusion conditionally"
    kept = " ".join(facts).strip()
    if not kept or DISCLOSES.search(kept):
        return None, None, "conclusion cannot be separated from the facts"
    return kept, " ".join(withheld).strip(), found.pop()


# ── the outline: which paragraph each element of the section is ──────────────
#
# The eCFR XML for a section is FLAT. Only the root carries attributes; every
# paragraph is a top-level <P> with its label as leading text, so the hierarchy
# -- that "(ii) Application of improvement rules to a building" is (e)(2)(ii)
# and not (i)(ii) or (k)(6)(ii) -- exists only in the sequence of labels. It has
# to be reconstructed, and it has to be reconstructed WITHOUT judgement, because
# a citation index built on a guess is an answer key built on a guess.
#
# Three facts about the source settle it, and none of them is a heuristic:
#
# 1. THE ALPHABETS CYCLE. CFR paragraph levels run (a), (1), (i), (A), (1), (i)
#    -- lower letter, arabic, lower roman, upper letter, arabic, lower roman.
#    A label can only sit at a level whose alphabet contains it.
# 2. THE FIFTH AND SIXTH LEVELS ARE SET IN ITALICS. The XML writes the second
#    level as `(1)` and the fifth as `(<I>1</I>)`. That is the regulation's own
#    typesetting saying which level a numeral is at, and it is what places
#    "(3) Property other than building" at (e)(3) rather than under
#    (e)(2)(v)(B), where a plain deepest-first walk put it.
# 3. A LABEL EITHER CONTINUES A LEVEL OR OPENS THE NEXT ONE. At a depth already
#    on the stack it must be the successor of what is there; one deeper it must
#    be the first of its alphabet. Nothing else is a placement.
#
# Every assignment of depths consistent with all three is enumerated. The
# committed fixture admits exactly one. Were it to admit more, the elements
# whose placement differs between readings are UNDERDETERMINED, and they are
# excluded and counted rather than resolved by preference -- a rule the section
# itself corroborates: it cites 109 of its own paragraph paths in full, and the
# reconstruction resolves 107 of them; the two it cannot name paragraphs that do
# not exist in the text (see `dangling`).

_ROMAN = ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"))


def _roman(n: int) -> str:
    out = ""
    for value, glyph in _ROMAN:
        while n >= value:
            out, n = out + glyph, n - value
    return out


LOWER = tuple(chr(c) for c in range(ord("a"), ord("z") + 1))
UPPER = tuple(chr(c) for c in range(ord("A"), ord("Z") + 1))
ARABIC = tuple(str(i) for i in range(1, 100))
ROMAN = tuple(_roman(i) for i in range(1, 40))

#: What each depth may be labelled with, as `(letters, italic)`. The italic flag
#: is part of the alphabet rather than a property of the depth, and that is the
#: whole of what changed here.
#:
#: A DEPTH MAY OFFER MORE THAN ONE ALPHABET, and § 1.446-1 is why. I published,
#: and then corrected, a diagnosis saying that section SKIPS the (A) level. It
#: does not. It uses a DIFFERENT ALPHABET AT THE SAME LEVEL, and it uses both in
#: the same section:
#:
#:     (c)(1)(ii)(A), (B), (C)     plain capitals, the modern scheme
#:     (c)(1)(iv)(a), (b)          italic lowercase, the 1957 scheme
#:
#: Both sit at depth 3. A single alphabet per depth cannot read a section that
#: writes both, so § 1.446-1, § 1.274-5T and two more had NO consistent reading
#: at all and `outline()` refused them -- correctly, on a gap in the reader.
#:
#: The italic flag is what keeps this from becoming ambiguous: depth 0 is
#: lowercase PLAIN and depth 3's second alphabet is lowercase ITALIC, so a label
#: never belongs to both, and the sequence rules below still have exactly one
#: alphabet to run against once a branch has opened.
ALPHABETS = (
    ((LOWER, False),),
    ((ARABIC, False),),
    ((ROMAN, False),),
    ((UPPER, False), (LOWER, True)),
    ((ARABIC, True),),
    ((ROMAN, True),),
)

_I0, _I1 = "\x01", "\x02"       # fences around italic runs, never in real text
_LABEL = re.compile(r"^\((\x01?)([a-zA-Z0-9]{1,4})\x02?\)\s*")
#: A RUN-IN HEADING, IN THE TWO SHAPES THE CFR ACTUALLY USES. The first is an
#: italic heading closed by an em-dash -- "(c) Coordination with other
#: provisions of the Code—(1) In general." -- which is how § 1.263(a)-3 writes
#: every one of its thirty.
#:
#: The second is an italic heading whose own FULL STOP sits INSIDE the italics,
#: followed by a bare space: "(iv) [i]Combinations of the foregoing methods.[/i]
#: (a) In a case..." § 1.446-1 writes them that way, and
#: the reader seeing only the em-dash form never captured that run-in `(a)`. Its
#: italic `(b)` then had no level to continue, no consistent reading existed for
#: the section at all, and `outline()` refused it -- correctly, and for a reason
#: that was a gap in the reader rather than in the regulation. Four more
#: sections refused for the same cause, and 53 worked examples sat behind it.
#:
#: WHAT KEEPS THIS SAFE IS THE ANCHOR, NOT THE FULL STOP. Both alternatives are
#: matched against the text IMMEDIATELY following the leading label, so an
#: italic run anywhere else in the sentence is never a candidate: a heading
#: touches its label, a term does not. I first wrote that the full stop was the
#: discriminator; dropping it broke nothing, twice, including against a case
#: built to catch it. It stays because it is the shape these sections actually
#: write, and narrower costs nothing -- not because it is load bearing.
#:
#: AND BEHIND THAT, `placements()` returns EVERY consistent reading and
#: `outline()` excludes any element whose path differs between them. A run-in
#: proposed wrongly does not become a wrong citation; it becomes an
#: underdetermined element, reported and left out.
_RUN_IN = re.compile(r"^\x01[^\x02]*\x02\s*—\s*(?=\()"
                     r"|^\x01[^\x02]*\.\x02\s+(?=\()")


#: TWO PARAGRAPHS RESERVED TOGETHER IN ONE ELEMENT, in the three ways these
#: sections write it:
#:
#:     (k) and (l) [Reserved]        § 1.274-5T, on the last of its 105 elements
#:     (a)-(b) [Reserved]            § 1.274-5, on its first
#:     (2)(i) and (ii) [Reserved]    § 1.274-5 again, continuing the DEEPEST
#:                                   label rather than the leading one
#:
#: A reader taking only the labels it opens leaves the outline standing at the
#: first of them, and the paragraph that follows is not its successor -- so both
#: sections had no consistent reading at all, one of them on its opening line.
#:
#: THE EXPANSION NEEDS NO ALPHABET, WHICH IS WHY IT CAN HAPPEN HERE. "and" names
#: exactly the two labels written down. A dash or "through" names a range, and a
#: range would need the alphabet -- unknown until `placements` has chosen a depth
#: -- EXCEPT where the two are adjacent, and then the range IS the two written
#: down whichever alphabet it is in. A range spanning more than two is refused
#: rather than guessed at; no section here writes one.
#:
#: WHAT KEEPS IT SAFE IS THE ANCHOR, NOT THE TRAILING BOUNDARY. The match starts
#: immediately after the labels the element opens, so a body mentioning "and (l)"
#: in the middle of a sentence is never a candidate. The `(?:\s|$)` on the end
#: was tried as a mutation and broke nothing; it stays because it is the shape
#: these sections write, not because it is load bearing. Said here rather than
#: implied, for the same reason `_RUN_IN` says it about its full stop.
_SPAN = re.compile(r"^(and|through|[-\u2010-\u2015])\s*"
                   r"\((\x01?)([a-zA-Z0-9]{1,4})\x02?\)(?:\s|$)")


@dataclass(frozen=True)
class Paragraph:
    """One paragraph of the section, outside its examples, at its full path."""
    path: tuple[str, ...]
    text: str

    @property
    def label(self) -> str:
        return "".join(f"({p})" for p in self.path)


#: A RUN-IN HEADING WHOSE ITALICS ARE BROKEN ACROSS THE LABEL, in the
#: government's own file. § 1.62-2 writes
#:
#:     <I>Returning amounts in excess of expenses—(</I>1<I>) In general.</I>
#:
#: putting the em-dash and the opening parenthesis inside the italics and the
#: numeral outside, where every other run-in in the CFR writes
#: `<I>Substantiation</I>—(1) <I>In general.</I>`. The two are the same sentence
#: typeset two ways, and the reader saw a heading in one and not the other -- so
#: § 1.62-2 had no consistent reading at all and the vehicle desk lost its
#: examples to a stray tag.
#:
#: THIS MOVES FENCES, NEVER TEXT. Strip the fences from either side and the
#: string is identical, which is the property that makes it a repair rather than
#: an edit -- and the label comes out PLAIN, which is what (f)(1) is.
_MISFENCED = re.compile(rf"—\({_I1}([a-zA-Z0-9]{{1,4}}){_I0}\)")


def _marked(elem) -> str:
    """The element's text with its italic runs fenced, so a label keeps its face."""
    out = [elem.text or ""]
    for kid in elem:
        inner = "".join(kid.itertext())
        out.append(f"{_I0}{inner}{_I1}" if kid.tag == "I" else inner)
        out.append(kid.tail or "")
    text = " ".join("".join(out).split())
    return _MISFENCED.sub(rf"{_I1}—(\1){_I0}", text)


def chains_of(elem) -> list[list[tuple[str, bool, str]]]:
    """The label chains this element opens -- more than one when it spans two
    paragraphs. Usually exactly one, which is `labels(elem)`."""
    chain, rest = _read_labels(elem)
    if not chain:
        return []
    m = _SPAN.match(rest)
    if m is None:
        return [chain]
    connector, italic, label = m.group(1), bool(m.group(2)), m.group(3)
    run = ((label,) if connector == "and"
           else _span_between(chain[-1][0], label))
    if run is None:
        # A RANGE NO SINGLE ALPHABET SETTLES -- "(i) through (v)" is five roman
        # numerals or fourteen letters, and nothing here can tell which. It is
        # left unexpanded, the section fails to read, and it says so. No section
        # this reader is pointed at writes one.
        return [chain]
    # Every paragraph in the span carries the element's own words with the span
    # taken off the front: "and (l)" is a label, not part of what any of them say.
    body = _plain(rest[m.end():])
    return ([chain[:-1] + [(chain[-1][0], chain[-1][1], body)]]
            + [[(x, italic, body)] for x in run])


def _span_between(first: str, second: str) -> tuple[str, ...] | None:
    """The labels from after `first` through `second`, if one alphabet settles it.

    THE DEPTH IS NOT KNOWN HERE and does not have to be. A range names two
    labels, and where exactly one alphabet holds both of them in that order, the
    run between them is the same whatever depth the pair turns out to sit at:
    "(3)-(7)" is 4, 5, 6, 7 in the only alphabet that has a 3 and a 7. Where two
    alphabets qualify -- "(i) through (v)" is five roman numerals or fourteen
    letters -- there is no answer here and it returns none rather than a guess.
    """
    runs = {letters[letters.index(first) + 1: letters.index(second) + 1]
            for level in ALPHABETS for letters, _ in level
            if first in letters and second in letters
            and letters.index(second) > letters.index(first)}
    return runs.pop() if len(runs) == 1 else None


def _after_label(elem) -> str:
    """The element's marked text with its leading label removed."""
    text = _marked(elem)
    m = _LABEL.match(text)
    return text[m.end():] if m else text


def labels(elem) -> list[tuple[str, bool, str]]:
    return _read_labels(elem)[0]


def _read_labels(elem) -> tuple[list[tuple[str, bool, str]], str]:
    """Every paragraph this element opens: `(label, italic, its text)`.

    RUN-IN HEADINGS OPEN MORE THAN ONE PARAGRAPH. "(c) Coordination with other
    provisions of the Code—(1) In general. Nothing in this section changes..."
    is one <P> that opens both (c) and (c)(1). A reader taking only the leading
    label never sees (c)(1) -- or (e)(2)(ii), the paragraph four of the first
    21 problems turned on. Thirty of the section's 141 elements do this, and
    one opens three levels at once. The heading is the parent's whole text; the
    body belongs to the deepest label.
    """
    text = _marked(elem)
    out: list[tuple[str, bool, str]] = []
    while (m := _LABEL.match(text)) is not None:
        label, italic = m.group(2), bool(m.group(1))
        rest = text[m.end():]
        run_in = _RUN_IN.match(rest)
        if run_in is not None:
            heading = rest[:run_in.end()].rstrip("— ")
            out.append((label, italic, _plain(heading)))
            text = rest[run_in.end():]
            continue
        if _LABEL.match(rest):
            # A LABEL SITTING DIRECTLY ON ANOTHER, WITH NO HEADING BETWEEN THEM.
            # "(2)(i) Except as otherwise expressly provided..." and
            # "(ii) (a) A change in the method of accounting..." are both one
            # <P> in § 1.446-1 opening two paragraphs, and neither carries the
            # italic run-in heading that was the only way this loop continued.
            # The parent has no text of its own -- its content IS the child --
            # so it is recorded with none rather than given the child's body.
            #
            # WHAT KEEPS IT HONEST is `placements`: a deeper label is descended
            # into only when it OPENS its level, and a chain whose deeper labels
            # do not all open yields no reading at all rather than a short path
            # with a long chain. So a body that merely happens to begin with a
            # parenthesised token cannot become a paragraph -- it would have to
            # begin with the first label of the next level down.
            out.append((label, italic, ""))
            text = rest
            continue
        out.append((label, italic, _plain(rest)))
        text = rest
        break
    return out, text


def _plain(text: str) -> str:
    return " ".join(text.replace(_I0, "").replace(_I1, "").split())


def _alphabet(depth: int, label: str, italic: bool) -> tuple | None:
    """The alphabet at `depth` this label belongs to, or None if none does.

    Returns the alphabet rather than a yes/no because everything downstream --
    what opens a level, what succeeds what -- has to run against the SAME one
    the label came from, and a depth may now offer two.
    """
    if not 0 <= depth < len(ALPHABETS):
        return None
    for letters, is_italic in ALPHABETS[depth]:
        if is_italic == italic and label in letters:
            return letters
    return None


def _fits(depth: int, label: str, italic: bool) -> bool:
    return _alphabet(depth, label, italic) is not None


def _opens(depth: int, label: str, italic: bool) -> bool:
    """Whether this label is the FIRST of the alphabet it belongs to here."""
    alphabet = _alphabet(depth, label, italic)
    return alphabet is not None and alphabet[0] == label


def _successor(depth: int, label: str, italic: bool) -> str | None:
    alphabet = _alphabet(depth, label, italic)
    if alphabet is None:
        return None
    i = alphabet.index(label)
    return alphabet[i + 1] if i + 1 < len(alphabet) else None


def placements(chains: list[list[tuple[str, bool]]]) -> list[list[tuple[str, ...]]]:
    """Every depth assignment the three facts above allow. Usually one.

    Each entry of `chains` is the label chain one element opens. The result is
    one path per element per reading -- the path of the DEEPEST label the
    element opens, from which the shallower ones follow.
    """
    readings: list[list[tuple[str, ...]]] = []

    def walk(i: int, stack: tuple, acc: list[tuple[str, ...]]) -> None:
        """`stack` carries `(label, italic)` because the face is part of the
        identity now: at depth 3 a plain `A` and an italic `a` are different
        alphabets, and the successor rule has to know which one it is in."""
        if i == len(chains):
            readings.append(acc)
            return
        chain = chains[i]
        label, italic = chain[0]
        for depth in range(min(len(stack), len(ALPHABETS) - 1) + 1):
            if not _fits(depth, label, italic):
                continue
            if depth < len(stack):
                if _successor(depth, *stack[depth]) != label:
                    continue
            # A new level opens with the first of its alphabet -- except the
            # very first element, which may be any top-level letter so that a
            # fragment of a section can be read. The stack is never empty
            # again after it, so this is exactly one element wide.
            elif stack and not _opens(depth, label, italic):
                continue
            path = stack[:depth] + ((label, italic),)
            for deeper, deeper_italic in chain[1:]:
                if _opens(len(path), deeper, deeper_italic):
                    path = path + ((deeper, deeper_italic),)
                else:
                    break
            else:
                walk(i + 1, path, acc + [tuple(l for l, _ in path)])

    walk(0, (), [])
    return readings


def outline(xml_path: Path) -> tuple[list[Paragraph], list[str]]:
    """Every paragraph of the section outside its examples, at its full path.

    Returns `(paragraphs, underdetermined)`. An element whose path differs
    between consistent readings is not placed by preference: it is named in
    `underdetermined` and left out, because a stored citation that might be the
    wrong paragraph is worse than none. An element that cannot be placed at all,
    or that carries no label, raises -- that is not a paragraph this reader
    understands, and a silent skip would shrink the corpus without a trace.
    """
    root = ET.parse(xml_path).getroot()
    elements = [c for c in root if c.tag in ("P", "PSPACE")]
    chains: list[list[tuple[str, bool, str]]] = []
    #: `{index into chains: the unlabelled elements that follow it}`.
    #:
    #: AN ELEMENT WITH NO LABEL IS A CONTINUATION, NOT A DEFECT. § 1.274-12
    #: writes "(B) Example. The following example illustrates the application of
    #: this paragraph (c)(2)(v)." and then puts the example itself in a separate
    #: <P> carrying no label at all. Raising on it cost the section entirely, and
    #: the honest reading is the one the layout states: the text belongs to the
    #: paragraph immediately above it.
    #:
    #: It stays an error BEFORE the first label, because then there is no
    #: paragraph for it to continue and attaching it anywhere would be a guess.
    continuations: dict[int, list[str]] = {}
    for n, elem in enumerate(elements, 1):
        opened = chains_of(elem)
        if not opened:
            if not chains:
                raise ValueError(
                    f"element {n} of the section carries no paragraph label and "
                    f"nothing precedes it to continue: "
                    f"{_plain(_marked(elem))[:60]!r}")
            continuations.setdefault(len(chains) - 1, []).append(
                _plain(_marked(elem)))
            continue
        chains.extend(opened)
    readings = placements([[(l, it) for l, it, _ in ch] for ch in chains])
    if not readings:
        raise ValueError("the section's labels cannot be read as a CFR outline; "
                         "no assignment of levels is consistent with the sequence")
    paragraphs, underdetermined = [], []
    for i, chain in enumerate(chains):
        placed = {reading[i] for reading in readings}
        if len(placed) > 1:
            underdetermined.append(
                f"({chain[0][0]}) {chain[-1][2][:50]}: could be "
                + " or ".join(sorted("".join(f"({p})" for p in x) for x in placed)))
            continue
        path = placed.pop()
        base = len(path) - len(chain)
        for k, (_label, _italic, text) in enumerate(chain):
            paragraphs.append(Paragraph(path=path[:base + k + 1], text=text))
        for text in continuations.get(i, ()):
            paragraphs.append(Paragraph(path=path, text=text))
    return paragraphs, underdetermined


#: A paragraph path as the regulation writes it in a cross-reference.
_PATH = r"(?:\([a-zA-Z0-9]{1,4}\))+"
_CITES = re.compile(
    rf"paragraphs? ({_PATH})((?:,? (?:and |or |through )?{_PATH})*)"
    rf"( of (?:this section|§ ?[\d.()a-zA-Z-]+))?")


def cited_paths(text: str) -> set[str]:
    """Every full paragraph path this text cites WITHIN its own section.

    "paragraph (e)(2)(ii) of this section", "paragraphs (d)(1) and (j)", "this
    paragraph (k)". A reference into another section -- "paragraph (c)(1)(i) of
    § 1.162-3" -- is not one of ours and is left out. Paths that do not start
    at a lettered level ("paragraph (3)") are relative and are left out too.
    """
    out: set[str] = set()
    for m in _CITES.finditer(text):
        if m.group(3) and "§" in m.group(3):
            continue
        head = m.group(1)
        for path in [head] + re.findall(_PATH, m.group(2)):
            resolved = path if path is head else _continues(_parts(head), path)
            if re.match(r"\([a-z]\)", resolved):
                out.add(resolved)
    return out


#: The alphabet a CITATION uses at each depth. Not the same question as
#: `ALPHABETS`, which is about what the section's own headings may be set in.
#:
#: THE DIFFERENCE MATTERS AND COST A WRONG PATH TO FIND. `ALPHABETS[3]` admits
#: italic lowercase as well as plain capitals, because § 1.446-1 writes its
#: fourth level that way. A cross-reference is plain text and says nothing about
#: face -- so asking `ALPHABETS` whether "(j)" could sit at level 3 answers yes,
#: and "paragraphs (g)(2)(i) and (j) of this section" resolved to the paragraph
#: (g)(2)(i)(j), which no section has. Read against the plain hierarchy the same
#: sentence resolves (j) to itself, which is what it says.
_CITED_LEVELS = (LOWER, ARABIC, ROMAN, UPPER, ARABIC, ROMAN)


def _at_level(level: int, label: str) -> bool:
    """Whether a cited label could sit at this depth. The depth settles it:
    `i` is the ninth letter and the first roman, and only one of those can be
    at level 2."""
    return 0 <= level < len(_CITED_LEVELS) and label in _CITED_LEVELS[level]


def _continues(head: tuple[str, ...], path: str) -> str:
    """A one-label item in an enumerated citation, resolved against its head.

    "amounts paid for a component of a unit of property under paragraph
    (c)(1)(iii), (iv), or (v) of this section" cites (c)(1)(iv) and (c)(1)(v).
    Read literally, it cited "(iv)" and "(v)" -- paragraphs no section has -- so
    two of the sections here reported a dangling citation that was the reader's
    and not the regulation's. Worse than the miscount: `governing()` chooses the
    citation an example is filed under FROM THIS SET, so a bare "(v)" is a
    candidate rule on any section whose examples live under (v).

    THE HEAD'S DEPTH SETTLES IT, and nothing else has to:

        (c)(1)(iii), (iv)      (iv) is roman, the head's own level -> a SIBLING
        (b)(3) (i), (ii)       (i) is roman, one level DOWN from arabic -> a CHILD
        (d)(1) and (j)         (j) is neither -> a path of its own, left alone

    Sibling is tried first because that is what a list of alternatives is.
    """
    parts = _parts(path)
    if len(parts) != 1 or not head:
        return path
    label = parts[0]
    if _at_level(len(head) - 1, label):
        return "".join(f"({x})" for x in head[:-1] + (label,))
    if _at_level(len(head), label):
        return "".join(f"({x})" for x in head + (label,))
    return path


def _parts(path: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\(([a-zA-Z0-9]{1,4})\)", path))


def governing(withheld: str, family: str, held: set[str]) -> tuple[str, str]:
    """The rule an example's own analysis says it rests on -- or why there is none.

    THE KEY IS READ, NEVER ASSIGNED. Three things the regulation states decide
    it, and nothing else does:

    1. WHICH PARAGRAPH THE EXAMPLE ILLUSTRATES. Every examples paragraph opens
       by saying so -- "The following examples illustrate the application of
       this paragraph (j) only" -- and `family` is that letter, read off the
       lead-in by `examples`. A reference outside it ((d)(1), (e)(2)(ii)) is,
       by the regulation's own words, not what the example is illustrating.
    2. WHICH PATHS THE ANALYSIS NAMES. Every "under paragraph (...)" in the
       withheld sentences, verbatim.
    3. THAT A PARAGRAPH CONTAINS ITS SUBPARAGRAPHS. Where the analysis names
       (j), (j)(1)(iii) and (j)(2)(ii), the conclusion "not a betterment under
       this paragraph (j)" names the rule the two steps sit inside, so (j) is
       the one named path that covers the rest. This is the CFR's structure,
       not a ranking: nothing here prefers deeper or shallower.

    After that, exactly one named path must remain. Two that neither contains
    -- (k)(2) beside (k)(1)(iv), say -- is an example resting on two rules with
    no single one stated, and it is excluded by name rather than settled here.
    Deciding which of two rules "really" governs is judgement, and judgement
    written into an answer key is the mistake this record exists to refuse.
    """
    named = {p for p in cited_paths(withheld) if _parts(p)[0] == family}
    if not named:
        return "", "analysis names no paragraph of the rules it illustrates"
    covering = {p for p in named if not any(_under(p, q) for q in named)}
    if len(covering) > 1:
        return "", "analysis names more than one paragraph and none contains the rest"
    key = covering.pop()
    if key not in held:
        return "", "analysis names a paragraph the section does not contain"
    return key, ""


PROBLEMS_HEAD = """# Problems — the denominator

Every problem is a worked example from Treas. Reg. § {section}, carrying the
conclusion the regulation itself states. **The answers are not ours**, and that is
the point: a score against answers we wrote measures agreement, not correctness.

Generated by `tools/extract_ecfr.py` from the section's own XML, so the facts are
verbatim by construction rather than retyped. Do not hand-edit.

**The conclusion and the analysis are withheld from the facts.** Every sentence
in which the regulation announces its outcome, and every sentence in which it
applies a rule of this section by name, is stripped out and kept only where the
answer key is read from. Written the other way -- the whole example into `Facts`
-- a model needed only to copy the phrase that had decided the answer; and with
the analysis left in, it needed only to copy the paragraph the analysis named.
A stipulation ("Assume that ...") stays in the facts, because the regulation
posed the problem with it, and a problem whose stipulations name its own
governing paragraph is left out rather than shipped with the citation in it.

**The citation is the rule that governs, read from the regulation's own
analysis.** Each examples paragraph says which paragraph its examples
illustrate; the expected citation is the paragraph of that family the withheld
analysis names, and where it names several, the one that contains the rest.
An example whose analysis names no such paragraph, or two that neither
contains, is left out and counted **by name** below -- deciding which of two
rules "really" governs would be an answer key written by hand, which is the
mistake three earlier exclusions were made to avoid, inverted.

**An example that states two outcomes is not a problem.** § 1.263(a)-3(l)(3)
Example 4 holds that a cleanup is not an adaptation and that the regrading must be
capitalized. Reading only some of the regulation's spellings, an earlier version
saw one of them and recorded the opposite answer -- which would have scored a
correct response as `wrongly_absorbed`, manufacturing the one number that costs
something. Anything that cannot be reduced to a single scorable conclusion is left
out and counted below.

## The count, and every exclusion

| | |
|---|---|
| Examples in the section | **{found}** |
| Usable as problems | **{kept}** |
| Left out | **{dropped}** |

| Left out | Because |
|---|---|
{reasons}

### Left out at the citation step, by name

These examples state a scorable conclusion and would have been problems under
the first record. They are not problems now, because the rule they rest on
cannot be read from their analysis without judgement.

| Example | Because | Its analysis names |
|---|---|---|
{by_name}

## What a model gets for free

| Answer | Problems |
|---|---|
{spread}

**Always answering the most common one scores {baseline}.** That is the number any
run has to beat before it has shown anything, and it is printed here because a
scoreboard whose baseline is unstated reads as skill when it may be arithmetic.

| Citation | Problems |
|---|---|
{citation_spread}

**Always citing the most common one matches {citation_baseline}.** The index a
model cites from holds **{rules}** paragraphs for **{kept}** problems, so the
citation cannot be solved as an assignment puzzle -- the first record's 21-for-21
could, and was. Of the {kept} problems, **{facts_naming}** have facts that name
some paragraph of this section in a stipulation; none names its own citation.

**Nothing is dropped silently.** An example that leans on one not shown cannot be
answered from what the desk is given, one whose outcome is not stated in
capitalisation terms cannot be scored without inventing a conclusion, and one
whose analysis does not name the rule it rests on cannot be cited without
inventing a citation — which is the single thing this whole plugin exists to
prevent.

---

"""

EXTRACTED_HEAD = """# Extracted authority — Treas. Reg. § 1.263(a)-3

Public-domain text under 17 U.S.C. § 105, stored in full because `SOURCES.md`
records S1 as `may_store: full_text`. Every passage is checkable against eCFR at
the URL recorded there.

**An agent may write this file.** Every line is verifiable against a public
source, which is why it is separate from `positions/` — that store holds what the
firm decided, and there an agent only proposes.

**What is stored: the rules AND the worked examples, each marked.** Every
paragraph of the section outside its examples, at its full path — {elements}
elements opening {rules} paragraphs, marked `Kind: rule` — and every one of the
section's {n_examples} worked examples, complete with its conclusion, marked
`Kind: example`. A run-in heading such as "(c) Coordination with other
provisions of the Code—(1) In general." opens two paragraphs, so (c) is stored
as its heading and (c)(1) as the text that follows.

**Why the examples are here, and why the mark is not decoration.** They are the
best authority in this document for classifying a real entry: the government
applying its own rule to a fact pattern and stating the outcome. They are also
where `PROBLEMS.md` comes from, so a graded brain that could see them would be
handed its own answer key — which happened, and was solved as a matching puzzle
rather than by reasoning. So they are withheld by KIND at three choke points:
`corpus_lines` (what a graded prompt shows), `citation_index` (what a reply is
scored against) and `ask.brief_for_grading`. An answering desk sees everything;
a graded one sees the rules.

This paragraph said "Not one worked example is here" until 7 September 2026,
which was true of the file and wrong about the record: measured across six
regulations, the desks were missing more authority than they held.

**How the paths were reconstructed, and how that is checked.** The eCFR XML is
flat; nesting exists only in the label sequence. Three facts about the source
place every label without judgement: the CFR's level alphabets cycle, the fifth
and sixth levels are set in italics in the XML itself, and a label either
continues its level or opens the next. The section admits {readings} consistent
reading. It also cites {cited} of its own paragraph paths in full; {resolved}
resolve to a paragraph stored here and {dangling_n} do not — {dangling} — which
name paragraphs the section's text does not contain. Underdetermined elements,
excluded rather than placed by preference: {underdetermined}.

Generated by `tools/extract_ecfr.py`; do not hand-edit.

---

"""


def examples(xml_path: Path):
    r"""Walk the section in document order, tagging each example with its paragraph.

    THE PATH COMES FROM THE OUTLINE, NOT FROM THE LEAD-IN'S PROSE, and that is a
    correction made on 7 September 2026. This matched the lead-in with
    `^\((\d+)\) Examples?\..*?paragraph \(([a-z])\)` -- a numbered sub-paragraph
    that names its parent in words. § 1.263(a)-3 phrases nine of its ten lead-ins
    exactly so, which is why it went unnoticed.

    THE TENTH IS (g)(2)(ii), LETTERED RATHER THAN NUMBERED. The pattern did not
    match it, so `para` was never updated and its four examples stayed attached
    to the previous match, (f)(4), continuing that paragraph's numbering as
    Examples 7-10. (f) is leasehold improvements; those four are about removing
    columns and disposing of shingles under (g)(2), removal costs. They were
    cited to the wrong rule, and their own text -- "Assume the same facts as
    Example 1" -- pointed at the wrong example too.

    Nothing caught it because nothing could: all four are dropped as problems
    (two state no scorable conclusion, two lean on an example not shown), so the
    mis-citation reached the answer key nowhere. It reached the CORPUS the moment
    the examples began to be stored.

    Measured on other sections, the prose pattern was worse than wrong -- it was
    silent: 0 of 14 examples in § 1.162-3 (lead-in lettered "(h) Examples."), 0 of
    10 in § 1.280F-6 ("this paragraph", no letter to capture), 0 of 9 in § 1.62-2
    and 0 of 3 in § 1.274-5T. Reading the path off `outline()` depends on no
    phrasing at all, and reproduces all 117 of § 1.263(a)-3's examples with
    identical text and four corrected citations.
    """
    root = ET.parse(xml_path).getroot()
    paragraphs, _ = outline(xml_path)
    path = para = sub = None
    n = 0
    for child in root:
        text = "".join(child.itertext()).strip()
        if child.tag in ("P", "PSPACE"):
            flat = " ".join(text.split())
            # THE LAST paragraph this element opens. A run-in heading opens two
            # ("(c) Coordination ...—(1) In general."), and the examples that
            # follow belong to the second, not to the heading.
            hit = None
            for q in paragraphs:
                if q.text and q.text in flat:
                    hit = q
            if hit is not None and re.search(r"\bExamples?\b", flat[:80]):
                path, n = hit.label, 0
                para = hit.path[0] if hit.path else None
                sub = hit.path[1] if len(hit.path) > 1 else None
        elif child.tag == "EXAMPLE" and path:
            n += 1
            head = "".join(child.find("HED").itertext()).strip()
            # EVERY child except the heading, not just PSPACE. An example's
            # later paragraphs are <P> SIBLINGS of <PSPACE>, not children of it,
            # and 24 of the section's examples have them. Collecting only
            # PSPACE dropped the (ii) paragraph -- which is usually where the
            # conclusion lives -- so ten examples reached `classify` with their
            # fact pattern intact and their answer missing, and were counted as
            # stating no conclusion. Silent truncation again, and this time it
            # shrank the denominator rather than breaking anything visible.
            body = " ".join(
                " ".join("".join(kid.itertext()).split())
                for kid in child if kid.tag != "HED"
            )
            yield {
                "path": path, "para": para, "sub": sub, "n": n,
                "title": head.split(". ", 1)[-1] if ". " in head else head,
                "text": body,
            }


def corpus(xml_path: Path) -> dict:
    """The stored rules and the facts the header states about them.

    Kept apart from `build` so the numbers the extracted file prints about
    itself come from one place, and a test can rebuild them and compare.
    """
    paragraphs, underdetermined = outline(xml_path)
    held = {p.label for p in paragraphs}
    root = ET.parse(xml_path).getroot()
    cited = cited_paths("".join(root.itertext()))
    chains = [labels(c) for c in root if c.tag in ("P", "PSPACE")]
    return {
        "paragraphs": paragraphs,
        "underdetermined": underdetermined,
        "elements": len(chains),
        "readings": len(placements([[(l, it) for l, it, _ in ch] for ch in chains])),
        "cited": cited,
        "resolved": cited & held,
        "dangling": cited - held,
    }


def build(xml_path: Path, desk_dir: Path, *, section="1.263(a)-3",
          source_id="S1", checked: str | None = None):
    """Build the record. `checked` is the day the XML was taken from eCFR.

    IT IS NOT THE CLOCK, AND IT HAS NO DEFAULT. Defaulted to `date.today()`, the
    documented offline regeneration -- run against a COMMITTED fixture, touching
    no network -- restamped every passage with the day it happened to be run. An
    old snapshot would read as freshly verified, and the staleness report would
    call it fresh at exactly the moment the live regulation had moved. The one
    signal designed to catch a stale record, silenced by rebuilding it.

    So it is required, and it is a fact about the fetch rather than about the
    run: never invent a value, and refuse rather than default.

    Returns `(all_examples, kept, dropped, problems, passages)`. `passages` are
    the section's rule paragraphs AND every worked example, each marked with its
    `Kind`.

    THAT SECOND HALF WAS ABSENT UNTIL 7 SEPTEMBER 2026, and this docstring said
    "never the examples". The reason it said so is at the top of this file and is
    still true: a corpus holding the examples it is also GRADED on carries its
    own answer key, and the frontier row solved such a set as a matching puzzle.
    What was wrong was the remedy. Dropping them fixed grading and silently cost
    the answering side the best authority in the document -- measured at 223,804
    characters across six regulations, against a whole corpus of 261,740.

    So the examples are stored and MARKED, and `ask.brief_for_grading` withholds
    them by kind. One store, two readers. The count of passages still has no
    relation to the count of problems -- more so now, since every example is
    stored and only some become problems -- and a test still asserts it.
    """
    if not checked:
        raise ValueError(
            "checked is required: the date the XML was taken from eCFR, not the "
            "day this ran. A rebuild is not a re-verification."
        )
    _date_only(checked)
    today = checked
    paragraphs, _ = outline(xml_path)
    held = {p.label for p in paragraphs}
    all_ex = list(examples(xml_path))
    kept, dropped = [], []
    for e in all_ex:
        if DEPENDENT.search(e["text"]):
            dropped.append((e, "depends on an example not shown"))
            continue
        facts, withheld, verdict = split_conclusion(e["text"])
        if facts is None:
            dropped.append((e, verdict))          # `verdict` is the reason
            continue
        rule, why = governing(withheld, e["para"], held)
        if not rule:
            dropped.append(({**e, "named": sorted(cited_paths(withheld))}, why))
            continue
        # THE LEAK, ONE BOUNDARY DOWN. A stipulation stays in the facts, so a
        # stipulation could in principle name the very paragraph the model is
        # being scored on finding. It is refused here, at the boundary every
        # problem passes, rather than by a check on the file afterwards.
        if rule in facts:
            dropped.append(({**e, "named": [rule]},
                            "facts name the governing paragraph"))
            continue
        kept.append(({**e, "facts": facts, "answer": verdict, "rule": rule}, None))

    # `break_on_hyphens=False`, AND IT IS A CORRECTNESS FIX RATHER THAN A STYLE
    # ONE. textwrap breaks on hyphens by default, so a wrap landing inside
    # "load-carrying" stores it across two lines; `parse_passages` rejoins lines
    # with a space and the passage becomes "load- carrying", which is not what
    # the publisher printed. That passage can never tie out again, and the
    # tie-out is the only thing that would ever say so.
    #
    # Every passage stored before this change dodged it by luck -- no rule
    # paragraph happened to wrap inside a hyphenated word. Storing the worked
    # examples hit it six times immediately, on `(f)(4) Example 7` and five
    # others, and only a diff of the stored text against the section found it.
    wrap = lambda t: "\n".join(textwrap.wrap(t, 78, initial_indent="> ",
                                             subsequent_indent="> ",
                                             break_on_hyphens=False))
    # THE FULL PATH, not `(para)(sub)`. Those two are the first and second labels
    # and cannot express (g)(2)(ii), whose examples were cited to (f)(4) until
    # 7 September 2026. `examples()` carries the outline's own label now.
    example = lambda e: f"26 CFR {section}{e['path']} Example {e['n']}"

    problems = [
        f"## P{i} · {e['title']}\n\n"
        f"**Citation:** 26 CFR {section}{e['rule']}\n\n"
        f"**Example:** {example(e)}\n\n"
        f"**Answer:** {e['answer']}\n\n"
        f"**Facts:** {e['facts']}\n"
        for i, (e, _) in enumerate(kept, 1)
    ]
    passages = [
        f"## 26 CFR {section}{p.label}\n\n"
        f"**Source:** {source_id} · **Checked:** {today} · **Kind:** rule\n\n"
        f"{wrap(p.text)}\n"
        for p in paragraphs
    ]
    # EVERY EXAMPLE, COMPLETE, AND `all_ex` RATHER THAN `kept`. An example that
    # could not become a PROBLEM -- because it states two outcomes, or leans on
    # one not shown, or names no rule -- is still authority the government
    # published. Dropping it from the corpus for failing a scoring test would
    # confuse "we cannot grade this" with "this is not law".
    #
    # STORED WITH ITS CONCLUSION, which `scoreboard.py` already required: "The
    # desk's STORED authority is the same example complete -- conclusion
    # included -- because that is what the authority is, and the engine needs it
    # to verify." The PROBLEM withholds the conclusion; the passage does not.
    passages += [
        f"## {example(e)}\n\n"
        f"**Source:** {source_id} · **Checked:** {today} · **Kind:** example\n\n"
        f"{wrap(e['text'])}\n"
        for e in all_ex
    ]
    return all_ex, kept, dropped, problems, passages


def counts(all_ex, kept, dropped):
    """The denominator, and the reason for every exclusion."""
    reasons = {}
    for _, why in dropped:
        reasons[why] = reasons.get(why, 0) + 1
    spread, citations = {}, {}
    for e, _ in kept:
        spread[e["answer"]] = spread.get(e["answer"], 0) + 1
        citations[e["rule"]] = citations.get(e["rule"], 0) + 1
    by_name = [(e, why) for e, why in dropped if "named" in e]
    facts_naming = sum(1 for e, _ in kept if ANALYSIS.search(e["facts"]))
    return {"found": len(all_ex), "kept": len(kept), "dropped": len(dropped),
            "reasons": reasons, "spread": spread, "citations": citations,
            "by_name": by_name, "facts_naming": facts_naming}


def _baseline(spread: dict, kept: int) -> str:
    top = max(spread.values()) if spread else 0
    return f"{top} of {kept} ({top * 100 // kept}%)" if kept else "nothing"


def write(desk_dir: Path, problems, passages, c, corpus_facts, *,
          section="1.263(a)-3") -> None:
    """Write what `build` produced. Separate so `build` stays pure and testable.

    The documented command computed both collections and then printed counts
    without writing either, so `desk_dir` was accepted and ignored and the
    "reproducible regeneration" path regenerated nothing. A command that exits
    0 having done nothing is worse than one that fails.
    """
    desk_dir = Path(desk_dir)
    reasons = "\n".join(f"| {n} | {why} |" for why, n in sorted(c["reasons"].items()))
    spread = "\n".join(f"| {a} | {n} |" for a, n in sorted(c["spread"].items()))
    citation_spread = "\n".join(
        f"| 26 CFR {section}{r} | {n} |" for r, n in sorted(c["citations"].items()))
    by_name = "\n".join(
        f"| ({e['para']})({e['sub']}) Example {e['n']} · {e['title']} | {why} | "
        f"{', '.join(e['named']) or '(nothing)'} |"
        for e, why in c["by_name"]) or "| (none) | | |"
    (desk_dir / "PROBLEMS.md").write_text(
        PROBLEMS_HEAD.format(
            section=section, found=c["found"], kept=c["kept"],
            dropped=c["dropped"], reasons=reasons, by_name=by_name,
            spread=spread, baseline=_baseline(c["spread"], c["kept"]),
            citation_spread=citation_spread,
            citation_baseline=_baseline(c["citations"], c["kept"]),
            rules=len(corpus_facts["paragraphs"]),
            facts_naming=c["facts_naming"])
        + "\n---\n\n".join(problems), encoding="utf-8")
    extracted = desk_dir / "extracted"
    extracted.mkdir(exist_ok=True)
    (extracted / f"treas-reg-{section.replace('.', '-').replace('(', '').replace(')', '')}.md"
     ).write_text(EXTRACTED_HEAD.format(
        elements=corpus_facts["elements"],
        rules=len(corpus_facts["paragraphs"]),
        # COUNTED FROM WHAT WAS STORED, not from `all_ex`. The header is the
        # first thing a reader believes about this file, and a figure taken
        # from the intention rather than the artifact is how "190 documents,
        # all fine" got written about 190 unreadable ones.
        n_examples=sum("**Kind:** example" in x for x in passages),
        readings=corpus_facts["readings"],
        cited=len(corpus_facts["cited"]),
        resolved=len(corpus_facts["resolved"]),
        dangling_n=len(corpus_facts["dangling"]),
        dangling=", ".join(sorted(corpus_facts["dangling"])) or "none",
        underdetermined="; ".join(corpus_facts["underdetermined"]) or "none",
    ) + "\n---\n\n".join(passages), encoding="utf-8")


def _date_only(value: str) -> str:
    """A real day. The record's parser will refuse anything else on read."""
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"checked is {value!r}, not a date: {exc}") from exc
    return value


if __name__ == "__main__":                                  # pragma: no cover
    if len(sys.argv) < 4:
        sys.exit("usage: extract_ecfr.py <reg.xml> <desk-dir> <YYYY-MM-DD "
                 "the day the XML was taken from eCFR>")
    xml_path, desk_dir, checked = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    all_ex, kept, dropped, problems, passages = build(
        xml_path, desk_dir, checked=checked)
    c = counts(all_ex, kept, dropped)
    facts = corpus(xml_path)
    write(desk_dir, problems, passages, c, facts)
    print(f"found {c['found']} examples; kept {c['kept']}; left out {c['dropped']}")
    for why, n in sorted(c["reasons"].items()):
        print(f"  {n:>3}  {why}")
    for e, why in c["by_name"]:
        print(f"       ({e['para']})({e['sub']}) Example {e['n']} · {e['title']}: "
              f"{why} [{', '.join(e['named']) or 'nothing'}]")
    print(f"rules: {facts['elements']} elements opening {len(facts['paragraphs'])} "
          f"paragraphs; {len(facts['resolved'])} of {len(facts['cited'])} "
          f"self-citations resolve; dangling: "
          f"{', '.join(sorted(facts['dangling'])) or 'none'}; underdetermined: "
          f"{len(facts['underdetermined'])}")
    print(f"wrote {len(problems)} problems and {len(passages)} passages to {desk_dir}")
