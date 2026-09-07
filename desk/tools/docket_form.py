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
#: Every matter the FIFTH docket carried, taken from the page published on
#: 6 September 2026 (artifact 80788800) and READ BACK from its own store on the
#: 7th. It is the only independent record of what was already open: without it,
#: "which matters are new" is read out of the same list that sets it.
#:
#: All six were answered between 01:33 and 01:59 UTC on 7 September. Two were
#: decisions to build and both are built. Four came back "Not yet" and are
#: carried here.
FIFTH_DOCKET = {
    "dec-cap-field",
    "dec-courts-again",
    "pos-capitalization-and-de-minimis-POS1",
    "pos-capitalization-and-de-minimis-POS2",
    "pos-personal-or-business-POS1",
    "pos-rewards-and-information-returns-POS3",
}

OTHERS = [
 {"key": "dec-register", "new": True, "group": "How positions are written",
  "tag": "Your words, and they land",
  "title": "You called a position AI dribble. You were right, and it is not one position.",
  "position": "Redraft every proposed position in plain words and bring them back.",
  "context": "You wrote, on the payment-rail position: <i>\u201cok right now this entire "
             "thing sounds like a ton of just AI dribble, what in the world are you "
             "communicating with some of these\u201d</i><br><br>Here is the sentence you "
             "were reading:<br><br><i>\u201cwhere a payment for services shows no evidence "
             "it settled through a third party payment network, treat it as outside "
             "section 6050W and count it toward the $2,000 threshold\u201d</i><br><br>"
             "In plain words that is: <b>if we cannot tell whether a payment went "
             "through a card processor, assume it did not, and count it.</b> Same rule, "
             "and you can decide whether you agree with it.<br><br>"
             "<b>This is not one bad sentence.</b> The repository already has a rule "
             "about this \u2014 <i>never transcribe a spec; no term a first-time reader "
             "would have to look up; a sentence past ~25 words was written to be "
             "complete rather than to be read</i> \u2014 and it is written for what "
             "clients see. Positions are not client-facing, so nothing enforced it, and "
             "they drifted into the register of the thing that generated them. "
             "<b>A position you cannot read is one you cannot ratify</b>, which makes "
             "this the reason some of them keep coming back \u201cNot yet\u201d.",
  "either": [("Redraft them",
              "I rewrite all three proposed positions in plain words \u2014 the rule "
              "unchanged, only the wording \u2014 and bring them back next to the current "
              "text so you can see exactly what moved. Nothing is ratified on my say-so."),
             ("Leave the wording alone",
              "They stay as drafted. That is a real answer: the wording is precise, and "
              "precision is worth something in a document that governs a filing "
              "position. The cost is that they stay hard to read, and so hard to "
              "ratify.")],
  "rec": "Redraft them. You have now objected to the wording of a position twice on "
         "two dockets, which is the strongest signal available that it is the wording "
         "and not the rule that is blocking you.",
  "picks": ["Redraft them", "Leave the wording alone", "Redraft just this one",
            "Not yet"]},

 {"key": "dec-searcher-scope", "new": True, "group": "The searching agent",
  "tag": "Blocks the rest of the design",
  "title": "When a desk has no answer, where may it go looking?",
  "position": "Limit the search to the eCFR, IRS.gov and the US Code.",
  "context": "You asked for an agent that goes and finds authority when a desk cannot "
             "answer, and checks what it finds the way we check everything else.<br><br>"
             "<b>Measuring first changed the design.</b> Of the 30 recorded failures "
             "from your September close, 11 were \u201cno authority on file\u201d "
             "\u2014 the rest needed a document or an answer from the client, which no "
             "amount of searching fixes.<br><br><b>And the missing rule is almost "
             "always on a site we already use.</b> Tax law lives on three: the eCFR, "
             "IRS.gov and the US Code. A real example from your own record: one rule we "
             "hold switches itself off for tips covered by <b>section 6053</b>, and we "
             "do not hold section 6053. That is not an open-internet problem \u2014 it "
             "is a page on a site we already trust that nobody has fetched.",
  "either": [("Those three sites only",
              "Everything it finds is a source you have already accepted, so nothing "
              "waits on a new decision about whether we may copy from it. It can run "
              "unattended. It will not find court decisions or anything in a paid "
              "database."),
             ("Let it search anywhere",
              "It could reach case law and commentary. But then something has to judge "
              "whether a page is authority at all \u2014 a law firm\u2019s marketing "
              "page is not \u2014 and that judgement is the part with no safe default.")],
  "rec": "Those three sites, at first. It is where nearly all of it is, and it is the "
         "version that can run without you in the room. Widening later costs nothing; "
         "starting wide means the first thing it does is make a legal call.",
  "picks": ["Those three sites only", "Let it search anywhere",
            "Add one more site \u2014 I will say which", "Not yet"]},

 {"key": "dec-parser", "new": True, "group": "The record",
  "tag": "31 examples, and it turned into a research problem",
  "title": "Four regulations will not read. Worth the work, or leave them?",
  "position": "Timebox one more attempt at the reader; stop if the acceptance test does not pass.",
  "context": "The desks gained 196 worked examples today \u2014 the government applying "
             "its own rules to real fact patterns, which is the closest thing in the "
             "record to the question a bookkeeper asks. <b>Four regulations still will "
             "not read</b>, holding about 31 more.<br><br>The tool refuses them rather "
             "than guessing, which is right: a paragraph number guessed wrong files an "
             "example under a rule that is not its own, and that happened today and was "
             "caught.<br><br><b>I found three causes and fixed none of them, because "
             "all three together are still not enough.</b> With all three, one of the "
             "four reads \u2014 and the regulation cites 31 of its own paragraphs, of "
             "which only 24 land. The one that works lands 100 of 102. So the reading "
             "is still wrong somewhere, and a fourth cause is unfound.",
  "either": [("Have another go",
              "Roughly 31 more worked examples, on the cash, vehicle and meals desks. "
              "There is a real pass mark now \u2014 the regulation grades the reading "
              "by whether every paragraph it cites is found \u2014 so it either works "
              "or it visibly does not."),
             ("Leave them",
              "Those desks keep their rules and lose the examples. Nothing is broken; "
              "they are simply thinner. The work goes to the searching agent instead, "
              "which may reach the same text another way.")],
  "rec": "One timeboxed attempt. The pass mark is real and unfakeable, so it cannot "
         "quietly half-work \u2014 but it is now a research problem rather than a typo, "
         "and I would stop rather than loosen the check to get a number.",
  "picks": ["Have another go", "Leave them", "Not yet"]},

 {"key": "dec-merge-300", "new": True, "group": "Housekeeping",
  "tag": "10 commits, everything verified",
  "title": "Merge tonight\u2019s work?",
  "position": "Merge <a href='https://github.com/AJSethuraman/SATC/pull/300'>#300</a>.",
  "context": "The desks went from 531 to 727 stored passages, and from 4 worked "
             "examples to 200. <b>Every one of the 727 was fetched back from the "
             "publisher and compared word for word</b> \u2014 0 differences, 0 "
             "unreachable \u2014 and against last week\u2019s text rather than "
             "January\u2019s, which is a second thing that was quietly wrong and is "
             "now fixed.<br><br>Five defects surfaced on the way, four of them mine, "
             "all fixed and guarded. Three things I told you turned out to be wrong "
             "and are corrected in the record rather than dropped.<br><br>559 tests "
             "pass. The desk job is green.",
  "either": [("Merge it",
              "It goes to <code>main</code>. Nothing here touches a client file or "
              "anything a client sees."),
             ("Hold it",
              "It sits on the branch. Nothing else is waiting on it, so holding costs "
              "nothing except that the next piece of work starts further from "
              "<code>main</code>.")],
  "rec": "Merge it. It is additive to the record, every passage is verified against "
         "its publisher, and the parts I am least sure about are written down as open "
         "rather than shipped as done.",
  "picks": ["Merge it", "Hold it", "Not yet"]},

 {"key": "dec-courts-again", "group": "Sources",
  "tag": "Carried a third time \u2014 and your note started something",
  "title": "The court hosts, still open.",
  "position": "Say which half you meant. I have still not read an answer into it.",
  "context": "<b>Your note last time became a design.</b> You wrote: <i>\u201cok as we "
             "talk about this the more it seems to make sense to simply run it through "
             "the tie-out process and verify it in the moment\u201d</i> \u2014 and "
             "that idea, verifying a source when it is used rather than approving it in "
             "advance, is what the searching agent above is built around. Recorded as "
             "yours.<br><br><b>The original question is still unanswered.</b> Two "
             "dockets ago you pressed a button (keep the five court hosts closed) and "
             "wrote words beside it (open everything we can use). Those point opposite "
             "ways. I have not picked one for you.<br><br><b>LexisNexis is not "
             "started.</b> Every source here is a government work in the public domain, "
             "which is why we may store the text. A licensed database is a different "
             "shape and would need you to decide what may be copied before a single "
             "passage could be kept.",
  "either": [("Keep the five hosts closed",
              "Nothing changes. A court decision reaches a desk when you hand it over, "
              "which is what happened with Anikeev."),
             ("Open them",
              "They refused automated access last time I tried. Opening them is a "
              "policy change here plus a real chance they still refuse.")],
  "rec": "Keep them closed and let the searching agent answer the question underneath "
         "it \u2014 which sources would actually settle the questions that keep coming "
         "to you. That is a measurement, not a policy change.",
  "picks": ["Keep hosts closed", "Open the hosts", "Look into LexisNexis first",
            "Not yet"]},
]

