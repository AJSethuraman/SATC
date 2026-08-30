"""The advisory half of the tenet linter. Prints. Never blocks.

WHY THIS IS A SEPARATE MODULE. The firm's rule, 27 August 2026:

  > A tenet a machine can check EXACTLY becomes a hard failure that blocks a
  > document from being sent. A tenet a machine can only guess at prints as an
  > advisory note. A tenet is promoted from advisory to blocking only after a
  > full cycle with no false positive.

`presend` holds the exact half. This holds the guesses, and holding them apart
is the point rather than tidiness: an advisory that can reach the exit code is
an advisory that will one day stop a real pack over a sentence a human would
have waved through, and the eight real gates get muted along with it. Nothing
here constructs a blocking `Finding`, and a test asserts that.

WHAT WAS MEASURED, AND WHAT WAS DROPPED. `docs/tenet-mechanization.md` ran
every candidate over the twelve templates and the 29 rendered packs and counted
the hits by hand. Thirteen tenets were dropped because a machine is the wrong
instrument for them -- T1 fired ten times and was wrong ten times; T28 fired
94 times and was wrong roughly 94 times. Ten survived as advisories, and each
carries the condition on which it may be promoted to blocking. Those conditions
live in ADVISORIES below and nowhere else, so promoting one is a deliberate
edit rather than something that drifts.

EVERY CHECK REPORTS ITS DENOMINATOR (SOFTWARE-TENETS S2). A note that says
"clean" having examined nothing is the exact failure this project keeps
finding, so each check returns what it LOOKED AT as well as what it found, and
the report prints the count whether or not anything fired.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import presend
from presend import Finding

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry"


# ── the promotion register ────────────────────────────────────────────────

@dataclass(frozen=True)
class Advisory:
    key: str
    tenet: str
    what: str
    promote_when: str


ADVISORIES: tuple[Advisory, ...] = (
    Advisory("A1", "T11", "certainty stated where only possibility is known",
             "one full cycle at zero. Best candidate in the set: the corpus is "
             "already swept, so a future hit is almost certainly new prose."),
    Advisory("A2", "T23b", "assurance vocabulary in a sentence with no negation",
             "one full cycle at zero, on this loose form only. The strict form "
             "(negator must precede the word) fired twice and was wrong twice."),
    Advisory("A3", "T20c", "client-facing sentence past 28 words",
             "never. Its job is to put the longest sentence in front of a "
             "human, not to gate a send; fourteen of its twenty-one hits are "
             "compliance sentences T23 forbids cutting."),
    Advisory("A4", "T19", "paragraph of more than three sentences",
             "never. Every raw hit was a compliance paragraph; after excluding "
             "those it fires on nothing."),
    Advisory("A5", "T8", "narrating our own tone, reasoning or inability",
             "one full cycle at zero, and only after the pattern has been "
             "stress-tested against a deliberate mutation."),
    Advisory("A6", "T15", "disapproving of the client's choice",
             "one full cycle at zero."),
    Advisory("A7", "T16", "advertising our own virtue",
             "never on client letters: the firm's own kept sentence "
             "\"costs nothing\" trips it. Scoped to the published fee "
             "schedule, where the tenet was aimed."),
    Advisory("A8", "T18", "a list label carrying two clauses",
             "one full cycle at zero."),
    Advisory("A9", "T2", "a list item repeating the heading above it",
             "never against template prose. Against the fee schedule's own "
             "phrases, one full cycle at zero."),
    Advisory("A10", "T21", "a clause cited from a letter this client "
                           "will not receive",
             "never. The bookkeeping letter lacks three sections the other "
             "three have, so the strict form is wrong by construction for a "
             "bookkeeping client."),
)

BY_KEY = {a.key: a for a in ADVISORIES}


def note(key: str, document: str, detail: str) -> Finding:
    """An advisory finding, and the only way this module makes one.

    `blocking=False` is not a default anybody may override here. Routing every
    finding through one constructor is what makes "nothing in this file can
    block" a property a test can assert rather than a claim in a docstring.
    """
    adv = BY_KEY[key]
    return Finding(f"{key}/{adv.tenet}", document, detail, blocking=False)


# ── sentences and words ───────────────────────────────────────────────────

# A full stop inside one of these does not end a sentence. Without the list the
# splitter cuts "U.S." in two and reports a four-word fragment as a sentence,
# which quietly deflates every length-based check below.
#
# THE LIST IS SHORT ON PURPOSE, AND IT WAS MEASURED. A first version carried
# the obvious company suffixes -- Inc., LLC, LLP, Co., Corp. Swept over the
# rendered corpus, the ONLY one of them that ever appears before a capital
# letter is "LLP.", twenty times, and all twenty are the real sentence end in
# "Thank you for choosing SAT-C LLP. This letter tells you what to send us."
# Every one of those twenty would have been glued to the sentence after it and
# read as one 30-word sentence that nobody wrote. An entry here has to earn its
# place by occurring mid-sentence in documents this firm actually sends.
_ABBREV = frozenset((
    "mr", "mrs", "ms", "dr", "jr", "sr", "u.s", "e.g", "i.e", "vs", "approx",
))
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[\"'(“]?[A-Z0-9])")


def _is_abbrev(piece: str) -> bool:
    tokens = piece.rstrip().rstrip("\"')”").split()
    if not tokens:
        return False
    last = tokens[-1].lower().strip("“”\"'()[],;:")
    return last.rstrip(".") in _ABBREV and last.endswith(".")


def sentences(text: str) -> list[str]:
    """Split readable text into sentences, conservatively.

    Conservative in ONE DIRECTION on purpose: where it is unsure it leaves two
    sentences joined rather than inventing a boundary. A missed boundary
    understates a paragraph's sentence count and overstates a sentence's word
    count -- both produce a note a human reads and dismisses. An invented
    boundary produces a note about a sentence that does not exist, which is how
    a checker loses its reader for good.
    """
    flat = " ".join(text.split())
    if not flat:
        return []
    out: list[str] = []
    for piece in _BOUNDARY.split(flat):
        if out and _is_abbrev(out[-1]):
            out[-1] = f"{out[-1]} {piece}"
        else:
            out.append(piece)
    return [s for s in (p.strip() for p in out) if s]


def words(sentence: str) -> list[str]:
    """Words as a reader counts them. Hyphenated compounds are one word, and a
    bare number or currency figure counts, because a client reads it."""
    return [w for w in re.split(r"\s+", sentence.strip()) if w.strip(".,;:()")]


_STOP = frozenset((
    "the", "and", "for", "you", "your", "our", "ours", "we", "us", "with",
    "that", "this", "these", "those", "from", "are", "is", "was", "were",
    "will", "not", "but", "its", "their", "have", "has", "had", "been",
    "what", "who", "how", "when", "which", "into", "out", "any", "all",
    "can", "may", "one", "than", "then", "them", "they", "each", "over",
    "such", "does", "did", "would", "could", "should", "about", "there",
    "here", "also", "both", "some", "more", "most", "only", "own", "same",
    "very", "get", "got", "put", "way", "use", "used",
))


def content_words(text: str) -> set[str]:
    """Lowercase words of three letters or more, stop list removed.

    The unit A9 counts overlap in. Numbers are excluded: a section numbered 03
    and a bullet naming 3 forms are not an echo of one another.
    """
    return {w for w in presend._normalize(text).split()
            if len(w) >= 3 and w not in _STOP and not w.isdigit()}


# THE BLOCKS A CLIENT READS AS SENTENCES. Paragraphs, bullets and the prose
# cells of a table -- not headings, not labels, not the masthead.
_BLOCK = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1>", re.S | re.I)


def prose_blocks(html: str) -> list[str]:
    """The paragraphs and bullets of a document, one string each.

    BLOCK BY BLOCK, NOT ONE FLAT STRING, and the difference is not cosmetic.
    Flattening the document first and splitting on full stops made the entire
    masthead -- firm name, address, document title, the client's name, the
    first heading -- into ONE 74-word "sentence", because none of it ends in a
    full stop. Measured on the 27 rendered packs that way, the 28-word check
    fired 162 times; the specification, counting by hand, found 21 across the
    twelve templates. Every one of the extra hits was a header block being
    read as prose.

    Headings are excluded on purpose too: a heading is a label, and holding it
    to a sentence-length rule is a check nobody will keep.
    """
    body = presend.merge._REF_BLOCK.sub(" ", html)
    out = []
    for _tag, raw in _BLOCK.findall(body):
        text = " ".join(presend._TAGS.sub(" ", raw).split())
        if text:
            out.append(text)
    return out


def readable_text(html: str) -> str:
    """Every prose block of a document, run together.

    For the phrase sweeps (A1, A2, A5, A6), which want the words and do not
    care where a paragraph ends.
    """
    return " ".join(prose_blocks(html))


# ── the documents to read ─────────────────────────────────────────────────

def _docs(pack: Path) -> list[Path]:
    return sorted(pack.glob("*.html"))


def doc_sentences(doc: Path) -> list[str]:
    """Every sentence of a document, block by block.

    One function, used by every sweep below, so that "how many sentences does
    this pack have" has exactly one answer. Five checks each splitting text
    their own way would report five different denominators for the same pack.
    """
    html = doc.read_text(encoding="utf-8", errors="replace")
    return [s for block in prose_blocks(html) for s in sentences(block)]


@dataclass
class Checked:
    """One advisory's result: what it found, and what it looked at."""
    key: str
    findings: list[Finding] = field(default_factory=list)
    examined: int = 0
    unit: str = "sentence"
    scope: str = ""

    def line(self) -> str:
        adv = BY_KEY[self.key]
        n, unit = self.examined, self.unit
        where = f" in {self.scope}" if self.scope else ""
        plural = "" if n == 1 else "s"
        if not self.examined:
            return (f"  SKIP   {self.key} ({adv.tenet}) {adv.what} — "
                    f"0 {unit}{plural}{where} to read, so nothing is known")
        found = len(self.findings)
        verdict = f"{found} to look at" if found else "none"
        return (f"  {'note ' if found else 'ok   '}  {self.key} ({adv.tenet}) "
                f"{adv.what} — {verdict}, across {n} {unit}{plural}{where}")


