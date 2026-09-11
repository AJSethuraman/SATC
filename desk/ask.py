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
import pool
import unsupported

HERE = Path(__file__).resolve().parent
#: One corpus. `dec-kill`, 8 September 2026 — "Kill the desks; one pool."
#: `DESKS` sat here beside it for two days and is gone with the directory.
CORPUS = HERE / "corpus"

#: What an answerer may see, and the omission that matters. `PROBLEMS.md` is the
#: answer key: a desk scored against problems its answerer could read measures
#: transcription. A PROPOSED position is likewise withheld — it is one agent's
#: suggestion nobody has said yes to, and showing it would let a guess become the
#: next agent's premise, which is the whole failure the two-store split prevents.
SHOWN = ("sources", "ratified positions", "stored authority")


#: The corpus is read once per process, not once per question. `pool.stats` is
#: an O(corpus) pass and `record.load` parses every passage off disk; doing
#: both per call turned a question into a full re-read of the record. Keyed by path so
#: a test pointing at a fixture corpus is not served the production one.
_LOADED: dict = {}


def _corpus(where: Path):
    """`(record, pool, stats)` for a corpus directory, read once."""
    key = str(Path(where).resolve())
    if key not in _LOADED:
        held = pool.assemble(where)
        _LOADED[key] = (record.load(where), held, pool.stats(held))
    return _LOADED[key]


def looked(question: str, corpus: Path = CORPUS, *,
           limit: int = 8) -> tuple:
    """What the pool returns for this question, before any of it is rendered.

    SPLIT OUT OF `consult` BY `dec-coverage`. `consult` used to return "" when
    nothing was found, and callers tested that emptiness to decide whether the
    corpus held anything. It no longer returns "" — silence is a document now,
    for the reason below — so the question "did anything come back" needs an
    answer that is not the brief's length.
    """
    held, stats = _corpus(corpus)[1], _corpus(corpus)[2]
    return pool.look(question, held, limit=limit, known=stats)


def nothing_on_file(question: str, corpus: Path = CORPUS) -> str:
    """What comes back when the corpus holds nothing that shares this question's
    language. A DOCUMENT, never an empty string.

    `dec-coverage`, 10 September 2026 — the firm: **"Both."** Say why the
    silence is silence, and build the missing coverage. Forge-Occam, reporting
    the failure this closes:

        "silence is indistinguishable from 'there is nothing to say here.'
         A doer reads it as permission. I nearly did."

    THAT IS THE WHOLE ARGUMENT AND IT IS NOT ABOUT POLITENESS. An empty return
    is ambiguous between two opposite findings — *nothing here settles this, go
    and ask* and *nothing here objects, carry on* — and a doer under time
    pressure reads the second. A firm's record cannot afford a silence that
    reads as approval, so there is no silence: there is a short paper saying
    what was searched, what it holds, and what to do next.

    IT SAYS WHAT WAS SEARCHED, WITH NUMBERS. "Nothing found" from a corpus of
    twelve citations and from one of 785 are different findings, and only one of
    them means the question is unusual.

    AND IT NAMES THE ASKER'S OWN WORDS. Measured 11 September 2026: "what do i
    do with it? we bought a forklift" reaches nothing, while the same
    transaction as "is the invoice price deducted or capitalized?" reaches eight
    passages including the firm's own $2,500 threshold. The cause is two words —
    `bought` and `forklift` appear in none of the 785 stored passages, while
    `purchase` appears in 85. Told only that nothing was found, a doer concludes
    the firm holds no authority on forklifts. They hold it under other words.

    THE LIST IS EXHAUSTIVE AND THAT IS NOT A COINCIDENCE — it is every
    substantive word in the question, necessarily, because the moment ONE of
    them is on file some passage scores above zero and this page is never
    reached. So naming them says exactly what the asker can act on (these are
    the words that missed) and NOTHING about whether a rule exists. The page
    says both halves. A version that named the words and implied the rule was
    probably there would be guessing with evidence attached.

    IT PROPOSES NOTHING. `pool.unseen` is a lookup against the word counts the
    corpus already has; it never returns a word the asker did not type. The day
    it suggests `purchase` it is the word list `dec-kill` deleted wearing a
    kinder name.
    """
    desk, held, known = _corpus(corpus)
    never = pool.unseen(question, known)
    return "\n".join([
        f"# {desk.name}{(' · desk ' + record.VERSION) if record.VERSION else ''}",
        "",
        f"**Asked:** {question}",
        "",
        "## Nothing on file addresses this",
        "",
        f"Searched every citation the firm has admitted — **{len(held)}** of "
        f"them, across **{len(desk.sources)}** publications — and not one shares "
        f"enough language with this question to be worth putting in front of "
        f"you.",
        "",
        *(["**The words that missed: "
           + ", ".join(f"`{w}`" for w in never)
           + "** — every substantive word you used, and the record has never "
             "seen any of them. That is always true when nothing comes back "
             "here (one word on file and something would have), so it tells "
             "you which words missed and it tells you nothing about whether a "
             "rule exists. The authority writes in its own vocabulary and a "
             "person writes in theirs, so saying the same thing the way a rule "
             "would say it is worth one try before parking it — and if that "
             "reaches nothing either, park it knowing the wording was not the "
             "problem. Which words to try is yours; nothing here will suggest "
             "one, because a list of what a word means instead is the list "
             "`dec-kill` deleted.",
           ""] if never else []),
        "**This is not permission.** It does not mean the answer is no, and it "
        "does not mean nobody objects. It means nothing on file reached this "
        "question, so there is nothing here to be right or wrong with — and an "
        "answer given anyway would be yours rather than the record's.",
        "",
        "**What to do.** Park it: the question goes to the firm with your "
        "working, and their answer is what builds the coverage that is missing. "
        "`ask.consult_or_file` does that in one call. Do not answer from "
        "memory, and do not read this page as a quiet yes.",
        "",
    ])


