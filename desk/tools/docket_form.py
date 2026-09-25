"""The docket, as a form — generated from the record, not from a session's memory.

Behaviour 14 says keep the log where the work is; the docket skill says a docket
is a thing the firm FILLS IN, not prose that ends in questions. So this writes
one page carrying every open decision with both outcomes, a recommendation
marked as one, and a box to answer in — and it takes the seventeen proposed
positions straight out of `desks/`, so the page cannot show a position a desk
does not hold.

The five non-position decisions are hand-written here because they are not in
the record: they are choices the authority leaves open, drafted from the firm's
own close questions in `docs/DECISIONS-WAITING-2026-09-05.md`.

ONE PAGE, ONE STORE. An artifact's store belongs to that artifact, so two pages
asking the same question cannot see each other's answers whatever the collection
is called -- renaming the collection would not have joined them. The docket is
therefore the only page that asks; the walkthrough and the earlier ratification
page were replaced with pointers to it rather than left live to collect a second,
invisible answer.

NOTHING ON THIS PAGE IS COUNTED BY HAND. Every total, filter label and figure in
the preface is derived from the rows generated above, because the first thing
that happens after a ratification is that this file gets run again -- and a page
that says seventeen when the record holds sixteen is the exact failure the
generator exists to prevent.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from position_walkthrough import positions                  # noqa: E402

#: Today, not a date typed into the file. The third docket went out headed
#: "5 September" because this was a literal and the run happened after midnight.
DATE = "%d %s %d" % (date.today().day, date.today().strftime("%B"), date.today().year)

#: The decisions no authority settles. Each carries BOTH outcomes and what it
#: costs to be wrong, because a decision handed over without its downside is one
#: somebody makes twice.
#: Every matter the SIXTH docket carried, READ BACK from `artifact/83e68c31`'s
#: own store rather than from this session's memory of publishing it. It is the only independent record of what was already open: without it,
#: "which matters are new" is read out of the same list that sets it.
#:
#: All eight were answered between 13:09 and 13:16 UTC on 7 September. Three
#: were ratifications, two were instructions to build, and both of those are
#: built. Nothing from that page is carried here: a matter the firm has answered
#: is not a matter, and asking it again is the fault this page was rebuilt to
#: stop.
#: AND FOUR MORE, ADDED 14 SEPTEMBER 2026, read off the Desk Docket page
#: published at artifact 642c3276 rather than off anything this file claims. That
#: page carried them as D2, D3, D4 and F4; they are the same four questions.
#:
#: THE BUG THIS FIXES, and it is the one this whole mechanism exists to stop.
#: The set named ONE page, 7 September. A matter carried from any page since then
#: has a key it never held, so it counted as NEW -- and the eighth docket rendered
#: "All eight are new" over four questions the firm had been holding across three
#: dockets, the oldest of which has blocked two ratified positions on every client
#: since 5 September. Telling somebody a question they have been sitting on for a
#: week is new is worse than not counting at all.
#:
#: THE FIX THAT WAS TRIED FIRST AND WAS WRONG: deriving it from a `"new": False`
#: flag on the card. The test caught it in one run. A flag is a claim the page
#: makes about itself, and the note above records two mutations surviving on the
#: third docket for exactly that reason. The set stays the record; it just has to
#: be kept current, which is what was actually broken.
ALREADY_OPEN = {
    # open on the Desk Docket, 14 September (artifact 642c3276)
    "dec-caprule",
    "dec-fasb",
    "dec-tie",
    "dec-unitcost",
    # the sixth docket, 7 September (artifact 83e68c31)
    "dec-courts-again",
    "dec-merge-300",
    "dec-parser",
    "dec-register",
    "dec-searcher-scope",
    "pos-capitalization-and-de-minimis-POS1",
    "pos-capitalization-and-de-minimis-POS2",
    "pos-rewards-and-information-returns-POS3",
}

#: EVERY MATTER THE SEVENTH DOCKET CARRIED, AND ALL FOUR ARE ANSWERED. They are
#: kept here rather than deleted because a docket that simply drops an answered
#: matter gives the firm no way to see what their answer did -- and the answer is
#: read back out of the PAGE'S OWN STORE, not out of this session's memory of
#: being told.
#:
#: THE INCIDENT, 7 September 2026, and it is why this list exists at all. The
#: firm filled the seventh docket in at 15:49. The page was then republished with
#: a new goal on it -- and the same four cards, three showing their answers and
#: one, answered in conversation rather than on the form, still showing as open.
#: The firm: *"i am generally confused i have filled this docket out"*. Correct:
#: they had. Republishing a docket over its own answered questions asks them
#: again, which is the exact fault the sixth docket was rebuilt to stop, arriving
#: through a door nothing was watching.
ANSWERED = [
 {"key": "dec-caprule",
  "title": "What is the default capitalisation rule for a client that has none?",
  "said": "Record it at intake",
  "where": "on the eighth docket, 14 September — with the note that was the real answer: “The firm’s threshold for our clients if non specified will be based on IRS rules for simplicity.”",
  "caused": "<b>Two of your twenty ratified positions are reachable again</b>, after "
            "being unservable on every client since 5 September. The refusal still "
            "refuses — you were offered a silent default in the code and declined it "
            "— but it now says what to write.<br><br><b>My first version told the "
            "preparer to write the wrong thing, and only running it showed that.</b> "
            "I had it say “record the IRS ceiling”, and recording a FIGURE is how you "
            "tell the desk this client is different. Four states, measured: blank "
            "refuses, <code>none</code> SERVES at your $2,500 / $5,000, and any "
            "figure at all refuses as a client-level rule. The word is "
            "<code>none</code>; POS2 supplies the number itself. All four are "
            "pinned.<br><br>And POS2’s own caveat is on the line where a preparer "
            "reads it: the safe harbour protects amounts under whichever is LOWER, "
            "their book policy or the ceiling — so POS3’s fact is load-bearing, not "
            "optional."},

 {"key": "dec-fasb",
  "title": "Is a free FASB update acceptable authority where the Codification is licensed?",
  "said": "Admit ASUs, secondary",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>BLOCKED, and not by anything in the desk.</b> This is the only one of "
            "the eight not built. Admitting a source means verifying its words "
            "against the publisher’s own page — that rule is the whole reason the "
            "searcher is allowed to look anywhere — and <b>fasb.org is refused by "
            "this environment’s network policy</b>. Measured rather than assumed: "
            "irs.gov answers 200 and ecfr.gov 302 from the same container, while "
            "www.fasb.org, fasb.org and asc.fasb.org all return 403, and the proxy’s "
            "own log names <code>fasb.org:443 connect_rejected</code>. Its "
            "instructions say to report a policy denial rather than retry it.<br><br>"
            "<b>Nothing was admitted from memory</b>, which is the one thing that "
            "would have been worse than not doing it.<br><br><b>Your existing map "
            "already fits the answer</b>, so nothing there needed changing: "
            "<code>DOMAINS.md</code> lists fasb.org under both <i>Publishes</i> (the "
            "Codification — primary, licensed) and <i>Explains itself at</i> (“the "
            "body’s own explanation, which is not the thing that governs” — "
            "secondary). An ASU lands in the second. What is missing is only the "
            "source entry, and that needs one fetch nobody here can make."},

 {"key": "dec-tie",
  "title": "When two bodies of authority tie, refuse — or warn and serve?",
  "said": "Keep warning",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>Nothing built, and that is the whole answer.</b> The 4-right-to-1-wrong "
            "trade stands. The evidence offered for changing it turned out to be "
            "about a different guard, which is the card below."},

 {"key": "dec-offsource",
  "title": "Should “this desk does not declare that source” refuse instead of warn?",
  "said": "Keep warning",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>Nothing built.</b> Measured first: refusing would refuse <b>17 of 98</b> "
            "recorded-correct answers on terse phrasing and <b>0 of 98</b> on "
            "full-facts phrasing. <b>That 17-versus-0 spread stays on the record as an "
            "open defect in the guard</b> rather than a closed question — it means the "
            "gate is partly measuring how wordy the asker is."},

 {"key": "dec-pair",
  "title": "Should the pool return your two opposite answers as an inseparable pair?",
  "said": "Pair them",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>A ratified sibling now comes back beside its partner whatever it "
            "scored, marked with what it came back beside</b> — a sibling placed by "
            "adjacency alone reads as having scored, with its own lower number next to "
            "it looking like the reason.<br><br><b>The question it exists for proved "
            "nothing.</b> On the 7 September deposit question the two halves were "
            "already adjacent, so a test written only on it would pass with the "
            "feature deleted. The case that exercises it is <i>“how do we treat "
            "deposits with no source recorded?”</i> — one of the three phrasings your "
            "own comparison document publishes as evidence the pool beat the word "
            "list. There the RIGHT half scores 5.7 and is now placed above a hit "
            "scoring 7.8."},

 {"key": "dec-scoped",
  "title": "Should a passage that says it applies somewhere else be marked as such?",
  "said": "Mark them",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>A passage that scopes itself in its own opening words now says so, "
            "printed directly above the passage</b> — not below, because a reader who "
            "has reached the end of a 2,000-character definition has already decided "
            "what it is about.<br><br><b>The docket said 36 and the measurement says "
            "28.</b> 36 counted a scoping phrase anywhere in the opening 300 "
            "characters, which sweeps in thirteen mid-sentence cross-references — a "
            "rule pointing at where its own sub-clause applies, which is not a passage "
            "announcing its reach. All six rows you were shown are inside the 28, and "
            "finding the difference turned up a real miss: a definition whose clause "
            "ends in a colon.<br><br><b>Marking does not fix the ranking, and that is "
            "pinned as a test.</b> The scoped definition still comes back first."},

 {"key": "dec-examples",
  "title": "What should the brief do with worked examples?",
  "said": "Label and never examples-only",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>Both halves built.</b> Every worked example in the answering brief now "
            "says it is another taxpayer’s facts and what to do about it; the grading "
            "brief still prints none.<br><br><b>I nearly shipped a guard that never "
            "fires.</b> The four questions I tried by hand all had a rule in their top "
            "eight. Measured on the whole denominator instead — fifteen working "
            "questions plus all 98 problems — it fires on <b>6 of 113</b> at the "
            "default, 13 at five hits, 25 at three.<br><br><b>And the rule it pulls in "
            "can be wrong, so the brief says so.</b> On those six it scores as low as "
            "3.2 — on <i>“A contractor paid by cheque”</i> it is a MEALS rule. That is "
            "the honest top-ranked rule and it is not about the question, so the brief "
            "says it was not among the closest matches and that the record may simply "
            "not hold one that is."},

 {"key": "dec-unitcost",
  "title": "Should the record hold what something cost?",
  "said": "Add it, with a format check",
  "where": "on the eighth docket, 14 September",
  "caused": "<b>The field was one word, as measured. The format check is the change.</b> "
            "It fires where the fact is RECORDED, not where it is answered: "
            "<code>Context</code> is frozen, so every path that builds one goes through "
            "the same constructor.<br><br>Forgiving about spelling, strict about being "
            "a number — <code>$2,500</code> is how POS2 itself writes the ceiling, so "
            "refusing that spelling would be a check nobody could satisfy from the "
            "documents in front of them. <i>one eighty five</i>, <i>about 200</i>, "
            "<i>185 each</i> and <i>12.345</i> all refuse. Nothing is normalised.<br><br>"
            "<b>Proved on the case it was added for.</b> The file that made round trip "
            "<code>a276e4aed20a</code> throw an answer away now prints "
            "<code>unit_cost: 185.00</code> under ON FILE."},

 {"key": "dec-whytrunc",
  "title": "A position\u2019s reasoning is cut off before it reaches the card you ratify from. Fix it?",
  "said": "Read the whole thing, folded",
  "where": "on the eighth docket, 18 September",
  "caused": "<b>The whole of a position\u2019s reasoning reaches the card now, and "
            "the default view did not move a character.</b> The opening paragraph "
            "is byte-for-byte what you were already reading \u2014 429 characters "
            "on POS2 \u2014 and the 1,831 that never arrived are one disclosure "
            "below it, with the fold saying how much is behind it.<br><br>"
            "<b>The fix was a reader, not a renderer.</b> A field ended at any "
            "line starting with bold, which is right for a value that wraps and "
            "wrong for prose \u2014 because a paragraph written to be read starts "
            "with its point in bold. Prose now ends at the entry\u2019s own field "
            "names, which is exact.<br><br><b>The tidy heuristic would have been "
            "worse than the bug.</b> Ending at any bold-text-then-colon looked "
            "right and `POSITIONS.md` contains one paragraph that opens <i>\u201cWhat "
            "this position does NOT settle, and why it is a position at "
            "all:\u201d</i> \u2014 so it would have truncated the reasoning at "
            "precisely the sentence a reader most needs. Found by looking, not by "
            "thinking about it.<br><br><b>And it moved a number nobody touched.</b> "
            "One unused gate reads a position\u2019s reasoning as part of its "
            "subject check, so giving it the rest of the text made one answer stop "
            "being wrongly refused \u2014 36 of 98 down to 35. Right direction, and "
            "it exposes a coupling nobody chose: how far that gate reaches depends "
            "on how much you happened to write. Recorded where the figure is "
            "pinned rather than fixed, because the gate is unused and fixing it "
            "means deciding what it should read."},
]

#: THREE MATTERS, all of which arrived AFTER the page said nothing needed
#: deciding -- which is the normal life of a docket rather than a fault. Each one
#: blocks something concrete: the Forge cannot be set up, a desk cannot answer a
#: question it now has the words for, and a hole found in the seam cannot be
#: closed without the firm saying so.
#: NOTHING IS OPEN. The three that were here were answered at 17:20 and are in
#: `ANSWERED` above with what each one did. A key may not be in both.
OTHERS = [
 {"key": "dec-reach",
  "kind": "decision",
  "group": "From the pilot",
  "tag": "retrieval \u00b7 dec-reach",
  "title": "How does a question reach authority that does not use the asker\u2019s words?",
  "rec": "<b>Add plain words.</b> Normalising the spelling is a day\u2019s work and "
         "I would do it either way, but measured it buys about one question of the "
         "five. The other four fail because the authority genuinely does not "
         "contain the words a preparer asks in \u2014 \u00a71.263(a)-1(f) never "
         "says <i>tool</i>, and \u00a71.274-11 never says <i>brewery</i>. No amount "
         "of tuning a score fixes that. <b>I want to name the thing you will "
         "object to before you read it:</b> this resembles <code>fires_on</code>, "
         "the word list you told me three times to delete. The difference is the "
         "whole recommendation \u2014 <code>fires_on</code> decided WHICH DESK a "
         "question reached, so a wrong word sent it somewhere else and the right "
         "authority became unreachable. Plain words would only ever ADD a passage "
         "to the pool, never remove one, and I would build the test that proves "
         "it cannot exclude before I build the feature. If you do not want it, "
         "say <i>normalise only</i> and I will ship the cheap half and we will "
         "live with six of eleven.",
  "rec_pick": "Add plain words",
  "position": "Each source declares the words a preparer would ask it in, and those "
              "words widen what the pool returns \u2014 they can never narrow it.",
  "context": "<b>The jargon, then what it means.</b> The desk scores every passage "
             "with <b>BM25</b> \u2014 a formula that rewards a passage for "
             "containing the question\u2019s words, and rewards rare words more "
             "than common ones. It has no idea what any word means. So a question "
             "reaches authority when the two happen to share vocabulary, and "
             "misses it when they do not.<br><br><b>The clean proof is your own "
             "Q4.</b> You asked <i>\u201cwhat is the capitalisation threshold?\u201d</i> "
             "The answer is on file \u2014 38 passages of \u00a71.263(a)-1(f), the "
             "de minimis safe harbour. It is not returned. Not ranked low: not "
             "returned at all. You spell it <i>capitalis</i>ation; the corpus "
             "spells it <i>capitaliz</i>ation 147 times and your spelling zero "
             "times. One letter. The only word left is <i>threshold</i>, and the "
             "1099 instructions have a heading called <b>\u201cIncrease in "
             "threshold\u201d</b> \u2014 so the desk answers a question about "
             "capitalising assets with the 1099 filing threshold. Spell it the "
             "American way and the safe harbour climbs to 14th, still outside the "
             "eight the answerer sees. Ask it as <i>\u201cde minimis safe harbor "
             "threshold\u201d</i> and it is 4th. <b>The desk answers when you "
             "already know the words the authority uses, which is the condition "
             "under which you did not need it.</b>",
  "either": [
    ("If you say add plain words",
     "Six of eleven becomes something I can move, and the mechanism is additive "
     "\u2014 a passage can be found by more routes and lost by none. The cost is "
     "real: the firm's vocabulary enters the record, which means it is yours to "
     "get right and mine to keep tested, and a source with sloppy words is a "
     "source that drags junk into briefs. It is roughly a week, not a day."),
    ("If you say normalise only",
     "You get the cheap, safe half \u2014 spelling and word endings \u2014 and "
     "nothing that requires a judgement about meaning. Q4 starts working. Q6, "
     "Q16, Q18 and Q31 do not, because no spelling rule connects "
     "brewery to \u00a71.274-11. The desk stays roughly where it is and "
     "we stop calling that a bug."),
    ("If you say neither",
     "The desk keeps refusing questions it holds the answer to, and those "
     "refusals read as caution. That is the part I would push back on: a wrong "
     "answer announces itself and a false refusal does not."),
  ],
  "picks": ["Add plain words", "Normalise only", "Neither", "Not yet"]},

 {"key": "dec-hyphen",
  "kind": "decision",
  "group": "From the pilot",
  "tag": "retrieval \u00b7 dec-hyphen",
  "title": "Should a hyphen between two ordinary words split them into two?",
  "rec": "<b>Split on a letter hyphen.</b> I told you yesterday this was too "
         "dangerous to touch because it risked every citation we hold. I measured "
         "it and that was wrong. The corpus holds 205 distinct hyphenated tokens: "
         "<b>113 contain a digit and 92 do not, and nothing is in both sets.</b> "
         "So \u201csplit only when there is no digit on either side\u201d leaves "
         "<code>1099-K</code>, <code>1.263(a)-3</code> and all 113 citation-shaped "
         "tokens untouched, and splits <code>cash-back</code>. It is a small, "
         "testable rule with a measurable blast radius \u2014 not the "
         "all-or-nothing I described.",
  "rec_pick": "Split on a letter hyphen",
  "position": "A hyphen splits a token only when there is no digit on either side "
              "of it, so citations stay whole and ordinary compound words do not.",
  "context": "<b>What Occam hit.</b> Asking about <i>cash-back</i> returns "
             "<b>nothing</b>; asking about <i>cash back</i> returns <b>20 "
             "passages</b>. <code>pool.terms</code> keeps the hyphen inside the "
             "word on purpose \u2014 that is <code>dec-fullstop</code>, and it "
             "exists so <code>1099-K</code> and <code>1.263(a)-3</code> survive "
             "tokenising. It does its job and it also swallows every ordinary "
             "English compound.<br><br><b>The honest cost, stated plainly:</b> 92 "
             "tokens change how they score \u2014 <i>built-in</i>, "
             "<i>first-in</i>, <i>half-year</i>, <i>employer-provided</i>. Every "
             "passage containing one of those is scored slightly differently "
             "afterwards, which means rankings across the whole corpus move a "
             "little. That is not a risk to citations; it is a re-measurement I "
             "would have to run.",
  "either": [
    ("If you say split",
     "cash-back and every other compound become findable. 113 "
     "citation tokens are provably untouched, and I would pin that with a test "
     "that fails if any of them ever splits. The 92 that do change shift the "
     "ranking slightly everywhere, so I re-run the 43 and report what moved "
     "before it ships."),
    ("If you say leave it alone",
     "Nothing anywhere moves and the tokeniser stays provably safe. Any question "
     "asked with a compound word keeps returning nothing at all \u2014 which is "
     "the worst failure shape the desk has, because zero results is "
     "indistinguishable from an honest hole."),
  ],
  "picks": ["Split on a letter hyphen", "Leave it alone", "Not yet"]},

 {"key": "dec-briefsize",
  "kind": "decision",
  "group": "From the pilot",
  "tag": "retrieval \u00b7 dec-briefsize",
  "title": "Should the answerer see more than the top eight passages?",
  "rec": "<b>Leave it at eight.</b> This is the obvious lever and I measured it "
         "so we could stop reaching for it. Going 8 \u2192 50 takes six of eleven "
         "to nine of eleven, and costs <b>five times the text</b> \u2014 6,300 "
         "characters of authority per brief becomes 32,300, which is about 8,100 "
         "tokens and sits on the ceiling of the 8,192-token window "
         "<code>LOCAL-LLM-PATTERN</code> rule 1 is written to. No room left for "
         "the question or the answer. <b>And it cannot buy the two worst:</b> Q4 "
         "and Q6 return nothing to rank, so there is no size that reaches them. "
         "Raising this would look like progress and would mostly buy noise.",
  "rec_pick": "Leave it at eight",
  "position": "The brief stays at eight passages; reach is fixed by finding the "
              "right passage, not by showing more wrong ones.",
  "context": "<b>What a brief is.</b> <code>pool.look</code> ranks every passage "
             "in the corpus and the top eight are what the answering model "
             "actually reads. Everything below eight might as well not be on "
             "file.<br><br><b>Measured on your eleven authority questions:</b> at "
             "8 the right authority is present for six; at 15 for seven; at 25 "
             "for seven; at 50 for nine. The curve is flat where it is cheap and "
             "expensive where it is not.",
  "either": [
    ("If you leave it at eight",
     "Nothing changes and nothing gets worse. The five misses stay misses until "
     "matter one is answered, which is where they are actually fixable."),
    ("If you raise it",
     "Three more questions reach their authority. Every brief carries five times "
     "the text, which breaks the local-model window outright and, on any model, "
     "buries the passage that matters among 42 that do not. A brief that holds "
     "everything is a brief that says nothing \u2014 the same argument "
     "consult already makes about handing over the whole corpus."),
  ],
  "picks": ["Leave it at eight", "Raise it", "Not yet"]},
]

#: BEHAVIOUR 19, ADDED TO CANON THIS MORNING AS 1.13.0: name the goal, report the
#: distance, then stop. Its incident is this session -- *"i feel like sometimes the
#: feedback is endless for the sake of being endless, when a stated goal can be
#: worked towards then moved naturally"* -- and the docket is where the firm asked
#: for it to live, so that the goal survives the session in the log rather than in
#: a session's memory of it.
#:
#: THE ONE ITEM SILENCE APPROVES, and the page says so in those words. Every other
#: matter blocks until answered; this one proceeds unless the firm objects.
#: Objecting is a line, agreeing is nothing.
#:
#: TWO MATTERS CAME OFF THIS PAGE TO GET HERE. "Add the 34 examples" and "read the
#: 29 written as prose" were drafted as decisions, and they are not decisions --
#: they are the work. Behaviour 19: *"do not manufacture the next decision.
#: Behaviour 13 says decisions go to the human; it does not say produce some."*
NEXT = {
 "goal": "A close\u2019s questions reach the authority the corpus already holds \u2014 "
         "measured on your own 43, not on a set I wrote.",
 "ends": "It ends when all eleven of your authority questions reach their "
         "authority inside the brief the answerer actually sees, and when every "
         "refusal the desk does make lands somewhere you can read it.",
 "distance": "Six of eleven today, and the queue that would record the other "
             "five has not shipped since 14 September.",
 "detail": "<b>V1 is met and I am not re-running it.</b> Occam installed the "
           "plugin from <code>main</code> and closed Sarcia start to finish \u2014 "
           "438 of 485 rows, both accounts tying to 0.00 for a third run. The "
           "skill called the desk and got answers back, which was the whole "
           "test.<br><br><b>Three things I would fix without asking, because none "
           "of them is a choice:</b><br>1. <code>corpus/unsupported/</code> ships "
           "again, so a refusal has somewhere to go. Mine to fix; I broke "
           "it.<br>2. <code>skills/be-the-desk/SKILL.md</code> lines 223 and 233 "
           "call <code>ask.answer(question, desk, ...)</code>. There is no such "
           "signature. A skill is prose an agent executes, so that is a live "
           "defect.<br>3. <code>relay.py</code> never says <i>judged</i> while the "
           "corpus declares <code>Judged: required</code>.<br><br><b>What I will "
           "not do:</b> touch the retriever before you answer matter one. Every "
           "option there changes which passages an answer can be built from, and "
           "picking one quietly is how the word list got built the first time.",
}

CHANGED = [
 ("6 of 11", "authority questions whose authority reaches the brief", "your own 43, measured on 0.34.0 \u2014 the rest of the record is fine, the route to it is not"),
 ("43 of 43", "questions the corpus answers something on", "it has no way to say it does not hold one"),
 ("18 of 43", "top hits sharing one word or fewer with the question", "the pick is made on a single generic token"),
 ("0", "passages of \u00a71.263(a)-1(f) returned for \u201cwhat is the capitalisation threshold?\u201d", "38 are on file; you spell it with an s and the corpus spells it with a z 147 times"),
 ("5\u00d7", "more text to buy four of the five misses", "and the two worst cannot be bought at any brief size"),
 ("1,392", "desk tests passing", "five guards added today, each mutated red first"),
]

LANDED = [
 ("Measured", "<b>43 of 43 close questions return something.</b> The corpus never "
              "says it does not hold a question. That is by design and the design "
              "is defensible; what is below is what it costs."),
 ("Measured", "<b>18 of 43 top hits share one word or fewer with the question.</b> "
              "<i>standard</i> reaches the Standard Mileage Rate twice; <i>draw</i> "
              "reaches a 1099 reporting example four times."),
 ("Measured", "<b>Six of your eleven authority questions reach their authority.</b> "
              "The other five rank 11th, 28th, 33rd, 47th and not at all."),
 ("Measured", "<b>Raising the brief from 8 to 50 buys four of them and costs five "
              "times the text.</b> Two cannot be bought at any size."),
 ("Measured", "<b>113 hyphenated tokens carry a digit, 92 do not, and nothing sits "
              "in both.</b> That is what makes matter two decidable."),
 ("Found", "<b><code>corpus/unsupported/</code> has not shipped since 14 "
           "September.</b> My regression, and the reason the pilot\u2019s refusals "
           "left no record."),
]

UNCHECKED = [
 ("Whether normalising the words actually buys anything.", "The spelling gap is "
  "proven on one question. I have not built a stemmer and measured it across the "
  "43, so the number it would move is unknown \u2014 my estimate of one question "
  "in six is reasoning, not measurement."),
 ("What plain-word indexing does to the questions that already work.", "Six of "
  "the eleven reach their authority today. Adding recall can reorder a brief, and "
  "I have not measured whether any of the six falls out."),
 ("Anything against a live model.", "Every run here is the retriever and the "
  "engine. What a brief with the right passage in it actually produces as an "
  "answer is not measured."),
 ("FASB, still.", "fasb.org is refused by this container\u2019s network policy. "
  "Unchanged since 14 September and nothing was admitted from memory."),
 ("Whether the pilot\u2019s 40 client flags and 7 preparer holds should have been "
  "questions at all.", "Five reached the desk. I have not read the other 47 to "
  "see how many were desk work and never got asked."),
]

WRONG = [
 ("<b>I told you four refusals were the problem. They were the symptom.</b>",
  "Yesterday I reported Occam\u2019s pilot as one served and four refused and left "
  "it there. Putting your own 43 close questions back through the corpus shows the "
  "refusals are mostly FALSE \u2014 the record holds the answer and the question "
  "cannot reach it. I reported the count without measuring the cause."),
 ("<b>&lsquo;The engine decides, not the retriever&rsquo; was doing more work than it could carry.</b>",
  "That is a real finding and it is in the code\u2019s own comments, so I kept "
  "repeating it. It answers whether a SCORE can declare silence. It says nothing "
  "about whether the right passage is in the eight the answerer sees, and that is "
  "the question that was actually failing."),
 ("<b>POS11 did not reproduce.</b>",
  "Occam reported that citing POS11 by its own citation string returned "
  "<code>authority_absent</code>. Run here it is SERVED. Reported as a finding "
  "about the tester, which is what was asked for."),
 ("<b>I let <code>corpus/unsupported/</code> stop shipping and did not notice for eleven days.</b>",
  "Clearing the queue on 14 September left the directory empty and untracked, so "
  "<code>git ls-files</code> returns nothing and the installed plugin has no queue "
  "to write to. <code>tools/holes.py</code> ships to read a store that is not "
  "there. Four real refusals from the pilot went nowhere."),
 ("<b>My first reading of the hyphen was that it was too dangerous to touch.</b>",
  "I said splitting <code>cash-back</code> risks every citation we hold. Measured, "
  "that is wrong: 113 hyphenated tokens contain a digit and 92 do not, and the two "
  "sets do not overlap. It is still a decision, but it is not the one I described."),
]

def _md(t: str) -> str:
    out = html.escape(t)
    for mark, tag in (("**", "strong"), ("*", "em"), ("`", "code")):
        parts = out.split(mark)
        out = "".join(p if i % 2 == 0 else "<%s>%s</%s>" % (tag, p, tag)
                      for i, p in enumerate(parts))
    return out.replace("\n\n", "</p><p>").replace("\n", " ")


def _opening(why: str) -> str:
    """A position's reasoning down to its first blank line.

    EXACTLY WHAT THE CARD SHOWED BEFORE, which is the point: the firm chose
    folding over full length, so nothing they were used to reading moved and
    everything that was missing is one disclosure below it.
    """
    body = [b.strip() for b in (why or "").strip().split("\n\n") if b.strip()]
    return body[0] if body else ""


def _after_the_opening(why: str) -> str:
    """Everything past the first paragraph, or `""`."""
    body = [b.strip() for b in (why or "").strip().split("\n\n") if b.strip()]
    return "\n\n".join(body[1:])


def _how_much(why: str) -> str:
    """How much is behind the fold, said on the fold itself.

    A disclosure with no size on it is one a reader takes for a footnote, and
    the whole finding here was that it is not: the part that did not reach the
    POS2 card contains *"$2,500 is a ceiling, not the number"*.
    """
    rest = _after_the_opening(why)
    if not rest:
        return ""
    paras = len([b for b in rest.split("\n\n") if b.strip()])
    return ("%d more paragraph%s, about %d words"
            % (paras, "" if paras == 1 else "s", len(rest.split())))


class DocketError(Exception):
    """A card that would ask a question it has already answered."""


#: The picks a proposed position is offered. Held here rather than beside each
#: position because the choice is the same one every time: it is the firm's own
#: words being ratified, not a design decision with alternatives.
POSITION_PICKS = ("Ratify it", "Ratify with an edit", "No", "Not yet")


def _ordered(row: dict) -> list:
    """The picks with the recommended one first, checked against the reasoning.

    THE FIRM, 7 SEPTEMBER 2026: *"i have no clue why you will even ask me things
    on the docket like 'should i ratify this' when your last thing is a
    recommendation saying 'i wouldn't activate this, it is missing a field'."*

    That is exactly what the fifth docket did. Two capitalisation positions
    carried a recommendation reading "do not ratify until the field exists" and
    the buttons underneath still led with **Ratify it** — because the
    recommendation was prose and the picks were a constant that nothing read. The
    page argued one way and asked the other, and the reader had to notice.

    So the recommendation now NAMES its pick, and a card whose recommendation
    argues for something it does not offer fails the build. Not a review note: a
    reviewer catching this is a reviewer who has to read every card against its
    own buttons, which is the work the generator exists to remove.
    """
    picks, pick = list(row["picks"]), row.get("rec_pick", "")
    rec = row.get("rec") or (row.get("note") or {}).get("rec", "")
    if rec and not pick:
        raise DocketError(
            f"{row['key']} recommends something and does not say which pick it "
            f"means. Name it in `rec_pick`, from: {picks}")
    if pick and pick not in picks:
        raise DocketError(
            f"{row['key']} recommends {pick!r}, which is not one of the buttons "
            f"it offers: {picks}. The card would ask a question it has answered.")
    return ([pick] + [x for x in picks if x != pick]) if pick else picks


def items():
    rows = []
    for p in positions():
        rows.append({
            "key": "pos-%s-%s" % (p["desk"], p["id"]),
            "kind": "position",
            "group": p["desk"],
            "tag": "%s · %s" % (p["desk"], p["id"]),
            "title": p["title"],
            "position": p["position"],
            "citation": p["citation"],
            "source": p["source"],
            "tier": p["tier"],
            "shape": p["kind"],
            "unlocks": p["unlocks"],
            # SPLIT, NOT WHOLE. `dec-whytrunc`, 18 September 2026 -- the firm:
            # "Read the whole thing, FOLDED." Until `record._prose` landed the
            # same day, this field stopped at the first bolded paragraph and
            # 23,044 characters across the twenty positions reached no card at
            # all. Fixing the parser alone would have handed them the OTHER
            # option on that card -- the whole thing at full length -- which
            # they declined, and POS13's reasoning is 6,658 characters.
            "why": _md(_opening(p["why"])),
            "why_rest": _md(_after_the_opening(p["why"])),
            "why_more": _how_much(p["why"]),
            "note": p["note"],
            "rec_pick": (p["note"] or {}).get("rec_pick", ""),
            "picks": list(POSITION_PICKS),
        })
    answered = {a["key"] for a in ANSWERED}
    for o in OTHERS:
        if o["key"] in answered:
            raise DocketError(
                f"{o['key']} is open and answered at the same time. The page "
                f"would ask a question it reports below as already answered -- "
                f"which is what the firm was looking at when they wrote "
                f"\"i am generally confused i have filled this docket out\".")
        rows.append(dict(o, kind="decision"))
    for r in rows:
        r["picks"] = _ordered(r)
    return rows


#: Small numbers read as words in a sentence and as digits on a control. Stops at
#: what a docket plausibly holds; above that the digits are clearer anyway.
_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
          "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
          "twenty-one", "twenty-two", "twenty-three", "twenty-four",
          "twenty-five", "twenty-six", "twenty-seven", "twenty-eight",
          "twenty-nine", "thirty")


def _word(n: int) -> str:
    return _WORDS[n] if n < len(_WORDS) else str(n)


def _counted():
    """Every figure the page states, measured from what it is about to show."""
    rows = items()
    pos = [r for r in rows if r["kind"] == "position"]
    rules = [r for r in pos if r["shape"] == "rule"]
    turns = [r for r in pos if r["unlocks"] > 0]
    blind = len(pos) - len(turns)
    ratified = len([q for q in record.load(HERE / "corpus").positions
                    if not q.proposed])
    # A POSITION THIS DOCKET ITSELF SAYS TO HOLD BACK, read off the note rather
    # than counted by hand -- the preface states how many are answerable now, and
    # a number typed there goes stale the moment one is ratified.
    waiting = [r for r in pos if r["rec_pick"] not in ("Ratify it",
                                                      "Ratify with an edit")]
    # NEW SINCE THE LAST DOCKET, and where each came from. The preface said
    # "four ... came out of the tie-out" and that was wrong by one: three came
    # from the tie-out and the fourth from a CI failure the same night. Flagged
    # on the matter rather than counted in a sentence.
    # NEW MEANS "NOT ON THE LAST DOCKET", read off the last docket rather than
    # off a flag this file also sets. A `"new": True` marker is a claim the page
    # makes about itself, and two mutations survived on the third docket because
    # the test that checked it read the same flag. A POSITION cannot carry the
    # flag at all -- it comes out of `desks/` -- so a flag-only count silently
    # missed POS3, which did not exist this morning.
    fresh = [r for r in rows if r["key"] not in ALREADY_OPEN]
    from_tieout = [r for r in fresh if r["group"] == "From the tie-out"]
    return {
        "rows": rows, "n": len(rows), "pos": len(pos), "dec": len(rows) - len(pos),
        "waiting": len(waiting), "answerable": len(pos) - len(waiting),
        "fresh": len(fresh), "from_tieout": len(from_tieout),
        "rules": len(rules), "concl": len(pos) - len(rules),
        "turns": len(turns), "blind": blind, "ratified": ratified,
    }


def render() -> str:
    c = _counted()
    n = c["n"]
    # THE PAGE HAS TO BE ABLE TO SAY THERE IS NOTHING. The docket skill asks for
    # "nothing needs deciding" in those words, and until 7 September this
    # generator could not produce them: every heading, the tab and the filter bar
    # were phrased for a page with matters on it, so an answered docket
    # republished itself still asking.
    title = "Docket \u00b7 All Answered" if not n else "Docket \u00b7 %s Open" % _word(n).capitalize()
    if not n:
        headline = "Nothing is waiting on you"
        lede = ("You answered every matter on this page. Each one is read back "
                "below \u2014 your words out of this page\u2019s own store, not my "
                "memory of being told \u2014 with what it caused. The only live "
                "thing here is the goal under <b>Next</b>: object in a line, or "
                "say nothing and I get on with it.")
    else:
        headline = "%s things waiting on you" % _word(n).capitalize()
        lede = ("%s Every one carries what I would do and why, and every one is "
                "answerable in a line. It saves as you type."
                % ("%s are choices no rule settles; no position is waiting \u2014 "
                   "all %s are ratified."
                   % (_word(c["dec"]).capitalize(), _word(c["ratified"]))))
    preface = _preface(c)
    return _PAGE % (title, _CSS, DATE, headline, lede, preface, _next_block(),
                    _bar(c), _waiting(c), _answered(), _blocks(c),
                    json.dumps(c["rows"]), _JS)


def _preface(c) -> str:
    """What today was, and then how many things it leaves for the firm.

    REWRITTEN 14 SEPTEMBER 2026, AND THE REASON IS THE REWRITE. Every sentence
    here was a literal describing 8 September -- three matters, the desks gaining
    their worked examples, eCFR being admitted. The page rendered all of it under
    today's date and today's eight cards, and NOTHING went red, because the
    generator's tests check that figures agree with the rows and cannot check
    that prose is about today.

    It was caught by printing the page and reading it, which is the only thing
    that catches this class. So the standing sentences are now the ones that stay
    true -- what this page IS -- and everything dated is derived from the rows or
    lives in `NEXT`, `CHANGED` and `ANSWERED`, each of which a test does hold.

    AND THE CARRIED/NEW SPLIT IS COUNTED, NOT ASSERTED. The old text said
    "nothing from the last page is carried forward" as a flat claim. Four of
    today's eight ARE carried, because they have gone unanswered across three
    dockets -- which is the single most useful thing this paragraph can say.
    """
    if not c["n"]:
        return (
          "<p><b>Nothing on this page needs an answer.</b> Every matter is read "
          "back below rather than deleted, with what your answer caused.</p>"
          "<p>No proposal is open and all %s ratified positions stand.</p>"
          % _word(c["ratified"]))
    carried = c["n"] - c["fresh"]
    split = (
      "<b>%s are new and %s have been waiting across earlier dockets.</b> The "
      "carried ones are marked as carried rather than re-dressed as findings: "
      "they are the same questions, and the longest-standing of them stops two "
      "of your own ratified positions being usable on any client."
      % (_word(c["fresh"]).capitalize(), _word(carried))
    ) if carried else (
      "<b>All %s are new.</b> Nothing from the last page is carried forward: "
      "asking an answered question again is the fault this page was rebuilt to "
      "stop." % _word(c["n"])
    )
    return (
      "<p><b>%s things wait on you.</b> %s</p>"
      "<p><b>Every figure on this page was measured, not recalled.</b> These "
      "matters came out of putting your own 43 close questions back through the "
      "corpus on the version Occam piloted, and out of that pilot\u2019s findings, "
      "which were reproduced here rather than believed. One of them did not "
      "reproduce and is reported as a finding about the tester. What I got wrong "
      "\u2014 including what I told you yesterday \u2014 is at the foot of this "
      "page.</p>"
      "<p>No proposal is open and all %s ratified positions stand, so nothing "
      "below is a position waiting to be ratified — every card is a choice "
      "no rule settles.</p>"
      % (_word(c["n"]).capitalize(), split, _word(c["ratified"]))
    )


def _bar(c) -> str:
    """The filter bar, and NOTHING when there is nothing to filter.

    "All 0 / Positions 0 / Other 0" is a control that does nothing above a list
    that holds nothing, and it is half of why an answered docket still read as a
    form waiting to be filled in."""
    if not c["n"]:
        return ""
    return ('<div class="bar">\n'
            '  <span class="tally" id="tally">0 of %d answered</span>\n'
            '  <span class="grow"></span>\n'
            '  <button class="filt" type="button" data-filt="all" aria-pressed="true">All %d</button>\n'
            '  <button class="filt" type="button" data-filt="position" aria-pressed="false">Positions %d</button>\n'
            '  <button class="filt" type="button" data-filt="decision" aria-pressed="false">Other %d</button>\n'
            '  <button class="filt" type="button" data-filt="open" aria-pressed="false">Unanswered</button>\n'
            '</div>') % (c["n"], c["n"], c["pos"], c["dec"])


def _waiting(c) -> str:
    """Either the matters, or the sentence that says there are none."""
    top = 'class="sec" style="border-top:none;padding-top:0;margin-top:0"'
    if c["n"]:
        return ('<h2 %s>Waiting on you</h2>'
                '<p class="lead">&ldquo;Not yet&rdquo; is a real answer \u2014 it '
                'keeps the matter open and brings it back next time. Nothing is '
                'lost by skipping one, and nothing is recorded without an '
                'explicit yes.</p>') % top
    return ('<h2 %s>Nothing needs deciding</h2>'
            '<p class="lead">Every matter is answered and acted on. What each '
            'answer did is below.</p>') % top


def _answered() -> str:
    """What the firm already answered, and what it caused.

    IT USED TO VANISH THE MOMENT A NEW MATTER ARRIVED, because it was rendered
    only on the empty page -- so the read-back existed exactly while there was
    nothing to read it beside. The firm's own answers and what they caused are
    the part that says whether answering is worth anything, and they belong on
    every docket until they are stale.
    """
    if not ANSWERED:
        return ""
    rows = "".join(
        '<li><code class="pr">%s</code> <b>%s</b> <i>%s</i><br>%s</li>'
        % (a["said"], a["title"], a["where"], a["caused"]) for a in ANSWERED)
    return ('<h2 class="sec">What you already answered, and what it did</h2>'
            '<p class="lead">All %s answered, %s acted on. Every one of these '
            'was answered ON THIS PAGE and is read back out of its own store, '
            'not out of any session\u2019s memory of being told \u2014 which is '
            'the only independent record of what you actually said. What each '
            'one caused is measured from the repository.</p>'
            '<p class="lead"><b>An earlier version of this line said these were '
            'transcribed from the log because they were answered elsewhere.</b> '
            'That was true of the four matters this section used to carry and '
            'false of these, and it stayed on the page for four days saying so. '
            'Corrected by reading the store rather than the sentence.</p>'
            '<ul class="plain">%s</ul>') % (_word(len(ANSWERED)),
                                            _word(len(ANSWERED) - 1), rows)


def _next_block() -> str:
    return ('<div class="next"><h4>Next</h4>'
            '<p class="goal">%(goal)s</p>'
            '<p class="ends">%(ends)s <b>%(distance)s</b></p>'
            '<p class="detail">%(detail)s</p>'
            '<p class="silence"><b>Unless you say otherwise, this is what I '
            'proceed with.</b> Everything below this block waits for your answer. '
            'This one does not \u2014 objecting is a line, agreeing is nothing. It '
            'approves what I work on next and nothing else: a position still needs '
            'your explicit yes, and nothing reaches a client without you.</p>'
            '</div>') % NEXT


def _blocks(c) -> str:
    stats = CHANGED + [("%d / %d" % (c["ratified"], c["pos"]),
                        "positions ratified / proposed",
                        "the %s are above" % _word(c["pos"]))]
    changed = "".join(
        '<div class="stat"><b>%s</b><span>%s</span><i>%s</i></div>' % r for r in stats)
    landed = "".join('<li><code class="pr">%s</code> %s</li>' % r for r in LANDED)
    unchecked = "".join('<li><b>%s</b> %s</li>' % r for r in UNCHECKED)
    wrong = "".join('<li><b>%s</b> %s</li>' % r for r in WRONG)
    return ('<div class="stats">%s</div>'
            '<h3 class="sub">What landed</h3><ul class="plain">%s</ul>'
            '<h2 class="sec">What I did not check</h2>'
            '<p class="lead">A clean result is a finding. A silent gap is not.</p>'
            '<ul class="plain">%s</ul>'
            '<h2 class="sec">What I got wrong</h2>'
            '<p class="lead">This is the part that says how much to trust the rest.</p>'
            '<ul class="plain">%s</ul>') % (changed, landed, unchecked, wrong)


_CSS = """
:root{--paper:#F5F5F2;--sheet:#FFF;--rule:#DCDCD6;--soft:#E9E9E4;
 --ink:#161E28;--ink2:#4A5563;--ink3:#7A8494;
 --ox:#8C2F39;--ox-soft:#F3E3E4;--ledger:#2C6650;--ledger-soft:#E2EDE8;
 --amber:#8A5A16;--amber-soft:#F6EBD9;--focus:#2F5C9E;
 --shadow:0 1px 2px rgba(22,30,40,.05),0 8px 24px rgba(22,30,40,.06)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#12161C;--sheet:#1A1F27;--rule:#2C333D;--soft:#232A33;
 --ink:#E7E9EC;--ink2:#AEB6C2;--ink3:#7C8593;--ox:#E2848C;--ox-soft:#331E21;
 --ledger:#79C4A5;--ledger-soft:#16291F;--amber:#DCA85E;--amber-soft:#2A2114;
 --focus:#7FA9E8;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.3)}}
:root[data-theme="dark"]{--paper:#12161C;--sheet:#1A1F27;--rule:#2C333D;--soft:#232A33;
 --ink:#E7E9EC;--ink2:#AEB6C2;--ink3:#7C8593;--ox:#E2848C;--ox-soft:#331E21;
 --ledger:#79C4A5;--ledger-soft:#16291F;--amber:#DCA85E;--amber-soft:#2A2114;
 --focus:#7FA9E8;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.3)}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-size:16px;line-height:1.62;
 font-family:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:50rem;margin:0 auto;padding:2.25rem 1.25rem 6rem}
h1,h2,h3{font-family:Newsreader,Georgia,serif;font-weight:600;margin:0;text-wrap:balance}
code{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-size:.85em}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:3px}
header.mast{border-bottom:2px solid var(--ink);padding-bottom:1rem;margin-bottom:1.2rem}
.eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:700}
h1{font-size:clamp(1.9rem,5vw,2.7rem);line-height:1.08;margin:.35rem 0}
.mast p{color:var(--ink2);margin:.5rem 0 0;max-width:62ch}
.bar{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);
 padding:.55rem 0;margin-bottom:1.4rem;display:flex;gap:.7rem;align-items:center;flex-wrap:wrap}
