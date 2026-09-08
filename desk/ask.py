"""The front door. What a stuck agent actually calls.

THIS EXISTED ONLY AS A PROMISE UNTIL 5 SEPTEMBER 2026. `routing.
refusal_naming_the_desk` has always handed a stopped agent the sentence "Ask
<desk> with ask_desk, then come back with the citation" — and there was no
`ask_desk`. Seven desks, the whole stored corpus, an engine that verifies every
citation, a gate measured at zero false refusals across 98 problems, and nothing
a caller could invoke. The record was complete and unreachable.

TWO CALLS, AND THE SPLIT IS THE WHOLE MECHANISM.

    consult(question)              -> what the desk will let you answer from
    answer(question, desk, ...)    -> served, or refused and KEPT

A model does not decide which desk to use: `routing.route` is a comparison, not a
judgement. A model does not decide whether its own citation holds: `engine.serve`
does, and refuses. What the model does is the only thing it is good at — reading
the authority it was handed and proposing a conclusion from it.

ONE TOOL IN THE CALLER, NOT ONE PER DESK. LOCAL-LLM-PATTERN rule 1: an 8 GB model
has an 8,192-token window, and loading a schema per desk "silently truncates the
model's own instructions — it then 'ignores' rules it never received." So the
caller holds one entry point and the router resolves the rest here, where it
costs nothing.

A REFUSAL IS FILED, NEVER DROPPED. `answer()` keeps every refusal in the desk's
own `unsupported/` queue with the reasoning intact, because a refusal is a
finding and the count of them is what tells the firm which authority is missing.
Retained is not accepted: nothing filed is ever returned to a caller.
"""
from __future__ import annotations

from pathlib import Path

import engine
import record
import routing
import unsupported

HERE = Path(__file__).resolve().parent
DESKS = HERE / "desks"

#: What an answerer may see, and the omission that matters. `PROBLEMS.md` is the
#: answer key: a desk scored against problems its answerer could read measures
#: transcription. A PROPOSED position is likewise withheld — it is one agent's
#: suggestion nobody has said yes to, and showing it would let a guess become the
#: next agent's premise, which is the whole failure the two-store split prevents.
SHOWN = ("sources", "ratified positions", "stored authority")


def consult(question: str, desks: Path = DESKS,
            context: record.Context | None = None) -> list[tuple[str, str]]:
    """`[(desk name, everything it will let you answer from)]`. Possibly empty.

    SILENCE IS A RESULT. A question touching no desk's subjects comes back empty
    rather than routed to the nearest one — a router that always answers is one
    whose answer means nothing.
    """
    out = []
    for r in routing.route(question, routing.registry(desks)):
        out.append((r.desk, brief(question, record.load(desks / r.desk), context)))
    return out


def brief(question: str, desk: record.Desk,
          context: record.Context | None = None) -> str:
    """Everything the desk will let an answerer see, and nothing else."""
    ratified = [q for q in desk.positions if not q.proposed]
    context = context or record.NOTHING_ON_FILE
    out = [f"# {desk.name}", "", f"**Asked:** {question}", "",
           "Answer ONLY from what follows. A citation to anything not printed",
           "here is refused by the engine, however real it is.", ""]
    if desk.records:
        # WHAT WE WERE TOLD, AND -- THE HALF THAT MATTERS -- WHAT WE WERE NOT.
        # Printing only the facts on file leaves an answerer to assume the rest
        # were not needed. Printing the gaps by name is what lets it escalate
        # `context_not_on_file` instead of reasoning from the vendor, which is
        # the failure this whole input exists to stop.
        out += ["## What the file already says", ""]
        for name in desk.records:
            value = str(context.facts.get(name, "")).strip()
            out.append(f"- **{name}:** {value}" if value
                       else f"- **{name}:** NOT ON FILE — do not infer it, and do "
                            f"not answer from a rule that needs it")
        out.append("")
    out += ["## Sources this desk may rely on", ""]
    out += [f"- **{s.id}** · {s.title} · tier **{s.tier}**" for s in desk.sources]
    if ratified:
        out += ["", "## The firm's own positions — binding, and quoted exactly", ""]
        for q in ratified:
            out += [f"### {q.citation}", "", f"> {q.position}", ""]
            # A DEFAULT SAYS SO, so an answerer is not told the firm's general
            # rule as though it were this client's. The firm, holding two
            # positions on 6 September 2026: "we shouldn't ignore client level
            # rules set with judgment with the desk answering broadly."
            #
            # The engine decides -- `_check` refuses whatever this says -- and
            # this is the disclosure, not the gate. An answerer that reads it and
            # escalates has reasoned correctly; one that does not is stopped
            # anyway, which is the difference between a prompt and a choke point.
            if q.unless:
                out += [f"This is the firm's DEFAULT. It does not apply to a "
                        f"client the firm treats differently on "
                        f"{', '.join(q.unless)}, and nothing here says whether "
                        f"this one is. The desk will ask rather than assume.", ""]
    out += ["", "## The authority", ""]
    # `record.shown` and not `desk.passages`: the engine counts the same call
    # when it reports how much a desk put in front of a model that then said the
    # desk held nothing. Two readings of "what was shown" is one too many.
    for p in record.shown(desk):
        out += [f"### {p.citation}", "", f"> {p.text}", ""]
    return "\n".join(out)


