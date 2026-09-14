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
 {"key": "dec-guidance-narrow",
  "title": "Should the guidance gate read \u201con this question\u201d or \u201canywhere in the corpus\u201d?",
  "said": "On this question",
  "where": "on the one-corpus docket, 11 September",
  "caused": "<b>84 \u2192 97 of 98 problems answered</b>, higher than it has ever been. "
            "Thirteen answers that were refused across seven desks now serve, and each "
            "traces to the cited source\u2019s own reason for being on file. <b>Two "
            "instruments were measured and rejected</b> rather than adopted \u2014 "
            "including \u201cdoes the pool surface a binding passage\u201d, which is "
            "true for all 24 non-binding problems and so cannot be a gate. And the "
            "caveat was found to be lying: it claimed no binding authority reached the "
            "question, which the narrowing makes false. The gate and the caveat now read "
            "one fact."},

 {"key": "dec-fullstop",
  "title": "A word ending in a full stop is a different word to the search. Fix it?",
  "said": "Fix it after Matter 2",
  "where": "on the one-corpus docket, 11 September",
  "caused": "<b>The ordering was obeyed and the interaction measured, and there was "
            "none.</b> 97 of 98 served either way. The precaution was right and the "
            "answer was no, which is a result rather than a wasted step. It recovered "
            "128 words that no question could reach at all."},

 {"key": "dec-lookjoin",
  "title": "The desk goes and looks. What happens to what it finds?",
  "said": "It parks \u2014 nothing found by searching is served",
  "where": "on the one-corpus docket, 11 September",
  "caused": "<b>The join was the missing thing, not the searcher.</b> The searching code "
            "had worked since 8 September and nothing on the answering path called it. "
            "Now it does \u2014 and <b>nothing it finds is ever served</b>, not the "
            "non-binding find nor the binding one. <b>Three defects came out of printing "
            "the page rather than reading the code that builds it</b>: a find that "
            "succeeded rendered as \u201cNothing tied out\u201d; \u201cwhat to do: park "
            "it\u201d printed three lines above the paragraph saying it had been parked; "
            "and a doer was told the record holds a paragraph without being told they may "
            "not reach for it."},

 {"key": "dec-pos11-review",
  "title": "POS11 was the only unreviewed policy on the record. Does anything contradict it?",
  "said": "Nearby, doesn\u2019t settle it",
  "where": "in your own words, 11 September",
  "caused": "<b>Two findings, and the position carries both.</b> As a review: nothing on "
            "file contradicts the policy. As coverage: nothing on file speaks to it at "
            "all. \u201cNo conflict\u201d would have claimed more than the search "
            "earned. The test that an open review is still marked open is now built "
            "rather than found."},
]