.bar .tally{font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--ink3)}
.bar .grow{flex:1}
.filt{font-family:inherit;font-size:.8rem;cursor:pointer;background:transparent;color:var(--ink2);
 border:1px solid var(--rule);padding:.25rem .6rem;border-radius:2px}
.filt[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
h2.sec{font-size:1.55rem;margin:2.6rem 0 .3rem;padding-top:1.2rem;border-top:1px solid var(--rule)}
h3.sub{font-size:1.15rem;margin:1.6rem 0 .4rem}
p.lead{color:var(--ink2);margin:.2rem 0 1rem;max-width:64ch}
.card{background:var(--sheet);border:1px solid var(--rule);border-left:3px solid var(--amber);
 box-shadow:var(--shadow);padding:1.3rem 1.4rem;margin-bottom:1.1rem}
.card[data-state="yes"]{border-left-color:var(--ledger)}
.card[data-state="no"]{border-left-color:var(--ox)}
.card[hidden]{display:none}
@media (max-width:34rem){.card{padding:1.05rem}}
.chips{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.6rem}
.chip{font-size:.66rem;letter-spacing:.07em;text-transform:uppercase;font-weight:700;
 padding:.16rem .48rem;border-radius:2px;background:var(--soft);color:var(--ink3)}
.chip.primary{background:var(--ledger-soft);color:var(--ledger)}
.chip.secondary{background:var(--amber-soft);color:var(--amber)}
.chip.tertiary{background:var(--ox-soft);color:var(--ox)}
.chip.kind{background:var(--ink);color:var(--paper)}
h3.t{font-size:1.28rem;line-height:1.26;margin:0 0 .7rem}
.says{border-left:2px solid var(--ink);padding:.15rem 0 .15rem .9rem;margin:.8rem 0;
 font-family:Newsreader,Georgia,serif;font-size:1.08rem;line-height:1.5}
.says b{display:block;font-family:"Public Sans",sans-serif;font-size:.66rem;font-weight:700;
 letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);margin-bottom:.28rem}
