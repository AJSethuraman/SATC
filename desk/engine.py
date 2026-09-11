"""The engine: verify a citation, then grade. Both jobs, one piece of code.

THE ONE RULE. An answer with no resolvable citation never counts as correct.
This is enforced here rather than asked for in a prompt, because the difference
was measured: the same policy written as skill prose was obeyed "100%, 4%, 0% of
runs"; at the API choke point it "is obeyed always, from every path"
(`docs/LOCAL-LLM-PATTERN.md`, rule 6).

WHY THE SCOREBOARD AND THE GATE ARE THE SAME CODE. C9 -- one mechanism, not two
beside each other. Verification is what converts an answer that would have shipped
wrong into one that was caught, so the thing that grades and the thing that gates
are the same question asked once.

FOUR OUTCOMES, AND THE ORDER THEY ARE REPORTED IN. `wrongly_absorbed` is first
because it is the only one that costs anything: an answer that was wrong, that
the engine could not fault, and that would therefore have reached a client with
nobody the wiser. `escalated` is a SUCCESS -- the desk knew it did not know.
Never sum them into one figure; a single percentage hides the only number that
matters.

VERIFICATION READS STORED TEXT, NEVER THE LIVE SOURCE. Freshness is a different
question, handled by the staleness check. An engine that reached out here would
make every test run depend on a government website being up, and would make
"prove every check can fail" nearly impossible to satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import record as record_mod
from record import Desk, Problem, Source


class Outcome(str, Enum):
    """Reported in this order, always. Never summed."""

    #: Answered, cited, the citation held -- and the answer was wrong anyway.
    #: The engine had nothing to catch it with, so in production this ships.
    WRONGLY_ABSORBED = "wrongly_absorbed"

    #: Answered, cited, and right.
    CORRECT = "correct"

    #: Wrong, and the engine caught it before it left -- the citation did not
    #: resolve, so the answer never had authority behind it.
    WRONG_CAUGHT = "wrong_caught"

    #: The desk declined to answer. A success, and it carries a reason.
    ESCALATED = "escalated"


#: Why a desk could not answer. A closed set, because an open one becomes prose
#: and prose cannot be counted. Each carries a fix, and only the last is not one:
#: a question the rules genuinely leave open is a POSITION, and positions are the
#: firm's. Everything else is a work item.
REASONS = (
    "source_blocked_by_us",     # our own egress policy refused the domain
    "source_refuses_us",        # the source's origin refused this client
    "authority_absent",         # not in the record yet; add it, cited
    "authority_permits_choice",  # NOT fixable. the firm decides.
    "no_citation",              # the answer cited nothing that resolves
    "citation_does_not_support",  # real authority, but not this question's
    "contradicts_ratified_position",  # cited the firm's words, said the opposite
    "facts_not_established",    # the rule is clear; what was bought is not. ASK.
    "document_not_requested",   # a named document settles it and nobody asked
    "context_not_on_file",      # the rule needs a fact the FILE should hold. not the client.
    "no_field_for_this_fact",   # nobody ever decided this should be written down
    "client_rule_governs",      # the file records the firm's own call for THIS client
    "authority_has_moved",      # the publisher no longer carries what we stored
    "wrong_body_of_authority",  # real authority, real subject, wrong universe
    "body_of_authority_unknown",  # nothing classified it, so nothing could check
    "model_gave_up",            # ran out of window or abandoned the task
    "judgment_not_in_the_passage",
    "not_judged",               # this desk may not serve what nobody read  # the second reader quoted words that are not there
)

# THE LAST TWO ARE THE FIRM'S, ASKED FOR ON 6 SEPTEMBER 2026, and they are two
# halves of one sentence. Holding three positions rather than ratifying them:
#
#   "This needs to ensure that there is no already standing rule for that client
#   in particular. The desk should ask that follow up if it is not clear, right?"
#   ... "we shouldn't ignore client level rules set with judgment with the desk
#   answering broadly." ... "if the follow up has no answer we know there's a
#   legit hole to fix because the accountant or firm never assigned it up front.
#   This is also a way to check for bugs or defects while agents perform real
#   work. What if this mattered only sometimes and we never even made a field
#   for it."
#
# `client_rule_governs` IS NOT A FAILURE AND IS NOT A GAP. The file records what
# the firm decided for this client, and it displaces the firm's own default --
# which is what a default means. The desk stops and hands over, because the
# answer exists and is not the desk's to give. It never prints the recorded
# value: `unsupported/` is a file in this repository and the value is a client's.
#
# `no_field_for_this_fact` IS THE ONE WORTH THE WHOLE MECHANISM. It fires when a
# position asks whether a client is treated differently and the desk has nowhere
# to record the answer -- so the follow-up cannot be answered by reading the
# file, by asking the client, or by fetching a document. Nobody decided the
# question was worth writing down. Every other reason here says something is
# missing from a record; this one says something is missing from the RECORD'S
# SHAPE, and it is discovered by real work rather than by an audit.
#
# WHY IT IS NOT `context_not_on_file`. That reason means the engagement should
# have recorded a fact and did not -- a gap in one client's file, fixed by the
# preparer filling it in. This one is fixed by the firm deciding the fact exists
# at all, which is a different person doing a different thing, and filing them
# together would bury the rarer and more valuable of the two.

# WHY `context_not_on_file` IS A THIRD THING, and it is the firm's own reasoning.
# `facts_not_established` is answered by asking the client; `document_not_requested`
# by obtaining a document that already exists. This one is answered by NEITHER,
# because the fact should already be in the engagement record and its absence is
# a gap in our own file.
#
# The firm, 5 September 2026, on the question they held rather than ratified:
# "the Accountant should've already recorded and known what sort of business
# we're dealing with. That's something we find out during the engagement and if
# they're missing that piece of information, something was just missing from the
# file." Filed as `facts_not_established` it would join the queue whose
# resolution is ASK THE CLIENT -- and the client is not the one who failed to
# write down that they are a contractor.
#
# WHY `document_not_requested` IS NOT `facts_not_established`, and why the firm
# had to say so before it existed. Both mean the rule is clear and a fact is
# missing. They differ in WHAT MAKES THE FACT ARRIVE, and that is the whole of
# their usefulness: one is answered by asking a person a question, the other by
# obtaining a document that already exists and that nobody requested.
#
# The firm, 5 September 2026, on a loan hiding in a year of deposits: "there
# should be something telling us to get like loan statements and stuff to make
# sure we understand the deal." Eight of their forty-three close questions
# resolve exactly that way -- the town's bill, the policy schedule, the cheque
# image, the payroll register, the marketplace order history -- and the closing
# agent's note on one of them is the whole argument: "the order history resolves
# every one of them and nobody asks for it."
#
# Filed as `facts_not_established` all eight would have gone to the queue whose
# resolution is ASK THE CLIENT, and the thing that actually settles them -- one
# document request -- would never have been raised.
#
# WHERE IT GOES IS THE FIRM'S CONSTRAINT AND IT IS LOAD-BEARING: "but not direct
# to client - things would be wired to go to me as the last resort right now."
# A desk naming a document raises it to the PREPARER, who decides whether to ask
# the client. Nothing this engine produces reaches a client without a person in
# between.

# WHY `facts_not_established` EXISTS, and why the set went eight rounds without
# it. Every other reason here is about the AUTHORITY -- absent, non-binding,
# uncited, unsupporting, contradicted. Not one was about the FACTS, so a desk
# holding exactly the right rule and missing the thing the rule asks about had
# no way to say so, and its only options were to guess or to blame the record.
#
# The firm, 5 September 2026, on an agent that classified a client's J.Crew
# purchases as personal: "no matter what, its answer was wrong." The lookup was
# not the error -- knowing J.Crew sells clothing is real evidence about WHAT WAS
# BOUGHT. The error was going from "sells clothing" to "personal expense"
# without reaching the test, which is § 1.262-1(b)(8): whether the item is
# "especially required by his profession and does not merely take the place of
# articles required in civilian life". Their client was a laborer who could
# legitimately need protective clothing, and the regulation has no vendor test
# in it at all -- its own example deducts a sword and refuses a uniform.
#
# What the firm does instead: "i could even flag it to ask the client." That is
# a real outcome and it was inexpressible. It is FIXABLE, like `authority_absent`
# and unlike `authority_permits_choice`: the answer exists, nobody has asked for
# it yet, and the working says what to ask.


@dataclass(frozen=True)
class Answer:
    """What a desk hands back. `position` is its conclusion, in its own words."""
    position: str
    citation: str = ""
    escalated: bool = False
    reason: str = ""
    working: str = ""
    #: THE DESK'S OWN FOLLOW-UP, in plain words, addressed to a person.
    #:
    #: `Refusal.ask` has existed since 5 September and was populated at SIX
    #: sites — every one of them a refusal the ENGINE detects. On an ESCALATION,
    #: where the DESK is the thing that noticed, there was nowhere to put a
    #: question and `ask` came back empty every time.
    #:
    #: The firm, 8 September 2026, reading a refusal with no question in it:
    #: *"why does it need client context though - i thought we are making it ask
    #: follow up questions for appropriate context?"* They are right, and the
    #: reason list has said so since it was written: `facts_not_established` is
    #: annotated *"the rule is clear; what was bought is not. ASK."*
    #:
    #: WHAT IT COST. Asked about a forklift, the desk worked out precisely what
    #: it needed — the invoice amount, whether the client elects the safe
    #: harbour, whether it has an applicable financial statement — and had to
    #: write all three into the PROSE of `working`, because no field would carry
    #: them. A caller cannot act on a paragraph. That looked like "the desk
    #: needs a client-context store", and it was not: the desk needs to be able
    #: to ask.
    ask: str = ""


#: The two things that can escalate, named once so a typo is not a third value.
DESK, ENGINE = "desk", "engine"


@dataclass(frozen=True)
class Result:
    """One graded answer, and why it landed where it did."""
    problem_id: str
    outcome: Outcome
    reason: str = ""
    detail: str = ""
    #: WHO ESCALATED: "desk" when the thing answering declined, "engine" when
    #: `_check` stopped a confident answer resting on non-binding authority.
    #: Empty for every other outcome.
    #:
    #: WITHOUT THIS THE ESCALATION COLUMN CANNOT BE READ, and on a desk built to
    #: exercise escalation it is the only column that matters. Where `_check`
    #: refuses with `authority_permits_choice` it does so before any conclusion
    #: is compared, so a desk that answered confidently and a desk that knew it
    #: did not know land in the same cell. The first was rescued by the record's
    #: tier; the second made the call. Reporting them as one number measures the
    #: record, not the brain.
    #:
    #: THE TIER GATE KEYS OFF WHAT THE BRAIN CITES, NOT WHAT THE QUESTION IS
    #: ABOUT, and this comment said otherwise until a run disproved it. It read
    #: "a problem keyed to a secondary source can ONLY grade escalated". False:
    #: on the cash desk, 5 September 2026, qwen3:8b cited § 1.446-1(a)(4) -- a
    #: PRIMARY paragraph, about inventory -- on all four problems, reasoning by
    #: explicit "extension". The tier gate never fired and the row graded
    #: wrong_caught 4/4 with zero escalations.
    #:
    #: The consequence is larger than the wording. ESCALATION CANNOT BE FORCED
    #: THROUGH THE RECORD. Keying problems to a secondary source does not compel
    #: the path; a brain routes around it by citing something binding. The
    #: escalation has to come from the brain's judgement, which is the thing
    #: measuring zero -- so a desk cannot be built that makes a brain decline.
    escalated_by: str = ""
    #: The follow-up a refusal carried, when it had one. Copied from
    #: `Refusal.ask` so a question raised at serve time survives into
    #: `unsupported/`, which is where the firm reads what the record is missing.
    #: A question that reached one caller and no file is a hole found and then
    #: dropped -- and the firm's reason for wanting it is exactly that it should
    #: accumulate: *"This is also a way to check for bugs or defects while agents
    #: perform real work."*
    ask: str = ""

    @property
    def costly(self) -> bool:
        """The only outcome that costs anything. Reported first, always."""
        return self.outcome is Outcome.WRONGLY_ABSORBED


class EngineError(Exception):
    """A caller broke the engine's contract. Never a silent default."""


