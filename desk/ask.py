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


def consult_or_file(question: str, *, queue: Path, desks: Path = DESKS,
                    context: record.Context | None = None,
                    model: str = "") -> tuple[list[tuple[str, str]], object]:
    """`consult`, and FILE the question when no desk holds it.

    SILENCE WAS THE ONE OUTCOME THAT LEFT NO RECORD. `consult` returning empty
    is a real result -- no expert here holds the question, and inventing one is
    what the routing exists to stop -- and `be-the-desk` says so. But a desk
    that refuses leaves a refusal `tools/holes.py` reads out, while a question
    that reached NO desk left nothing at all. On a close that is the worst of
    the three: the doer gets nothing back, and the firm never learns the
    question was asked.

    The firm, 8 September 2026, setting exactly this expectation:

        "You do not prep it with information and if it can't get the
         information that means there's an actual hole."

    MEASURED the same day, on twenty month-end questions in a bookkeeper's own
    words: fifteen reached a desk and FIVE reached nothing. Two of the five were
    subjects a desk already holds and the routing missed.

    IN CODE RATHER THAN IN THE SKILL, for the reason the README already gives
    about the citation rule: the same policy written as skill prose was obeyed
    "100%, 4%, 0% of runs". `unsupported.from_question` existed and was reachable
    only from a batch tool somebody runs by hand.

    Returns `(briefs, filed)`. `filed` is None whenever a desk answered -- a
    queue that grew a row per question would be a traffic log, and the count
    would stop meaning anything.
    """
    briefs = consult(question, desks, context)
    if briefs:
        return briefs, None
    queue = Path(queue)
    existing = (unsupported.parse(queue.read_text(encoding="utf-8"))
                if queue.exists() else [])
    entry = unsupported.from_question(
        question,
        why="no desk holds this subject — routing reached nothing",
        model=model,
        existing=existing,
    )
    unsupported.append(queue, entry)
    return [], entry