def brief_for_grading(question: str, desk: record.Desk,
                      context: record.Context | None = None) -> str:
    """The same brief with every worked example withheld. FOR SCORING ONLY.

    WHAT THIS IS PROTECTING. Six of these desks draw their PROBLEMS from the
    worked examples of the regulation they store. Print those examples to
    something being scored and the corpus carries its own answer key -- which is
    not a hypothetical: the first record this repository built stored the 21
    examples it also graded on, and the frontier row solved the set as a matching
    puzzle rather than by reasoning (`runs/2026-09-04/SCOREBOARD.md`).

    WHY EXCLUDING THE PROBLEM'S OWN CITATION IS NOT ENOUGH, which is the whole
    reason this is a function and not a note. A problem is cited to the RULE its
    analysis names -- `(h)(1)`, say -- and never to the example it was drawn
    from. So a filter on the problem's citation leaves the example that states
    the answer sitting in the brief, under a different citation, fully readable.
    The class has to go, not the row.

    `scoreboard.py` records the rule this replaces: "THE ADAPTER MUST NEVER BE
    HANDED THE PASSAGE FOR THE PROBLEM'S OWN CITATION [...] This cannot be tested
    here: the thing that answers is injected and does not exist yet (#227). It is
    a constraint on whoever writes it, recorded rather than assumed." A
    constraint recorded rather than assumed is still prose, and prose policy in
    this operation is policy one run in three (LOCAL-LLM-PATTERN rule 6). This is
    the choke point instead.
    """
    return brief(question, desk.rules_only(), context)


def answer(question: str, desk_name: str, *, position: str = "",
           citation: str = "", escalate: str = "", model: str = "",
           working: str = "", ask: str = "", desks: Path = DESKS,
           keep: bool = True,
           context: record.Context | None = None, prove=None):
    """Put a proposed answer through the production path. Served, or refused.

    `keep` files a refusal in the desk's `unsupported/` queue. It defaults on
    because the queue is the only thing that says what the record is missing, and
    a refusal thrown away is a finding destroyed. Pass `keep=False` only when
    measuring, never when answering.

    `prove` IS A TRANSPORT, NOT A FLAG, and that is deliberate. The firm asked
    for this on the fourth docket -- *"the agents tie out their position to
    prove it to the desk"* -- and a boolean would mean this function reaches the
    network whenever something, somewhere, is configured true. Pass a callable
    and it is fetched; pass nothing and nothing is fetched, which is what the
    whole suite passes.

    The gate runs FIRST and is unchanged. A proof is taken only on an answer the
    engine already agreed to serve, so this can add a refusal and can never
    remove one. Where the publisher no longer carries the passage the answer is
    withdrawn (`authority_has_moved`); where the publisher could not be reached
    the answer stands and says the proof could not be taken.
    """
    desk = record.load(desks / desk_name)
    # `working` REACHES THE ANSWER, and this front door dropped it. `Answer`
    # carries the field and `unsupported.from_refusal` persists it, so every
    # entry filed through here arrived with BLANK reasoning -- while the skill
    # beside it demands a real one, because "could not tell" helps nobody and
    # the reasoning is the only thing that says what authority is missing. A
    # queue of blank refusals is a count, and the count was the thing this was
    # built not to be. Found by Codex on #272.
    if escalate:
        proposed = engine.Answer(position="", citation="", escalated=True,
                                 reason=escalate, working=working, ask=ask)
    else:
        proposed = engine.Answer(position=position, citation=citation,
                                 working=working)

    out = engine.serve(proposed, desk, question=question, context=context)
    if prove is not None and isinstance(out, engine.Served):
        import dataclasses

        import proving
        p = proving.prove(out, desk, prove)
        if p.verdict == proving.DIFFERS:
            out = engine.Refusal(
                proving.MOVED,
                f"{out.citation!r} resolves in this desk's record, and the "
                f"publisher no longer carries it: {p.note}. The record is the "
                f"only witness to that text, which is not enough to serve it on",
                ask=f"Re-read {p.url or out.citation} and bring the stored "
                    f"passage back into line with it, or retire the citation. "
                    f"Until then this desk has no authority for the answer.")
        else:
            out = dataclasses.replace(out, proof=p)
    if isinstance(out, engine.Refusal) and keep:
        path = desks / desk_name / "unsupported" / "asked.md"
        existing = (unsupported.parse(path.read_text(encoding="utf-8"))
                    if path.exists() else [])
        unsupported.append(path, unsupported.from_refusal(
            question, proposed, engine.Result(
                "asked", engine.Outcome.WRONG_CAUGHT, reason=out.reason,
                detail=out.detail, ask=out.ask),
            model=model, existing=existing, desk=desk))
    return out