# ── A1 · certainty where only possibility is known (T11) ──────────────────

CERTAINTY = ("will likely", "is likely to", "typically", "generally",
             "in most cases", "usually", "in all cases", "always results in")


def a1_certainty(pack: Path) -> Checked:
    """Hedges that read as certainty, or certainty that should be a hedge.

    Cannot be exact, and the reason is a tax question rather than a text one:
    "that penalty is commonly charged per owner, per month" is a hedge that IS
    the fact, which T11 expressly allows. Telling the two apart means knowing
    whether the underlying claim is certain, which no regex knows.
    """
    got = Checked("A1", unit="sentence", scope="the pack")
    for doc in _docs(pack):
        for sentence in doc_sentences(doc):
            got.examined += 1
            flat = presend._normalize(sentence)
            for phrase in CERTAINTY:
                if re.search(rf"\b{re.escape(presend._normalize(phrase))}\b", flat):
                    got.findings.append(note(
                        "A1", doc.name,
                        f"says {phrase!r}: “{_clip(sentence)}”\n"
                        f"         If the hedge IS the fact, leave it. If the "
                        f"thing is certain, say it plainly."))
                    break
    return got


# ── A2 · assurance vocabulary with no negation in the sentence (T23b) ─────

ASSURANCE = ("audit", "audits", "audited", "auditing", "assurance",
             "attest", "attestation", "examination", "review engagement")