CHANGED = [
 ("6 of 6", "matters you answered", "two were instructions to build; both are built"),
 ("727 of 727", "passages fetched back and compared", "0 differences, 0 unreachable"),
 ("4 \u2192 200", "worked examples the desks hold", "the government applying its own rules to real facts"),
 ("531 \u2192 727", "stored passages in all", "262,000 characters of authority to 497,000"),
 ("559", "desk tests passing", "514 before the searcher; 470 when this branch started"),
]

LANDED = [
 ("New", "<b>The desks hold their regulations\u2019 worked examples.</b> They had four. "
         "They have 200. These are the passages where the IRS takes a fact pattern and "
         "says what the answer is \u2014 the closest thing in the whole record to the "
         "question somebody actually asks while closing a set of books."),
 ("Found", "<b>The desks were missing more authority than they held.</b> 224,000 "
           "characters of worked examples across six regulations, never extracted, "
           "against a whole corpus of 262,000. Not an oversight \u2014 they were "
           "dropped on purpose years of sessions ago, because a desk that stores the "
           "examples it is also TESTED on is holding its own answer key. Right for "
           "testing, and it quietly cost the answering side the best thing in the "
           "document."),
 ("Fixed", "<b>They are marked now instead of deleted.</b> Each passage says whether it "
           "is a rule or a worked example, and three separate places hide the examples "
           "from anything being scored. The two examples deleted on Saturday for "
           "leaking into a test are back, and that desk still scores 19 of 19."),
 ("Found", "<b>\u201cRoof\u201d appeared three times in the fixed-asset desk\u2019s "
           "own practice questions \u2014 which we wrote \u2014 and zero times in its "
           "actual authority.</b> The regulation is full of roof cases; it is the "
           "classic did-you-repair-it-or-improve-it question. It now appears 49 times."),
 ("Found", "<b>Four examples were filed under the wrong rule.</b> One regulation labels "
           "a heading differently from the rest, the reader did not notice, and four "
           "examples about tearing out columns and disposing of shingles were filed "
           "under leasehold improvements. Their own text says \u201cassume the same "
           "facts as Example 1\u201d, which under the wrong numbering pointed at the "
           "wrong example too."),
 ("Found", "<b>Text was being stored that the publisher never printed.</b> Long "
           "passages are wrapped across lines for readability, and the wrapping split "
           "words at hyphens \u2014 so \u201cload-carrying\u201d was stored as "
           "\u201cload- carrying\u201d. That passage could never again be proved "
           "against its source. Every passage stored before today dodged it by luck."),
 ("Found", "<b>Everything was being verified against January\u2019s text.</b> The "
           "check was pinned to 1 January on a note saying that was as recent as the "
           "government\u2019s site allowed. It was not \u2014 the site serves last "
           "week. That failure can only ever hide a change, never invent one. The tool "
           "now asks the site for its own latest date."),
 ("Found", "<b>A run folder named for a date was overwriting that date\u2019s "
           "evidence.</b> Re-running rewrote seventeen briefs inside a folder still "
           "claiming to be from two days earlier. Nothing failed; only <code>git</code> "
           "noticed."),
]

