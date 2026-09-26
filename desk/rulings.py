"""The desk asks the firm to rule, and records the answer itself.

THE FIRM, 26 September 2026, twice in one exchange. On POS7, which an
independent reader had found disallowing what its own regulation allows:

    "is this not something i would expect the desk to ask me so it can record
     the right answer?"

and on the question of which plain words should reach a paragraph the law
words differently:

    "why wouldn't the desk send me a notification asking me to rule on
     something and record it itself"

Both findings had reached the firm the long way -- a doer noticed, reported to
the session that builds the desk, which relayed it in chat. The desk had the
channel the whole time (`notifying` pushes one line, `reply_in` reads the reply,
`unsupported.settle` files it) and was built so that a reply could close a
question and never change what the desk holds. That was the right rule for a
QUESTION. It is the wrong rule for a RULING: the firm's reply to a ruling is
the yes, and making them say it twice -- once to the desk and again on a pull
request -- is the gap they named.

WHAT THE DESK RULES ON, AND WHAT IT DOES NOT. `findings` is mechanical and
reads only the record: a paragraph admitted to answer a question that the
question does not reach, and a position stating a figure the words it rests on
do not contain. The desk model PROPOSES the fix -- which words, what wording --
and the engine checks the proposal would do what it says before anything is
sent. The firm DISPOSES. Nothing here decides what the law is.

WHAT A RULING CHANGES.

    reach      the ruled words bring the paragraph into every brief whose
               question contains all of them, labelled as the firm's ruling.
               Nothing is ranked lower and no text is rewritten.
    position   the position's wording and what it rests on are replaced, and
               `Ruled:` records the firm's reply verbatim.

A reply of "no" is a ruling too: the finding is recorded as answered and is
not asked again.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import notifying
import pool
import record

RULINGS_FILE = "RULINGS.md"
QUEUE_ENV = "SATC_DESK_RULINGS"
KINDS = ("reach", "position")

#: A figure a position may state: an amount, a percentage, a period. These are
#: the claims a reader can check against a quotation character by character,
#: and the ones that did the damage -- POS7's "50 percent" is in no word it
#: rests on, and applied as written it disallows what the regulation allows.
FIGURE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:percent\b|%)"
    r"|\b\d+\s*(?:months?|days?|years?)\b", re.I)


def _figure(text: str) -> str:
    """One spelling for one figure: `50 percent`, `50%` and `50  percent` agree,
    and `$50` stays a different figure from `50%`."""
    return re.sub(r"[\s,]", "", text.lower().replace("percent", "%"))


def unsupported_figures(position) -> tuple[str, ...]:
    """The figures a position states that no word it rests on contains."""
    quoted = {_figure(f) for _c, words in getattr(position, "rests_on", ())
              for f in FIGURE.findall(words)}
    out = []
    for f in FIGURE.findall(position.position):
        if _figure(f) not in quoted and f not in out:
            out.append(f)
    return tuple(out)


@dataclass(frozen=True)
class Finding:
    """Something the record shows the firm has to rule on."""
    kind: str
    #: The paragraph (reach) or the position id (position).
    subject: str
    #: One line, the finding in the desk's words. It is what the firm reads.
    why: str
    #: The question that missed (reach) -- verbatim, it is the evidence.
    asked_by: str = ""


@dataclass(frozen=True)
class Ruling:
    """One ruling the firm has made, as the record holds it."""
    id: str
    kind: str
    subject: str
    ruled: str
    asked: str
    reply: str
    #: reach: the ruled words, each a phrase every word of which must be in a
    #: question for it to bring `subject`. Empty when the firm said no.
    reaches_on: tuple = ()
    #: position: `amended` or `upheld`.
    outcome: str = ""


_HEAD = re.compile(r"^## (R\d+) · (.+)$", re.M)


def _field(block: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*[ \t]*(.*)$", block, re.M)
    return m.group(1).strip() if m else ""


def _quoted(block: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*\s*\n\n((?:> ?.*\n?)+)", block, re.M)
    if not m:
        return ""
    return "\n".join(l[2:] if l.startswith("> ") else l[1:]
                     for l in m.group(1).rstrip("\n").split("\n"))


def parse(text: str) -> tuple[Ruling, ...]:
    """RULINGS.md. Refuses an entry it cannot read -- a ruling dropped here is
    the firm's word ignored, which is worse than a ruling never asked for."""
    out = []
    heads = list(_HEAD.finditer(text))
    for i, h in enumerate(heads):
        block = text[h.end():heads[i + 1].start() if i + 1 < len(heads) else None]
        rid, subject = h.group(1), h.group(2).strip()
        kind = re.search(r"\*\*Kind:\*\* (\w+)", block)
        ruled = re.search(r"\*\*Ruled:\*\* (\d{4}-\d{2}-\d{2})", block)
        if not kind or kind.group(1) not in KINDS or not ruled:
            raise record.RecordError(
                f"{RULINGS_FILE} {rid}: needs '**Kind:** reach|position · "
                f"**Ruled:** YYYY-MM-DD'")
        reply = _quoted(block, "Reply")
        if not reply.strip():
            raise record.RecordError(f"{RULINGS_FILE} {rid}: no reply recorded")
        out.append(Ruling(
            id=rid, kind=kind.group(1), subject=subject, ruled=ruled.group(1),
            asked=_quoted(block, "Asked"), reply=reply,
            reaches_on=tuple(p.strip() for p in
                             _field(block, "Reaches on").split(";") if p.strip()),
            outcome=_field(block, "Outcome")))
    ids = [r.id for r in out]
    if len(ids) != len(set(ids)):
        raise record.RecordError(f"{RULINGS_FILE} numbers a ruling twice")
    return tuple(out)