.rests{background:var(--soft);padding:.55rem .75rem;margin:.8rem 0;font-size:.86rem;color:var(--ink2)}
.rests .c{font-family:"JetBrains Mono",monospace;font-size:.79rem;word-break:break-word;color:var(--ink)}
.ctx{color:var(--ink2);font-size:.94rem;margin:.7rem 0;max-width:64ch}
.blk{margin:.8rem 0;padding:.6rem .8rem;font-size:.92rem}
.blk h4{margin:0 0 .18rem;font-size:.66rem;letter-spacing:.09em;text-transform:uppercase;
 font-family:"Public Sans",sans-serif;font-weight:700}
.blk p{margin:.22rem 0;max-width:64ch}
.blk.for{background:var(--ledger-soft);border-left:2px solid var(--ledger)}
.blk.for h4{color:var(--ledger)}
.blk.against{background:var(--ox-soft);border-left:2px solid var(--ox)}
.blk.against h4{color:var(--ox)}
.blk.silent{background:var(--amber-soft);border-left:2px solid var(--amber)}
.blk.silent h4{color:var(--amber)}
.blk.rec{background:var(--soft);border-left:2px solid var(--ink)}
.blk.rec h4{color:var(--ink)}
/* THE RECOMMENDATION LEADS. It sat last, under four labelled blocks, and the
   reader had to assemble the point before reaching it. */