# The LOOSE form -- a negator anywhere in the sentence. Measured: loose fires
# 0 of 12; the strict form (negator must precede the banned word) fires 2 of
# 12 and is wrong both times, on "If a lender specifically requires audited or
# reviewed statements, that is a separate engagement". The whole gap between
# the two is negation vocabulary tuned to this corpus, which is the definition
# of a guess.
NEGATION = ("not", "no", "never", "cannot", "nor", "neither", "without",
            "separate engagement", "separately quoted", "separately")


def a2_assurance(pack: Path) -> Checked:
    got = Checked("A2", unit="sentence", scope="the pack")
    for doc in _docs(pack):
        for sentence in doc_sentences(doc):
            got.examined += 1
            flat = presend._normalize(sentence)
            hit = next((w for w in ASSURANCE
                        if re.search(rf"\b{re.escape(w)}\b", flat)), None)
            if not hit:
                continue
            if any(re.search(rf"\b{re.escape(n)}\b", flat) for n in NEGATION):
                continue
            got.findings.append(note(
                "A2", doc.name,
                f"uses {hit!r} outside a negation: “{_clip(sentence)}”\n"
                f"         The floor allows these words only where the "
                f"sentence says we do NOT do the thing."))
    return got


# ── A3 · the longest sentences (T20c) ─────────────────────────────────────

