"""The adapter and the script: put 21 problems to two brains and grade both.

MEASURED, NEVER ASSERTED. No score produced here is asserted by a test and
nothing here gates CI. `scoreboard.py` says why: "a non-deterministic run cannot
gate a build without either flaking or being weakened until it proves nothing."
This is a script run at the desk, and its output is committed as a record. The
deterministic parts -- how the prompt is composed, what it refuses to carry, how
a reply is read -- ARE tested, because a leak gate nothing exercises is a promise.

WHAT THE MODEL IS SHOWN. `build_prompt` composes exactly three things: the
desk's sources (id, title, tier, citation prefix), the desk's stored authority,
and `problem.facts`. The authority is the section's RULES -- every paragraph
outside its worked examples -- and it may be shown, because a rule states a test
and not the outcome for these facts. The first record stored the worked examples
themselves as authority, so showing the corpus leaked every conclusion and the
adapter had to withhold it; "cite your authority" then meant recalling example
numbers from a list of 21 bare strings, one per problem, which the frontier row
solved as an assignment puzzle (`runs/2026-09-04/SCOREBOARD.md`).

Two shapes, and the run records which. `index` gives each citation with the
first sentence of its paragraph -- about 4,100 tokens for this desk, inside the
8,192-token window 8 GB of VRAM allows (rule 1). `text` gives every paragraph
in full, about 17,000 tokens, for a brain with the window. Rows answered under
different shapes are different runs and are not a gap.

`problem.title` is withheld: several titles name the outcome. `check_no_leak`
re-reads the finished prompt and raises, so the whitelist is a mechanism rather
than a promise (rule 6: policy at the choke point). What it now refuses is a
worked example reaching the prompt -- the leak moved to the boundary between
the rules and the examples, and so did the gate.

THE ONE THING DISCLOSED ON PURPOSE. The engine compares a position to the known
one exactly, normalised for case and space only, so a desk that phrases its
conclusion differently scores `wrongly_absorbed` -- the single number that costs
anything -- for punctuation. So the prompt names the desk's admissible
conclusions, derived from the record rather than typed here. That discloses that
the answer space is binary. It discloses nothing about WHICH, and the 57%
baseline in PROBLEMS.md already assumes a reader who knows the space. It is
stated in the run's notes because a disclosure nobody wrote down is a leak.

NOTHING IS REPAIRED ON THE WAY BACK. `parse_reply` strips the transport -- a
reasoning block, a code fence -- and reads the fields verbatim. It never maps a
near-miss conclusion onto an admissible one and never repairs a citation against
the index. If the model will not cite, that is `no_citation` and the engine says
so. Rule 10: a scoreboard that tidies the answer is measuring the tidier.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scoreboard                                        # noqa: E402
from engine import REASONS, Answer                       # noqa: E402
from record import Desk, Problem                         # noqa: E402


class AdapterGaveUp(Exception):
    """The brain returned nothing usable at all.

    Raised rather than answered, because `scoreboard.run` turns an exception into
    an escalation with reason `model_gave_up` and keeps the denominator. Rule 9:
    the give-up tail is accepted and made harmless, not prompted away.
    """


# -- what the model is shown --------------------------------------------------

#: The escalation reasons a brain may choose. A subset of `engine.REASONS` on
#: purpose: the two fetch reasons describe our egress and the source's origin,
#: neither of which the thing answering can observe, and `model_gave_up` is the
#: harness's word for an abandoned run, not a choice.
OFFERABLE = ("authority_absent", "authority_permits_choice", "no_citation",
             "citation_does_not_support")

_TEMPLATE = """\
You are a desk. You answer only from the authority listed below, and you cite it.

SOURCES YOU MAY RELY ON
{sources}

AUTHORITY THIS DESK HOLDS. Each line is a citation, copied verbatim, followed by
the paragraph it names. Cite the ONE rule these facts turn on. Nothing outside
this list resolves, and an answer whose citation does not resolve is refused
before it reaches anyone.
{citations}

THE FACTS
{facts}

REPLY WITH ONE JSON OBJECT AND NOTHING ELSE:
{{"position": "<exactly one of: {positions}>",
 "citation": "<one citation copied verbatim from the list above: the part before the dash, nothing after it>",
 "escalated": false,
 "reason": "",
 "working": "<one or two sentences: why that conclusion, from that authority>"}}