.next{margin:1.2rem 0;padding:.9rem 1.1rem;background:var(--ledger-soft);
 border:1px solid var(--ledger);border-left-width:4px}
.next h4{margin:0 0 .3rem;font-size:.66rem;letter-spacing:.09em;
 text-transform:uppercase;font-family:"Public Sans",sans-serif;color:var(--ledger)}
.next .goal{margin:0 0 .35rem;font-size:1.06rem;font-weight:600;max-width:64ch}
.next .ends,.next .detail,.next .silence{margin:.35rem 0;max-width:64ch;
 font-size:.94rem;color:var(--ink2)}
.next .silence{color:var(--ink)}
.reclead{margin:.8rem 0;padding:.7rem .9rem;background:var(--sheet);
 border:1px solid var(--ink);border-left-width:3px}
.reclead h4{margin:0 0 .25rem;font-size:.66rem;letter-spacing:.09em;
 text-transform:uppercase;font-family:"Public Sans",sans-serif;color:var(--ink)}
.reclead p{margin:0;max-width:64ch;font-size:1rem}
.pick.is-rec{border-color:var(--ink);font-weight:600}
.pick.is-rec::after{content:" \u00b7 recommended";font-weight:400;
 font-size:.72rem;color:var(--ink3)}
.pick.is-rec[aria-pressed="true"]::after{color:inherit}
details.why{margin:.8rem 0}
details.rest{margin:.5rem 0 0;padding-left:.75rem;border-left:2px solid var(--rule)}
details.rest summary{cursor:pointer;font-size:.68rem;letter-spacing:.08em;
 text-transform:uppercase;color:var(--ink3);font-weight:700}