#: THREE MATTERS, all of which arrived AFTER the page said nothing needed
#: deciding -- which is the normal life of a docket rather than a fault. Each one
#: blocks something concrete: the Forge cannot be set up, a desk cannot answer a
#: question it now has the words for, and a hole found in the seam cannot be
#: closed without the firm saying so.
#: NOTHING IS OPEN. The three that were here were answered at 17:20 and are in
#: `ANSWERED` above with what each one did. A key may not be in both.
OTHERS = [

 {"key": "dec-caprule", "new": False, "group": "The capitalisation positions",
  "tag": "Carried — blocks every client",
  "title": "What is the default capitalisation rule for a client that has none?",
  "position": "Record it at intake, pre-filled with the firm’s own threshold.",
  "context": "<b>This is the most expensive thing on the page and it is not close.</b> "
             "POS1 and POS2 — your two positions on the de minimis safe harbour "
             "— both carry <code>Unless: capitalization_rule</code>, meaning "
             "<i>this holds unless this client is treated differently</i>. That field "
             "is blank everywhere, so <b>neither position can be served on any "
             "client</b>.<br><br><b>Run just now, not assumed.</b> Asked <i>what is the "
             "client’s capitalisation threshold?</i> with POS2’s own "
             "citation, the engine returns a refusal reading: <i>“Nothing on file "
             "says either way, and a default applied without looking is not a "
             "default.”</i><br><br>That is the engine working correctly. It is "
             "also two of your twenty ratified positions being unreachable on every "
             "engagement — and a Sarcia close is capitalisation-heavy, so this "
             "will fire whether or not it is answered first.<br><br><b>The "
             "<code>Unless:</code> line was your own instruction</b> — <i>“This "
             "needs to ensure that there is no already standing rule for that client in "
             "particular.”</i> That half is right and is not in question. What is "
             "missing is the other half: what happens when there is no standing rule.",
  "either": [("Record it at intake",
              "POS1 and POS2 become servable. Somebody records the value per client, "
              "pre-filled with your standard — $2,500 per invoice or per item, "
              "$5,000 where the client has an applicable financial statement. The "
              "\u201cunless\u201d check still fires for any client you record a "
              "different rule against."),
             ("A silent default in the code",
              "Every client gets the firm’s number with nobody looking. Faster, "
              "and it cuts straight across \u201cfacts are recorded, not inferred\u201d "
              "— which is the principle the refusal is currently enforcing."),
             ("Leave it blank",
              "Every capitalisation question in every close refuses "
              "as not on file until a preparer fills the field. "
              "Honest, and it is most of what this part of the record is for.")],
  "rec": "Record it at intake with your standard pre-filled. It ends the blanket "
         "refusal without the engine ever assuming a fact — somebody still puts "
         "their name to it, which is the whole shape you asked for.",
  "rec_pick": "Record it at intake",
  "picks": ["Record it at intake", "A silent default in the code", "Leave it blank",
            "Not yet"]},

 {"key": "dec-fasb", "new": False, "group": "US GAAP",
  "tag": "Carried — a door with nothing behind it",
  "title": "Is a free FASB update acceptable authority where the Codification is licensed?",
  "position": "Admit ASUs, tiered secondary.",
  "context": "<b>Show the jargon, then say what it means.</b> The <b>Codification</b> "
             "is the compiled, current, official statement of US GAAP — it is "
             "licensed, and its text may not reach a model at all, which is why the "
             "record marks it <code>human_only</code>. An <b>ASU</b> (Accounting "
             "Standards Update) is the amendment FASB publishes each time it changes a "
             "standard, and it is free to read on fasb.org.<br><br><b>The gap, "
             "measured.</b> <code>DOMAINS.md</code> names <code>us-gaap</code> as a "
             "body of authority and gives fasb.org as its publisher. "
             "<code>SOURCES.md</code> admits <b>34 sources and not one of them is US "
             "GAAP</b>. So a question can classify into <code>us-gaap</code>, pass the "
             "publisher gate, and then find the record holds nothing.<br><br><b>What it "
             "costs today: almost nothing on paper.</b> Zero of the 98 recorded "
             "problems classify <code>us-gaap</code> outright; one touches a second "
             "domain at all. It bites on the <i>live</i> path — the lease question "
             "typed the way an accountant types it is where <code>us-gaap</code> fires, "
             "and that is a real close question.",
  "either": [("Admit ASUs, secondary",
              "US GAAP gets something to answer from, and lease questions "
              "stop reaching an empty body. Secondary rather than primary because an "
              "ASU is an amendment and a later one can supersede it."),
             ("Admit ASUs, primary",
              "Same reach, and the desk would treat an ASU as binding — which "
              "overstates it, because the compiled Codification is what actually "
              "governs and we cannot read it."),
             ("Take us-gaap out of DOMAINS.md",
              "Honest in the other direction: a publisher the record admits nothing "
              "from is a promise the desk cannot keep. The cost is that lease questions "
              "then reach nothing at all rather than reaching a wall that names "
              "itself.")],
  "rec": "Admit ASUs, tiered secondary. An ASU is the standard-setter’s own "
         "published words, which is what makes it authority — and it is an "
         "amendment that can be superseded, which is what stops it being primary. "
         "Leaving a domain wired to a publisher we hold nothing from is the worse of "
         "the two.",
  "rec_pick": "Admit ASUs, secondary",
  "picks": ["Admit ASUs, secondary", "Admit ASUs, primary",
            "Take us-gaap out of DOMAINS.md", "Not yet"]},

 {"key": "dec-tie", "new": False, "group": "When two authorities both reach",
  "tag": "Carried — and the new evidence is not about it",
  "title": "When two bodies of authority tie, refuse — or warn and serve?",
  "position": "Keep warning.",
  "context": "<b>What a tie is.</b> A question’s words fire on two bodies of "
             "authority equally — <code>federal-tax</code> and "
             "<code>us-gaap</code> on lease vocabulary — and the alphabet picks "
             "<code>federal-tax</code>. The engine says so on the answer rather than "
             "refusing.<br><br><b>The measurement is unchanged.</b> Of the 98 recorded "
             "problems, 28 fire on any domain, <b>5 tie, and 4 of those 5 are tax "
             "questions with correct tax answers</b>. Refusing spends four right "
             "answers to catch one wrong one.<br><br><b>Forge-Desk attached their "
             "Finding 3 to this decision and it does not belong to it.</b> I checked: "
             "their question, <i>are unidentified deposits gross receipts?</i>, "
             "classifies <code>federal-tax</code> alone, with no second domain. It is "
             "not a tie and never was. What that finding is really about is the card "
             "below this one.",
  "either": [("Keep warning",
              "Four answers keep being served with the tie named on them. One wrong one "
              "goes out the same way, and a person is the check."),
             ("Refuse on a tie",
              "The wrong one stops. So do the four — and today the reader has "
              "nowhere else to go, because no US GAAP source exists (the FASB card)."),
             ("Refuse, but only once FASB lands",
              "Refusing costs the reader nothing once there is somewhere to send them. "
              "It also means this stays open until the FASB card is answered.")],
  "rec": "Keep warning. It is 4 to 1 against, and the new evidence offered for changing "
         "it turned out to be about a different mechanism.",
  "rec_pick": "Keep warning",
  "picks": ["Keep warning", "Refuse, but only once FASB lands", "Refuse on a tie",
            "Not yet"]},

 {"key": "dec-offsource", "new": True, "group": "When two authorities both reach",
  "tag": "New — split out of the one above",
  "title": "Should “this desk does not declare that source” refuse instead of warn?",
  "position": "Keep warning — but the guard is phrasing-dependent and that is a defect.",
  "context": "<b>This is what Forge-Desk’s worst finding is actually about.</b> "
             "<code>SUBJECTS.md</code> records which source answers which subject. When "
             "an answer cites a source the desk does <i>not</i> declare for that "
             "subject, the engine prints a loud warning and <b>still serves the "
             "answer</b>.<br><br><b>Their trap, reproduced here exactly.</b> A "
             "deliberately wrong answer — <i>unidentified deposits are gross "
             "receipts and are booked to sales</i> — citing a real regulation, "
             "with a genuine quote and a careless second reader saying it supports. "
             "<b>It served, marked primary and binding.</b> And the passage refutes it "
             "twice in its own words: it opens <i>“For purposes of applying "
             "paragraph (h)(3)(i)”</i> — the safe harbour for <i>building "
             "improvements</i> — and later says <i>“Gross receipts do not "
             "include the repayment of a loan or similar instrument”</i>, which an "
             "unexplained deposit very often is.<br><br><b>The number Forge-Desk did "
             "not have.</b> I ran the warning over all 98 recorded problems using each "
             "problem’s <i>own recorded correct citation</i>. Refusing instead of "
             "warning would have refused: <b>17 of 98</b> right answers when the "
             "question is phrased tersely, and <b>0 of 98</b> when it carries its full "
             "facts.<br><br>A bookkeeper’s real sentence sits nearer the terse "
             "end.",
  "either": [("Keep warning",
              "The wrong answer still serves, wearing a warning and, underneath it, the "
              "passage that refutes it. A reader who stops at the headline is taken in."),
             ("Refuse",
              "That answer never serves. Up to 17 recorded-correct answers stop serving "
              "too, and which ones depends on how the asker happens to type."),
             ("Fix the phrasing sensitivity first",
              "Neither, yet. 17-versus-0 on the same 98 problems means the guard is "
              "measuring how wordy the question is as much as whether the source fits "
              "— which is a defect in the guard, not an argument for either "
              "answer.")],
  "rec": "Keep warning, and treat this as unsettled. 17 to 1 at worst is a far worse "
         "trade than the 4 to 1 you already declined — but I would not call it "
         "decided, because the honest read is that the guard is phrasing-dependent.",
  "rec_pick": "Keep warning",
  "picks": ["Keep warning", "Fix the phrasing sensitivity first", "Refuse",
            "Not yet"]},

 {"key": "dec-pair", "new": True, "group": "The 7 September incident",
  "tag": "New — and the diagnosis was wrong",
  "title": "Should the pool return your two opposite answers as an inseparable pair?",
  "position": "Yes — a hit with a ratified sibling brings the sibling with it.",
  "context": "<b>The ranking reproduces exactly.</b> Asked <i>a deposit was made on the "
             "last day of the month and is not on the bank statement yet — do we "
             "make an entry in the books?</i>, the pool returns your <b>wrong</b> answer "
             "at rank 1 (score 33.6, <i>an entry in the books</i>) and your <b>right</b> "
             "one at rank 2 (22.0, <i>a reconciling item, no entry in the "
             "books</i>).<br><br><b>But <code>alongside</code> is not dead code, and "
             "Forge-Desk said it was.</b> I served the wrong half through the full "
             "engine. The answer came back carrying, in capitals above everything else: "
             "<i>THE FIRM HAS ANSWERED THIS SAME PASSAGE MORE THAN ONCE, and the other "
             "answer is not this one. Which is in play is a question about the facts, "
             "and nothing here has looked at the facts</i> — naming your other "
             "answer, and printing <b>both</b> passages in full. The second one says in "
             "its own words: <i>“Does not include deposits made after the statement "
             "date.”</i><br><br>It works by matching the citation <b>stem</b> on "
             "the record, not by reading the pool — which is why it was invisible "
             "from where Forge-Desk was standing.<br><br><b>So the exposure is narrower "
             "than reported, and it is real.</b> Anything going through the engine is "
             "protected. Anything reading the pool directly and taking rank 1 is not.",
  "either": [("Pair them",
              "When a hit’s citation has a ratified sibling, the sibling comes "
              "back next to it whatever its score, marked as your other answer. The "
              "pool stops being a pure score ranking, which is a real change to what it "
              "is."),
             ("Leave it",
              "The protection stays where it is, in the engine. Any caller that skips "
              "the engine can take the wrong half — which is exactly what happened "
              "on 7 September.")],
  "rec": "Pair them. It is deterministic, it reads your own record rather than making a "
         "judgement, exactly one pair fires today, and it closes the gap without tuning "
         "any score. The pool’s own rule — <i>it ranks and does not choose</i> "
         "— survives: returning both is the opposite of choosing.",
  "rec_pick": "Pair them",
  "picks": ["Pair them", "Leave it", "Not yet"]},

 {"key": "dec-scoped", "new": True, "group": "What the pool returns",
  "tag": "New — a class, not an instance",
  "title": "Should a passage that says it applies somewhere else be marked as such?",
  "position": "Mark it. Do not demote it.",
  "context": "<b>The instance.</b> A regulation headed <i>“Definition of gross "
             "receipts”</i> really does define the term — and its first words "
             "are <i>“For purposes of applying paragraph (h)(3)(i) of this "
             "section”</i>, the small-taxpayer safe harbour for <b>building "
             "improvements</b>. It is a turnover threshold borrowed for one narrow "
             "purpose. Asked <i>are unidentified deposits gross receipts?</i> it ranks "
             "<b>1</b>; Pub. 583, the authority that actually reaches the question, "
             "ranks <b>5</b>.<br><br><b>The class, measured.</b> 36 passages open with a "
             "clause scoping themselves; 13 of those are definitions. Six probed all "
             "come back in the top 7 for the very term they scope.<br><br>Nothing marks "
             "them. The scoping clause is in the stored text, so a careful reader "
             "catches it — which is the design, and it is doing work.",
  "either": [("Mark them",
              "A passage whose own first line scopes itself carries a flag, printed "
              "above the passage: this says it applies for the purposes of [X]. "
              "Nothing is demoted and no score changes."),
             ("Demote them",
              "They stop ranking first. It also means tuning a ranking by taste, which "
              "is the thing the pool was built not to do."),
             ("Leave it",
              "The reader catches the scoping clause or does not. Today it is printed "
              "in full directly under the answer.")],
  "rec": "Mark, do not demote. Marking is a deterministic read of the passage’s own "
         "first sentence — the same kind of fact the record already trades in. "
         "Demoting is a judgement with a number on it.",
  "rec_pick": "Mark them",
  "picks": ["Mark them", "Leave it", "Demote them", "Not yet"]},

 {"key": "dec-examples", "new": True, "group": "What the pool returns",
  "tag": "New — somebody else’s facts, first",
  "title": "What should the brief do with worked examples?",
  "position": "Label them, and never let a brief be examples only.",
  "context": "<b>What an example is.</b> A worked fact pattern the regulation prints to "
             "show a rule applied — <i>somebody else’s facts</i>. They are "
             "narrative and concrete, so they share more words with a bookkeeper’s "
             "sentence than an abstract rule does.<br><br><b>Measured.</b> Examples are "
             "<b>260 of 786</b> entries in the pool (a third) and they take <b>7 of "
             "12</b> top slots on real working questions — roughly twice their "
             "share. Forge-Desk measured 6 of 12 on the same twelve; I get "
             "7.<br><br><b>You already treat them as special.</b> The grading brief "
             "prints none of them, so the corpus cannot leak its own answer key. The "
             "<i>live</i> brief prints all of them, and the pool now ranks them first. "
             "Nothing in the engine knows that this client’s paint booth is not "
             "Example 11’s paint booth.",
  "either": [("Label and never examples-only",
              "Each example is marked as another taxpayer’s facts, and if every "
              "top hit is an example the highest-ranked rule is pulled in beside them. "
              "An example read beside its rule is useful."),
             ("Label only",
              "Cheaper and half the protection: the answerer is told whose facts these "
              "are but can still be handed nothing but fact patterns."),
             ("Leave it",
              "On roughly half of real questions the first thing the answerer reads is "
              "a fact pattern that is not this client’s.")],
  "rec": "Label and never examples-only. The label costs nothing; the second half is "
         "what actually protects the answer, because an example read <i>instead of</i> "
         "its rule is a confident wrong answer waiting to happen.",
  "rec_pick": "Label and never examples-only",
  "picks": ["Label and never examples-only", "Label only", "Leave it", "Not yet"]},

 {"key": "dec-unitcost", "new": False, "group": "What the record may hold",
  "tag": "Carried — one word, and one risk",
  "title": "Should the record hold what something cost?",
  "position": "Add it, with a format check in the same change.",
  "context": "<b>The record declares exactly three facts it may hold about an "
             "engagement</b> — <code>capitalization_rule</code>, <code>trade</code>, "
             "<code>taxpayer</code>. There is no field for <b>what a unit of property "
             "cost</b>, in a record whose ratified positions are stated in dollars "
             "($2,500 and $5,000) and whose regulations turn on $200, $500 and "
             "$5,000.<br><br><b>It cost a real answer.</b> On round trip "
             "<code>a276e4aed20a</code> the asker supplied the per-unit cost, the brief "
             "said <i>“NOT ON FILE and cannot be put on file”</i>, and the "
             "desk escalated <code>no_field_for_this_fact</code> exactly as instructed. "
             "Two of four purchases were each under $200 in total, so no unit inside "
             "either can exceed $200 and the materials-and-supplies definition settles "
             "them outright. <b>That answer existed and was thrown away at the "
             "door.</b><br><br><b>What it costs, measured rather than estimated.</b> I "
             "added the field in a scratch copy: it is <b>one word on one line</b> of "
             "<code>corpus/SUBJECTS.md</code>. No code change.<br><br><b>The risk, and "
             "this is the part worth your attention.</b> Fact values are free text. So "
             "the field would accept <code>$185</code>, <code>185.00</code> and "
             "<i>one eighty five</i> alike — and a threshold question answered off "
             "a mistyped value is a wrong answer with a real number under it.",
  "either": [("Add it, with a format check",
              "The $200, $500, $2,500 and $5,000 rules become answerable instead of "
              "refusing at the door, and a value that is not a plain decimal amount is "
              "refused when it is recorded rather than when it is answered."),
             ("Add it, plain",
              "Same reach, one word, today. And the first mistyped amount produces a "
              "confident wrong answer that looks arithmetic."),
             ("No field",
              "Every dollar-threshold question keeps escalating, which on a "
              "capitalisation-heavy close is most of them, and the figure is "
              "re-supplied by hand each time.")],
  "rec": "Add it with the format check in the same change. Your own vocabulary says "
         "<code>no_field_for_this_fact</code> means the firm decides the fact exists at "
         "all — so this is yours — but the field is one word and the check is "
         "what stops it becoming a liability.",
  "rec_pick": "Add it, with a format check",
  "picks": ["Add it, with a format check", "Add it, plain", "No field", "Not yet"]},
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
 "goal": "Occam installs the plugin and runs a close from start to finish on "
         "Sarcia Services \u2014 the firm\u2019s V1 goal, set on 11 September 2026.",
 "ends": "It ends with one engagement\u2019s close questions put to the desk through "
         "the installed plugin, and a written record of three things: every answer "
         "served, every refusal with what it asked for, and the questions the desk "
         "never saw.",
 "distance": "<b>The plugin is ready and the pilot has not run.</b> The last leg of the "
             "round trip landed on 12 September \u2014 an answer coming back from "
             "another agent is now read on arrival, measured on all 98 recorded "
             "problems: 97 served, 1 refused, <b>0 misread</b>. The parked queue is "
             "cleared and archived. Today the six checks that prove an install "
             "actually run from one, so the suite is green from both places for the "
             "first time.",
 "detail": "<b>What it refuses, because a goal that refuses nothing is not a goal.</b> "
           "It refuses building more desk machinery: if the desk lacks authority "
           "mid-pilot, that is a finding to write down, not a thing to go and fix. It "
           "refuses inventing a client. And it refuses client PII reaching the desk "
           "\u2014 the desk sees the question and the engagement\u2019s de-identified "
           "facts, never a name, an SSN or an EIN.<br><br><b>One thing stands between "
           "this and the pilot, and it is not a decision.</b> The work on this page is "
           "on a branch. Occam installs from <code>main</code>, so it wants merging "
           "first \u2014 otherwise the pilot runs the version without any of "
           "it.<br><br><b>And the first card will fire during the close.</b> "
           "Capitalisation questions refuse on every client until it is answered. That "
           "is not a finding the pilot will produce; it is this page arriving on "
           "schedule.",
}