def brief(question: str, desk: record.Desk,
          context: record.Context | None = None) -> str:
    """Everything the desk will let an answerer see, and nothing else."""
    ratified = [q for q in desk.positions if not q.proposed]
    context = context or record.NOTHING_ON_FILE
    # THE RUNNING CODE SAYS WHAT IT IS, in the one artifact an answerer always
    # reads. See `record._version`: a session was served a five-release-stale
    # `ask-desk` on 8 September, and the version warning meant to catch that
    # lives in the file that did not load. This line comes from the code doing
    # the work, so a skill claiming something else is visibly wrong.
    stamp = f" · desk {record.VERSION}" if record.VERSION else ""
    # THE SECOND PARAGRAPH IS NEW AND THE FIRST IS NOT WEAKENED. Until 0.13.1
    # this said only the first thing, and it was the whole ceiling: everything
    # outside the stored corpus refused, the searcher found the rule, and the
    # trail stopped at the firm because a source had to be admitted before any
    # desk could cite it. Verification is the gate now (#343) -- but the gate is
    # a FETCH, not the answerer's word, so the instruction has to be exact about
    # what is being asked for. Quoting from memory is the failure this engine
    # exists to stop and it must not read as newly permitted.
    out = [f"# {desk.name}{stamp}", "", f"**Asked:** {question}", "",
           "Answer ONLY from what follows. A citation to anything not printed",
           "here is refused by the engine, however real it is.", "",
           "If the rule you need is NOT printed here, do not cite it from",
           "memory — escalate `authority_absent`. If you have been given a way",
           "to fetch, you may instead hand in the URL you found it at and the",
           "exact words you are resting on: the engine will fetch that page and",
           "serve only if those words are on it right now. It will not take",
           "your word for what the page says.", ""]
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
    # WHAT WE WERE TOLD AND CANNOT HOLD. See `record.Context.unrecorded`: these
    # were passed by the caller and match no field this desk declares, so before
    # 0.9.3 they were dropped in silence -- and a desk went on to serve an answer
    # resting on one of them. They are printed here NOT as facts on file but as
    # the opposite: a fact with nowhere to live is `no_field_for_this_fact`, a
    # hole the firm has to decide about, and the answering side is the only
    # place that can notice it.
    if unrecorded := context.unrecorded(desk.records):
        out += ["## Told to us, and this desk has NOWHERE to record it", ""]
        for name in unrecorded:
            out.append(f"- **{name}** — NOT ON FILE and cannot be put on file. "
                       f"No desk field exists for it.")
        out += ["",
                "**These are not facts you may answer from.** Nobody decided "
                "this should be written down, so nothing verified it, nothing "
                "will retain it, and the next agent asked the same question "
                "will not have it. If your answer turns on one of them, "
                "escalate `no_field_for_this_fact` and name it — that is a "
                "hole the firm has to decide about, and a preparer who had to "
                "hand it over has just found it by doing the work.", ""]
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
                # AND IT SAYS SOMETHING DIFFERENT ONCE THE FACT IS ON FILE.
                #
                # This was one static string: *"nothing here says whether this
                # one is. The desk will ask rather than assume."* True and
                # load-bearing while the field is empty — and FALSE the moment
                # the follow-up loop 0.9.2 exists to close actually succeeds,
                # because then the brief does say, twelve lines above.
                #
                # Found by the desk session on the first run where the loop
                # worked, 8 September 2026: *"'Nothing here says whether this
                # one is' is false in that exact brief. The brief says. It is a
                # static string that is not conditioned on whether the fact it
                # names is present [...] Since 0.9.2 exists to make that loop
                # work, this is the sentence it breaks."*
                told = [f for f in q.unless if str(context.facts.get(f, "")).strip()]
                if silent := [f for f in q.unless if f not in told]:
                    out += [f"This is the firm's DEFAULT. It does not apply to "
                            f"a client the firm treats differently on "
                            f"{', '.join(silent)}, and nothing here says "
                            f"whether this one is. The desk will ask rather "
                            f"than assume.", ""]
                if told:
                    out += [f"The file says this client is on the firm's "
                            f"default for {', '.join(told)} — printed above, "
                            f"in the caller's words. So this position applies "
                            f"unless what is recorded there says otherwise; "
                            f"read it before relying on this.", ""]
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
           context: record.Context | None = None, prove=None, judged=None,
           found_at: str = "", found_text: str = ""):
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

    `found_at` AND `found_text` ARE THE CANDIDATE PATH. Where the gate refuses
    `authority_absent` -- the record does not hold this citation -- and the
    caller has both a transport and a URL it found the rule at, the answer is
    served if and only if `found_text` is on that page right now. `candidates.py`
    is the whole of it, including the two checks that run before any fetch.

    BOTH ARE REQUIRED, and passing neither leaves behaviour byte-identical to
    before. A URL with no words is nothing to compare; words with no URL is the
    model's own recollection, which is the thing this engine exists not to serve.

    EVERY ATTEMPT IS RECORDED, WHATEVER IT DID, into the desk's `tie-outs/`
    store, under `keep` like a refusal is. The firm asked for it in as many
    words -- *"It should state what happened when trying to tie it out. I need
    info to make decisions down the line."* -- and the decisions it is for are
    about PUBLISHERS rather than about any one answer: one unreachable source is
    a shrug, forty against the same host is a source to retire. `attempts.py`
    says what is written and what is deliberately not.

    `judged` IS A SECOND READER'S VERDICT, and it is the same trade as `prove`:
    an input, never something this function goes and obtains. Pass a
    `judging.Judgment` -- who read the passage, whether it carries the
    conclusion, and the words they rest that on -- and the engine checks the one
    thing about it that is checkable without reading: that those words are in
    the passage. Pass nothing and nothing is checked, which is what the whole
    suite passes today.

    IT RUNS LAST, AFTER THE PROOF, and for the same reason the proof runs after
    the gate: each stage may add a refusal and none may remove one. Judging an
    answer whose passage the publisher no longer carries would be a second
    reader confirming text that has already been withdrawn.

    NOTHING REQUIRES A JUDGMENT. Which desks may not serve unjudged is the
    firm's decision and is on the docket; a gate that turned itself on across
    seven desks overnight would be this session making it.
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

    # WHAT THE PUBLISHER ACTUALLY SERVED, held for the judge and for nothing
    # else. It is captured through a WRAPPER rather than added to `Proof`,
    # deliberately: `Proof` is evidence a reader re-checks by hand, every field
    # of it is short, and the log takes the repr -- a whole fetched document on
    # that object would end up in a log line the first time anything printed
    # one. This lives for the duration of the call and is written nowhere.
    fetched = {}

    def _watching(source, citation):
        raw = prove(source, citation)
        fetched["text"] = raw.text if hasattr(raw, "text") else str(raw)
        return raw

    transport = _watching if prove is not None else None

    out = engine.serve(proposed, desk, question=question, context=context)
    # THE CANDIDATE PATH, and it sits exactly here for a reason: AFTER the gate
    # has run and refused. It can therefore add a refusal and can never remove
    # one, which is the property every stage in this function has.
    #
    # `authority_absent` ONLY. It is the one refusal that says "the record does
    # not hold this", and the record not holding something is the whole of what
    # a live proof answers. Every other refusal is a finding about the question,
    # the client or the authority, and a fetch says nothing about any of them.
    if (isinstance(out, engine.Refusal) and out.reason == "authority_absent"
            and prove is not None and found_at and found_text):
        import attempts
        import candidates
        out = candidates.consider(
            question=question, position=position, citation=citation,
            url=found_at, text=found_text, desk=desk,
            transport=transport)
        if keep and getattr(out, "proof", None) is not None:
            attempts.record(desks, desk_name, out.proof)
    # `out.proof is None` MEANS NOT YET PROVED, and it is what keeps the two
    # paths from proving the same answer twice. A candidate arrives here already
    # carrying its proof; running the stored path over it would resolve its
    # citation in a record that does not hold it, get COULD NOT, and OVERWRITE
    # a TIED proof with a failure — the served answer looked right and its
    # evidence was replaced by the evidence of a lookup that could not have
    # worked. `engine.serve` never sets this field, so the condition is exact.
    if prove is not None and isinstance(out, engine.Served) and out.proof is None:
        import dataclasses

        import attempts
        import proving
        p = proving.prove(out, desk, transport)
        if p.verdict == proving.DIFFERS:
            out = engine.Refusal(
                proving.MOVED,
                f"{out.citation!r} resolves in this desk's record, and the "
                f"publisher no longer carries it: {p.note}. The record is the "
                f"only witness to that text, which is not enough to serve it on",
                ask=f"Re-read {p.url or out.citation} and bring the stored "
                    f"passage back into line with it, or retire the citation. "
                    f"Until then this desk has no authority for the answer.",
                # THE WITHDRAWAL CARRIES ITS OWN EVIDENCE. This refusal exists
                # BECAUSE something was fetched, and before the field existed it
                # was the one refusal in the engine nobody could re-run by hand:
                # the note survived inside a sentence and the host, the moment
                # and the digest did not.
                proof=p, desk=desk.name)
        else:
            out = dataclasses.replace(out, proof=p)
        # RECORDED WHATEVER IT DID, and gated by `keep` for the same reason
        # refusals are: `keep=False` means measuring. The firm asked for this in
        # as many words -- *"It should state what happened when trying to tie it
        # out. I need info to make decisions down the line."* -- and a decision
        # about a PUBLISHER cannot be made from the one attempt in front of you.
        # A TIED is kept too: a source that ties out for months and then stops is
        # only visible if the months were written down.
        if keep:
            attempts.record(desks, desk_name, p)
    if judged is not None and isinstance(out, engine.Served):
        import dataclasses

        import judging

        # THE FETCHED DOCUMENT WHERE THERE IS ONE, our stored copy otherwise --
        # the firm, 8 September 2026: *"it is handed in with the suggestion so
        # the judge can actually assess it."* A judgment checked against our own
        # copy establishes that the judge read what WE hold, which is a weaker
        # claim than that they read what the PUBLISHER holds, and `Read.against`
        # is what lets a reader tell the two apart afterwards.
        live = fetched.get("text", "")
        seen = judging.read(
            judged, live or out.passage, answered_by=model,
            against=("the document fetched from the publisher" if live
                     else "this desk's stored passage"))
        if seen.verdict == judging.SAYS_NO:
            out = engine.Refusal(
                "citation_does_not_support",
                f"{out.citation!r} resolves and this desk does hold it, and a "
                f"second reader ({seen.by}) says the paragraph does not carry "
                f"{out.position!r}: {seen.because}. Real authority in front of "
                f"the wrong question is the one error every exact check in this "
                f"engine passes",
                ask=f"Cite the paragraph that answers what was asked, or "
                    f"escalate that no authority here reaches it. Do not re-run "
                    f"this with a softer conclusion until it serves.",
                desk=desk.name)
        elif seen.verdict == judging.NOT_IN_THE_PASSAGE:
            out = engine.Refusal(
                "judgment_not_in_the_passage",
                f"{seen.by} judged {out.citation!r} to support {out.position!r} "
                f"and quoted {seen.missing!r}, which is not in the passage. The "
                f"answer is not refused on its merits — nobody has read it. A "
                f"judgment that quotes what is not there is not a second reading",
                ask=f"Judge it again against the passage as stored, quoting "
                    f"what it says. `[...]` marks a gap you are skipping.",
                desk=desk.name)
        else:
            out = dataclasses.replace(out, judged=seen)
    # THE DESK'S OWN DECLARATION, and the firm's answer on the docket: *"The
    # judge can look at it all I guess?"* -- all seven. It runs LAST, after the
    # proof and after a supplied judgment has been checked, because every stage
    # here may add a refusal and none may remove one.
    #
    # `out.judged is None` MEANS NOBODY READ IT, and it is the exact condition
    # for the same reason `out.proof is None` is: the engine never sets the
    # field, so it is set if and only if a judgment came in and passed the
    # check above. Written as `judged is None` -- the argument rather than the
    # result -- this fired on answers a second reader HAD read, because a
    # judgment that says SAYS_NO or NOT_IN_THE_PASSAGE has already refused by
    # then and one that HOLDS is on the object, not in the argument.
    if desk.needs_a_judge and isinstance(out, engine.Served) and out.judged is None:
        out = engine.Refusal(
            "not_judged",
            f"{desk.name} does not serve an answer no second reader has looked "
            f"at, and none was supplied. Nothing is wrong with the answer or "
            f"with the record — the engine checked what it can check and the "
            f"one thing it cannot is whether {out.citation!r} carries "
            f"{out.position!r}",
            ask=f"Have a party OTHER than the one that answered read the "
                f"passage and say whether it carries the conclusion, quoting "
                f"the words they rest that on. Pass it as "
                f"`judged=judging.Judgment(by=..., supports=..., because=...)`. "
                f"One model wearing both hats raises rather than serves.",
            desk=desk.name)
    # AND THIS ONE IS NOT FILED. `unsupported/` is what says the RECORD is
    # missing something; a missing judgment is a caller contract and the record
    # is complete. Filing it would put a work item in a queue nobody can act on
    # and would inflate the one count that is supposed to mean something.
    if isinstance(out, engine.Refusal) and keep and out.reason != "not_judged":
        path = desks / desk_name / "unsupported" / "asked.md"
        existing = (unsupported.parse(path.read_text(encoding="utf-8"))
                    if path.exists() else [])
        unsupported.append(path, unsupported.from_refusal(
            question, proposed, engine.Result(
                "asked", engine.Outcome.WRONG_CAUGHT, reason=out.reason,
                detail=out.detail, ask=out.ask),
            model=model, existing=existing, desk=desk))
    return out