details.rest p{margin-top:.4rem}
details.why summary{cursor:pointer;font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;
 color:var(--ink3);font-weight:700}
details.why .d{color:var(--ink2);font-size:.9rem;margin-top:.45rem;max-width:64ch}
.answer{border-top:1px dashed var(--rule);margin-top:1.1rem;padding-top:.9rem}
.answer>label{font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);font-weight:700}
.picks{display:flex;gap:.4rem;flex-wrap:wrap;margin:.5rem 0}
button.pick{font-family:inherit;font-size:.9rem;font-weight:500;cursor:pointer;background:var(--sheet);
 color:var(--ink);border:1px solid var(--rule);padding:.42rem .9rem;border-radius:2px}
button.pick:hover{border-color:var(--ink3)}
button.pick[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
textarea{width:100%;min-height:3.2rem;font-family:inherit;font-size:.94rem;line-height:1.55;
 color:var(--ink);background:var(--paper);border:1px solid var(--rule);padding:.55rem .7rem;
 border-radius:2px;resize:vertical}
textarea::placeholder{color:var(--ink3)}
.saved{font-size:.75rem;color:var(--ink3);margin-top:.35rem;min-height:1.1em}
.saved.ok{color:var(--ledger)} .saved.err{color:var(--ox)}
.stats{display:flex;flex-wrap:wrap;gap:0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);margin:.6rem 0 0}
.stat{flex:1 1 8.5rem;padding:.9rem 1rem .8rem 0}
.stat b{display:block;font-family:Newsreader,Georgia,serif;font-size:1.7rem;font-weight:600;
 font-variant-numeric:tabular-nums;line-height:1.1}