LONG_SENTENCE = 28
LONG_SHOWN = 5


def a3_long_sentences(pack: Path) -> Checked:
    """The five longest sentences past the cap, longest first.

    TOP FIVE, NOT ALL, and that is the whole design. Twenty-one sentences in
    the twelve templates are past 28 words and at least fourteen are
    compliance-floor sentences T23 forbids cutting. A note listing all
    twenty-one is a note nobody finishes reading; a note naming the worst five
    puts the 50-word officer-compensation sentence where a human sees it.
    """
    got = Checked("A3", unit="sentence", scope="the pack")
    over: list[tuple[int, str, str]] = []
    for doc in _docs(pack):
        for sentence in doc_sentences(doc):
            got.examined += 1
            n = len(words(sentence))
            if n > LONG_SENTENCE:
                over.append((n, doc.name, sentence))
    over.sort(key=lambda t: -t[0])
    shown = over[:LONG_SHOWN]
    for n, name, sentence in shown:
        got.findings.append(note(
            "A3", name,
            f"{n} words: “{_clip(sentence, 200)}”"))
    if len(over) > len(shown):
        got.findings.append(note(
            "A3", "(pack)",
            f"{len(over) - len(shown)} more sentence(s) past "
            f"{LONG_SENTENCE} words are not listed. Longest first; the "
            f"tail is mostly compliance wording that stays."))
    return got


# ── A4 · paragraphs of more than three sentences (T19) ────────────────────

PARA_SENTENCES = 3
_PARA = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)


def _compliance_groups() -> list[list[list[str]]]:
    """The keyword groups `required.yaml` holds, as the exclusion list.

    DERIVED, NOT RESTATED (SOFTWARE-TENETS S6). The paragraphs T23 protects are
    exactly the paragraphs the compliance floor requires, and that list already
    exists in one place. A second hand-written list of protected paragraphs
    would be a second thing to keep in step, and it would fall behind.
    """
    path = REGISTRY / "required.yaml"
    if not path.exists():
        return []
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [entry.get("must_contain_all") or []
            for entry in (spec.get("required") or [])]


def _is_compliance(text: str, groups: list[list[list[str]]]) -> bool:
    flat = presend._normalize(text)
    return any(groups_all and all(
        any(presend._normalize(word) in flat for word in group)
        for group in groups_all) for groups_all in groups)


def a4_long_paragraphs(pack: Path) -> Checked:
    """Paragraphs that carry more than a decision.

    EVERY RAW HIT ON THIS CORPUS IS A COMPLIANCE PARAGRAPH, which is why the
    exclusion is the check. Unexcluded it fires on the billing-and-suspension
    paragraph of every engagement letter -- 27 times over the 27 packs -- and
    the fix a preparer would have to make is to delete a sentence T23 forbids
    deleting. A check whose only advice is "break a rule" is a check that gets
    muted, and it takes the exact gates with it.
    """
    got = Checked("A4", unit="paragraph", scope="the pack")
    groups = _compliance_groups()
    protected = 0
    for doc in _docs(pack):
        html = doc.read_text(encoding="utf-8", errors="replace")
        body = presend.merge._REF_BLOCK.sub(" ", html)
        for raw in _PARA.findall(body):
            text = " ".join(presend._TAGS.sub(" ", raw).split())
            if not text:
                continue
            got.examined += 1
            if _is_compliance(text, groups):
                protected += 1
                continue
            n = len(sentences(text))
            if n > PARA_SENTENCES:
                got.findings.append(note(
                    "A4", doc.name,
                    f"{n} sentences in one paragraph: "
                    f"“{_clip(text, 160)}”\n"
                    f"         A section states the decision; the reasoning "
                    f"and the edge cases usually belong somewhere else."))
    if protected:
        got.scope += f" ({protected} compliance paragraph(s) left alone)"
    return got


# ── A5 · narrating our own tone or inability (T8) ─────────────────────────