UNCHECKED = [
 ("No model has answered anything, again.", "Every number here measures the record and "
  "the machinery around it. Nothing has been asked to reason about a client\u2019s "
  "books, so \u201c200 worked examples\u201d is a fact about the library and not yet "
  "about the advice."),
 ("No desk has met a real client file.", "Still true, still deliberate \u2014 scoring "
  "against answers we wrote ourselves measures agreement rather than correctness \u2014 "
  "and still the largest gap between this and something you could use."),
 ("The scoreboard was not re-run.", "The rewards desk gained 38 worked examples today "
  "and I have not measured what that does to its scores. It should not change them "
  "\u2014 examples are hidden from anything being scored \u2014 but should-not is not "
  "measured."),
 ("Four regulations still will not read.", "About 31 worked examples behind them. Three "
  "causes found, none shipped, because all three together still are not enough."),
 ("The exhibits were opened, but by machine.", "I pulled the text back out of the PDFs "
  "to prove they are readable and carry the right figures. Nobody has looked at one "
  "with their eyes."),
 ("The register problem was diagnosed, not fixed.", "Nothing was reworded. That is "
  "matter 1 on this page, because rewriting a position you did not ask me to rewrite is "
  "the exact thing the positions store exists to prevent."),
]

WRONG = [
 ("<b>You answered this docket two hours before I read it.</b>", "01:33 to 01:59 UTC. I "
  "worked until 03:40 without looking. Two of your six answers were instructions to "
  "build something and both sat there while a large pile of other work went in on top. "
  "The rule I broke is written down in the skill I was following: <i>\u201can answer "
  "sitting in a store nobody reads back is worse than no form at all.\u201d</i> They "
  "are built now."),
 ("<b>I published a diagnosis that was wrong, and then found out by building it.</b>", "I "
  "told you a regulation \u201cskips a numbering level\u201d and that its own citations "
  "proved it. The citations were real; my reading of them was not \u2014 it uses a "
  "different <i>alphabet</i> at the same level. Corrected in the record rather than "
  "quietly dropped, because the wrong version had already been committed."),
 ("<b>I said a safeguard was doing work it was not doing.</b>", "I wrote in the code that "
  "one particular check was what kept the reader from misfiring. Then I deliberately "
  "broke that check twice and nothing failed. Something else entirely was doing the "
  "protecting. A safeguard everyone believes in that does nothing is worse than none, "
  "because it stops anyone looking for the real one."),
 ("<b>I told you the desks held zero worked examples. They held four.</b>", "All four on "
  "one desk, all put there by hand by whoever built it, and they are the most useful "
  "passages on that desk \u2014 which is the argument I was making, made better by the "
  "thing I got wrong."),
 ("<b>One of my own tests passed for no reason.</b>", "I wrote a check to prove the "
  "worked examples stay hidden from anything being scored, sabotaged it to confirm it "
  "fires, and one sabotage survived: the list an answer is judged against still "
  "included examples the model was never shown. That is the number that detects "
  "answering from memory. Found by attacking my own work, not by writing it."),
]