.stat span{display:block;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);font-weight:700}
.stat i{display:block;font-style:normal;font-size:.8rem;color:var(--ink2);margin-top:.15rem}
ul.plain{list-style:none;padding:0;margin:.4rem 0}
ul.plain li{border-top:1px solid var(--rule);padding:.7rem 0;color:var(--ink2);font-size:.95rem;max-width:66ch}
ul.plain li b{color:var(--ink);font-weight:600}
code.pr{background:var(--soft);padding:.1rem .35rem;color:var(--ink);font-weight:700}
.banner{background:var(--amber-soft);border:1px solid var(--amber);color:var(--amber);
 padding:.6rem .85rem;font-size:.88rem;margin-bottom:1.2rem;display:none}
.banner.show{display:block}
.preface{background:var(--sheet);border:1px solid var(--rule);border-left:3px solid var(--focus);
 padding:.9rem 1.1rem;margin-bottom:1.6rem}
.preface p{margin:.4rem 0;max-width:64ch}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

_PAGE = """<title>%s</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>%s</style>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">Docket · desk · %s</div>
  <h1>%s</h1>
  <p>%s</p>
</header>

<div id="offline" class="banner">Answers are not saving — this view could not reach the store. Tell me in the conversation instead.</div>

<div class="preface">%s</div>

%s

%s

%s
<div id="list"></div>

%s

<h2 class="sec">What changed</h2>
<p class="lead">Denominators, measured now rather than remembered.</p>
%s
</div>
<script>const DATA = %s;</script>
<script>%s</script>
"""