def load(corpus: Path) -> tuple[Ruling, ...]:
    f = Path(corpus) / RULINGS_FILE
    return parse(f.read_text(encoding="utf-8")) if f.is_file() else ()


def brought_by(question: str, rulings) -> tuple:
    """`((ruling, citation), ...)`: paragraphs the firm ruled this question reaches.

    EVERY WORD OF A RULED PHRASE MUST BE IN THE QUESTION, the rule `dec-reach`
    already uses, and for its reason: a phrase firing on one of its words would
    fire "convenience fee" on every question saying "fee".
    """
    asked = set(pool.terms(question))
    out = []
    for r in rulings:
        if r.kind != "reach":
            continue
        for phrase in r.reaches_on:
            need = set(pool.terms(phrase))
            if need and need <= asked:
                out.append((r, r.subject))
                break
    return tuple(out)


#: How deep a question may reach a paragraph and still count as reaching it:
#: the eight a brief prints. Not chosen here -- it is `ask.consult`'s `limit`.
DEPTH = 8


def findings(corpus: Path) -> tuple[Finding, ...]:
    """What the record shows the firm has to rule on, and nothing it has ruled.

    READS THE RECORD AND NOTHING ELSE. No model, no network, no queue: the same
    corpus gives the same findings, so a test can hold the list and a change
    to it is a change somebody made.
    """
    import ask
    desk = record.load(corpus)
    ruled = {(r.kind, r.subject) for r in load(corpus)}
    out = []
    for s in desk.sources:
        for cit, question in s.admitted_for:
            if ("reach", cit) in ruled:
                continue
            got = [f.held.citation for f in ask.looked(question, corpus,
                                                       limit=DEPTH)]
            if cit in got:
                continue
            everything = ask.looked(question, corpus, limit=10_000)
            rank = next((i + 1 for i, f in enumerate(everything)
                         if f.held.citation == cit), 0)
            where = f"ranked it {rank}" if rank else "did not reach it at all"
            out.append(Finding(
                kind="reach", subject=cit, asked_by=question,
                why=(f"admitted to answer a question that {where}; a brief "
                     f"shows {DEPTH}")))
    for q in desk.positions:
        if q.proposed or q.is_policy or q.ruled or ("position", q.id) in ruled:
            continue
        missing = unsupported_figures(q)
        if missing:
            out.append(Finding(
                kind="position", subject=q.id,
                why=(f"{q.id} states {', '.join(missing)}; the words it rests "
                     f"on do not")))
    return tuple(out)


# ---------------------------------------------------------------- the queue