def consult(question: str, corpus: Path = CORPUS,
            context: record.Context | None = None, *, limit: int = 8) -> str:
    """Everything the corpus will let you answer this from — or why it will not.

    ONE CORPUS, ONE BRIEF. This returned `[(desk name, brief)]` until
    10 September 2026, because a question reached one desk or several and each
    got its own. `dec-kill` — *"Kill the desks; one pool"* — ends that: there is
    no desk to name, and a list of one is a shape that only makes sense to
    somebody who remembers the thing it replaced.

    WHAT NARROWS IT. `pool.look` scores every citation in the corpus on the
    authority's OWN TEXT and this brief is built from the top `limit`. Handing
    over the whole corpus instead is two orders of magnitude more text — an
    answerer given everything is an answerer given nothing, and a model with
    an 8,192-token window (LOCAL-LLM-PATTERN rule 1) is given less than nothing.

    IT NO LONGER RETURNS "". `dec-coverage`: an empty return is ambiguous
    between *nothing settles this* and *nothing objects*, and a doer reads the
    second. `nothing_on_file` says which, in words, with the size of what was
    searched. Callers deciding whether the corpus HOLDS anything ask `looked`.

    SILENCE IS STILL A RESULT and it is still the retriever's weakest claim.
    A SCORE cannot tell you that nothing on file answers a question — measured,
    and `test_a_score_cannot_tell_you_nothing_answers_this.py` holds the
    numbers: the two populations overlap almost completely, and a question no
    tax authority anywhere addresses outscores most of the ones the corpus
    really answers. So this returns what it found and the ENGINE decides whether
    any of it binds. That is `dec-books` — *"it looks for sources and conveys
    and if it is not directly authoritative it would run the opinion by me"* —
    and a threshold here would be this function deciding on a word count what
    the whole engine exists to decide properly.
    """
    found = looked(question, corpus, limit=limit)
    if not found:
        return nothing_on_file(question, corpus)
    return brief(question,
                 _corpus(corpus)[0].narrowed_to([f.held.citation for f in found]),
                 context)