# Tuned to MISS "we cannot transmit anything until the signed authorization is
# back with us" -- a fact about the law, not a narration of our inability. A
# looser `we cannot` catches it and is wrong. Saying the pattern is tuned to
# miss that sentence is another way of saying it is tuned to this corpus,
# which is why it advises rather than blocks.
SELF_NARRATION = ("we cannot tell", "we are unable to", "we have no way of",
                  "we have no way to", "as a courtesy", "to be clear",
                  "for the avoidance of doubt", "not a brush off",
                  "please understand", "we appreciate", "we want to be")


def a5_self_narration(pack: Path) -> Checked:
    return _phrase_sweep(
        pack, "A5", SELF_NARRATION,
        "narrates our own tone or inability",
        "State what happens instead. The reader does not need our posture.")


# ── A6 · disapproving of the client's choice (T15) ────────────────────────

DISAPPROVAL = ("we would not advise", "we do not advise",
               "we would not recommend", "we do not recommend",
               "we recommend against", "not advisable", "unwise",
               "you should not", "it may not be secure",
               "we strongly advise", "we strongly urge")


def a6_disapproval(pack: Path) -> Checked:
    return _phrase_sweep(
        pack, "A6", DISAPPROVAL,
        "disapproves of the client's choice",
        "Their choice, our limit: say what we will and will not do. "
        "“at your own risk” is the form the firm settled on.")


def _phrase_sweep(pack: Path, key: str, phrases: tuple[str, ...],
                  what: str, fix: str) -> Checked:
    got = Checked(key, unit="sentence", scope="the pack")
    for doc in _docs(pack):
        for sentence in doc_sentences(doc):
            got.examined += 1
            flat = presend._normalize(sentence)
            for phrase in phrases:
                if presend._normalize(phrase) in flat:
                    got.findings.append(note(
                        key, doc.name,
                        f"{what} — {phrase!r}: “{_clip(sentence)}”\n"
                        f"         {fix}"))
                    break
    return got


# ── A7 · advertising our own virtue (T16) ─────────────────────────────────

VIRTUE = ("free of charge", "at no cost", "no extra charge",
          "no additional charge", "costs nothing", "we never charge",
          "we pride", "at our own expense", "we absorb", "happy to")


def a7_virtue(extra: Path | None = None) -> Checked:
    """Scoped to the published fee schedule, and NOT to client letters.

    T16 killed a "$0 amendment" line because it read as a marketing claim on a
    PUBLIC page. The same words in one client's own letter, about one specific
    favour, were fine -- the firm's own kept sentence is "Reading one and
    telling you what it actually says costs nothing." Run over client letters
    this check flags copy the firm wrote and approved, so it does not run over
    them.

    `extra` takes a second file to sweep -- a published price page, when
    somebody wants one swept -- without this module holding a path into another
    project's folder.
    """
    got = Checked("A7", unit="published phrase", scope="the fee schedule")
    targets: list[tuple[str, str]] = []

    path = REGISTRY / "fee-schedule.yaml"
    if path.exists():
        spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for phrase in (spec.get("phrases") or {}).values():
            if isinstance(phrase, str):
                targets.append(("fee-schedule.yaml", phrase))
        for key, entry in (spec.get("assumed") or {}).items():
            if not isinstance(entry, dict):
                continue
            for field_name in ("label", "assumes", "trigger"):
                value = entry.get(field_name)
                if isinstance(value, str):
                    targets.append((f"fee-schedule.yaml:{key}", value))

    if extra is not None and Path(extra).exists():
        text = Path(extra).read_text(encoding="utf-8", errors="replace")
        for sentence in sentences(presend._TAGS.sub(" ", text)):
            targets.append((Path(extra).name, sentence))
        got.scope += f" and {Path(extra).name}"

    for where, text in targets:
        got.examined += 1
        flat = presend._normalize(text)
        for phrase in VIRTUE:
            if presend._normalize(phrase) in flat:
                got.findings.append(note(
                    "A7", where,
                    f"advertises a kindness — {phrase!r}: "
                    f"“{_clip(text)}”\n"
                    f"         Say the price. Behaving well is not a "
                    f"selling point on a published page."))
                break
    return got


# ── A8 · a list label carrying two clauses (T18) ──────────────────────────