@dataclass(frozen=True)
class Served:
    """What actually leaves the desk. Carries its authority or it does not exist."""
    position: str
    citation: str
    tier: str
    checked: str
    #: Whether the citation was checked against the question's subject. False
    #: means nobody could look -- the desk declares no subjects, or the question
    #: touched none of them -- NOT that it was checked and found fine. Those two
    #: were the same answer until 5 September 2026, and the difference is four
    #: served answers on that day's Forge row.
    checked_subject: bool = False
    #: THE SENTENCE THAT TRAVELS WITH THE ANSWER, and it is computed rather than
    #: passed so it cannot be left off.
    #:
    #: THE INCIDENT, 7 September 2026. A session testing the installed plugin
    #: aimed five traps at `fixed-assets` -- the largest desk, and the one
    #: carrying no ratified positions at all -- and FOUR SERVED. The sharpest
    #: cited § 1.263(a)-2(d)(1),
    #: whose text opens *"a taxpayer must capitalize amounts paid to acquire or
    #: produce a unit of real or personal property"*, and concluded "deducted,
    #: not capitalized" -- the literal negation of its own citation, served
    #: `tier=primary`, `binding=True`, no caveat.
    #:
    #: EVERY FIELD ON THIS OBJECT IS A PROPERTY OF THE SOURCE, NOT OF THE
    #: CONCLUSION, and together they read to an accountant as though the answer
    #: had been checked. `tier` is the regulation's standing. `binding` says the
    #: firm declared that source as authority that binds -- NOT that this answer
    #: binds. `checked_subject` is word overlap between the question and the
    #: desk's subjects. `checked` is when somebody last confirmed the PASSAGE
    #: against its publisher. Not one of them is a statement about whether the
    #: paragraph says what the position claims.
    #:
    #: The tester's words: *"Served carries no field for 'did anyone check that
    #: this paragraph says this?'"*. It does now, and it says no.
    #:
    #: THE SKILL ALREADY SAID SO AND THAT WAS NOT ENOUGH. `ask-desk` carries the
    #: sentence *"what it does not verify is that the conclusion follows"* -- in
    #: prose, at the top, read once by the agent and gone by the time an answer
    #: is rendered onward to a person. A warning that does not travel with the
    #: thing it warns about is a warning nobody reads.
    unchecked: str = ""
    #: THE CITED TEXT, served WITH the answer rather than left to be looked up.
    #: Until a judge exists, a person reading the answer is the only thing
    #: standing between a desk and a wrong entry -- and that person cannot do
    #: the one check that matters without the paragraph in front of them. Making
    #: them go and fetch it is what makes the review nominal.
    passage: str = ""
    #: THE FIRM'S OTHER POSITIONS ON THIS SAME PASSAGE — `((citation, position,
    #: passage text), ...)`, and empty on the ordinary answer where there are
    #: none. The TEXT is carried because a reader warned that the firm answers
    #: this passage differently elsewhere needs the words that answer rests on,
    #: for exactly the reason `passage` exists: *"The whole argument for
    #: `passage` — do not hand someone a conclusion without the words it rests
    #: on — applies with equal force to the conclusion you are warning them
    #: about."* (the Desk session, 8 September 2026.)
    #:
    #: THE INCIDENT, 7 September 2026. `cash-and-bank` holds two positions on one
    #: section of Pub. 583 with OPPOSITE answers. Asked about a deposit in
    #: transit, an agent cited the one for what the books are updated for and the
    #: engine served *"an entry in the books"* — `binding`, in the firm's own
    #: words, and the desk's own answer key (CB1) says the opposite.
    #:
    #: WHY NO EXISTING CHECK CAUGHT IT. `_check` refuses a conclusion that
    #: CONTRADICTS a ratified position. Here the agent did not contradict the
    #: firm; it quoted them exactly and applied them to facts they were not
    #: about. Nothing in the pipeline is a statement about which of two adjacent
    #: rules is in play, and nothing can be — that judgement needs the facts.
    #:
    #: SO IT IS SHOWN RATHER THAN DECIDED, which is the same trade `passage`
    #: made: the engine cannot tell right from wrong here, but it can stop the
    #: alternative from being invisible. The tester on the version without this:
    #: *"The reader is shown one of two adjacent rules and not told the other
    #: exists."* A reader handed both opposite answers side by side is a reader
    #: who can catch this in a second; one handed a single confident answer is
    #: not, however carefully they read the passage.
    alongside: tuple = ()
    #: Whether the authority behind this answer SETTLES the question or merely
    #: reads it. False means the desk answered from guidance because no rule and
    #: no position reached, which the firm allowed on 6 September 2026 -- and
    #: allowed on condition that the reader is told.
    #:
    #: IT IS NOT `tier` RESTATED. `tier` is a label on the source; this is a
    #: statement about THIS answer, and the two come apart at the one place that
    #: matters: a ratified POSITION on a tertiary source is binding here and
    #: tertiary there, because the firm decided it. A caller keying off `tier`
    #: alone would caveat the firm's own word.
    binding: bool = True
    #: The sentence a reader must see when `binding` is false. Empty otherwise --
    #: an empty caveat and an absent one must not look alike, so the flag is what
    #: is tested and this is what is shown.
    caveat: str = ""
    #: Whether a PERSON has classified this document's tier. False on the
    #: candidate path, where `domains.tier_for` has classified the HOST and
    #: nobody has read the document.
    #:
    #: FOUND LIVE, 8 September 2026, first round trip on 0.17.0. A passage
    #: fetched from irs.gov printed `primary · not binding — read the note
    #: below` above a note saying nobody had classified it. The desk that served
    #: it: *"Both cannot be informative ... a tired reader keeps the word
    #: 'primary' and drops the paragraph."* Pub. 946 is the Service explaining
    #: itself, which `DOMAINS.md` makes SECONDARY; the host is primary because
    #: it also publishes the rules. The host's answer is not the document's.
    #:
    #: NOT the cost `candidates.py` accepted -- that one errs toward caution (a
    #: real regulation arriving caveated). This is the other direction, and it
    #: is the one the reader cannot detect.
    classified: bool = True
    #: Set when the citation came from a source this desk does not DECLARE for
    #: this question's subject. Advice, not a verdict: the paragraph may be
    #: exactly right and the declaration merely narrow -- which is what it was
    #: on 8 September, when "how is the depreciation worked out?" refused the
    #: acquisition rule for a thing that had been bought.
    off_source: str = ""
    #: Facts the CALLER supplied that this desk declares no field for. Not a
    #: refusal and not a fault: the answer is unaffected. What it stops is the
    #: SILENCE. Found by the desk on the first live close, 8 September 2026 --
    #: a fact obtained by a round trip was "accepted, ignored, and nothing said
    #: so", and its own reading is the reason this exists: *"the fact that
    #: stopped a desk and cost a round trip is by that alone worth a field."*
    #:
    #: DISTINCT FROM `no_field_for_this_fact`, which covers a POSITION asking
    #: for a fact with nowhere to live. This is a CALLER offering one nobody
    #: asked for.
    undeclared: tuple = ()
    #: A `proving.Proof` when the caller asked for one, and None when they did
    #: not. Typed loosely on purpose: `proving` imports the record and reaches
    #: the network, and this module must do neither. THE ENGINE NEVER SETS THIS.
    #: It is attached by `ask.answer` after `serve` has already decided, so the
    #: rule that verification reads stored text is not bent to carry it.
    #:
    #: None means NOT ASKED FOR, never "asked for and fine". A proof that could
    #: not be taken is a `Proof` with verdict COULD NOT, and it says so.
    proof: object = None
    #: THE GATE FIRED ON A COIN TOSS, and this is the reader being told so.
    #: Empty wherever the domain was decided on evidence -- which is every
    #: answer but the straddles.
    #:
    #: `domains.Verdict.tied` carries the argument in full. The short version:
    #: a question firing on the same number of words in two bodies of authority
    #: is ordered BY NAME, so `federal-tax` beats `us-gaap` because of the
    #: alphabet, and `wrong_body_of_authority` then does not fire because the
    #: source governs the domain the sort happened to pick. On 8 September a
    #: Treasury regulation about amounts paid to ACQUIRE property was served,
    #: primary and binding, for *"does the equipment go on our books as an
    #: asset?"* about a 36-month lease -- and the passage LOOKS supportive,
    #: which is what makes it worse than the forklift case it resembles.
    #:
    #: SAID RATHER THAN REFUSED, and the ratio is why: of 98 recorded problems,
    #: 5 straddle and all 5 are exact ties, every one `federal-tax` against
    #: `us-gaap` on lease vocabulary. Four of those five are tax questions with
    #: correct tax answers. A refusal would spend them to catch this.
    straddle: str = ""
    #: The second reader's verdict, when one was given. `judging.Read`, or None.
    #: Never a score and never a substitute for a check: the engine confirmed
    #: the quoted words are in the passage; whether they carry the conclusion is
    #: the judge's call, recorded here rather than recomputed.
    judged: object = None

    def __str__(self) -> str:
        """The whole answer, laid out for a person. WHY THIS IS NOT IN THE SKILL.

        THE INCIDENT, 7 September 2026, and it is the one defect that has bitten
        every Forge run. The Skill tool served `desk:ask-desk` from a plugin
        cache FOUR releases stale — a SKILL.md with no mention of `unchecked`,
        no mention of `passage`, and a first snippet that raises. The tester
        produced correct output only by reading the current file off disk, which
        is not what the skill tells anyone to do, and named the shape of it:
        *"the warning you added lives in the file that does not load [...]
        Anything that depends on the loaded SKILL.md being current cannot fix a
        stale SKILL.md. If it can be checked from ask.consult/ask.answer
        themselves — the code that is current — that is the only channel that
        reaches an agent in this state."*

        So the instruction moves out of the prose and into the object. An agent
        following a two-release-old skill that says "print the answer" now
        prints all of it, because printing it IS this. The skill can go stale;
        the rendering cannot.

        `__repr__` is untouched and still carries every field. That split is
        deliberate: the tester also found `showed` and `showed_by_source`
        — instrumentation counting what the desk put in front of the model —
        reaching a human reader beside a sentence written for them. Diagnostics
        belong in the log, and the log takes the repr.
        """
        # `binds` ALONE WAS CONFIDENTLY WRONG, and the Desk session caught it on
        # the first run this rendering was read by anyone but its author:
        # *"an IRS publication is not binding authority in the tax sense — Pub.
        # 583 is guidance, it is not law, it does not bind the Service [...] The
        # line as printed reads, to anyone who has not memorised the field
        # semantics, as 'this secondary source is binding', and a preparer could
        # carry 'Pub. 583 binds' to an accountant on the strength of it."*
        # `binding` has only ever meant the FIRM treats this as authority that
        # binds their own work. The field said so; the rendering did not.
        # THE STRADDLE NOTE GOES ABOVE THE CONCLUSION, NOT BELOW IT, and that
        # is the single highest-value edit the reader asked for:
        #
        #   "By the time I reach line 6 I have read the answer AND a badge
        #    saying primary and binding, which reads as two independent things
        #    vouching for it. The warning then has to un-sell something I have
        #    already bought. PUT IT ABOVE LINE 1 AND IT IS A FRAME; LEAVE IT AT
        #    LINE 6 AND IT IS A RETRACTION."
        #
        # It sat above the AUTHORITY and below the ANSWER, and a test pinned it
        # there -- pinning exactly the wrong half. `caveat` and `alongside` stay
        # where they are: both are about the authority the reader is being sent
        # to, and are read after the answer on purpose. This one is about
        # whether the answer is even the reader's question, so it is read first
        # or it is read too late.
        # BOTH WARNINGS GO ABOVE THE CONCLUSION, for the reason the firm gave
        # about the straddle note: "PUT IT ABOVE LINE 1 AND IT IS A FRAME;
        # LEAVE IT AT LINE 6 AND IT IS A RETRACTION."
        out = ([self.straddle, ""] if self.straddle else []) + \
              ([self.off_source, ""] if self.off_source else []) + [
               self.position, "",
               f"    {self.citation}",
               f"    {self.tier if self.classified else 'tier not established'} · "
               f"{'the firm treats as binding' if self.binding else 'not binding — read the note below'}"
               f" · confirmed {self.checked}"]
        if (tied := _tieout_line(self.proof)):
            out += [tied]
        if self.caveat:
            out += ["", self.caveat]
        if self.alongside:
            # THREE LINES, AND IT STAYS THREE LINES. The other position's TEXT
            # goes below the answer's own passage rather than here: this block
            # has to be short enough that skipping it takes as long as reading
            # it, and it sits above the authority so it cannot be reached past.
            out += ["", "THE FIRM HAS ANSWERED THIS SAME PASSAGE MORE THAN "
                        "ONCE, and the other answer is not this one. Which is "
                        "in play is a question about the facts, and nothing "
                        "here has looked at the facts:"]
            for citation, position, _ in self.alongside:
                out += [f"  · {position}", f"      {citation}"]
        # WHAT NOBODY CHECKED IS DECIDED AT PRINT TIME, NOT AT SERVE TIME.
        #
        # `unchecked` is composed inside `serve()`, and `serve()` has no
        # `judged` parameter -- the judgment is attached one layer up by
        # `ask.answer`, after the sentence is already baked. So the text could
        # never know a second reader had looked, and said "Nobody checked that
        # this paragraph says this" on answers carrying an affirmative
        # judgment. Found by the desk on 8 September 2026, on the worst possible
        # answer to be wrong about: *"the most dangerous served answer in this
        # whole set -- wrong citation, affirmative judgment, off-source warning
        # -- tells its reader that nobody checked, which is the one claim in it
        # that is not true."*
        #
        # IT STILL SENDS THE READER TO THE PASSAGE. A judgment is one reader's
        # yes, not a verification: `engine` checks the quoted words are present
        # and in order, never that they support the conclusion. Replacing the
        # warning with a reassurance would be worse than the bug it fixes.
        # AND ONLY THE CLAIM THAT BECAME FALSE IS REPLACED. The first cut of
        # this suppressed `unchecked` entirely whenever a judgment stood, and
        # two render tests went red for the right reason: an answer from a
        # RATIFIED POSITION carries a different sentence there -- that the firm
        # ratified this conclusion and it is served in their words -- which a
        # second reader does not make untrue. Only "Nobody checked" is the claim
        # a judgment contradicts.
        seen = self.judged if getattr(self.judged, "stands", False) else None
        if seen is not None:
            out += ["", f"A second reader ({seen.by}) read this paragraph and "
                        f"says it carries this conclusion — checked against "
                        f"{seen.against or 'the record'}. That is one reader's "
                        f"yes, not a verification: the engine checks their "
                        f"quotation is really in the passage, never that it "
                        f"settles the question. Read the passage below."]
        if self.unchecked and not (seen is not None
                                   and self.unchecked.startswith("Nobody checked")):
            out += ["", self.unchecked]
        if self.undeclared:
            named = ", ".join(f"`{k}`" for k in self.undeclared)
            out += ["", f"YOU SUPPLIED {named}, WHICH THIS DESK DOES NOT "
                        f"DECLARE — it changed nothing here. Said out loud "
                        f"because a fact somebody went and obtained is "
                        f"evidence the record wants a field, and that evidence "
                        f"is worth more than the answer it did not alter."]
        if self.passage:
            out += ["", "THE AUTHORITY, in full:", "", f"> {self.passage}"]
        # IN FULL, AND NEVER AN EXCERPT. The obvious fix was a snippet under
        # each entry above. It fails on the one case this exists for: in the
        # Pub. 583 passage behind the firm's other cash position, the clause
        # that actually decides between the two — *"Update your checkbook and
        # journals for items shown on the reconciliation as not recorded (such
        # as service charges)"* — begins 88% of the way through 2,683
        # characters of reconciliation procedure. A head-excerpt would show the
        # reader generic boilerplate and hide the discriminator, which is the
        # same defect wearing a different hat.
        for citation, position, text in self.alongside:
            if text:
                out += ["", f"AND THE AUTHORITY UNDER THE FIRM'S OTHER ANSWER "
                            f"({position}), in full:", "", f"> {text}"]
        return "\n".join(out)