def default_queue() -> Path:
    """Where an open ruling waits for the firm: OUTSIDE the plugin, like the
    parked-question queue, and for the reasons `unsupported.default_queue`
    gives -- an update must not take the firm's pending questions with it."""
    override = os.environ.get(QUEUE_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".satc" / "desk" / "rulings" / "OPEN.md"


@dataclass(frozen=True)
class Asked:
    """A ruling put to the firm and not yet recorded in the corpus."""
    id: str
    kind: str
    subject: str
    why: str
    #: What the desk proposes. reach: phrases, semicolon-separated.
    #: position: the new wording, then a line `Rests on:` and its lines.
    proposed: str
    asked_by: str = ""
    recorded: str = ""
    answer: str = ""
    answered: str = ""

    def question(self) -> str:
        """The one line the firm is asked. Short: it rides on a notification."""
        if self.kind == "reach":
            return (f"should questions saying \"{self.proposed}\" bring up "
                    f"{self.subject}? Reply yes, no, or your words")
        return (f"{self.why}. Reply yes to the desk's new wording, no to keep "
                f"it, or your own")


def _q(text: str) -> list[str]:
    return [("> " + l) if l else ">" for l in text.split("\n")]


def _render_asked(a: Asked) -> str:
    lines = [f"## {a.id} · {a.subject}", "",
             f"**Kind:** {a.kind} · **Recorded:** {a.recorded}", "",
             "**Why:**", "", *_q(a.why), "",
             "**Proposed:**", "", *_q(a.proposed)]
    if a.asked_by:
        lines += ["", "**Asked by:**", "", *_q(a.asked_by)]
    if a.answered:
        lines += ["", f"**Answered:** {a.answered}", "",
                  "**Answer:**", "", *_q(a.answer)]
    return "\n".join(lines) + "\n"


def _parse_asked(text: str) -> list[Asked]:
    out = []
    heads = list(_HEAD.finditer(text))
    for i, h in enumerate(heads):
        block = text[h.end():heads[i + 1].start() if i + 1 < len(heads) else None]
        kind = re.search(r"\*\*Kind:\*\* (\w+) · \*\*Recorded:\*\* (\S+)", block)
        if not kind:
            raise record.RecordError(f"ruling queue {h.group(1)}: unreadable")
        answered = re.search(r"^\*\*Answered:\*\* (\S+)", block, re.M)
        out.append(Asked(
            id=h.group(1), kind=kind.group(1), subject=h.group(2).strip(),
            recorded=kind.group(2), why=_quoted(block, "Why"),
            proposed=_quoted(block, "Proposed"), asked_by=_quoted(block, "Asked by"),
            answer=_quoted(block, "Answer"),
            answered=answered.group(1) if answered else ""))
    return out


_PREAMBLE = ("# Rulings the desk has asked the firm for\n\n"
             "Written by the desk. An answered entry is recorded into the "
             "corpus by `rulings.record`.\n\n")


def _write(path: Path, entries) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_PREAMBLE + "\n---\n\n".join(_render_asked(e) for e in entries),
                    encoding="utf-8")


def queued(path: Path) -> list[Asked]:
    path = Path(path)
    return _parse_asked(path.read_text(encoding="utf-8")) if path.exists() else []


def _next_id(queue: Path, corpus: Path) -> str:
    used = [int(x.id[1:]) for x in queued(queue)] + \
           [int(r.id[1:]) for r in load(corpus)]
    return f"R{max(used, default=0) + 1}"


def _split_proposal(proposed: str) -> tuple[str, str]:
    """A position proposal: `(wording, rests-on lines)`."""
    text, _, rests = proposed.partition("\nRests on:")
    return text.strip(), rests.strip()


def check(finding: Finding, proposed: str, corpus: Path) -> None:
    """Refuse a proposal that would not do what it says. The model proposes;
    this disposes, before the firm is ever asked."""
    proposed = proposed.strip()
    if not proposed:
        raise ValueError(f"{finding.subject}: an empty proposal asks the firm "
                         f"to rule on nothing")
    if finding.kind == "reach":
        asked = set(pool.terms(finding.asked_by))
        for phrase in (p.strip() for p in proposed.split(";") if p.strip()):
            short = set(pool.terms(phrase)) - asked
            if short:
                raise ValueError(
                    f"{finding.subject}: \"{phrase}\" would not bring it up for "
                    f"the question that missed it -- that question does not "
                    f"say {', '.join(sorted(short))}")
        return
    wording, rests = _split_proposal(proposed)
    try:
        _amended(corpus, finding.subject, wording, rests, ruled="",
                 check_only=True)
    except record.RecordError as exc:
        raise ValueError(f"{finding.subject}: that proposal would not load -- "
                         f"{exc}") from exc


def ask(finding: Finding, proposed: str, *, queue: Path, corpus: Path,
        on: str = "") -> tuple[Asked, str]:
    """File the ruling and return it with the exact line to push.

    ONE OPEN RULING PER SUBJECT. Asking twice about one paragraph is two
    answers to reconcile, and the firm would be right to ask which counts.
    """
    check(finding, proposed, corpus)
    entries = queued(queue)
    if any(e.subject == finding.subject and not e.answered for e in entries):
        raise ValueError(f"{finding.subject} is already waiting on the firm")
    entry = Asked(id=_next_id(queue, corpus), kind=finding.kind,
                  subject=finding.subject, why=finding.why,
                  proposed=proposed.strip(), asked_by=finding.asked_by,
                  recorded=on or date.today().isoformat())
    _write(Path(queue), entries + [entry])
    return entry, notifying.line(entry.question(), ref=entry.id,
                                 verb="Desk asks you to rule")