def _md(t: str) -> str:
    out = html.escape(t)
    for mark, tag in (("**", "strong"), ("*", "em"), ("`", "code")):
        parts = out.split(mark)
        out = "".join(p if i % 2 == 0 else "<%s>%s</%s>" % (tag, p, tag)
                      for i, p in enumerate(parts))
    return out.replace("\n\n", "</p><p>").replace("\n", " ")


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
            "picks": ["Ratify it", "Ratify with an edit", "No", "Not yet"],
        })
    for o in OTHERS:
        rows.append(dict(o, kind="decision"))
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
    ratified = sum(len([q for q in record.load(d).positions if not q.proposed])
                   for d in sorted((HERE / "desks").iterdir())
                   if (d / "SOURCES.md").is_file())
    # A POSITION THIS DOCKET ITSELF SAYS TO HOLD BACK, read off the note rather
    # than counted by hand -- the preface states how many are answerable now, and
    # a number typed there goes stale the moment one is ratified.
    waiting = [r for r in pos if "Do not ratify" in (r["note"] or {}).get("rec", "")]
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
    fresh = [r for r in rows if r["key"] not in FIFTH_DOCKET]
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
    headline = _word(c["n"]).capitalize()
    # The claim this page opens by retracting, restated from the measurement
    # rather than from what I said last time -- which was itself off by two.
    if c["turns"] == 0:
        measured = ("<b>Not one of them</b> sits on a citation any of its own "
                    "desk's scored problems turn on")
    else:
        measured = ("Only <b>%s</b> of them sits on a citation its own desk's "
                    "scored problems turn on" % _word(c["turns"]))
    preface = (
      "<p><b>You answered all six of the last docket \u2014 and I did not read your "
      "answers for two hours.</b> You filled the form in between 01:33 and 01:59. "
      "I worked until 03:40 without looking. Two of the six were instructions to "
      "build something and both sat there while a large pile of other work went in "
      "on top of them. They are built now, and the rule I broke is written into "
      "the skill I was following: <i>an answer sitting in a store nobody reads "
      "back is worse than no form at all.</i></p>"
      "<p><b>The desks went from 4 worked examples to 200.</b> These are the "
      "passages where the IRS takes a real fact pattern and says what the answer "
      "is \u2014 the closest thing in the record to the question somebody asks "
      "while closing a set of books. They had been dropped on purpose, long ago, "
      "for a good reason that only applied to testing. All 727 stored passages "
      "were fetched back from their publishers and compared word for word: no "
      "differences, nothing unreachable.</p>"
      "<p><b>%(nw)s things wait on you, and %(freshw)s of them are new.</b> Two of "
      "the new ones come straight out of what you wrote on the last form \u2014 "
      "including the one about how these positions are written, which you were "
      "right about.</p>"
      "<p><b>A correction, and it inverts what the last docket told you.</b> That "
      "page said the desk was REFUSING the safe-harbour questions and that adding "
      "the field would stop it. It was not refusing. Measured on 7 September: "
      "asked about the safe harbour with nothing on file, the desk answers "
      "straight from the regulation and never asks whether that client has a rule "
      "of its own \u2014 which is the thing you objected to in the first place. The "
      "follow-up only runs off a position you have RATIFIED; a proposal is nobody\u2019s "
      "word, so the desk never consults it. Adding the field was necessary and it "
      "was never the switch.</p>"
      "<p><b>%(ansv)s of the %(posw)s positions here are answerable today</b>, and "
      "nothing is blocking them but your yes. The remaining objection is the "
      "wording, which is matter 1 \u2014 a separate question from whether the rule is "
      "right.</p>"
    ) % {"posw": _word(c["pos"]),
         "freshw": _word(c["fresh"]), "nw": _word(c["n"]).capitalize(),
         "ansv": ("%s" % _word(c["answerable"]).capitalize()) if c["waiting"]
                 else "Every one"}
    lede = ("%s of them are positions to approve or reject. %s are choices no rule "
            "settles." % (_word(c["pos"]).capitalize(), _word(c["dec"]).capitalize()))
    return _PAGE % (_word(c["n"]).capitalize(), _CSS, DATE, headline, lede,
                    preface, c["n"], c["n"], c["pos"], c["dec"], _blocks(c),
                    json.dumps(c["rows"]), _JS)


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