def _tieout_line(proof) -> str:
    """What the tie-out attempt DID, in one line, whatever it did.

    THE FIRM, 8 September 2026: *"It should state what happened when trying to
    tie it out. I need info to make decisions down the line."* All three
    verdicts are findings, so all three are said. A rendering that spoke only
    on failure would teach a reader that silence means checked -- and silence
    here means NOT ASKED FOR, which is a different thing entirely.

    TYPED LOOSELY, LIKE THE FIELD. `proving` imports the record and reaches the
    network; this module must do neither, so nothing here is imported and every
    field is read off the object.
    """
    if proof is None:
        return ""
    verdict = getattr(proof, "verdict", "")
    at = getattr(proof, "fetched_at", "") or "an unrecorded moment"
    host = _host_of(getattr(proof, "url", ""))
    if verdict == "TIED":
        return (f"    tied out against {host or 'the publisher'} at {at} — the "
                f"passage below is in the document served there right now")
    note = getattr(proof, "note", "") or "no reason was recorded"
    return (f"    NOT TIED OUT ({verdict or 'unknown'}) — {note} "
            f"This rests on this desk's record alone; nothing has been checked "
            f"against the publisher.")


def _host_of(url: str) -> str:
    """The registered host of a URL. A reader needs WHO, not which path."""
    import urllib.parse
    host = urllib.parse.urlsplit(url or "").hostname or ""
    return host.lower().removeprefix("www.")