_JS = """
const list = document.getElementById("list");
const state = {};
let db = null, filt = "all";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const YES = ["Ratify it", "Ratify with an edit"];

function tally() {
  // The bar is not rendered when nothing is open, so this can be absent.
  const el = document.getElementById("tally");
  if (!el) return;
  const n = DATA.filter(d => (state[d.key] || {}).choice).length;
  el.textContent = n + " of " + DATA.length + " answered";
}

function applyFilter() {
  DATA.forEach(d => {
    const el = document.getElementById("card-" + d.key);
    if (!el) return;
    const answered = !!(state[d.key] || {}).choice;
    el.hidden = filt === "open" ? answered : (filt !== "all" && d.kind !== filt);
  });
}

function card(d) {
  const n = d.note || {}, s = state[d.key] || {};
  const el = document.createElement("div");
  el.className = "card";
  el.id = "card-" + d.key;
  el.dataset.state = YES.includes(s.choice) ? "yes" : s.choice === "No" ? "no" : "";
  const kindLabel = d.kind === "decision" ? "a choice no rule settles"
    : d.shape === "conclusion" ? "a conclusion about the law" : "a rule about how you work";
  el.innerHTML = `
    <div class="chips">
      <span class="chip">${esc(d.tag)}</span>
      ${d.tier ? `<span class="chip ${esc(d.tier)}">${esc(d.tier)} authority</span>` : ""}
      <span class="chip kind">${kindLabel}</span>
    </div>
    <h3 class="t">${esc(d.title)}</h3>
    ${(n.rec || d.rec) ? `<div class="reclead"><h4>What I would do</h4><p>${n.rec || d.rec}</p></div>` : ""}
    <div class="says"><b>${d.kind === "decision" ? "What I would put in place" : "What the desk would say, in your words"}</b>&ldquo;${esc(d.position)}&rdquo;</div>
    ${d.citation ? `<div class="rests">Rests on <span class="c">${esc(d.citation)}</span><br>${esc(d.source)}</div>` : ""}
    ${d.context ? `<p class="ctx">${d.context}</p>` : ""}
    ${(d.either || []).map((e, i) => `<div class="blk ${i === 0 ? "for" : "against"}"><h4>${esc(e[0])}</h4><p>${esc(e[1])}</p></div>`).join("")}
    ${n.against ? `<div class="blk against"><h4>What cuts against it</h4><p>${n.against}</p></div>` : ""}
    ${(() => {
      const more = [
        n.read ? `<div class="blk rec"><h4>Before you decide</h4><p>${n.read}</p></div>` : "",
        n.for ? `<div class="blk for"><h4>What supports it</h4><p>${n.for}</p></div>` : "",
        n.silent ? `<div class="blk silent"><h4>What the authority does not say</h4><p>${n.silent}</p></div>` : "",
        d.kind === "position" ? `<div class="blk rec"><h4>What saying yes changes</h4><p>${
          d.unlocks > 0
            ? `<b>${d.unlocks}</b> of this desk's scored problems turn on this exact citation, so ratifying makes them answerable.`
            : `<b>No scored problem changes.</b> What changes is that the desk stops handing the question back and starts saying ${d.shape === "rule" ? "what to do next" : "this, in your words, with the citation behind it"}.`
        }</p></div>` : "",
        d.why ? `<div class="blk"><h4>The reasoning as drafted</h4><p>${d.why}</p>${
          d.why_rest
            ? `<details class="rest"><summary>The rest of it \u2014 ${d.why_more}</summary><p>${d.why_rest}</p></details>`
            : ""
        }</div>` : "",
      ].filter(Boolean);
      return more.length
        ? `<details class="why"><summary>What else I looked at (${more.length})</summary><div class="d">${more.join("")}</div></details>`
        : "";
    })()}
    <div class="answer">
      <label for="ta-${d.key}">Your answer</label>
      <div class="picks">
        ${d.picks.map(p => `<button type="button" class="pick${p === d.rec_pick ? " is-rec" : ""}" data-choice="${esc(p)}" aria-pressed="${s.choice === p}">${esc(p)}</button>`).join("")}
      </div>
      <textarea id="ta-${d.key}" placeholder="Reword it and I will use your words, not the draft's.">${esc(s.notes || "")}</textarea>
      <div class="saved" role="status" aria-live="polite"></div>
    </div>`;

  const ta = el.querySelector("textarea");
  const said = el.querySelector(".saved");
  let timer = null;

  const save = () => {
    const cur = state[d.key] || {};
    if (!db) { said.className = "saved err"; said.textContent = "Not saving \\u2014 tell me in the conversation."; return; }
    said.className = "saved"; said.textContent = "Saving\\u2026";
    db.doc("decisions/" + d.key).set({
      kind: d.kind, group: d.group, title: d.title, proposed: d.position,
      choice: cur.choice || "", notes: ta.value, answeredAt: new Date().toISOString()
    }).then(() => { said.className = "saved ok"; said.textContent = "Saved."; })
      .catch(e => { said.className = "saved err";
        said.textContent = "Not saved (" + ((e && e.code) || "unknown") + "). Your text is still on screen."; });
  };

  el.querySelectorAll(".pick").forEach(b => b.addEventListener("click", () => {
    const cur = state[d.key] || (state[d.key] = {});
    cur.choice = cur.choice === b.dataset.choice ? "" : b.dataset.choice;
    cur.notes = ta.value;
    el.dataset.state = YES.includes(cur.choice) ? "yes" : cur.choice === "No" ? "no" : "";
    el.querySelectorAll(".pick").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.choice === cur.choice)));
    tally(); clearTimeout(timer); save();
  }));
  ta.addEventListener("input", () => {
    (state[d.key] || (state[d.key] = {})).notes = ta.value;
    clearTimeout(timer); timer = setTimeout(save, 700);
  });
  return el;
}

function draw() { list.innerHTML = ""; DATA.forEach(d => list.appendChild(card(d))); tally(); applyFilter(); }

document.querySelectorAll(".filt").forEach(b => b.addEventListener("click", () => {
  filt = b.dataset.filt;
  document.querySelectorAll(".filt").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  applyFilter();
}));

draw();

(async () => {
  db = await claude.use("db");
  if (!db) { document.getElementById("offline").classList.add("show"); return; }
  db.collection("decisions").onSnapshot(snap => {
    let changed = false;
    snap.docs.forEach(doc => {
      const v = doc.data() || {};
      const cur = state[doc.id] || {};
      if (cur.choice !== v.choice || cur.notes !== v.notes) {
        state[doc.id] = { choice: v.choice || "", notes: v.notes || "" };
        changed = true;
      }
    });
    // Never rebuild under someone's hands: a redraw would wipe a half-typed answer.
    if (changed && document.activeElement.tagName !== "TEXTAREA") draw();
  }, () => { document.getElementById("offline").classList.add("show"); });
})();
"""


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "docket.html"
    out.write_text(render(), encoding="utf-8")
    print(out)