_TWO_CLAUSES = re.compile(r"[;]|\.\s+\S")


def a8_two_clause_labels() -> Checked:
    """A request label is a noun phrase. Two clauses in one is the shape that
    produced the tenet: "The ID only if we have not seen it before. We need the
    numbers, not the cards."

    THE CONJUNCTION FORM WAS DROPPED, deliberately. "Rental income and expenses
    for each property", "Your business income and expenses" and "Farm income
    and expenses" are each one ask about one thing, and a check that split them
    would be wrong three times out of three on the corpus as it stands.
    """
    got = Checked("A8", unit="request label", scope="document-requests.yaml")
    path = REGISTRY / "document-requests.yaml"
    if not path.exists():
        return got
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for entry in _walk_requests(spec):
        label = entry.get("document")
        if not isinstance(label, str) or not label.strip():
            continue
        got.examined += 1
        if _TWO_CLAUSES.search(label.strip().rstrip(".")):
            got.findings.append(note(
                "A8", entry.get("id") or "document-requests.yaml",
                f"two clauses in one label: “{_clip(label)}”\n"
                f"         A label is a noun phrase. The second clause is "
                f"usually a `why:` or a `note:`."))
    return got


def _walk_requests(node) -> list[dict]:
    """Every mapping with a `document:` key, wherever the file nests it.

    Walks rather than reaching for a known path: the registry has been
    reshaped twice, and a check that indexes into one shape reports zero
    labels examined the day it changes -- which reads as clean.
    """
    out: list[dict] = []
    if isinstance(node, dict):
        if "document" in node:
            out.append(node)
        for value in node.values():
            out += _walk_requests(value)
    elif isinstance(node, list):
        for value in node:
            out += _walk_requests(value)
    return out


# ── A9 · a list item repeating the heading above it (T2) ──────────────────

# A heading needs at least this many content words before "the bullet repeats
# the whole heading" means anything. "What this estimate assumes" has two --
# {estimate, assumes} -- and that is the heading the real failure was under.
ECHO_WORDS = 2
_HEADING_TEXT = re.compile(
    r'<h[1-6][^>]*>(.*?)</h[1-6]>|<div class="h"[^>]*>(.*?)</div>', re.S | re.I)
_ITEM = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S | re.I)


def a9_heading_echo(pack: Path) -> Checked:
    """A bullet that says its own heading back.

    LIST ITEMS ONLY, NEVER PROSE. Against prose this fires once on the corpus
    and is wrong: a section headed "Filing the paper returns" whose first
    sentence must say "filing these returns is your responsibility" is a
    repetition doing a job. The failure that actually happened was five
    estimate bullets each opening "this estimate assumes" under a heading
    reading "What this estimate assumes" -- a list, under a heading.
    """
    got = Checked("A9", unit="list item under a heading", scope="the pack")
    short = 0
    for doc in _docs(pack):
        html = presend.merge._REF_BLOCK.sub(
            " ", doc.read_text(encoding="utf-8", errors="replace"))
        for heading, items in _sections_with_items(html):
            hw = content_words(heading)
            if len(hw) < ECHO_WORDS:
                # "01 Questions" cannot be echoed in any useful sense. Counted
                # rather than dropped: a run where every heading was too short
                # examined nothing, and must not read as clean.
                short += len(items)
                continue
            for item in items:
                got.examined += 1
                if hw <= content_words(item):
                    got.findings.append(note(
                        "A9", doc.name,
                        f"a bullet says its whole heading back — "
                        f"“{_clip(heading, 60)}”\n"
                        f"         “{_clip(item, 120)}”\n"
                        f"         The heading has already said it. This is "
                        f"the five estimate bullets that each opened “this "
                        f"estimate assumes”."))
    if short:
        got.scope += (f" ({short} item(s) under a heading too short to echo)")
    return got


def _sections_with_items(html: str) -> list[tuple[str, list[str]]]:
    """(heading text, the list items that follow it) for each heading."""
    out: list[tuple[str, list[str]]] = []
    marks = [(m.start(), " ".join(presend._TAGS.sub(
        " ", m.group(1) or m.group(2) or "").split()))
        for m in _HEADING_TEXT.finditer(html)]
    for i, (start, heading) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(html)
        items = [" ".join(presend._TAGS.sub(" ", raw).split())
                 for raw in _ITEM.findall(html[start:end])]
        out.append((heading, [t for t in items if t]))
    return out