def consult_or_file(question: str, *, queue: Path, corpus: Path = CORPUS,
                    context: record.Context | None = None,
                    model: str = "") -> tuple[str, object]:
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
    # ASKED OF THE POOL, NOT OF THE BRIEF'S LENGTH. `consult` returns a
    # document either way since `dec-coverage`, so testing it for emptiness
    # would file every question ever asked.
    if looked(question, corpus):
        return consult(question, corpus, context), None
    queue = Path(queue)
    existing = (unsupported.parse(queue.read_text(encoding="utf-8"))
                if queue.exists() else [])
    # THE REASON CARRIES THE EVIDENCE OR IT IS A SHRUG. `tools/holes.py` reads
    # this out to the firm, and "nothing shares a word with this question" is
    # the same sentence on every row: it cannot be sorted, compared or acted on.
    # The WORDS can: a row reading `bought, forklift` and one reading `crypto,
    # staking` are a vocabulary gap and a coverage gap, and the firm can see
    # which is which at a glance without being told by us -- which is the point,
    # because telling them would be a judgement nothing here has earned.
    #
    # THE SECOND HALF OF THAT EXAMPLE STOPPED BEING FILED ON 11 SEPTEMBER.
    # "how do we handle crypto staking rewards?" reached nothing until
    # `dec-fullstop`, because Pub. 525's section opens "Rewards." and the pool
    # held the full stop. It reaches that section now and is never filed. The
    # example is kept because it is what the mechanism is FOR, and marked
    # because an example that no longer happens should not read as one that
    # does.
    never = pool.unseen(question, _corpus(corpus)[2])
    why = "nothing in the corpus shares a word with this question"
    if never:
        why = ("the corpus has never seen any word in this question: "
               + ", ".join(never))
    entry = unsupported.from_question(
        question,
        why=why,
        model=model,
        existing=existing,
    )
    unsupported.append(queue, entry)
    # THE EXPLANATION, NOT "". `dec-coverage`: the caller that just had its
    # question parked is exactly the caller who must not read the result as
    # permission, and returning an empty string here would have left that one
    # path silent while every other path spoke.
    return nothing_on_file(question, corpus), entry


def against(position, corpus: Path = CORPUS, *, limit: int = 8) -> tuple:
    """The authority nearest an uncited position, for somebody to read AGAINST it.

    THE SECOND OF THE FIRM'S TWO CONDITIONS ON `dec-pos2`, and it is the risk
    that arrives with the approval rather than an objection to it:

        "I would also be remiss if something I said is my position blatantly
         goes against a regulation or something. I would want the option to
         review that too though"

    THE INVERSE OF A CITATION CHECK. Every other gate here asks *what proves
    this* — a citation resolves, a paragraph carries a conclusion, a second
    reader quotes the words. An uncited position has nothing to run those on,
    and the question that matters about it is the other one: **does anything on
    file contradict it.** That is not answerable by lookup, so this does the
    half that is — it finds what the corpus holds nearest the position's own
    words and hands it over to be read.

    THE POSITION'S OWN WORDS ARE THE QUERY. A hand-written list of what to check
    a policy against is written by whoever is proposing the policy, which is the
    preparer verifying their own work (C6). `pool.look` scores the corpus on the
    position's title and text, so what comes back is what the RECORD says is
    nearest, and a reviewer can disagree with it out loud.

    IT DOES NOT DECIDE, AND NOTHING HERE PRETENDS OTHERWISE. Whether a paragraph
    contradicts a policy is a reading, and readings in this operation are made
    by a named party quoting words — `judging.read` for an answer, the firm for
    a policy. A version of this that returned "contradicted: yes/no" would be
    the thing `dec-books` says not to build.
    """
    return looked(f"{position.title} {position.position}", corpus, limit=limit)