@dataclass(frozen=True)
class Refusal:
    """The desk declining to serve. Names the next step, never just "no"."""
    reason: str
    detail: str
    #: THE FOLLOW-UP, IN PLAIN WORDS, ADDRESSED TO THE PREPARER. Empty on the
    #: refusals that have no question to ask -- an absent citation is a fix, not
    #: an enquiry.
    #:
    #: The firm asked for this in as many words: *"it can ask a follow up and if
    #: the follow up has no answer we know there's a legit hole to fix."* A
    #: reason code is countable and a question is answerable, and the two do
    #: different jobs: `detail` explains to whoever reads the queue, `ask` is the
    #: sentence somebody can act on.
    #:
    #: IT GOES TO THE PREPARER AND NEVER TO A CLIENT. The firm, 5 September 2026:
    #: *"but not direct to client - things would be wired to go to me as the last
    #: resort right now."* Nothing this engine produces reaches a client without a
    #: person in between, and that includes a question.
    ask: str = ""
    #: THE FACT THE REFUSAL TURNS ON, and THE POSITION THAT ASKED FOR IT. Named
    #: as fields rather than left in `detail`'s prose, because on 7 September
    #: 2026 the firm approved letting a desk ask for a FIELD to be built --
    #: *"that seems low stakes and required and i would approve it fairly
    #: easily"* -- on one condition: the ask must arrive carrying WHICH POSITION
    #: WANTED IT. A desk asks for a field because a position it holds names a
    #: fact, so approving the field approves that position's reach. Approving a
    #: change to the software on the strength of a chain nobody can see is what
    #: the condition exists to stop, and a chain parsed back out of a sentence is
    #: not a chain anybody can see.
    #:
    #: EMPTY ON THE REFUSALS THAT NAME NO FACT, which is most of them. Only the
    #: three that turn on a position's `Needs:` or `Unless:` set them.
    fact: str = ""
    by_position: str = ""
    #: A `proving.Proof` when a tie-out was attempted, and None when none was.
    #: Typed loosely for the same reason as `Served.proof`, and set by
    #: `ask.answer` rather than here.
    #:
    #: A REFUSAL CAUSED BY A TIE-OUT MUST SAY WHAT THE TIE-OUT DID, and before
    #: this field it could not: `authority_has_moved` carried the proof's note
    #: inside a sentence and dropped the host, the moment and the digest, so the
    #: one refusal that exists BECAUSE something was fetched was the one nobody
    #: could re-run by hand. #343's candidate path needs the same field for the
    #: opposite case -- a citation no desk holds, refused because the fetch
    #: failed -- where the whole content of the refusal is what happened when
    #: trying.
    proof: object = None
    #: WHICH DESK REFUSED. Empty only where nothing routed.
    #:
    #: A QUESTION REACHES MORE THAN ONE DESK, and a printed refusal did not say
    #: which one it came from. The forklift question routed to two on 8
    #: September and came back as two refusals for two DIFFERENT reasons — one
    #: a hole in our own file, one a fact about the transaction nobody had
    #: stated. The desk session: *"Both refusals above are distinguishable only
    #: because I typed the headings myself. Print two in a row without them and
    #: you have two anonymous paragraphs."*
    #:
    #: `Served` never had this problem because its citation identifies where it
    #: came from. A refusal cites nothing — that is what makes it a refusal —
    #: so the desk has to be carried explicitly or it is not recoverable.
    desk: str = ""
    #: HOW MUCH THE DESK PUT IN FRONT OF THE MODEL, on an `authority_absent`
    #: escalation and on nothing else.
    #:
    #: THE INCIDENT, 7 September 2026. The meals desk escalated a question about a
    #: streaming subscription saying *"§ 1.274-11's own text is not in this desk's
    #: record"*. It is — ten passages of it, including the general disallowance at
    #: (a), the definition of entertainment at (b)(1)(i) and the objective test at
    #: (b)(1)(iii) — all of it printed in the brief the model was answering from.
    #: The claim was false and nothing could tell: `authority_absent` is the
    #: MODEL'S claim about its own record and this function takes it at its word.
    #: The other three escalations in the same run were correct, and this one
    #: looked identical.
    #:
    #: IT REPORTS AND IT DOES NOT OVERRULE, which is the whole shape of the thing
    #: and the reason the firm was asked rather than told. The engine can say the
    #: desk showed 76 passages, 10 of them from the source the model named; it
    #: cannot say whether any of them answered the question. That judgement stays
    #: with the model and with whoever reads the queue. An engine that REFUSED the
    #: escalation would be deciding the merits, which is the wrong side of the
    #: line every other part of this file draws.
    #: THE ASKER'S OWN REASONING, HANDED BACK. It went only to the queue.
    #:
    #: THE FORGE, 7 September 2026, closing a set of books for real: the desk
    #: escalated `authority_absent` and returned `detail="escalated by the
    #: desk"`, an empty `ask`, and `showed_by_source={'S1': 63, 'S2': 40, ...}`.
    #: The agent's `working` — the reasoning about WHY nothing reaches, which
    #: `ask-desk` insists is written in full — was not on the object at all.
    #:
    #: *"So the one answer where the agent has the most to say hands the caller
    #: the least, and I had to write the accountant's paragraph from my own
    #: memory rather than from anything the desk returned. Meanwhile
    #: `showed_by_source` — pure instrumentation — does come back. That is
    #: exactly backwards for a human reader."*
    #:
    #: The queue keeps it so the firm learns what authority is missing. The
    #: caller needs it too, and for a different reason: it is the only sentence
    #: in an escalation that tells a person what to do next.
    working: str = ""
    showed: int = 0
    #: `{source id: passages}` — a total alone does not falsify the claim that was
    #: actually made. The claim named a source, so the answer has to be by source.
    showed_by_source: dict = field(default_factory=dict)

    def __bool__(self) -> bool:            # so `if served:` reads correctly
        return False

    def __str__(self) -> str:
        """The refusal as something to hand a person. See `Served.__str__`.

        `working` LEADS, because it is the only part of an escalation written by
        something that read the question. The tester, on the release before it
        was carried back at all: *"the one answer where the agent has the most
        to say hands the caller the least"* — and, once it was: *"I wrote the
        accountant's paragraph straight off the returned object rather than from
        memory, which I could not do last run."*

        `showed` and `showed_by_source` are NOT here, and their absence is the
        point. They count what the desk put in front of the model, to falsify a
        model's claim that the desk held nothing — a question for the queue and
        for whoever audits an escalation, not for the preparer reading this. The
        tester found them printed beside a sentence meant for a person and named
        it *"pure instrumentation next to a sentence meant for a person"*. They
        stay on the repr, which is what the log takes.
        """
        # THE VERDICT LEADS, AND THIS REVERSES A CHANGE MADE TWO RELEASES AGO.
        #
        # 0.7.5 put `working` first, on a tester's finding that the escalation
        # "hands the caller the least" — correct at the time, because `working`
        # was not on the object at all and, once it was, it was the only part
        # worth reading. What that fix did not anticipate is that the skill
        # pushes for LONG working, and it succeeded: the next run produced a
        # 900-character paragraph opening *"The rule is clear and it is
        # conditional"*.
        #
        # The desk session that wrote it, 8 September 2026: *"a reader skimming
        # a refusal meets a long paragraph whose opening words here are 'The
        # rule is clear and it is conditional' — which reads like the beginning
        # of an answer — and only reaches 'THE DESK DID NOT ANSWER' once they
        # have already started forming one. The verdict is the one line that
        # must not be missed and it is the last thing rendered."*
        #
        # Both findings are right and they are not in conflict: `working` must
        # come back, and it must not come back FIRST. `Served` puts the
        # conclusion at the top and the caveats under it; a refusal that
        # inverts that teaches a reader the shape means nothing.
        out = [f"THE DESK DID NOT ANSWER — {self.reason}"
               + (f"  ·  {self.desk}" if self.desk else ""), f"    {self.detail}"]
        # WHAT THE TIE-OUT DID, WHERE ONE WAS TRIED. Directly under the detail,
        # because on the refusals that exist because of a fetch it IS the
        # detail -- the host asked, the moment, and what came back.
        if (tied := _tieout_line(self.proof)):
            out += [tied]
        if self.working:
            out += ["", self.working]
        if self.ask:
            out += ["", f"It asks: {self.ask}"]
        if self.fact:
            out += ["", f"The fact it turns on: {self.fact}"
                        + (f", wanted by {self.by_position}" if self.by_position
                           else "")]
        return "\n".join(out)


def _text_of(backing) -> str:
    """Whatever words back a citation, whichever store it came from."""
    kind, obj, _ = backing
    if kind == "position":
        return f"{obj.position} {getattr(obj, 'why', '')}"
    return obj.text


def off_subject(answer: Answer, desk: Desk, question: str) -> tuple[bool, str]:
    """`(refuse, detail)` — the cited authority shares no subject with the ask.

    MEASURED, 5 SEPTEMBER 2026, AND THIS IS WHY IT EXISTS. On the cash desk
    qwen3:8b answered four bank-reconciliation questions by citing
    § 1.446-1(a)(4) -- a real, resolvable, PRIMARY paragraph about keeping
    accounting records -- reasoning by explicit "extension". `grade()` caught all
    four on `passage.citation != problem.citation`, a check it can only make
    because it holds an answer key. `serve()` holds none, had no equivalent, and
    returned the accounting conclusion stamped `tier='primary'`. So the scoreboard
    reported `wrongly_absorbed = 0` while the path with a client on the end of it
    would have shipped four.

    THE CHECK IS EXACT AND THE JUDGEMENT IS THE FIRM'S. It computes one thing:
    of the desk's declared subjects, which appear in the question, and does the
    cited authority mention any of them. Whole words only, through `touches` --
    the one matching rule in this codebase. Zero overlap is the signal; anything
    above zero passes. It does not score relevance, rank citations or read
    meaning, because none of that is checkable and `guards.py` draws the line
    where a machine stops being exact.

    IT REFUSES ONLY WHEN IT COULD ACTUALLY LOOK. A desk with no declared subjects,
    or a question touching none of them, gives it nothing to compare -- and it
    passes rather than blocks, because "I could not check" and "I checked and it
    is fine" must never be the same answer. `Served.checked_subject` carries which
    of the two happened.

    THE COST IS REAL AND IS NOT HIDDEN: an authority whose text is written in
    pronouns, or in vocabulary the desk never declared, is refused though it may
    be exactly right. That shows up as `citation_does_not_support` in the queue
    with the working intact, which is where a wrongly refused answer is meant to
    be found.
    """
    touches = _canon_touches()
    asked = tuple(t for t in desk.fires_on if touches(question, t))
    if not asked:
        return False, ""
    backing = desk.authority_for(answer.citation)
    if backing is None:
        return False, ""
    text = _text_of(backing)
    if any(touches(text, t) for t in asked):
        return False, ""
    return True, (
        f"the question is about {', '.join(asked)}; {answer.citation!r} is real "
        f"authority this desk holds and mentions none of them. A citation that "
        f"shares no subject with the question is not this question's authority"
    )