If the authority above does not settle it, do not guess. Reply with the same
object, "escalated": true, an empty "citation", and "reason" set to exactly one
of: {reasons}. Declining is a success here; a guess that cites nothing is not.
"""


#: The two shapes the authority may take in a prompt. A closed set so a run can
#: only ever record one of two words for what it showed.
SHAPES = ("index", "text")


def build_prompt(problem: Problem, desk: Desk, *, shape: str = "index") -> str:
    """Compose the only thing the brain sees. A whitelist, and a short one."""
    if shape not in SHAPES:
        raise ValueError(f"shape is {shape!r}; must be one of {', '.join(SHAPES)}")
    sources = "\n".join(
        f'{s.id} - {s.title} - tier: {s.tier} - citations begin "{s.citation_prefix}"'
        for s in desk.sources
    )
    prompt = _TEMPLATE.format(
        sources=sources,
        citations="\n".join(corpus_lines(desk, shape)),
        facts=problem.facts,
        positions=" | ".join(admissible(desk)),
        reasons=", ".join(OFFERABLE),
    )
    check_no_leak(prompt, problem, desk)
    return prompt


_FIRST = re.compile(r"(?<=\.)\s")


def corpus_lines(desk: Desk, shape: str) -> list[str]:
    """The stored authority as the prompt shows it, in the record's order.

    Record order is the regulation's order, and it is kept: with the rules as
    authority and the examples as problems there is no nth-line-for-nth-problem
    pairing to hide, and a reader checking a transcript against eCFR should find
    the paragraphs where the section puts them. `index` shows each paragraph's
    first sentence -- its heading where it has one, its operative sentence where
    it does not; `text` shows all of it.
    """
    if shape == "text":
        return [f"  {p.citation}\n    {p.text}" for p in desk.passages]
    return [f"  {p.citation} — {_FIRST.split(p.text, 1)[0]}" for p in desk.passages]


def citation_index(desk: Desk) -> list[str]:
    """Every citation the desk holds, as a set a reply can be checked against."""
    return sorted({p.citation for p in desk.passages})


def admissible(desk: Desk) -> list[str]:
    """The conclusions this desk can state, read off the record, not typed here.

    Typed here it would be a second copy of the answer vocabulary, free to drift
    from the one the engine grades against -- and the drift would show up as
    `wrongly_absorbed`, which is the number that must never be manufactured.
    """
    return sorted({p.answer for p in desk.problems})


class Leak(Exception):
    """Something the brain must not see reached the prompt."""


def check_no_leak(prompt: str, problem: Problem, desk: Desk) -> None:
    """Re-read the finished prompt for the three things it must never carry.

    A whitelist that is only enforced by how the template was written is a
    convention; this is the gate. It checks the OUTPUT rather than the inputs,
    so a future edit that adds a helpful line is caught by the same code.

    THE WORKED EXAMPLES MAY NOT REACH THE PROMPT, FROM ANY DIRECTION. The
    authority shown is the section's rules; if a worked example is ever stored
    beside them again -- the first record stored nothing else -- it would carry
    its own conclusion into every prompt. The tell is a problem's fact pattern
    appearing where only the rules should be: the problem's own facts must
    appear exactly once (as the question), and no other problem's at all. The
    longest sentence of each fact pattern is the probe, because a short one
    ("Assume that § 1.212-1 does not apply.") can legitimately appear in a rule.
    """
    bare = _bare(prompt)
    # Checked against the STORED authority as well as the finished prompt: in
    # the `index` shape only a passage's first sentence is shown, so a worked
    # example stored beside the rules would pass a prompt-only probe while
    # still being what the model is told it may cite.
    stored = _bare(" ".join(p.text for p in desk.passages))
    for other in desk.problems:
        probe = _bare(max(_SENTENCES.split(other.facts), key=len))
        if probe in stored:
            raise Leak(
                f"{problem.id}: the stored authority carries the fact pattern of "
                f"{other.id}. A worked example in the authority carries its own "
                f"conclusion; the corpus is the rules"
            )
        allowed = 1 if other.id == problem.id else 0
        if bare.count(probe) > allowed:
            raise Leak(
                f"{problem.id}: the prompt carries the fact pattern of {other.id} "
                f"where only the rules should be"
            )
    if _bare(problem.title) in _bare(prompt):
        raise Leak(
            f"{problem.id}: the prompt carries the problem's title "
            f"({problem.title!r}); several titles name the outcome"
        )
    # The answer may appear only where the template lists the admissible
    # conclusions, once per conclusion. Anywhere else it is the answer key.
    if _bare(prompt).count(_bare(problem.answer)) > 1:
        raise Leak(
            f"{problem.id}: {problem.answer!r} appears in the prompt outside the "
            f"list of admissible conclusions"
        )


_SENTENCES = re.compile(r"(?<=\.)\s+(?=[A-Z(])")


def _bare(text: str) -> str:
    return " ".join(text.split()).casefold()


# -- what comes back ----------------------------------------------------------

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_reply(raw: str) -> Answer:
    """Read the fields verbatim. Strip the transport; repair nothing else.

    A reply that is not JSON is not an error to be fixed here. It becomes an
    Answer with the model's words as its position and no citation, which the
    engine refuses as `no_citation` -- which is the true outcome, and the one a
    tolerant parser would have hidden.
    """
    body = _THINK.sub("", raw).strip()
    if not body:
        raise AdapterGaveUp("empty reply")
    if (fence := _FENCE.search(body)) is not None:
        body = fence.group(1).strip()

    obj = _first_object(body)
    if obj is None:
        return Answer(position=body, working=raw)

    escalated = bool(obj.get("escalated"))
    reason = str(obj.get("reason") or "").strip()
    if escalated and reason not in REASONS:
        # An unrecognised reason is not an escalation the engine can count, and
        # inventing one for it would be the scoreboard answering for the model.
        # It becomes an ordinary answer and is graded on what it cited.
        escalated = False
        reason = ""
    return Answer(
        position=str(obj.get("position") or "").strip(),
        citation=str(obj.get("citation") or "").strip(),
        escalated=escalated,
        reason=reason if escalated else "",
        working=str(obj.get("working") or "").strip() or raw.strip(),
    )


def _first_object(text: str) -> dict | None:
    """The first balanced {...} that loads as an object. No repairs."""
    for start in (i for i, ch in enumerate(text) if ch == "{"):
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
                    return obj if isinstance(obj, dict) else None
    return None


# -- the two brains -----------------------------------------------------------

OLLAMA = "http://127.0.0.1:11434/api/chat"


def ollama(model: str, prompt: str, *, num_ctx: int, timeout: int = 900) -> str:
    """One call to the local model. Raises, so the harness counts a give-up.

    `num_ctx` is passed rather than defaulted because rule 1 is the first
    constraint on this box: 8 GB of VRAM is an 8,192-token window, and a request
    that exceeds it does not error -- it silently drops the front of the prompt,
    which on this desk is the instruction to cite.

    Thinking is off. qwen3 emits its reasoning into the same window it must
    answer from, and the window is the budget. That is a deliberate configuration
    of this run and is recorded in its notes, not a fact about the model.
    """
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "seed": 0, "num_ctx": num_ctx,
                    "num_predict": 512},
    }).encode()
    req = urllib.request.Request(
        OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError) as exc:
        raise AdapterGaveUp(f"{model}: {type(exc).__name__}: {exc}") from exc
    return body.get("message", {}).get("content", "")


def forge_adapter(desk: Desk, model: str, transcript: Path, *, num_ctx: int,
                  shape: str = "index"):
    """`ask(problem) -> Answer` backed by the local model, keeping every reply."""
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("", encoding="utf-8")

    def ask(problem: Problem) -> Answer:
        prompt = build_prompt(problem, desk, shape=shape)
        try:
            raw = ollama(model, prompt, num_ctx=num_ctx)
        except AdapterGaveUp as exc:
            _log(transcript, problem, prompt, "", str(exc))
            raise
        _log(transcript, problem, prompt, raw, "")
        return parse_reply(raw)

    return ask


class ReplayMismatch(scoreboard.HarnessError):
    """The replayed replies did not answer the prompts being rebuilt.

    A `HarnessError` rather than a plain one, because `scoreboard.run` absorbs
    every ordinary exception into `model_gave_up`: raised as a plain exception
    this refusal produced sixteen false give-ups, a scoreboard claiming an
    authority shape nobody saw, and an exit code of zero. Found in review of
    the pull request that added it.
    """


def replay_adapter(desk: Desk, replies: dict, transcript: Path, *,
                   shape: str = "index", shown: dict | None = None):
    """`ask(problem) -> Answer` reading replies a brain already produced.

    The frontier row is obtained this way: the prompts `build_prompt` composes
    are written out, answered, and read back through the SAME parser the local
    model's replies go through. Two brains graded by one code path, which is the
    only way the gap between the rows means anything.

    THE REBUILT PROMPT IS CHECKED AGAINST THE ONE THE BRAIN ACTUALLY SAW.
    A `.jsonl` transcript stores the prompt beside every reply, and this used to
    discard it and rebuild the evidence from whatever `--corpus` the replay was
    invoked with. Regrade a `text`-corpus transcript without `--corpus text` and
    the record's own `AUTHORITY SHOWN` line then claimed `index` over replies
    that had seen something else -- a claim in one place and the behaviour in
    another, which is the failure this repository exists to close.

    Deriving the shape from the stored prompt would fix that one case. Comparing
    the whole prompt fixes the category: a changed desk, a changed template, a
    reordered index and a wrong `--corpus` all diverge here, and any of them
    makes these replies un-regradable rather than merely mislabelled. So it
    refuses instead of recording a number nobody can check.
    """
    shown = shown or {}

    # CHECKED BEFORE THE RUN STARTS, NOT PER PROBLEM ON THE WAY PAST. Whether a
    # transcript answers the prompts being rebuilt is a property of the
    # transcript, known here; discovering it on problem seven is late for no
    # reason, and it is late in the one way that matters -- by then the refusal
    # is being raised inside `scoreboard.run`, whose catch-all is what turned it
    # into sixteen `model_gave_up` escalations and a scoreboard that shipped.
    by_id = {p.id: p for p in desk.problems}
    for pid, was in sorted(shown.items()):
        if pid not in by_id or not was:
            continue
        rebuilt = build_prompt(by_id[pid], desk, shape=shape)
        if was != rebuilt:
            raise ReplayMismatch(
                f"{pid}: the reply being replayed answered a different prompt "
                f"({len(was)} chars) than the one rebuilt here ({len(rebuilt)} "
                f"chars). These replies cannot be regraded against this desk and "
                f"this --corpus shape; the record would state an authority shape "
                f"the brain never saw."
            )

    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("", encoding="utf-8")

    def ask(problem: Problem) -> Answer:
        prompt = build_prompt(problem, desk, shape=shape)
        raw = replies.get(problem.id)
        if raw is None:
            _log(transcript, problem, prompt, "", "no reply recorded")
            raise AdapterGaveUp(f"{problem.id}: no reply recorded")
        _log(transcript, problem, prompt, raw, "")
        return parse_reply(raw)

    return ask


def _log(path: Path, problem: Problem, prompt: str, raw: str, error: str) -> None:
    """Every exchange, verbatim, appended as it happens.

    Written per call rather than at the end so an abandoned run still leaves the
    evidence of how far it got -- which is the only thing that tells a give-up
    apart from a crash.
    """
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"problem": problem.id, "prompt": prompt,
                             "reply": raw, "error": error}) + "\n")


# -- the script ---------------------------------------------------------------

def watched(ask, seen: dict):
    """Keep the Answer each call produced, so the run can be described later.

    THIS IS NOT WHERE THE SCORE COMES FROM. Rule 10: every reported outcome is
    read off the `Result` objects the engine produced. These Answers back one
    supplementary diagnostic -- how often the conclusion was right while the
    citation was not -- which is a fact about the record and the engine's own
    comparison, never about what the model claimed for itself.
    """
    def ask_and_keep(problem: Problem) -> Answer:
        answer = ask(problem)
        seen[problem.id] = answer
        return answer
    return ask_and_keep


def queue_refusals(desk: Desk, run, answers: dict, path: Path) -> int:
    """Keep every answer the engine would not serve, with its reasoning.

    Refused means `wrong_caught` or `escalated`: those are the outcomes where
    `serve()` hands back a Refusal. A `wrongly_absorbed` answer was served -- it
    is a scoreboard finding, not a queue entry, and putting it here would say the
    desk had caught something it did not.
    """
    from engine import Outcome
    import unsupported

    refused = 0
    problems = {p.id: p for p in desk.problems}
    for result in run.results:
        if result.outcome not in (Outcome.WRONG_CAUGHT, Outcome.ESCALATED):
            continue
        answer = answers.get(result.problem_id)
        if answer is None:                 # the harness caught a give-up
            answer = Answer(position="", escalated=True, reason=result.reason)
        unsupported.append(path, unsupported.from_refusal(
            problems[result.problem_id].facts, answer, result, model=run.model,
            existing=unsupported.parse(path.read_text(encoding="utf-8"))
            if path.exists() else [],
        ))
        refused += 1
    return refused


def diagnostic(desk: Desk, run, answers: dict) -> dict:
    """One cross-tab the four outcomes cannot show, and it matters here.

    `grade` refuses a citation that is real authority but not this question's
    BEFORE it ever compares the conclusion. So a desk that reasons correctly and
    cannot name the right worked example lands in `wrong_caught`, and the
    scoreboard cannot tell that apart from a desk that was simply wrong. That is
    the engine behaving exactly as designed -- an answer without its own
    authority behind it has not earned to be called right -- but it means
    `wrongly_absorbed` is structurally suppressed, and a reader should be told
    by how much rather than left to assume the desk was clean.

    Read from the record and the engine's own comparison. Never from prose.
    """
    from engine import _same

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_ecfr import _under

    problems = {p.id: p for p in desk.problems}
    right_position = sum(
        1 for pid, a in answers.items()
        if not a.escalated and _same(a.position, problems[pid].answer))
    right_citation = sum(
        1 for pid, a in answers.items()
        if not a.escalated and a.citation.strip() == problems[pid].citation)
    # WITHIN THE GOVERNING RULE'S SUBTREE, REPORTED AND NEVER SCORED.
    #
    # Seven problems key to (j) and five to (l), because that is the paragraph
    # the regulation's own conclusion names. A desk that answers "betterment,
    # (j)(1)(iii)" has reached the right rule by a finer path and the engine
    # refuses it, correctly: `_check` is shared with `serve`, so anything that
    # accepts a near-miss here also hands one to a client, and `Desk.passage`
    # documents exact match as the thing stopping "an answer cit[ing] something
    # adjacent to the rule it relied on and still verify".
    #
    # So the distinction is measured rather than forgiven. It is deliberately
    # NOT a fifth outcome and not added to any total: containment admits 14 of
    # 172 paths under (j) and exactly 1 under (k)(1)(vi), so scoring by it would
    # grade seven problems fourteen times more leniently than one for no reason
    # but how verbosely the regulation phrased its conclusion.
    near_citation = sum(
        1 for pid, a in answers.items()
        if not a.escalated and a.citation.strip() != problems[pid].citation
        and _under(a.citation.strip(), problems[pid].citation))
    off_index = sum(
        1 for pid, a in answers.items()
        if not a.escalated and a.citation.strip()
        and a.citation.strip() not in citation_index(desk))
    return {
        "answered": sum(1 for a in answers.values() if not a.escalated),
        "position_matched": right_position,
        "citation_matched": right_citation,
        "citation_within_governing_rule": near_citation,
        "citation_off_index": off_index,
        "gave_up": run.gave_up,
    }


def constant_control(desk: Desk) -> dict:
    """What answering the same thing every time scores. Computed, never typed.

    PROBLEMS.md states that always giving the most common conclusion agrees with
    12 of 21, and that is the number a run has to beat before it has shown
    anything. It is a fact about the CONCLUSIONS, not about this scoreboard: put
    through the engine, a constant answer cites nothing and scores zero correct,
    because an answer with no resolvable citation never counts as correct. Both
    numbers belong beside the result, and a reader given only one of them will
    draw the wrong conclusion from either.
    """
    from collections import Counter
    from engine import Answer, grade, tally

    conclusion, agrees = Counter(
        p.answer for p in desk.problems).most_common(1)[0]
    # AND THE SAME FOR THE CITATION. With the rules as authority several
    # problems share a governing paragraph, so always citing the commonest one
    # matches some of them by arithmetic. That number belongs beside a
    # citation score for the same reason 57% belonged beside the conclusion.
    citation, cites = Counter(
        p.citation for p in desk.problems).most_common(1)[0]
    graded = [grade(Answer(position=conclusion), p, desk) for p in desk.problems]
    return {"conclusion": conclusion, "agrees_with": agrees,
            "citation": citation, "cites": cites,
            "of": len(desk.problems), "through_the_engine": tally(graded)}


def _replies(path: str) -> tuple[dict, dict]:
    """`(replies, prompts)` keyed by problem id, from a map or a transcript.

    A run's own `.jsonl` transcript is accepted so a committed record can be
    regraded from the evidence it shipped with -- which is the difference
    between a scoreboard a reader can check and one they have to believe. That
    transcript also stores the prompt each reply answered, and it is returned
    beside the replies so `replay_adapter` can refuse a regrade against a prompt
    the brain never saw. A plain map carries no prompts and yields `{}`, which
    is not an error: it is how a fresh frontier context hands answers back.
    """
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".jsonl"):
        rows = [json.loads(l) for l in text.splitlines() if l.strip()]
        return ({r["problem"]: r["reply"] for r in rows if r["reply"]},
                {r["problem"]: r.get("prompt", "") for r in rows if r["reply"]})
    return json.loads(text), {}


#: What a finished run leaves behind. Any one of these means the directory holds
#: a measured record, and a measured record is not overwritten.
RUN_RECORDS = ("SCOREBOARD.md", "SCOREBOARD.txt", "outcomes.json")


class RunWouldOverwrite(Exception):
    """The output directory already holds a run. Refused rather than replaced."""


def run_dir(out: str, desk_name: str, today: date) -> Path:
    """Where this run writes, refusing a directory that already holds one.

    FOUND BY THE SECOND FORGE RUN, 4 SEPTEMBER 2026. The default is
    `runs/<today>/` and both runs happened on the same day, so the documented
    command would have written the second run's scoreboard over the first run's
    measured record -- the one thing in this directory that cannot be
    regenerated, since the brain that produced it is not deterministic. The
    session running it noticed and passed `--out` by hand. A default whose
    safety depends on somebody noticing is the mechanism absent.

    It refuses on an EXPLICIT `--out` too. Deriving the date differently would
    fix the day-collision and leave `--out runs/2026-09-04` pointed at the same
    record with the same result; what must not happen is a measured record being
    replaced, whichever argument named it. There is deliberately no `--force`:
    moving the old directory costs one command, and the record costs a rerun
    that cannot reproduce it.
    """
    d = Path(out) if out else ROOT / "desks" / desk_name / "runs" / today.isoformat()
    held = [n for n in RUN_RECORDS if (d / n).is_file()]
    if held:
        raise RunWouldOverwrite(
            f"{d} already holds a run ({', '.join(held)}). A scoreboard is a "
            f"measured record and the brain that produced it is not "
            f"deterministic, so it cannot be regenerated. Two runs on one day "
            f"is the case this catches: pass --out with a directory of its own "
            f"(runs/{today.isoformat()}-second-run, say), and say in the record "
            f"that they are two runs on one day rather than two days."
        )
    return d


def _main(argv: list[str]) -> int:
    import argparse

    from record import load

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desk", default=str(ROOT / "desks" / "fixed-assets"))
    ap.add_argument("--out", default="")
    ap.add_argument("--dump-prompts", default="",
                    help="write the prompts for a brain answered elsewhere")
    ap.add_argument("--forge-model", default="qwen3:8b")
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--skip-forge", action="store_true")
    ap.add_argument("--forge-replies", default="",
                    help="grade a recorded local run instead of calling the "
                         "model again; the record regenerates from its own "
                         "transcript, and re-running the scoreboard never "
                         "re-rolls the dice")
    ap.add_argument("--frontier-replies", default="")
    ap.add_argument("--frontier-label", default="frontier")
    ap.add_argument("--notes", default="",
                    help="a file of what was NOT checked, one per line")
    ap.add_argument("--corpus", default="index", choices=SHAPES,
                    help="how the stored rules are shown: 'index' (citation "
                         "and first sentence, fits the Forge's window) or "
                         "'text' (every paragraph in full). Recorded in the "
                         "run, because rows shown different things are not "
                         "comparable")
    args = ap.parse_args(argv)

    desk = load(Path(args.desk))
    prompt_for = lambda p: build_prompt(p, desk, shape=args.corpus)

    if args.dump_prompts:
        out = Path(args.dump_prompts)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {p.id: prompt_for(p) for p in desk.problems},
            indent=2), encoding="utf-8")
        print(f"{len(desk.problems)} prompts ({args.corpus}) -> {out}")
        return 0

    out_dir = run_dir(args.out, desk.name, date.today())
    out_dir.mkdir(parents=True, exist_ok=True)
    queue_dir = Path(args.desk) / "unsupported"

    runs, answers, queues, diags = [], {}, {}, {}

    if not args.skip_forge:
        label = f"{args.forge_model} (Forge)"
        seen: dict = {}
        if args.forge_replies:
            forge_replies, forge_shown = _replies(args.forge_replies)
            backend = replay_adapter(desk, forge_replies,
                                     out_dir / "forge-regraded.jsonl",
                                     shape=args.corpus, shown=forge_shown)
        else:
            backend = forge_adapter(desk, args.forge_model,
                                    out_dir / "forge.jsonl",
                                    num_ctx=args.num_ctx, shape=args.corpus)
        ask = watched(backend, seen)
        r = scoreboard.run(desk, ask, model=label)
        runs.append(r)
        answers[label], seen = seen, {}
        diags[label] = diagnostic(desk, r, answers[label])
        queues[label] = queue_refusals(
            desk, r, answers[label], queue_dir / "forge.md")

    if args.frontier_replies:
        label = args.frontier_label
        replies, front_shown = _replies(args.frontier_replies)
        seen = {}
        ask = watched(replay_adapter(desk, replies,
                                     out_dir / "frontier.jsonl",
                                     shape=args.corpus, shown=front_shown), seen)
        r = scoreboard.run(desk, ask, model=label)
        runs.append(r)
        answers[label] = seen
        diags[label] = diagnostic(desk, r, answers[label])
        queues[label] = queue_refusals(
            desk, r, answers[label], queue_dir / "frontier.md")

    notes = [ln.strip() for ln in
             Path(args.notes).read_text(encoding="utf-8").splitlines()
             if ln.strip()] if args.notes else []
    control = constant_control(desk)

    lines = [scoreboard.render(runs, notes=notes), ""]
    lines.append(f"AUTHORITY SHOWN: {len(desk.passages)} stored paragraphs as "
                 f"'{args.corpus}', for {len(desk.problems)} problems.")
    lines.append("")
    lines.append("BASELINE, BESIDE THE RESULT AND NOT BELOW IT:")
    lines.append(f"  answering {control['conclusion']!r} every time agrees with "
                 f"{control['agrees_with']} of {control['of']} conclusions "
                 f"({control['agrees_with'] * 100 // control['of']}%),")
    lines.append(f"  and through the engine scores "
                 f"{control['through_the_engine']['correct']} correct: a "
                 f"constant answer cites nothing.")
    lines.append(f"  citing {control['citation']!r} every time matches "
                 f"{control['cites']} of {control['of']} citations "
                 f"({control['cites'] * 100 // control['of']}%).")
    lines.append("")
    lines.append("gap (correct): " + ", ".join(
        f"{k} {v}" for k, v in scoreboard.gap(runs).items()))
    lines.append("")
    lines.append("DIAGNOSTIC -- not one of the four outcomes, and not a score:")
    for label, d in diags.items():
        lines.append(f"  {label}: conclusion matched {d['position_matched']}/"
                     f"{len(desk.problems)}, citation matched "
                     f"{d['citation_matched']}/{len(desk.problems)}, "
                     f"within the governing rule but not it "
                     f"{d['citation_within_governing_rule']}, "
                     f"cited outside the index {d['citation_off_index']}, "
                     f"gave up {d['gave_up']}")
    lines.append("")
    lines.append("UNSUPPORTED QUEUE (entries this run produced):")
    for label, n in queues.items():
        lines.append(f"  {label}: {n}")
    body = "\n".join(lines)
    print(body)
    (out_dir / "SCOREBOARD.txt").write_text(body + "\n", encoding="utf-8")

    (out_dir / "outcomes.json").write_text(json.dumps({
        r.model: {"counts": r.counts, "gave_up": r.gave_up,
                  "results": [{"problem": x.problem_id,
                               "outcome": x.outcome.value,
                               "reason": x.reason, "detail": x.detail}
                              for x in r.results],
                  "diagnostic": diags[r.model],
                  "queued": queues[r.model]}
        for r in runs}, indent=2), encoding="utf-8")
    print(f"\nengine state -> {out_dir / 'outcomes.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