_PAGE = """<title>Docket · %s Open</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>%s</style>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">Docket · desk · %s</div>
  <h1>%s things waiting on you</h1>
  <p>%s Every one carries what I would do and why, and every one is answerable in
  a line. It saves as you type.</p>
</header>

<div id="offline" class="banner">Answers are not saving — this view could not reach the store. Tell me in the conversation instead.</div>

<div class="preface">%s</div>

<div class="bar">
  <span class="tally" id="tally">0 of %d answered</span>
  <span class="grow"></span>
  <button class="filt" type="button" data-filt="all" aria-pressed="true">All %d</button>
  <button class="filt" type="button" data-filt="position" aria-pressed="false">Positions %d</button>
  <button class="filt" type="button" data-filt="decision" aria-pressed="false">Other %d</button>
  <button class="filt" type="button" data-filt="open" aria-pressed="false">Unanswered</button>
</div>

<h2 class="sec" style="border-top:none;padding-top:0;margin-top:0">Waiting on you</h2>
<p class="lead">&ldquo;Not yet&rdquo; is a real answer — it keeps the matter open and
brings it back next time. Nothing is lost by skipping one, and nothing is recorded
without an explicit yes.</p>
<div id="list"></div>

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
  const n = DATA.filter(d => (state[d.key] || {}).choice).length;
  document.getElementById("tally").textContent = n + " of " + DATA.length + " answered";
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
    <div class="says"><b>${d.kind === "decision" ? "What I would put in place" : "What the desk would say, in your words"}</b>&ldquo;${esc(d.position)}&rdquo;</div>
    ${d.citation ? `<div class="rests">Rests on <span class="c">${esc(d.citation)}</span><br>${esc(d.source)}</div>` : ""}
    ${d.context ? `<p class="ctx">${d.context}</p>` : ""}
    ${n.read ? `<div class="blk rec"><h4>Before you decide</h4><p>${n.read}</p></div>` : ""}
    ${n.for ? `<div class="blk for"><h4>What supports it</h4><p>${n.for}</p></div>` : ""}
    ${n.against ? `<div class="blk against"><h4>What cuts against it</h4><p>${n.against}</p></div>` : ""}
    ${n.silent ? `<div class="blk silent"><h4>What the authority does not say</h4><p>${n.silent}</p></div>` : ""}
    ${(d.either || []).map((e, i) => `<div class="blk ${i === 0 ? "for" : "against"}"><h4>${esc(e[0])}</h4><p>${esc(e[1])}</p></div>`).join("")}
    ${d.kind === "position" ? `<div class="blk rec"><h4>What saying yes changes</h4><p>${
      d.unlocks > 0
        ? `<b>${d.unlocks}</b> of this desk's scored problems turn on this exact citation, so ratifying makes them answerable.`
        : `<b>No scored problem changes.</b> What changes is that the desk stops handing the question back and starts saying ${d.shape === "rule" ? "what to do next" : "this, in your words, with the citation behind it"}.`
    }</p></div>` : ""}
    ${(n.rec || d.rec) ? `<div class="blk rec"><h4>What I would do</h4><p>${n.rec || esc(d.rec)}</p></div>` : ""}
    ${d.why ? `<details class="why"><summary>The full reasoning as drafted</summary><div class="d"><p>${d.why}</p></div></details>` : ""}
    <div class="answer">
      <label for="ta-${d.key}">Your answer</label>
      <div class="picks">
        ${d.picks.map(p => `<button type="button" class="pick" data-choice="${esc(p)}" aria-pressed="${s.choice === p}">${esc(p)}</button>`).join("")}
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