def cited_off_declared_citation(answer: Answer, desk: Desk,
                                asked: list[str]) -> tuple[bool, str]:
    """The FINER declaration, and the half that still BLOCKS.

    A source-level mapping cannot separate two rules living in one source, and
    the cash desk holds exactly that pair: the timing rule and the correction
    rule, both Publication 583, OPPOSITE ANSWERS. Measured 5 September 2026 --
    handed CB4's facts and the TIMING citation, `serve()` returned "a
    reconciling item, no entry in the books" with `checked_subject=True`. The
    right source. The wrong paragraph. The opposite treatment.

    WHY THIS ONE KEPT ITS TEETH WHEN THE SOURCE-LEVEL CHECK LOST THEM,
    8 September 2026. Both were measured over all 98 recorded problems, asking
    whether each would refuse the desk's OWN recorded citation:

        phrased as the full fact pattern    source-level 0    per-citation 0
        phrased as the short title          source-level 10   per-citation 0

    Every one of the ten is the source-level check. This one costs nothing in
    either phrasing, because it fires only on subjects a desk has DECLARED per
    citation -- opt-in, so its cost can only be paid by a desk that asked for
    it -- and because it separates paragraphs a reader genuinely cannot tell
    apart from the source name. A wrong answer here is not a narrow one; it is
    the opposite treatment of the same money.

    It narrows and never widens: a desk declaring nothing per citation is
    unaffected.
    """
    covered = [t for t in asked
               if any(t in terms for terms in desk.answered_by.values())]
    if not covered:
        return False, ""
    narrowed = {c for c, terms in desk.answered_by.items()
                if any(t in covered for t in terms)}
    if answer.citation in narrowed:
        return False, ""
    named = ", ".join(sorted(narrowed))
    return True, (
        f"the question is about {', '.join(covered)}, which this desk "
        f"answers at {named}; {answer.citation!r} is a different rule in "
        f"the same source. Two paragraphs of one publication can carry "
        f"opposite answers, and the source alone cannot tell them apart"
    )


def cited_off_source(answer: Answer, desk: Desk, question: str,
                     *, source: Source | None = None) -> tuple[bool, str]:
    """`(refuse, detail)` — the citation comes from a source that does not
    answer what was asked.

    THE FACT IS RECORDED, NOT INFERRED, and that is the whole difference. A desk
    declares in SUBJECTS.md which source answers which subject. So the check is
    a lookup: which subjects does the question touch, which sources are declared
    to answer them, and did the citation come from one of those. No word overlap
    between the question and the authority, no relevance judgement, nothing to
    tune -- which is why this one may BLOCK where `off_subject` may not.

    MEASURED, 5 SEPTEMBER 2026 (#266). qwen3:8b answered four bank-reconciliation
    questions on the cash desk by citing § 1.446-1(a)(4) -- accounting records --
    by explicit "extension". Real, resolvable, primary, and `serve()` handed all
    four out stamped `tier='primary'`, because it had no key and no equivalent of
    `grade()`'s citation check. Comparing words instead either refused four of
    the sixteen fixed-assets problems answered with their OWN citation, or caught
    nothing at all. This refuses those four and none of fixed-assets.

    IT REFUSES ONLY WHEN IT COULD LOOK. A question touching no declared subject
    gives it nothing, and it passes -- `Served.checked_subject` says which
    happened, because "I could not check" and "I checked and it is fine" must
    never be the same answer.

    THE COST IS THE FIRM'S TO CONTROL AND IS VISIBLE WHEN PAID. Under-declare a
    subject and a right answer is refused; the refusal names the sources that
    were declared, so the record says how to fix itself, and the entry lands in
    `unsupported/` with the working intact.
    """
    if not desk.answered_from:
        return False, ""
    touches = _canon_touches()
    asked = [t for t in desk.fires_on if touches(question, t)]
    if not asked:
        return False, ""
    allowed = {sid for sid, terms in desk.answered_from.items()
               if any(t in asked for t in terms)}
    if not allowed:
        return False, ""
    # THE SOURCE IS THE RESOLVED ONE, NEVER RE-INFERRED. This matched the
    # citation against every source's prefix and took the first hit, which is a
    # second, weaker copy of a resolution `record.authority_for` has already
    # made exactly -- by `source_id` for a passage, and by a prefix match
    # `load()` proves is unique for a position. Two ways of answering the same
    # question disagree in two directions: overlapping prefixes (`G` and `G 1`)
    # named the wrong source and refused a right answer, and a stored passage
    # whose citation starts with no prefix at all named NO source, so the gate
    # passed silently on the case it exists to catch. A gate that opens when it
    # cannot identify the source is worse than no gate, because `serve()` then
    # stamps the answer `checked_subject=True`.
    if source is None:
        backing = desk.authority_for(answer.citation)
        source = backing[2] if backing is not None else None
    # THE FINER DECLARATION FIRST, AND ONLY WHERE THE DESK MADE ONE (M8).
    #
    # A source-level mapping cannot separate two rules living in one source, and
    # the cash desk holds exactly that pair: the timing rule and the correction
    # rule, both Publication 583, opposite answers. Measured 5 September 2026 --
    # handed CB4's facts and the TIMING citation, `serve()` returned "a
    # reconciling item, no entry in the books" with `checked_subject=True`. The
    # right source. The wrong paragraph. The opposite treatment.
    #
    # It narrows and never widens: only the asked subjects a desk has actually
    # declared per citation are gated, so a desk declaring none is unaffected and
    # the cost of this gate can only be paid by a desk that opted in.
    astray, why = cited_off_declared_citation(answer, desk, asked)
    if astray:
        return True, why

    if source is None or source.id in allowed:
        return False, ""
    cited = source.id
    named = ", ".join(sorted(allowed))
    return True, (
        f"the question is about {', '.join(asked)}, which this desk answers from "
        f"{named}; {answer.citation!r} comes from {cited}. A citation from a "
        f"source the desk does not use for this subject is not this question's "
        f"authority, however real it is"
    )


def _canon_touches():
    """Whole-word matching, borrowed rather than rewritten.

    It lives in one place because it was briefly written twice, once whole-word
    and once not, and the two disagreed for a day with nothing comparing them.
    """
    from _canon import load_record
    return load_record().touches


def _follow_up(facts, ruling) -> str:
    """The question a preparer can act on, in place of a code they cannot.

    A reason is countable and a question is answerable, and the queue needs
    both: `detail` explains the refusal to whoever reads it, this is the
    sentence somebody does something about. It names the fact and never a value.
    """
    named = ", ".join(facts)
    return (f"Does the file record {named} for this engagement? The firm's "
            f"position {ruling.id} cannot be applied until it does, and it is "
            f"ours to record rather than the client's to be asked.")


def _rule_reaches(desk: Desk, question: str) -> bool:
    """Whether this desk declares BINDING authority for anything the question
    is about.

    Three cases, and the middle one is the one worth the lines.

    NO BINDING SOURCE ON THE DESK AT ALL -> no rule can reach, unambiguously,
    and guidance is the best authority there is. The rewards desk's whole
    rewards half is this: the Code and the regulations define gross income and
    stop, so every statement that a rebate is not income is a ruling, an
    announcement or a publication.

    BINDING SOURCES, BUT NO DECLARED MAPPING -> REFUSE. A rule might reach and
    nothing here can tell. "I could not check" and "I checked and it is fine"
    must never be the same answer -- the rule `off_subject` is written to, and
    the direction to fail in is the one that asks the firm rather than the one
    that answers on a publication while a regulation sits unread beside it.

    BINDING SOURCES AND A MAPPING -> read it off `answered_from`, which the firm
    wrote, rather than judged.
    """
    binding = {s.id for s in desk.sources if s.binding}
    if not binding:
        return False
    if not desk.answered_from:
        return True
    touches = _canon_touches()
    asked = [t for t in desk.fires_on if touches(question, t)]
    if not asked:
        # The question touches nothing this desk declared, so the mapping cannot
        # answer either. Same reasoning as above: unable to tell is not clear.
        return True
    return any(sid in binding and any(t in asked for t in terms)
               for sid, terms in desk.answered_from.items())