def settle(queue: Path, rid: str, answer: str, *, on: str = "") -> Asked:
    """The firm's reply, verbatim, against one open ruling."""
    answer = answer.strip()
    if not answer:
        raise record.RecordError(f"{rid}: an empty answer rules on nothing")
    entries = queued(queue)
    known = {e.id: e for e in entries}
    if rid not in known:
        raise record.RecordError(f"{rid} is not an open ruling")
    if known[rid].answered:
        raise record.RecordError(f"{rid} was answered on {known[rid].answered}")
    done = replace(known[rid], answer=answer,
                   answered=on or date.today().isoformat())
    _write(Path(queue), [done if e.id == rid else e for e in entries])
    return done


# --------------------------------------------------------- into the record


_YES_WORDS = {"yes", "yep", "yeah", "y", "ok", "okay", "approve", "approved",
              "agree", "agreed", "sure"}
_NO_WORDS = {"no", "nope", "n", "keep", "leave", "decline", "declined"}
#: Words that may ride along with a yes or a no without changing it.
_FILLER = {"it", "is", "as", "the", "that", "this", "one", "please", "thanks",
           "thank", "you", "go", "ahead", "do", "looks", "good", "fine",
           "sounds", "same", "wording", "keep", "leave", "yes", "no"}


def _verdict(body: str) -> str:
    """`yes`, `no`, `words` (the firm's own), or `unclear`.

    "No, make it 60%" IS NOT A NO, and reading it as one would record the
    opposite of what the firm said. So a yes or a no is only a yes or a no
    when nothing else is said; a reply that opens with one and goes on to say
    something is refused, and the desk asks again. A reply opening with
    neither is the firm's own words.
    """
    words = re.findall(r"[a-z0-9%$.]+", body.lower())
    if not words:
        return "unclear"
    first, rest = words[0], [w.strip(".") for w in words[1:]]
    if first in _YES_WORDS or first in _NO_WORDS:
        if all(w in _FILLER for w in rest if w):
            return "yes" if first in _YES_WORDS else "no"
        return "unclear"
    return "words"


def _reply_body(answer: str, rid: str) -> str:
    """The reply without the reference the firm quoted to address it."""
    return re.sub(rf"\[?\b{rid}\b\]?:?", " ", answer, flags=re.I).strip()


def _amended(corpus: Path, pid: str, wording: str, rests: str, *,
             ruled: str, check_only: bool = False) -> None:
    """Rewrite one position's wording and rests-on, then prove the record loads
    and the figure check passes -- on a copy, before the real file is touched."""
    corpus = Path(corpus)
    pfile = next(f for f in sorted((corpus / "positions").glob("*.md"))
                 if re.search(rf"^## {re.escape(pid)} · ", f.read_text(encoding="utf-8"), re.M))
    text = pfile.read_text(encoding="utf-8")
    head = re.search(rf"^## {re.escape(pid)} · .*$", text, re.M)
    nxt = re.search(r"^## POS\d+ · ", text[head.end():], re.M)
    end = head.end() + nxt.start() if nxt else len(text)
    block = text[head.end():end]
    pos_at = block.index("**Position:**")
    why_at = block.index("**Why:**")
    # A WORDING-ONLY PROPOSAL KEEPS WHAT THE POSITION RESTS ON; one that names
    # new words replaces them. Either way the result is loaded before it is kept.
    if rests:
        block = (block[:pos_at] + f"**Position:** {wording}\n\n"
                 f"**Rests on:** {rests}\n\n" + block[why_at:])
    else:
        line_end = block.index("\n", pos_at)
        block = block[:pos_at] + f"**Position:** {wording}" + block[line_end:]
    if ruled:
        rat = re.search(r"^\*\*Ratified:\*\*.*$", block, re.M)
        at = rat.end() if rat else len(block.rstrip())
        block = block[:at] + f"\n\n**Ruled:** {ruled}" + block[at:]
    new_text = text[:head.end()] + block + text[end:]
    with tempfile.TemporaryDirectory() as tmp:
        trial = Path(tmp) / "corpus"
        shutil.copytree(corpus, trial)
        (trial / "positions" / pfile.name).write_text(new_text, encoding="utf-8")
        desk = record.load(trial)
        q = next(x for x in desk.positions if x.id == pid)
        if unsupported_figures(q):
            raise ValueError(
                f"{pid}: that wording still states "
                f"{', '.join(unsupported_figures(q))}, which the words it rests "
                f"on do not contain")
    if not check_only:
        pfile.write_text(new_text, encoding="utf-8")