CHANGED = [
 ("1,258", "desk tests passing", "1,254 yesterday; identical now from a checkout and from an install"),
 ("0 \u2192 6", "checks that can run where they are meant to prove something", "three could not run installed; three had been deleted by accident"),
 ("97 / 98", "answers rendered and read back", "1 refused, 0 misread \u2014 the whole record, not a sample"),
 ("786", "citations in the pool", "526 rules, 260 worked examples"),
 ("22 \u2192 0", "questions parked in the queue", "all 4 September, none carrying your answer; archived, not deleted"),
 ("10 of 10", "checks green on the pull request", "nothing red, no conflict with main"),
]

LANDED = [
 ("New", "<b>An answer coming back from another agent is readable on arrival.</b> "
         "Until now the asking side could send a question and had no reliable way to "
         "read what came back. It now parses into its parts \u2014 the answer, the "
         "citation, how binding it is, who checked it, and any follow-up question "
         "\u2014 and says whether it can be acted on. Refusals arrive with their "
         "reason and their follow-up intact rather than as an unreadable blob. "
         "<b>Measured on the whole record rather than a sample: all 98 recorded "
         "problems rendered and read back, 97 served, 1 refused, 0 misread.</b>"),
 ("Fixed", "<b>Six checks that prove an install now run from one.</b> Three asserted a "
           "fact about the installed plugin and could only run from a checkout \u2014 "
           "so the only checks about an install were the only ones that could not fail. "
           "Three more had been deleted by accident when the desks were removed, "
           "including the one written specifically to prove the installed layout works. "
           "All six confirmed by breaking them on purpose first."),
 ("Cleared", "<b>The parked queue is empty for a fresh pilot.</b> 22 entries, every one "
             "the same refusal, every one 4 September, none carrying an answer from "
             "you. Archived rather than deleted, so the record of what was asked "
             "survives."),
 ("Checked", "<b>Forge-Desk\u2019s seven findings were re-run before any of them were "
             "accepted.</b> Six reproduced. Two carried corrections that changed what "
             "is being asked \u2014 both are on the cards above."),
]