def review_brief(position, corpus: Path = CORPUS, *, limit: int = 8) -> str:
    """What goes in front of whoever answers *does anything here contradict it*.

    THE FIRM IS THE READER, so this is prose and not a list of citation labels:
    the question is not answerable from a label. It prints the position in their
    own words, then the paragraphs the record puts nearest it, then the one
    question it is asking — and it says what a `yes` and a `no` each mean, so
    the answer that comes back can be written into `Reviewed:` without anybody
    interpreting it.
    """
    desk = _corpus(corpus)[0]
    found = against(position, corpus, limit=limit)
    out = [f"# Does anything on file contradict {position.id}?", "",
           f"**{position.title}**", "",
           f"> {position.position}", ""]
    if position.why:
        out += ["*Why the firm holds it:*", "", f"> {position.why}", ""]
    out += [
        f"This is **firm policy**. It rests on the firm rather than on a "
        f"paragraph, and it is cited to nothing — which is why it is being put "
        f"in front of you: an uncited position is the kind that can sit against "
        f"authority with nothing noticing.", "",
        "## The nearest authority on file", "",
    ]
    if not found:
        out += ["Nothing in the record shares enough language with it to be "
                "worth reading against it. **That is not a clean bill.** It "
                "means the corpus holds nothing near this policy, so nobody "
                "here can say whether authority contradicts it — which is a "
                "coverage answer, not a review one.", ""]
    else:
        out += [f"Searched every citation the firm has admitted — "
                f"**{len(desk.passages)}** of them — and these are the "
                f"**{len(found)}** nearest this policy's own words. They were "
                f"chosen by word overlap, not by anybody deciding they bear on "
                f"it.", ""]
        for hit in found:
            out += [f"### {hit.held.citation}", "",
                    f"*{hit.held.tier} · {hit.held.source_id}*", "",
                    f"> {hit.held.text}", ""]
    out += [
        "## What is being asked", "",
        "**Does any of that contradict the position above?**", "",
        "- **No** — the policy stands as written, and this review is recorded "
        "against it with the date. It can be asked again whenever the record "
        "grows.",
        "- **Yes, and here is the paragraph** — the policy is wrong, or it is "
        "narrower than it reads, and either way it stops being served until you "
        "have said which.",
        "- **It is nearby and does not settle it** — the commonest answer, and "
        "it is a real one. Recorded the same way.", "",
        "Nothing is decided here. This is the material; the reading is yours.",
        "",
        "---",
        "",
        f"*Assembled by `ask.review_brief` from the corpus at desk "
        f"{record.VERSION or 'unversioned'}. Not written by hand and not edited "
        f"afterwards — re-run it and it comes back the same, or comes back "
        f"different because the record moved.*",
        "",
    ]
    return "\n".join(out)


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
    # THE ANSWERING CONTRACT, AND IT USED TO LIVE SOMEWHERE ELSE.
    #
    # `tools/ask_the_desks.py` carried a SECOND brief with these lines in it,
    # kept in step with this one by nobody. The tool was the only thing that
    # ever told an answerer the shape to return or what `ask` is for; the live
    # path said "escalate `authority_absent`" and left the rest to be guessed.
    # `dec-kill` deleted the duplicate, so the instructions move here rather
    # than going with it — a brief that is wrong now is wrong in production,
    # where somebody sees it.
    # HOW THESE WERE CHOSEN, SAID OUT LOUD. The other half of `dec-coverage`.
    #
    # The first half is `nothing_on_file`: an empty result must not read as
    # permission. This is the case that is easier to miss and harder to fix —
    # a result that is not empty and settles nothing. `pool.look` scores every
    # citation on word overlap with the question, weighted by rarity, and it
    # ALWAYS RETURNS SOMETHING when any word matches. Measured: *"Which sonnet
    # did Shakespeare write about a summer day?"* comes back with 7,384
    # characters of tax authority, more than the real prepaid-insurance
    # question's 5,060, and
    # `test_a_score_cannot_tell_you_nothing_answers_this.py` establishes that no
    # score cutoff separates the two populations — five of six questions with no
    # answer on file outscore the weakest question that has one.
    #
    # SO THE CUTOFF CANNOT BE HERE AND THE DISCLOSURE CAN. An answerer told
    # nothing about how these arrived reads "here is the authority" as "here is
    # the authority ON THIS", which is the same misreading as silence-as-
    # permission, one step further in. The engine still decides what binds;
    # this is what stops a model doing the engine's job badly first.
    out += ["**These paragraphs were chosen by word overlap with your "
            "question, not by anybody deciding they answer it.** Being shown a "
            "passage is not evidence that it settles anything — the corpus "
            "returns its closest text for every question, including questions "
            "it holds no authority on at all. If none of it reaches what you "
            "were asked, say so and escalate `authority_absent`; that is a "
            "finding, not a failure.", ""]
    out += ["## What you must return", "",
            "```json",
            '{"position": "<your conclusion, one short line>",',
            ' "citation": "<one citation, copied EXACTLY from a heading below>",',
            ' "working": "<why that paragraph settles it>"}',
            "```", "",
            "Or, if nothing below settles it:", "",
            "```json",
            '{"escalated": true, "reason": "<one of: authority_absent, '
            'authority_permits_choice, facts_not_established>", "working": '
            '"<what is missing>", "ask": "<the question a person must answer>"}',
            "```", "",
            "**`facts_not_established`** is the right answer when the rule is "
            "clear and what you do not know is a fact about the client — what "
            "was bought, which entity, which period. It is not a failure; it "
            "is the answer that says who has to be asked.", "",
            "**On that reason you MUST fill in `ask`, and the engine refuses "
            "without it.** Name the fact and say what would settle it, in "
            "words a preparer can act on — *\"What was the invoice amount? "
            "Under $2,500 the safe harbour may reach it.\"* — not *\"more "
            "information needed\"*. A refusal that names a gap and not the "
            "question is a dead end wearing a reason code, and it is the "
            "difference between a queue somebody can work and a count.", ""]
    # WHICH FACTS BEAR ON THIS QUESTION, and it is not all of them any more.
    #
    # ONE CORPUS MADE THIS NECESSARY. Each of the seven records declared the
    # facts ITS positions turned on -- `trade` on personal-or-business,
    # `capitalization_rule` on capitalization-and-de-minimis, `taxpayer` on
    # rewards -- and a question reaching one desk saw one field. `dec-kill`
    # merged them, so `desk.records` is now the union and an unnarrowed brief
    # announces all three on every question. That is not merely noisy: two of
    # them come back "NOT ON FILE" on any given question, and the line beside
    # them tells the answerer to escalate rather than answer from a rule that
    # needs it. A hairstylist question would invite `context_not_on_file` about
    # a capitalization threshold nothing shown turns on.
    #
    # SO A FIELD IS PRINTED WHEN IT BEARS ON WHAT IS SHOWN: we already know it
    # (a fact on file is context whatever the question), or a position printed
    # above needs it. Fields that are neither are silent -- not hidden, since
    # `desk.records` is untouched and `unrecorded` still checks against the
    # whole of it, so a fact with nowhere to live is still the hole it was.
    needed = {f for q in ratified for f in getattr(q, "needs", ())}
    bearing = [name for name in desk.records
               if str(context.facts.get(name, "")).strip() or name in needed]
    if bearing:
        # WHAT WE WERE TOLD, AND -- THE HALF THAT MATTERS -- WHAT WE WERE NOT.
        # Printing only the facts on file leaves an answerer to assume the rest
        # were not needed. Printing the gaps by name is what lets it escalate
        # `context_not_on_file` instead of reasoning from the vendor, which is
        # the failure this whole input exists to stop.
        out += ["## What the file already says", ""]
        for name in bearing:
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
        # COPY THE POSITION, DO NOT RESTATE IT -- and the brief has to say so.
        #
        # `engine._same` compares a submitted position to the firm's word by
        # EXACT string equality (case and surrounding space aside), on purpose:
        # "a looser comparison here would quietly turn wrong answers into right
        # ones, which is the one direction this code must never fail in."
        #
        # The header alone never carried it. On the 8 September pilot four of
        # twelve answered attempts came back `contradicts_ratified_position`
        # while AGREEING with the firm -- Q6, Q7, and Q31 on two desks --
        # because an answerer told a position is "binding" naturally
        # paraphrases it. Re-serving the same run with the four positions
        # copied verbatim and nothing else changed took it from 3 served to 7.
        # A third of the run was measuring this paragraph's absence.
        out += ["**If you rely on one of these, copy its wording EXACTLY into "
                "`position`.** The engine compares what you submit to the "
                "firm's sentence character for character and refuses anything "
                "else as a contradiction, however much you agree with it. Put "
                "your own words in `working`, never in `position`.", ""]
        for q in ratified:
            out += [f"### {q.citation}", "", f"> {q.position}", ""]
            # A POLICY SAYS WHAT IT IS WHERE IT IS READ. `dec-pos2`, the firm's
            # first condition: *"I want this to be clearly marked as they may
            # need to be reviewed/changed at some point."* `engine.serve` puts
            # the same thing on the answer that leaves; this puts it in front of
            # the answerer BEFORE they rely on it, which is the difference
            # between a disclosure and a footnote.
            if getattr(q, "is_policy", False):
                out += ["**This is the firm's own standing policy, not "
                        "authority.** It rests on the firm and there is no "
                        "paragraph behind it to go and read. It binds — where "
                        "the firm has spoken, their words are the answer — and "
                        "it may be reviewed or changed. "
                        + ("Nobody has yet read it against what is on file."
                           if getattr(q, "unreviewed", False) else
                           f"Read against the record: {q.reviewed}"), ""]
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