def _check(answer: Answer, desk: Desk, question: str = "", context=None):
    """The one verification. Shared by the gate and the scoreboard on purpose.

    If serving and grading each had their own copy, they would drift, and the
    scoreboard would stop measuring the thing the gate actually does — which is
    the shape of nearly every real bug in this operation: a claim in one place,
    the behaviour in another, and nothing comparing them.

    Returns `(refusal, passage, source, verdict)`. A refusal of None means it
    passed. The verdict is handed back rather than recomputed by the caller for
    the same reason `cited_off_source` is handed the resolved source: one
    resolution, one answer, and no second copy to drift.
    """
    verdict = None
    if not answer.citation.strip():
        return Refusal(
            "no_citation",
            "answered with no citation; cite this desk's recorded authority, "
            "or escalate with a reason",
        ), None, None, verdict

    backing = desk.authority_for(answer.citation)
    if backing is None:
        return Refusal(
            "authority_absent",
            f"{answer.citation!r} is not in this desk's record; add it cited, "
            f"or escalate with reason 'authority_absent'",
        ), None, None, verdict

    kind, passage, source = backing
    if source is None:                                  # pragma: no cover
        raise EngineError(
            f"{answer.citation!r} has no source; load() checks this")

    # THE RULE MAY NEED A FACT NOBODY PUT ON THE FILE, and then it does not
    # matter how good the citation is. Checked against the RATIFIED position
    # resting on this citation, so a desk whose positions declare nothing --
    # which is all of them but two -- behaves exactly as it did.
    #
    # It is checked HERE rather than in `serve` so the scoreboard sees the same
    # gate the caller does. That is the standing rule of this function and the
    # shape of nearly every real bug in this operation is a claim in one place
    # and the behaviour in another.
    ruling = desk.position(answer.citation)
    if ruling is not None and ruling.needs:
        import record as _record

        absent = (context or _record.NOTHING_ON_FILE).missing(ruling.needs)
        if absent:
            return Refusal(
                "context_not_on_file",
                f"{answer.citation!r} is answered by the firm's position {ruling.id}, "
                f"which cannot be applied without {', '.join(absent)} on file. "
                f"That is the engagement's to record, not the client's to be asked",
                ask=_follow_up(absent, ruling),
                fact=", ".join(absent), by_position=ruling.id,
            ), passage, source, verdict

    # A DEFAULT IS NOT AN ANSWER UNTIL SOMEBODY HAS LOOKED FOR THE EXCEPTION.
    #
    # The firm, holding three positions on 6 September 2026: "This needs to
    # ensure that there is no already standing rule for that client in
    # particular. The desk should ask that follow up if it is not clear, right?"
    # and "we shouldn't ignore client level rules set with judgment with the
    # desk answering broadly."
    #
    # THREE ANSWERS, NEVER TWO, and `Context.standing_rule` is where that lives.
    # "Nothing on file" and "on file, and there is no client rule" are opposite
    # facts that a `dict.get` cannot tell apart, and collapsing them is exactly
    # how a desk answers broadly over a client the firm treats differently.
    #
    # WHY THE RECORDED CASE REFUSES RATHER THAN SERVING THE CLIENT'S RULE. The
    # desk holds no client data and never will -- `dec-override`, answered the
    # same day: "Keep unconditional". What the file records is the firm's own
    # call for that client, and it displaces the firm's default, which is what a
    # default means. The desk stops and hands over. The value is NEVER printed:
    # `unsupported/` is a file in this repository and that value is a client's.
    if ruling is not None and ruling.unless:
        import record as _record

        ctx = context or _record.NOTHING_ON_FILE
        for fact in ruling.unless:
            state = ctx.standing_rule(fact)
            if state == _record.NONE:
                continue                      # looked, and this client is not special
            if state == _record.RECORDED:
                return Refusal(
                    "client_rule_governs",
                    f"{answer.citation!r} is the firm's default position "
                    f"({ruling.id}), and this engagement records a standing rule "
                    f"on {fact!r}. The recorded rule governs and the default does "
                    f"not; read it from the file rather than from this desk",
                    ask=f"This client has a recorded rule on {fact}. Apply that "
                        f"rather than the firm's general position — and if it no "
                        f"longer reflects what the firm does, say so.",
                    fact=fact, by_position=ruling.id,
                ), passage, source, verdict
            if fact not in desk.records:
                return Refusal(
                    "no_field_for_this_fact",
                    f"{answer.citation!r} is the firm's default position "
                    f"({ruling.id}), which holds unless this client is treated "
                    f"differently on {fact!r} — and this desk has nowhere to "
                    f"record that. The gap is in what the firm decided to write "
                    f"down, not in what this client was asked",
                    ask=f"Is there a standing rule for this client on {fact}? "
                        f"Nothing on file can answer that, because no such field "
                        f"exists. Deciding whether it should is the firm's.",
                    fact=fact, by_position=ruling.id,
                ), passage, source, verdict
            return Refusal(
                "context_not_on_file",
                f"{answer.citation!r} is the firm's default position "
                f"({ruling.id}), which holds unless this client is treated "
                f"differently on {fact!r}. Nothing on file says either way, and "
                f"a default applied without looking is not a default",
                ask=_follow_up((fact,), ruling),
                fact=fact, by_position=ruling.id,
            ), passage, source, verdict

    # THE DECLARED MAPPING, WHICH IS EXACT AND SO MAY BLOCK (#266). It is handed
    # the source the line above resolved, rather than working it out again from
    # the citation: one resolution, one answer.
    # THE FINER HALF STILL GATES. Two paragraphs of one publication carrying
    # opposite answers is not a narrow refusal, it is the opposite treatment of
    # the same money -- and it costs 0 of 98 in either phrasing.
    _touches = _canon_touches()
    _asked = [t for t in desk.fires_on if _touches(question, t)]
    astray, why = cited_off_declared_citation(answer, desk, _asked)
    if astray:
        return Refusal("citation_does_not_support", why), None, None, verdict

    # THE SOURCE-LEVEL HALF ADVISES; IT DOES NOT GATE. It used to return
    # `Refusal("citation_does_not_support", ...)` here. `serve()` computes the
    # same note after the checks pass and carries it ON the answer.
    #
    # WHY IT WAS ALLOWED TO BLOCK, AND WHY THAT IS GONE. Its own docstring: on
    # 5 September `serve()` "had no key and no equivalent of `grade()`'s
    # citation check", so a real-but-irrelevant paragraph could not be caught
    # downstream. #346 built the judge -- a second reader on the paragraph and
    # the conclusion, on every answer -- which reads meaning where this reads a
    # keyword table. And every measurement behind the block is `qwen3:8b`; the
    # firm, 8 September: "We currently do not need to test against ollama."
    #
    # WHAT IT COST, over all 98 recorded problems, asked whether it would refuse
    # each desk's OWN recorded citation: 0 of 98 when the question is the full
    # fact pattern, 10 of 98 when it is the short title. It measures how many
    # declared keywords the asker typed. `PROBLEMS.md` is written verbosely,
    # which is the style that scores zero, so the suite could not see it.

    # `off_subject` IS NOT WIRED IN HERE, AND THE MEASUREMENT IS WHY (#266).
    # It refuses 4 of the 16 fixed-assets problems answered with their own
    # recorded citation -- a quarter of the working desk, wrongly. Comparing the
    # cited text against the DESK's subjects instead of the QUESTION's drops that
    # to zero and stops catching the case it exists for. Word overlap either
    # over-refuses or under-catches; neither is exact enough to block on, which
    # is the line `guards.py` draws. Left public, tested and unused until the
    # firm picks a shape.

    # A ratified position IS the firm's answer, so tier does not gate it: the
    # firm already made the choice that a secondary source would only have
    # invited. This is the whole point of `human_only` — a source the engine
    # may never read is reachable only through what the firm wrote about it.
    if kind == "position":
        # AND IT MUST BE THE POSITION THE FIRM ACTUALLY TOOK. This branch used
        # to approve on the citation alone, never comparing what was submitted
        # with what the firm wrote -- so on the `human_only` path, where a
        # position is the desk's ENTIRE knowledge of a source it may never read,
        # a model could cite a real position and hand back the opposite
        # conclusion, and `serve()` would return that conclusion as the firm's.
        # The one path that exists because a human decided was the one path that
        # did not check the human's decision.
        if not _same(answer.position, passage.position):
            return Refusal(
                "contradicts_ratified_position",
                f"cited {answer.citation!r}, where the firm's position is "
                f"{passage.position!r}; answered {answer.position!r}. A position "
                f"is the firm's word and a desk does not revise it",
            ), passage, source, verdict
        return None, passage, source, verdict

    # THE BODY OF AUTHORITY, checked before tier and after positions.
    #
    # THE TRAP, 7 September 2026, found by a session testing the installed
    # plugin on the Forge rather than by anyone building it. Asked *"how do i
    # know if a lease should be booked as an asset"* -- a US GAAP recognition
    # question -- an answer citing IRS Pub. 463 (2025), "Leasing a Car" was
    # SERVED, `checked_subject=True`. The entire cited paragraph:
    #
    #   "If you lease a car, truck, or van that you use in your business, you
    #    can use the standard mileage rate or actual expenses to figure your
    #    deductible expense. This section explains how to figure actual
    #    expenses for a leased car, truck, or van."
    #
    # Two sentences about figuring a deduction. Nothing about the balance
    # sheet, nothing about recognition. Every existing check passed and was
    # right to: the citation resolves, and `lease` IS a declared subject of
    # that source. The conclusion was directionally the expensive error --
    # expense the lease, omit the right-of-use asset and the lease liability.
    #
    # WHY THE SUBJECT CHECK COULD NOT CATCH IT. `checked_subject` asks whether
    # this desk answers this SUBJECT from this SOURCE. Both were true. What was
    # false is that a federal-tax publisher can settle a US GAAP question at
    # all, and nothing asked that. The firm named the shape before the trap was
    # found: *"you don't check the IRS website for coding tips."*
    #
    # IT GATES AUTHORITY AND NEVER A POSITION, which is why it sits below the
    # `kind == "position"` branch rather than above it. A ratified position is
    # the firm's own word and tier does not gate it either; an engine that
    # refused the firm's answer because of where its citation was published
    # would be overruling them, which is the wrong side of every line this file
    # draws.
    #
    # AND IT IS SILENT WHERE THE MAP IS. A question matching no domain, or a
    # source with no url, leaves this untouched -- refusing on an absent
    # classification would be guessing a domain to get a gate, which is the
    # same error the gate exists to stop.
    if source.url and question:
        import domains as _domains

        verdict = _domains.classify(question)
        if verdict and not _domains.governs(source.url, verdict.domain):
            also = ", ".join(d.name for d in verdict.also)
            return Refusal(
                "wrong_body_of_authority",
                f"{answer.citation!r} resolves and this desk does answer "
                f"{verdict.matched[0]!r} from {source.id} — and "
                f"{_domains._registered(source.url)} does not settle "
                f"{verdict.domain.name} questions. {verdict.domain.body} does. "
                f"A paragraph in the wrong body of authority is not made into "
                f"this question's rule by being real",
                ask=(f"This is a {verdict.domain.name} question"
                     + (f" that also reaches {also}" if also else "")
                     + f". Cite {verdict.domain.body}, or escalate that no "
                       f"desk holds the authority that governs it."),
            ), passage, source, verdict

    if not source.binding:
        # SERVED, AND MARKED AS GUIDANCE -- but only where no rule reaches.
        #
        # The firm, fourth docket, 6 September 2026: "Serve it, marked", on the
        # question they had asked for while holding a position the day before:
        # "if we don't have an opinion and have a good reason to form one, maybe
        # we just use a safe Harbor Rule which in this case would be deferring
        # to whatever the IRS says."
        #
        # THE CONDITION IS WHAT MAKES IT SAFE, and it is read off the record
        # rather than judged. If any BINDING source is declared to answer a
        # subject this question touches, then a rule does reach it, and a
        # publication may not be served in its place -- otherwise a model could
        # dodge a regulation by citing the plain-English summary of it. That is
        # not hypothetical on this record: the tie-out found § 1.263(a)-1 saying
        # $500 and the IRS page saying $2,500, both live, and a desk that served
        # the second without saying so would hand over a number the regulation
        # does not contain.
        #
        # WHERE NO RULE REACHES, refusing was never protecting anyone. It sent
        # the same question back to the firm every time it was asked, which is
        # the thing they asked to stop.
        if _rule_reaches(desk, question):
            return Refusal(
                "authority_permits_choice",
                f"{source.title} is {source.tier} authority, which is somebody's "
                f"reading rather than the rule -- and this desk holds binding "
                f"authority on this subject. Cite the rule, or escalate",
                ask=f"Is {answer.citation!r} being cited because the rule does "
                    f"not reach this, or because it was easier to read? This "
                    f"desk holds a binding source for what was asked.",
            ), passage, source, verdict
        return None, passage, source, verdict

    return None, passage, source, verdict


def serve(answer: Answer, desk: Desk, *, question: str,
          context=None) -> Served | Refusal:
    """Stamp every refusal with the desk that made it, then hand it back.

    ONE PLACE, NOT FOUR. `_serve` refuses at three points today and a fourth
    will be added: the comment inside it already says as much about `working`,
    which is carried at one site "so no refusal can be added later that quietly
    drops it". The same argument applies to the desk, and a wrapper is the only
    shape that cannot be forgotten — a new `return Refusal(...)` inherits it.
    """
    out = _serve(answer, desk, question=question, context=context)
    if isinstance(out, Refusal) and not out.desk:
        import dataclasses as _dc
        return _dc.replace(out, desk=desk.name)
    return out