# ── A10 · a clause cited from a letter this client will not receive (T21) ─

def a10_strict_citations(pack: Path) -> Checked:
    """The strict half of the citation check.

    `presend.cited_clauses` resolves a cited clause name against the UNION of
    the four engagement letters and blocks when nothing has it. That is exact:
    a name no letter carries is a broken pointer whoever the client is.

    This asks the stricter question -- does the name resolve in the letter THIS
    pack actually contains? -- and it cannot block, because it is wrong by
    construction for a bookkeeping client: the bookkeeping letter genuinely
    lacks three sections the other three carry, so a delivery letter citing
    "Your deadline, and extensions" beside it is a real mismatch on some packs
    and a non-issue on others. A human reads the note and knows which.
    """
    got = Checked("A10", unit="cited clause", scope="the pack")
    here = _pack_section_names(pack)
    if not here:
        return got
    for doc in _docs(pack):
        html = presend.merge._REF_BLOCK.sub(
            " ", doc.read_text(encoding="utf-8", errors="replace"))
        for match in presend._CITE.finditer(html):
            got.examined += 1
            name = presend._clause_name(match.group(1))
            if name not in here:
                got.findings.append(note(
                    "A10", doc.name,
                    f"cites “{match.group(1).strip()}”, which is in "
                    f"no engagement letter IN THIS PACK.\n"
                    f"         It resolves against the four letters as a set, "
                    f"so it is not a broken pointer — but this client will "
                    f"not have the letter that carries it."))
    return got


def _pack_section_names(pack: Path) -> set[str]:
    """Section headings of the engagement letters actually in this pack."""
    out: set[str] = set()
    for doc in _docs(pack):
        if "engagement" not in doc.name.lower():
            continue
        html = doc.read_text(encoding="utf-8", errors="replace")
        # presend's regex, not a second one: it strips the `<span class="n">`
        # section number, and a name that reads "01 fees and billing" matches
        # no citation anywhere. Two regexes for one job disagree eventually
        # (SOFTWARE-TENETS S3); this one has a test behind it already.
        for head in presend._H2_TEXT.findall(html):
            out.add(presend._clause_name(head))
    return out


# ── the run ───────────────────────────────────────────────────────────────

# Stripping a tag leaves a space where the tag was, so "<b>choose</b>." comes
# out as "choose .". Harmless to every check -- none of them counts punctuation
# -- but the QUOTED sentence is what a preparer reads, and a note that misquotes
# the document by a space is a note they have to go and check.
_LOOSE_PUNCT = re.compile(r"\s+([.,;:!?])")


def _clip(text: str, limit: int = 120) -> str:
    flat = _LOOSE_PUNCT.sub(r"\1", " ".join(text.split()))
    return flat if len(flat) <= limit else flat[:limit - 1].rstrip() + "…"


def review(pack: Path, *, extra_published: Path | None = None) -> list[Checked]:
    """Every advisory, on one pack, in the order they were specified."""
    return [
        a1_certainty(pack),
        a2_assurance(pack),
        a3_long_sentences(pack),
        a4_long_paragraphs(pack),
        a5_self_narration(pack),
        a6_disapproval(pack),
        a7_virtue(extra_published),
        a8_two_clause_labels(),
        a9_heading_echo(pack),
        a10_strict_citations(pack),
    ]


def findings(checks: list[Checked]) -> list[Finding]:
    return [f for c in checks for f in c.findings]


def format_notes(checks: list[Checked]) -> str:
    """What the advisories say out loud.

    Prints every check's denominator whether or not it fired, then the notes
    themselves. A check that examined nothing prints SKIP, never ok: "0 of 0
    clean" is the sentence this whole project exists to stop producing.
    """
    out = [c.line() for c in checks]
    body = [f for c in checks for f in c.findings]
    if body:
        out.append("")
        out += [f.line() for f in body]
        out.append("")
        out.append("  None of the above blocks anything. They are readings, "
                   "not rulings —")
        out.append("  the exit code belongs to the eight checks that are "
                   "exact.")
    return "\n".join(out)