def answer(question: str, *, position: str = "",
           citation: str = "", escalate: str = "", model: str = "",
           working: str = "", ask: str = "", corpus: Path = CORPUS,
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
    # ONE CORPUS. This took a `desk_name` until 10 September 2026 and loaded
    # `desks/<name>/`; `dec-kill` deleted the desks, so there is nothing to name
    # and nothing to choose between. The citation identifies the authority, which
    # is what it always did — the desk was only ever the folder it sat in.
    desk = _corpus(corpus)[0]
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
            attempts.record(corpus, out.proof)
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
            attempts.record(corpus, p)
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
    # AND AN OFF-SOURCE ANSWER NEEDS ONE WHATEVER THE DESK DECLARED.
    #
    # The firm, 8 September 2026, choosing "leave it demoted, add the judgment
    # requirement" after Forge-Desk measured that the judge does NOT by itself
    # catch what the source map used to block. `Served.off_source` marks an
    # answer whose citation came from a source this desk does not declare for
    # this subject -- exactly the class that used to be refused outright. It is
    # served now, so the one thing that must not also be optional is that
    # somebody read the paragraph.
    #
    # THIS DOES NOT CLOSE MISJUDGMENT and nothing here pretends it does: a
    # careless yes still serves. It closes OMISSION on the class where omission
    # is least affordable, on every desk rather than only the ones that opted in.
    needs = desk.needs_a_judge or bool(getattr(out, "off_source", ""))
    if needs and isinstance(out, engine.Served) and out.judged is None:
        out = engine.Refusal(
            "not_judged",
            (f"this answer cites a source {desk.name} does not declare for "
             f"this subject, so it is not served until a second reader has "
             f"looked at the paragraph, and none was supplied. "
             if getattr(out, "off_source", "") and not desk.needs_a_judge else
             f"{desk.name} does not serve an answer no second reader has "
             f"looked at, and none was supplied. ")
            + f"Nothing is wrong with the answer or with the record — the "
              f"engine checked what it can check and the one thing it cannot "
              f"is whether {out.citation!r} carries {out.position!r}",
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
        path = corpus / "unsupported" / "asked.md"
        existing = (unsupported.parse(path.read_text(encoding="utf-8"))
                    if path.exists() else [])
        # THE REFUSAL ITSELF, NOT A `Result` BUILT FROM THREE OF ITS FIELDS.
        #
        # `dec-fields`, 10 September 2026. `Unsupported` carries `needs_field`
        # and `asked_by` — the fact that has nowhere to live and the position
        # that asked for it — and `from_refusal` reads them off `result.fact`
        # and `result.by_position`. `engine.Result` HAS NEITHER FIELD. So every
        # `no_field_for_this_fact` ever filed on the live path landed with both
        # empty: a field request with no field named and no chain back to the
        # position behind it, which is exactly what the firm made the condition
        # of approving field requests at all.
        #
        # The whole channel existed — the dataclass, the parser, the renderer,
        # `tools/holes.py` reading it — and nothing had ever put anything in it.
        # Verified before fixing, by filing one and reading the file back.
        #
        # `Refusal` already carries everything `from_refusal` reads: `reason`,
        # `detail`, `ask`, `fact`, `by_position`. Handing it over directly is
        # one fewer shape to keep in step, and the shape that was NOT kept in
        # step is what this bug was.
        unsupported.append(path, unsupported.from_refusal(
            question, proposed, out, model=model, existing=existing, desk=desk))
    return out