def _serve(answer: Answer, desk: Desk, *, question: str,
           context=None) -> Served | Refusal:
    """The production path: hand back an answer, or refuse and say why.

    **Nothing leaves here without authority behind it.** An uncited answer is
    refused by this function, not by a prompt asking the model nicely — the
    difference was measured at 100%, 4% and 0% of runs as prose, and always at
    the choke point.

    A refusal is not a dead end. Pair it with `unsupported.from_refusal` to keep
    the reasoning, which is the best evidence of what the record is missing.

    `question` IS REQUIRED, AND THAT IS THE FIX. Without it this function could
    verify that the cited authority exists and binds, and nothing at all about
    whether it had anything to do with what was asked -- so it served four
    bank-reconciliation answers citing a rule about accounting records, stamped
    primary, on 5 September 2026. `grade()` caught them only because it holds an
    answer key. There is no key here and there never will be; the question is
    what stands in for one.

    WHAT IS STILL NOT VERIFIED, said plainly because `Served` used to imply
    otherwise: that the cited paragraph is the BEST authority, that it is the one
    the regulation itself would name, or that the conclusion follows from it.
    Only that it exists, that it binds or carries the firm's word, and that it
    shares a subject with the question. `checked_subject` says whether even that
    last one could be looked at.
    """
    if answer.escalated:
        _reason(answer.reason)
        if answer.reason in MUST_ASK and not answer.ask.strip():
            raise EngineError(
                f"escalating {answer.reason!r} without a follow-up question. "
                f"This reason means a PERSON can resolve it, so the desk has to "
                f"say what to ask them — `ask=` on the answer. A refusal that "
                f"names a gap and not the question is one nobody can act on, "
                f"and the reason list has said so since it was written: "
                f"{answer.reason!r} is the case where the rule is clear and the "
                f"facts are not.")
        if answer.reason != "authority_absent":
            return Refusal(answer.reason, "escalated by the desk",
                           working=answer.working, ask=answer.ask)
        # ONLY `authority_absent`, because it is the only escalation that is a
        # claim about the RECORD. `facts_not_established` is a claim about the
        # client and `authority_permits_choice` is a reading of authority the
        # desk does hold; counting passages against either would print a number
        # that argues with nothing.
        by_source = record_mod.shown_by_source(desk)
        total = len(record_mod.shown(desk))
        return Refusal(
            answer.reason, "escalated by the desk", working=answer.working,
            ask=answer.ask, showed=total, showed_by_source=by_source)

    refusal, passage, source, verdict = _check(answer, desk, question, context)
    if refusal is not None:
        # CARRIED HERE RATHER THAN AT FIFTEEN CONSTRUCTION SITES, so no refusal
        # can be added later that quietly drops it.
        import dataclasses as _dc
        return (_dc.replace(refusal, working=answer.working)
                if answer.working else refusal)
    # A RATIFIED POSITION IS THE FIRM'S WORD AND IS NEVER CAVEATED, whatever the
    # tier of the source under it -- that is the whole point of `human_only`, and
    # of the firm being the last layer. Only a passage from a non-binding source
    # carries the caveat.
    backing = desk.authority_for(answer.citation)
    from_position = backing is not None and backing[0] == "position"
    binding = bool(from_position or source.binding)
    astray, why = cited_off_source(answer, desk, question, source=source)
    supplied = tuple((context.facts if context else {}) or {})
    undeclared = tuple(k for k in supplied if k not in (desk.records or ()))
    return Served(
        binding=binding,
        straddle=_straddle_note(verdict, desk),
        undeclared=undeclared,
        off_source=(
            f"THIS DESK DOES NOT DECLARE THAT SOURCE FOR THIS SUBJECT, and the "
            f"paragraph may still be the right one — the declaration is a "
            f"keyword table, not a reading. {why} Check the passage below "
            f"answers what was asked before relying on it."
        ) if astray else "",
        # A FIRM POLICY IS BINDING AND STILL CARRIES A CAVEAT, which is the one
        # combination this field did not have before `dec-pos2`.
        #
        # The firm's first condition, verbatim: *"I'm good with this but can I
        # want this to be clearly marked as they may need to be
        # reviewed/changed at some point."* So it SERVES — "I'm good with this"
        # — and it says what it is. That is the same disposition they chose for
        # guidance on the fourth docket ("Serve it, marked"), for the same
        # reason: refusing throws away a real answer, and serving silently
        # throws away the one thing the reader needs to know about it.
        #
        # AND IT SAYS WHETHER ANYBODY HAS CHECKED IT. Their second condition is
        # the inverse of a citation check — does anything on file contradict
        # this — and until somebody has read `ask.review_brief` and written what
        # they found into `Reviewed:`, the honest answer is nobody knows. An
        # uncited position is exactly the kind that can sit against authority
        # with nothing noticing, so "nobody has looked" is a fact about this
        # answer and belongs on it.
        caveat=(
            (f"This is the firm's own standing policy. It rests on the firm "
             f"and not on any paragraph — there is nothing to go and read "
             f"behind it, which is why it says so. "
             + ("Nobody has yet checked it against the authority on file; "
                "`ask.review_brief` is what puts that question to the firm."
                if getattr(passage, "unreviewed", False) else
                f"Checked against the record: {getattr(passage, 'reviewed', '')}"))
            if from_position and getattr(passage, "is_policy", False)
            else "" if binding else (
                f"This rests on {source.title}, which is {source.tier} "
                f"authority: the IRS's own guidance, not the rule. No binding "
                f"authority on this desk reaches the question. Read it as the "
                f"Service's stated position and not as settled law.")),
        # A position is the firm's words, so those are the words that leave the
        # desk -- not a restatement, however close. `_check` has already refused
        # one that disagrees; this makes the agreeing case exact rather than
        # merely equivalent, which is what "the model proposes, the engine
        # disposes" means at the only point where it is observable.
        position=getattr(passage, "position", None) or answer.position,
        citation=passage.citation,
        tier=source.tier,
        # THE HOST'S TIER IS NOT THE DOCUMENT'S. `candidates.source` builds its
        # tier from `domains.tier_for`, which classifies a publisher; the record
        # classifies a document by hand, and a candidate is one document nobody
        # has read. Printing the host's answer in the document's slot is a badge
        # the caveat underneath then has to retract.
        classified=getattr(source, "id", "") != "candidate",
        # A passage records when someone last confirmed it against the source;
        # a position records when the firm took it. Both answer "how old is
        # this?", which is what a caller needs, and neither is allowed to be
        # absent -- so read whichever this authority carries rather than
        # defaulting one in.
        checked=getattr(passage, "checked", None) or passage.recorded,
        # Stated rather than implied. `tier='primary'` used to be the whole
        # story a caller got, and it read as "this is solid" when all that had
        # been verified was that the authority exists and binds.
        checked_subject=bool(
            question and any(_canon_touches()(question, t) for t in desk.fires_on)
        ),
        # THE AUTHORITY UNDERNEATH, not the answer restated.
        #
        # `_check` resolves through `authority_for`, which on a ratified
        # citation hands back the POSITION — and a Position has no `.text`,
        # only `.position`. The first fix for the resulting empty field fell
        # back to `.position`, which made the field echo the answer:
        #
        #     an entry in the books            <- position
        #     > an entry in the books          <- "the words it rests on"
        #
        # The Forge tester, 7 September 2026: *"the whole argument for `passage`
        # is 'so the reader can check the conclusion against the words it rests
        # on' — and here the words it rests on are the Pub. 583 text, which is
        # not shown. The one case where the reader is told a human already
        # decided is the case where the underlying authority becomes
        # invisible."* Correct, and the text was reachable the whole time:
        # `desk.passage()` on the same citation carries 2,683 characters of it.
        #
        # So the SOURCE TEXT wins wherever the desk holds any, and the firm's
        # words are the fallback only for a citation-only source — `human_only`,
        # where a position genuinely IS the desk's entire knowledge of the
        # authority and there is nothing else to show.
        passage=(getattr(passage, "text", "")
                 or getattr(desk.passage(answer.citation), "text", "")
                 or getattr(passage, "position", "") or ""),
        # COMPUTED, NEVER PASSED, for the same reason `unchecked` is: an answer
        # that can be constructed without it is one that will be. Read off the
        # record on EVERY served answer and not only the position-backed ones —
        # an agent citing the bare section, with no qualifier, has a stem that
        # matches both halves and most needs telling that the firm split it.
        alongside=tuple(
            (p.citation, p.position,
             getattr(desk.passage(p.citation), "text", "") or "")
            for p in desk.alongside(answer.citation)),
        # TWO DIFFERENT SENTENCES, BECAUSE TWO DIFFERENT THINGS ARE TRUE.
        #
        # A POSITION-BACKED ANSWER HAS BEEN CHECKED, by the firm, and saying
        # otherwise is a lie in the safe direction -- which is still a lie, and
        # a worse one here: a disclaimer that cries wolf on the safest answers
        # teaches a reader to skip it on the dangerous ones. `_check` has
        # already refused any restatement, so the words above ARE the firm's
        # words for this citation; there is no gap between conclusion and
        # authority to warn about. What is left unchecked is narrower and real:
        # whether the firm's position fits THESE facts.
        #
        # Found by running the round trip. Printed for a person, the first
        # version showed the firm's position as the thing to check the answer
        # against, when the engine forces them to be identical -- so it read as
        # "check this against itself".
        # THE LAST TWO SENTENCES ARE DROPPED WHENEVER `alongside` CARRIES THEM.
        # The Desk session, reading the two blocks two lines apart: *"'Which one
        # is in play is a question about the facts, and nothing here has looked
        # at the facts' and 'What NOBODY checked is whether their position fits
        # these particular facts' are the same sentence [...] Repetition is how
        # a warning becomes wallpaper, and this is a warning you want read on
        # the run where it matters, possibly months from now."* Their call on
        # which to keep, and it is the right one: the `alongside` copy is bound
        # to the specific fork, this one is general.
        unchecked=(
            ("THE FIRM RATIFIED THIS CONCLUSION for this citation, and it is "
             "served in their words rather than a restatement — the engine "
             "refuses one that disagrees."
             + ("" if desk.alongside(answer.citation) else
                " What NOBODY checked is whether their position fits these "
                "particular facts. That judgement is yours."))
            if from_position else
            # SHORTER THAN IT WAS, because it has to survive repetition. The
            # Forge, after handing three of these to an accountant: *"at one
            # answer it lands; at the fortieth of a close, the eye slides off
            # the capitals and the reader stops reading the part that varies.
            # The load-bearing content is the first clause plus 'read the
            # passage below'; the middle inventory of what was checked is the
            # part I would actually cut."* Cut. What was checked is a property
            # of the source and is already printed beside the citation.
            ("Nobody checked that this paragraph says this — only that the "
             "citation resolves and the source is one this desk uses here. "
             "Read the passage below.")),
    )