UNCHECKED = [
 ("The live round trip the dollar-field card rests on.", "It happened on your machine "
  "and left no trace in this repository. I verified that card from the record instead "
  "\u2014 the three declared fields, and the dollar thresholds in your own position. "
  "The story of what the asker supplied is Forge-Desk\u2019s, and I could not test it."),
 ("Forge-Desk\u2019s six junk questions.", "They were not published, so I used six of my "
  "own \u2014 see below. Different sample, so not a contradiction."),
 ("Whether the three failing checks behave the same on Windows.", "I reproduced and "
  "fixed them on Linux. Forge-Desk\u2019s note about Windows temporary folders is "
  "untested by me."),
 ("Any of this against a model.", "Every engine run used a recorded second reader "
  "rather than a live one. The confidently-wrong answer is the engine\u2019s behaviour, "
  "not a model\u2019s."),
 ("What adding the dollar field would do to the 98 recorded problems.", "I proved the "
  "field can be declared in one word. I did not measure which problems would then "
  "answer differently."),
 ("The pilot itself.", "That is the goal above, and it has not run."),
]

WRONG = [
 ("<b>I told you Forge-Desk was blocked on \u201cfour decisions of its own\u201d.</b>",
  "It was blocked on four <i>findings</i>, and holds three carried decisions. I read "
  "that off a one-line status field and stated it as though I had read their docket. I "
  "had not \u2014 it had never been written anywhere I could reach, which is the thing "
  "I should have said instead."),
 ("<b>I said the fix above was four checks. It was six.</b>",
  "Forge-Desk named one deleted check; the deletion had taken three. I repeated their "
  "number without counting."),
 ("<b>Forge-Desk: \u201cnothing in the pool has an <code>alongside</code> to fire "
  "on\u201d \u2014 wrong.</b>",
  "It fires, on exactly the pair in question, and the served answer carries both of "
  "your positions and both passages. It works off the citation stem on the record "
  "rather than off the pool, which is why it was invisible from where they stood. This "
  "changes the card from \u201cis it dead?\u201d to \u201cshould the pool pair them "
  "too?\u201d"),
 ("<b>Forge-Desk: the confidently-wrong answer is evidence about ties \u2014 wrong.</b>",
  "That question fires on one body of authority, not two. It is a different guard with "
  "a different denominator. Attaching it to the tie decision would have argued a 4-to-1 "
  "trade from evidence that is not about it."),
 ("<b>Forge-Desk: all three phrasings reach the right authority at rank 1 \u2014 two of "
  "three.</b>",
  "The third returns the <i>wrong half</i> of the pair in the 7 September card. The "
  "headline evidence for the pool\u2019s biggest win contains an instance of its "
  "sharpest defect. It strengthens that card rather than weakening the pool."),
 ("<b>Forge-Desk: four of six junk questions return nothing \u2014 not on my six.</b>",
  "Two of six returned nothing, and <i>\u201crecommend a good restaurant near the "
  "office\u201d</i> scored higher than the fifth-ranked hit on a real question. "
  "Different questions, so a caveat rather than a contradiction \u2014 but it means "
  "the silence claim does not generalise."),
]

