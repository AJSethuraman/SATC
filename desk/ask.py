"""The front door. What a stuck agent actually calls.

THIS EXISTED ONLY AS A PROMISE UNTIL 5 SEPTEMBER 2026. `routing.
refusal_naming_the_desk` has always handed a stopped agent the sentence "Ask
<desk> with ask_desk, then come back with the citation" — and there was no
`ask_desk`. Seven desks, 533 stored passages, an engine that verifies every
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


def consult(question: str, desks: Path = DESKS) -> list[tuple[str, str]]:
    """`[(desk name, everything it will let you answer from)]`. Possibly empty.

    SILENCE IS A RESULT. A question touching no desk's subjects comes back empty
    rather than routed to the nearest one — a router that always answers is one
    whose answer means nothing.
    """
    out = []
    for r in routing.route(question, routing.registry(desks)):
        out.append((r.desk, brief(question, record.load(desks / r.desk))))
    return out


def brief(question: str, desk: record.Desk) -> str:
    """Everything the desk will let an answerer see, and nothing else."""
    ratified = [q for q in desk.positions if not q.proposed]
    out = [f"# {desk.name}", "", f"**Asked:** {question}", "",
           "Answer ONLY from what follows. A citation to anything not printed",
           "here is refused by the engine, however real it is.", "",
           "## Sources this desk may rely on", ""]
    out += [f"- **{s.id}** · {s.title} · tier **{s.tier}**" for s in desk.sources]
    if ratified:
        out += ["", "## The firm's own positions — binding, and quoted exactly", ""]
        for q in ratified:
            out += [f"### {q.citation}", "", f"> {q.position}", ""]
    out += ["", "## The authority", ""]
    for p in desk.passages:
        out += [f"### {p.citation}", "", f"> {p.text}", ""]
    return "\n".join(out)


def answer(question: str, desk_name: str, *, position: str = "",
           citation: str = "", escalate: str = "", model: str = "",
           working: str = "", desks: Path = DESKS, keep: bool = True):
    """Put a proposed answer through the production path. Served, or refused.

    `keep` files a refusal in the desk's `unsupported/` queue. It defaults on
    because the queue is the only thing that says what the record is missing, and
    a refusal thrown away is a finding destroyed. Pass `keep=False` only when
    measuring, never when answering.
    """
    desk = record.load(desks / desk_name)
    if escalate:
        proposed = engine.Answer(position="", citation="", escalated=True,
                                 reason=escalate)
    else:
        proposed = engine.Answer(position=position, citation=citation)

    out = engine.serve(proposed, desk, question=question)
    if isinstance(out, engine.Refusal) and keep:
        path = desks / desk_name / "unsupported" / "asked.md"
        existing = (unsupported.parse(path.read_text(encoding="utf-8"))
                    if path.exists() else [])
        unsupported.append(path, unsupported.from_refusal(
            question, proposed, engine.Result(
                "asked", engine.Outcome.WRONG_CAUGHT, reason=out.reason,
                detail=out.detail),
            model=model, existing=existing, desk=desk))
    return out