#: The escalations whose fix is A PERSON ANSWERING A QUESTION. Each of these
#: refuses without an `ask`, because a refusal a caller cannot act on is a
#: dead end wearing a reason code.
#:
#: NOT EVERY REASON. `authority_absent` is a search task and there is nobody to
#: ask; `model_gave_up` and the two source failures are not questions at all.
#: Requiring one everywhere would produce a question invented to satisfy a
#: check, which is worse than none — the firm would answer it and learn nothing.
MUST_ASK = (
    "facts_not_established",    # the rule is clear; what was bought is not
    "context_not_on_file",      # the FILE should hold it; a preparer fills it in
    "document_not_requested",   # a named document settles it and nobody asked
)


def _reason(reason: str) -> str:
    if reason not in REASONS:
        raise EngineError(
            f"escalation reason {reason!r} is not one of: {', '.join(REASONS)}. "
            f"An open reason set cannot be counted."
        )
    return reason


def grade(answer: Answer, problem: Problem, desk: Desk) -> Result:
    """Verify the citation, then grade against the known answer.

    Verification and grading are genuinely separate and stay separate. A citation
    can resolve to a passage that does not support the claim, and an answer can be
    right while citing the wrong paragraph — collapsing them would report both as
    the same thing.
    """
    if answer.escalated:
        return Result(problem.id, Outcome.ESCALATED, reason=_reason(answer.reason),
                      escalated_by=DESK)

    # THE PROBLEM'S OWN CONTEXT, not the caller's. A worked example carries the
    # facts it was written with, and grading it against anything else would
    # measure the harness rather than the desk.
    refusal, passage, source, _ = _check(answer, desk, problem.facts, problem.context)

    if refusal is not None:
        # An interpretive source is not an error, it is the case where authority
        # permits a choice — so it escalates rather than counting as wrong.
        if refusal.reason == "authority_permits_choice":
            return Result(problem.id, Outcome.ESCALATED,
                          reason=refusal.reason, detail=refusal.detail,
                          escalated_by=ENGINE)
        return Result(problem.id, Outcome.WRONG_CAUGHT,
                      reason=refusal.reason, detail=refusal.detail)

    # THE CITATION MUST SUPPORT THIS PROBLEM, not merely exist.
    #
    # Written without this check, an answer that gave the right conclusion while
    # citing any other primary passage in the desk was scored CORRECT — so a
    # model could reach the right verdict from the wrong paragraph, or from a
    # paragraph about something else entirely, and inflate the scoreboard. That
    # contradicts this function's own stated distinction between a citation that
    # resolves and a citation that is the right one, which had been written down
    # and then not implemented.
    if passage is not None and passage.citation != problem.citation:
        return Result(
            problem.id, Outcome.WRONG_CAUGHT, reason="citation_does_not_support",
            detail=f"cited {answer.citation!r}, which is real authority but not "
                   f"what this question turns on ({problem.citation!r})",
        )

    if _same(answer.position, problem.answer):
        return Result(problem.id, Outcome.CORRECT)

    return Result(
        problem.id, Outcome.WRONGLY_ABSORBED,
        detail=f"answered {answer.position!r} with authority that held; the "
               f"example concludes {problem.answer!r}",
    )


def _mid_sentence(text: str) -> str:
    """The firm's own sentence, set inside one of ours. First letter folded,
    every other left alone -- "the United States" is not "the united states"."""
    text = text.strip().rstrip(".")
    return text[:1].lower() + text[1:]


def _straddle_note(verdict, desk) -> str:
    """The sentence a reader sees when the words did not rule the other body out.

    REWRITTEN 8 SEPTEMBER, BY THE READER IT IS FOR. The first version put the
    machine's tie-break in the middle and the consequence last, conditional. The
    Forge desk read it as the six-o'clock reader and took it apart:

        "S2 IS THE ONE I SKIM. It is 38% of the note and it is the machine
         explaining its own tie-break. At 6pm I do not care HOW the gate
         decided; 'name sort' is a fact about your sort key, not about my
         books."

        "The operative clause is LAST and it is CONDITIONAL […] THE READER WHO
         IS ABOUT TO MAKE THIS MISTAKE IS EXACTLY THE READER WHO DOES NOT KNOW
         THEIR QUESTION HAS TWO HALVES. You are asking the one person who cannot
         answer it to self-diagnose, at the end of the longest sentence."

        "It never says DO NOT ACT ON THIS."

    So: consequence first, no internals, and the other half named in the firm's
    own plain words rather than by its body's thirteen-word legal name. That
    phrase is `Domain.about`, already written in `DOMAINS.md` -- "what the books
    say, and what goes on the balance sheet" -- so nothing here is invented.

    LENGTH WAS NOT THE PROBLEM AND IS NOT CHANGED. Asked directly whether three
    lines is too much at four correct answers per wrong one: *"THREE LINES IS
    CHEAP AND I WOULD NOT SHORTEN IT. On the four correct tax answers the note
    is not noise: it truthfully tells a tax-correct answer that a book half
    exists and is not covered. That is a second finding, not a tax. The thing
    that IS noise on all five is S2."*
    """
    if verdict is None:
        return ""
    apart = getattr(verdict, "apart", ())
    if not apart:
        return ""
    import domains as _domains

    won = verdict.domain
    others = [d for d, _ in apart]
    # `about` IS THE FIRM'S OWN SENTENCE. Only its first letter is folded so it
    # reads inside ours: `.lower()` on the whole thing published "what a
    # taxpayer owes the united states, and when".
    theirs = ", ".join(_mid_sentence(d.about) for d in others)
    held = _domains.reachable(others, desk)

    # THE WINNER IS NAMED AND NOT EXPLAINED; the OTHER half is explained. That
    # is the desk's own draft and it is right: the reader can see the answer
    # above, so what they need is what it is NOT about. Spending a clause on
    # `federal-tax.about` here cost nine words and told them nothing new.
    out = [f"THIS ANSWER MAY NOT BE ABOUT YOUR QUESTION. It answers the "
           f"{won.name} half only."]

    if verdict.only_shared_words:
        # NOTHING WAS WEIGHED, so the note must not imply anything was. The fix
        # is in the asker's wording and only they can make it.
        word = ", ".join(f"{w!r}" for w in verdict.matched) or "what you wrote"
        out.append(f"The other half is {theirs} — and NOTHING YOU WROTE TELLS "
                   f"THE TWO APART: {word} is in both vocabularies.")
    else:
        said = ", ".join(f"{w!r}" for _, words in apart for w in words)
        out.append(f"You also wrote {said}, which belongs to the other half: "
                   f"{theirs}.")

    # THE BODY'S NAME GOES LAST, NOT FIRST. The desk's objection was to opening
    # a sentence with thirteen words of proper noun before the verb -- "the
    # Financial Accounting Standards Board, through the Accounting Standards
    # Codification settles us-gaap" -- and it stands. But a reader who is about
    # to escalate needs to know WHO settles it, and by this point they already
    # know which half they are being warned about, so the name informs instead
    # of blocking.
    who = "; ".join(d.body for d in others)
    out.append(f"This desk holds that half too — ask it that question rather "
               f"than reading the answer above as if it covered both."
               if held else
               f"No desk here holds that half — {who} settles it. If it is the "
               f"half you meant: stop, and escalate.")
    return " ".join(out)


#: Characters that are the SAME CHARACTER as far as the firm's word goes, and
#: differ only in which key or which editor produced them. Nothing here changes
#: a word; each pair is visually identical or near enough that no reader could
#: tell them apart on a screen.
#:
#: `dec-apostrophe`, 10 September 2026. Forge-Occam had a submission refused
#: `contradicts_ratified_position` over a curly versus straight apostrophe
#: inside the firm's own quoted position -- two characters that look identical,
#: one of which Word, phones and most editors insert automatically. It cost a
#: round and the cause was invisible to the person hitting it. Offered the
#: choice between normalising and staying byte-exact, the firm: **"Normalise."**
#:
#: THIS LIST IS CLOSED AND STAYS SHORT. Every entry is a crack in "a desk does
#: not revise the firm's word", and the principle is right: the reason this is
#: defensible is that a curly apostrophe is not a different word, it is a
#: different way of typing the same one. Anything that could change meaning --
#: a word, a number, a negation -- must still fail.
_TYPOGRAPHY = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u2032": "'", "\u00b4": "'", "\u0060": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2033": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2015": "-", "\u2212": "-",
})

#: KNOWN AND DELIBERATELY NOT HANDLED: a non-breaking space (U+00A0) inside a
#: position still fails the comparison. It is the same class of invisible
#: hazard, the firm approved quotes and dashes, and widening past what they
#: approved is the failure this whole check exists to prevent. Recorded here so
#: the next person hitting it finds a note rather than a mystery.


def _same(given: str, known: str) -> bool:
    """Compare a conclusion to the known one.

    Exact once normalised for case, surrounding space, and the typographic
    variants in `_TYPOGRAPHY` -- and exact in every other respect. A looser
    comparison here would quietly turn wrong answers into right ones, which is
    the one direction this code must never fail in, and `wrongly_absorbed` is
    precisely the count a generous comparison would hide.
    """
    return (given.translate(_TYPOGRAPHY).strip().casefold()
            == known.translate(_TYPOGRAPHY).strip().casefold())


def tally(results: list[Result]) -> dict[str, int]:
    """Count outcomes. Ordered with the costly one first, never summed."""
    return {o.value: sum(1 for r in results if r.outcome is o) for o in Outcome}


def report(results: list[Result]) -> str:
    """The denominator, written so the number that costs something is read first.

    Zero is stated rather than omitted: a line that disappears when it is clean
    teaches a reader that its absence means nothing was checked.
    """
    counts = tally(results)
    width = max((len(k) for k in counts), default=0)
    lines = [f"{len(results)} graded"]
    lines += [f"  {name:<{width}}  {counts[name]}" for name in
              (o.value for o in Outcome)]
    return "\n".join(lines)