def _md(t: str) -> str:
    out = html.escape(t)
    for mark, tag in (("**", "strong"), ("*", "em"), ("`", "code")):
        parts = out.split(mark)
        out = "".join(p if i % 2 == 0 else "<%s>%s</%s>" % (tag, p, tag)
                      for i, p in enumerate(parts))
    return out.replace("\n\n", "</p><p>").replace("\n", " ")


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
            "why": _md(p["why"]),
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
      "<p><b>Every card was re-run before it reached this page.</b> These began "
      "as findings from the session that tests the desk on your machine. It asked "
      "for them to be verified rather than believed, so each one was reproduced "
      "here first — six held, two carried corrections that changed the "
      "question being asked, and what did not reproduce is listed under "
      "<i>What I got wrong</i> at the foot of this page.</p>"
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
            '<p class="lead">All %s answered, all %s acted on. <b>These were '
            'answered somewhere else</b> \u2014 on the one-corpus docket and in '
            'conversation \u2014 so unlike previous pages these are transcribed '
            'from the log rather than read out of this page\u2019s own store. '
            'Where each was said is on the line. What each one caused is measured '
            'from the repository.</p>'
            '<ul class="plain">%s</ul>') % (_word(len(ANSWERED)),
                                            _word(len(ANSWERED)), rows)


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
    ${(n.rec || d.rec) ? `<div class="reclead"><h4>What I would do</h4><p>${n.rec || esc(d.rec)}</p></div>` : ""}
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
        d.why ? `<div class="blk"><h4>The full reasoning as drafted</h4><p>${d.why}</p></div>` : "",
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