def _append_ruling(corpus: Path, r: Ruling) -> None:
    f = Path(corpus) / RULINGS_FILE
    text = f.read_text(encoding="utf-8") if f.is_file() else RULINGS_PREAMBLE
    lines = [f"## {r.id} · {r.subject}", "",
             f"**Kind:** {r.kind} · **Ruled:** {r.ruled}", "",
             "**Asked:**", "", *_q(r.asked), "",
             "**Reply:**", "", *_q(r.reply)]
    if r.reaches_on:
        lines += ["", f"**Reaches on:** {'; '.join(r.reaches_on)}"]
    if r.outcome:
        lines += ["", f"**Outcome:** {r.outcome}"]
    sep = "" if text.endswith("\n\n") else "\n"
    f.write_text(text + sep + "\n".join(lines) + "\n\n---\n\n", encoding="utf-8")


RULINGS_PREAMBLE = """# Rulings — what the firm ruled when the desk asked

**The desk writes this file, and only with the firm's reply in hand.** The
firm, 26 September 2026: *"why wouldn't the desk send me a notification asking
me to rule on something and record it itself"*. Each entry is a question the
desk put to the firm (`rulings.ask`), their reply verbatim, and what it changed.
`rulings.record` writes it; nothing else does.

"""


def record_ruling(corpus: Path, entry: Asked) -> Ruling:
    """Write an answered ruling into the corpus. The firm's reply is the yes.

    yes     the desk's proposal is recorded
    no      nothing changes, and the finding is not raised again
    other   the firm's own words are recorded in place of the proposal

    REFUSES RATHER THAN RECORDING SOMETHING THAT WOULD NOT LOAD. A position
    reworded by the firm is loaded on a copy first; if their words state a
    figure nothing they rest on contains, this raises and the desk asks again,
    quoting why. The record never holds a ruling the engine cannot serve.
    """
    if not entry.answered:
        raise record.RecordError(f"{entry.id} has not been answered")
    body = _reply_body(entry.answer, entry.id)
    verdict = _verdict(body)
    if verdict == "unclear":
        raise ValueError(
            f"{entry.id}: the reply \"{entry.answer}\" opens with a yes or a no "
            f"and then says more. Ask the firm which they meant; recording "
            f"either would be a guess.")
    said_yes, said_no = verdict == "yes", verdict == "no"
    base = Ruling(id=entry.id, kind=entry.kind, subject=entry.subject,
                  ruled=entry.answered, asked=entry.question(),
                  reply=entry.answer)
    if entry.kind == "reach":
        if said_no:
            r = replace(base, outcome="declined")
        else:
            words = entry.proposed if said_yes else body
            r = replace(base, reaches_on=tuple(
                p.strip() for p in re.split(r"[;\n]", words) if p.strip()),
                outcome="ruled")
        _append_ruling(corpus, r)
        return r
    # ONE LINE, NO ASTERISKS: `Ruled:` is read up to the next `**`, so a reply
    # carrying emphasis would cut its own record short.
    said = " ".join(entry.answer.replace("*", "").split())
    ruled = f'{entry.id} — {entry.answered}: "{said}"'
    if said_no:
        r = replace(base, outcome="upheld")
        _mark_upheld(corpus, entry.subject, ruled)
    else:
        wording, rests = _split_proposal(entry.proposed)
        if not said_yes:
            wording = body
        _amended(corpus, entry.subject, wording, rests, ruled=ruled)
        r = replace(base, outcome="amended")
    _append_ruling(corpus, r)
    return r


def _mark_upheld(corpus: Path, pid: str, ruled: str) -> None:
    """The firm kept the wording: record that they were asked and said so."""
    for f in sorted((Path(corpus) / "positions").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        head = re.search(rf"^## {re.escape(pid)} · .*$", text, re.M)
        if not head:
            continue
        nxt = re.search(r"^## POS\d+ · ", text[head.end():], re.M)
        end = head.end() + nxt.start() if nxt else len(text)
        block = text[head.end():end]
        rat = re.search(r"^\*\*Ratified:\*\*.*$", block, re.M)
        at = rat.end() if rat else len(block.rstrip())
        block = block[:at] + f"\n\n**Ruled:** {ruled}" + block[at:]
        f.write_text(text[:head.end()] + block + text[end:], encoding="utf-8")
        return
    raise record.RecordError(f"no position {pid}")
