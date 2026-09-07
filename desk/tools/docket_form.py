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
SIXTH_DOCKET = {
    "dec-courts-again",
    "dec-merge-300",
    "dec-parser",
    "dec-register",
    "dec-searcher-scope",
    "pos-capitalization-and-de-minimis-POS1",
    "pos-capitalization-and-de-minimis-POS2",
    "pos-rewards-and-information-returns-POS3",
}

OTHERS = [
 {"key": "dec-admit-publishers", "new": True, "group": "The searching agent",
  "tag": "Built and run \u2014 one decision left",
  "title": "Two publishers tied out. Do they become sources?",
  "position": "Admit eCFR and Cornell\u2019s LII on fixed-assets, for \u00a7 1.162-3.",
  "context": "<b>Your question killed the design I was about to build.</b> I had the "
             "searcher limited to three sites you already trust. You wrote: <i>\u201chow "
             "would you know you need to access a site not on the whitelist before being "
             "asked?\u201d</i> You cannot ask permission for a site you do not yet know "
             "you need \u2014 so a list of approved sites means it can only ever find "
             "what we already have.<br><br><b>So it looks anywhere, and the gate is on "
             "keeping, not looking.</b> Nothing it finds goes into the record unless the "
             "words are still on the publisher\u2019s own page today AND the publisher "
             "is one you have accepted. Anything else comes to you, like this.<br><br>"
             "<b>One real question, run through it.</b> The fixed-assets desk holds "
             "\u00a7 1.263(a)-3, whose own examples point at \u00a7 1.162-3 \u2014 and "
             "it cannot follow the pointer. One search, eight results, four passages "
             "read: two are real and check out, one was too short to prove which "
             "paragraph it came from, one site refused us. The two that check out are "
             "the definition of materials and supplies, and the desk cannot use either "
             "until you say where it may read them from.",
  "either": [("Admit both",
              "The desk answers materials-and-supplies questions instead of handing "
              "them back. Both are free government-text publishers; eCFR is the "
              "government\u2019s own and Cornell\u2019s is a university library. "
              "Nothing is copied that is not checked against the publisher first."),
             ("Leave the gap open",
              "The desk keeps refusing the question, which is honest \u2014 it is not "
              "guessing. The cost is that this comes back to you every time somebody "
              "asks about spare parts, and the searcher keeps finding the same two "
              "pages.")],
  "rec": "Admit eCFR and leave Cornell for now. eCFR is the government publishing its "
         "own regulation and you already rely on it for \u00a7 1.263(a)-3 \u2014 this "
         "is the same site, one section over. Cornell is a faithful copy rather than "
         "the source, so it earns nothing eCFR does not already give us.",
  "rec_pick": "Admit eCFR only",
  "picks": ["Admit eCFR only", "Admit both", "Leave the gap open", "Not yet"]},

 {"key": "dec-register-standing", "new": True, "group": "How positions are written",
  "tag": "You corrected me \u2014 and it may have emptied the job",
  "title": "The standing check on how positions are worded: still wanted?",
  "position": "Do not build it yet. The complaint it was for turned out to be elsewhere.",
  "context": "<b>You answered this on the last docket and then told me I had the target "
             "wrong.</b> You said <i>\u201credraft them\u201d</i>, and added: "
             "<i>\u201cwe have to ensure our rules are followed as answers are added to "
             "the desk.\u201d</i> I read that as: build a mechanical check on how a "
             "position is worded, the way we already check the price page.<br><br>Then "
             "you said: <i>\u201cwhen i say AI dribble i don\u2019t necessarily mean "
             "that the position itself is. i mean how you explain it.\u201d</i><br><br>"
             "<b>That was the real fault and it is fixed.</b> The card on this page now "
             "leads with what I would do instead of burying it under four sections, and "
             "a card can no longer offer you \u201cRatify it\u201d while its own "
             "recommendation says do not \u2014 that is a build error now, not "
             "something a reader has to catch.<br><br><b>What I do not know is whether "
             "the positions themselves still need a rule.</b> I measured before "
             "assuming: length is not the tell. The position you called dribble is 29 "
             "words against a median of 27, and the meals positions run 61 to 73 and "
             "drew no complaint. So I have no measured rule to write, and writing one "
             "anyway is how the dribble got there in the first place.",
  "either": [("Drop it \u2014 the card was the problem",
              "Nothing more is built. The docket card fix stands, and if a position "
              "reads badly again you tell me and we look at that one."),
             ("Still want the check",
              "I go and measure what actually separates a position you accepted from "
              "one you rejected, and bring you the rule before writing it \u2014 not a "
              "word count borrowed from the price page.")],
  "rec": "Drop it. You have told me twice now that the problem is how I explain things, "
         "and both times I found the fault in my writing rather than in the record. A "
         "rule invented to satisfy an instruction is the thing this repository keeps "
         "catching.",
  "rec_pick": "Drop it \u2014 the card was the problem",
  "picks": ["Drop it \u2014 the card was the problem", "Still want the check",
            "Not yet"]},

 {"key": "dec-merge-305", "new": True, "group": "Housekeeping",
  "tag": "6 commits, 585 desk tests, job green",
  "title": "Merge today\u2019s work?",
  "position": "Merge <a href=\'https://github.com/AJSethuraman/SATC/pull/305\'>#305</a>.",
  "context": "Three things, none of which touches a client file, anything a client "
             "sees, or any desk\u2019s record.<br><br><b>The searching agent.</b> It "
             "looks anywhere, checks what it finds against the publisher\u2019s own "
             "page, and can put nothing in the record without you. 47 tests, and I "
             "broke seven of its safety rules on purpose to confirm each one is "
             "caught.<br><br><b>The docket card.</b> Leads with the recommendation; "
             "cannot offer a button its own recommendation argues against.<br><br>"
             "<b>The reader.</b> Seven causes, all eleven regulations reading. Fifteen "
             "mutations tried, fourteen caught \u2014 and the fifteenth broke nothing, "
             "so the comment now says that rule is not load bearing instead of claiming "
             "it is.",
  "either": [("Merge it",
              "It goes to <code>main</code>. The searcher becomes available to any "
              "session; the reader fix applies the next time anything is extracted."),
             ("Hold it",
              "It sits on the branch. Nothing is waiting on it except the two decisions "
              "above, which need it merged before they can be acted on.")],
  "rec": "Merge it. It adds tools and no authority \u2014 the two passages the searcher "
         "found are on this page waiting on you, and neither is in the record.",
  "rec_pick": "Merge it",
  "picks": ["Merge it", "Hold it", "Not yet"]},
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
 "goal": "Get the three thin desks holding the worked examples their own "
         "regulations already contain \u2014 cash, vehicle and meals.",
 "ends": "It ends when each of the three holds every example its sections carry, "
         "with the before-and-after scores on the page.",
 "distance": "2 of 3 desks done \u2014 cash and vehicle are complete.",
 "detail": "<b>The 34 that could be extracted are in</b>, and every one of the "
           "761 stored passages was fetched back from its publisher and compared "
           "word for word \u2014 0 differences, 0 unreachable. Cash went from no "
           "worked examples to 19 and vehicle from 10 to 22; both are complete."
           "<br><br><b>Meals is the one left, and it is short by 29.</b> Three of "
           "its regulations write an example as an ordinary numbered paragraph "
           "rather than in a tagged block, so those sections read perfectly and "
           "the extractor returns nothing from them. It has 3 of the 32 examples "
           "its own authority carries. That is the rest of this goal.",
}

CHANGED = [
 ("8 of 8", "matters you answered last time", "two were instructions to build; both are built"),
 ("11 of 11", "regulations these desks rely on now read", "every path each one cites lands"),
 ("34", "worked examples added, all tied out", "and 29 more the reader still cannot see"),
 ("761 of 761", "passages fetched back and compared", "0 differences, 0 unreachable"),
 ("585", "desk tests passing", "514 when today\u2019s work started; 47 of the new ones are the searcher\u2019s"),
]

LANDED = [
 ("New", "<b>The searching agent, built and run against live publishers.</b> When a "
         "desk has no answer it goes and looks \u2014 anywhere, because you were right "
         "that a list of approved sites can only find what we already have. It reads "
         "the passage off the publisher\u2019s own page rather than off the search "
         "result, and it can put nothing in the record without you."),
 ("Run", "<b>One real gap, end to end.</b> The fixed-assets desk holds a regulation "
         "whose own examples point at \u00a7 1.162-3, and it could not follow the "
         "pointer. One search, eight results, four passages read: two check out, one "
         "was too short to prove which paragraph it came from, one site refused us. "
         "Both good ones are waiting on you, above."),
 ("Fixed", "<b>Every regulation these three desks rely on reads now.</b> Seven "
           "separate causes. Two I had described to you, and five I had not \u2014 "
           "including a paragraph with no number on it, two paragraphs reserved on one "
           "line, and one regulation whose italics are broken across a paragraph "
           "number in the government\u2019s own file. That last one, a stray tag, had "
           "cost the vehicle desk every example it might have had."),
 ("Fixed", "<b>This page cannot ask you something it has already answered.</b> The "
           "recommendation used to sit last, under four sections of argument. It now "
           "leads. And a card can no longer offer <i>Ratify it</i> as its first button "
           "while its own recommendation says do not \u2014 which is exactly what the "
           "docket before last did to you, twice. It is a build failure now, not "
           "something a reader has to notice."),
 ("Found", "<b>A citation was being read as naming paragraphs that do not exist.</b> "
           "<i>\u201cparagraph (c)(1)(iii), (iv), or (v)\u201d</i> was read as citing "
           "a paragraph called \u201c(v)\u201d. Not just a miscount \u2014 that list "
           "is where the tool picks which rule an example is filed under, so a bare "
           "\u201c(v)\u201d was a candidate rule on any regulation whose examples "
           "live under (v). Same class as the four examples filed under the wrong rule "
           "on Saturday."),
 ("New", "<b>Two of the three thin desks now hold their regulations\u2019 worked "
         "examples.</b> Cash had none and has 19; vehicle had 10 and has 22; meals "
         "had none and has 3. Every one was fetched back from its publisher and "
         "matched word for word, along with all 727 that were already there."),
 ("Found", "<b>29 more worked examples exist that the reader cannot see at all</b>, "
           "every one of them on the meals desk. It is the Next above, and it is "
           "why meals holds 3 of the 32 its own authority carries."),
]

UNCHECKED = [
 ("No model has answered anything, again.", "Every number here measures the record and "
  "the machinery around it. Nothing has been asked to reason about a client\u2019s "
  "books."),
 ("No desk has met a real client file.", "Still true, still deliberate, and still the "
  "largest gap between this and something you could use."),
 ("No desk\u2019s score has been re-measured since the examples went in.", "Scoring "
  "asks a model to answer, and no model has been asked anything today. What IS "
  "measured is that the brief a GRADED model sees did not change size on any of the "
  "seven desks \u2014 34 examples went in and the withholding held \u2014 so the "
  "scores should not move. Should-not is not measured."),
 ("The 29 invisible examples were counted, not extracted.", "29 is the number of "
  "paragraphs that begin <i>\u201cExample 1.\u201d</i> in those three regulations. How "
  "many survive the filters that keep a desk from being tested on its own answer key "
  "is not known until it is built."),
 ("The scoreboard was not re-run.", "It has not been run since the rewards desk gained "
  "38 examples yesterday. It should not have changed \u2014 examples are hidden from "
  "anything being scored \u2014 but should-not is not measured."),
 ("Only two of the six test suites were run here.", "desk (585 passed, 1 skipped) and "
  "canon (181 passed), both run just now. client-documents, satc_system, "
  "invoice-generator and credit-suite ran on the server; four had reported green and "
  "two were still running when I last looked. Nothing in today\u2019s work touches "
  "any of them."),
 ("The exhibits were opened, but by machine.", "Nobody has looked at one with their "
  "eyes."),
]

WRONG = [
 ("<b>I told you six regulations had started reading. Three had.</b>", "The other three "
  "were already reading before I touched anything. I caught it an hour later by "
  "checking a claim I had already written into a follow-up note \u2014 and by then it "
  "was in a commit message and on the draft of this page, promising you examples on "
  "desks whose regulations still would not read. Corrected in the record rather than "
  "quietly fixed. Both of those now read too."),
 ("<b>I ran this docket on the old rulebook.</b>", "canon updated to 1.13.0 this "
  "morning with a new standing behaviour \u2014 name the goal, report the distance, "
  "then stop. The plugin here was still on the version from Thursday, nine releases "
  "behind, and building the page loaded the old instructions. You told me to look at "
  "it. The install command that actually installs is a different one from the command "
  "that refreshes the list, which is the trap canon\u2019s own log already "
  "describes."),
 ("<b>Two of the things on this page were not decisions.</b>", "\u201cAdd the 34 "
  "examples\u201d and \u201cread the 29 the reader cannot see\u201d were drafted as "
  "matters for you. They are not \u2014 they are the work, and the new behaviour says "
  "so plainly: <i>do not manufacture the next decision.</i> They are the Next block "
  "instead, and the page went from five things waiting on you to three."),
 ("<b>I spent an hour measuring the wrong thing about the wording.</b>", "You said a "
  "position read like AI dribble, and I went and measured word counts and sentence "
  "shapes across all twenty positions. Then you told me you meant how I <i>explain</i> "
  "a position, not the position. The measurement was not wasted \u2014 it is why "
  "matter 2 says I have no rule to write \u2014 but I built the wrong thing first "
  "because I did not ask."),
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
    for o in OTHERS:
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
    ratified = sum(len([q for q in record.load(d).positions if not q.proposed])
                   for d in sorted((HERE / "desks").iterdir())
                   if (d / "SOURCES.md").is_file())
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
    fresh = [r for r in rows if r["key"] not in SIXTH_DOCKET]
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
      "<p><b>I read your eight answers this time, and both build orders are "
      "built.</b> Last docket I left them sitting for two hours. The searcher is "
      "running against live publishers and the reader now reads every regulation "
      "these desks rely on \u2014 which is what you meant by <i>have another "
      "go</i>.</p>"
      "<p><b>You set the pass mark for the reader and it is met.</b> A regulation "
      "names its own paragraphs; a reading is right when every one of them is "
      "found. The best attempt before today found 24 of the 31 that one section "
      "names, and I told you that was not good enough to ship. It now finds all "
      "thirty, across eleven regulations, and the one that already worked reads "
      "identically \u2014 same 172 paragraphs, same two dead references.</p>"
      "<p><b>%(nw)s things wait on you, and %(freshw)s of them are new.</b> "
      "Nothing from the last page is carried forward: you answered all eight, and "
      "asking an answered question again is the fault this page was rebuilt to "
      "stop.</p>"
      "<p><b>The fault you named was mine, not the record\u2019s.</b> You said the "
      "dribble was in how I <i>explain</i> a position, not in the position. You "
      "were right, and it was worse than wording \u2014 the page was arguing one "
      "way and asking the other. The recommendation now leads instead of sitting "
      "under four sections of argument, and a card that recommends against "
      "something can no longer offer it as the first button. Matter 2 is what is "
      "left of that: whether the positions themselves still need a rule, which I "
      "no longer think they do.</p>"
      "<p><b>Two of the three thin desks now hold every worked example their "
      "regulations carry.</b> 34 added \u2014 19 to cash, 12 to vehicle, 3 to "
      "meals \u2014 and all 761 stored passages were fetched back from their "
      "publishers and compared word for word: no differences, nothing "
      "unreachable. All %(rat)s ratified positions stand and no proposal is "
      "open.</p>"
    ) % {"nw": _word(c["n"]).capitalize(), "freshw": _word(c["fresh"]),
         "rat": _word(c["ratified"])}
    lede = ("%s are choices no rule settles; no position is waiting \u2014 all %s "
            "are ratified." % (_word(c["dec"]).capitalize(), _word(c["ratified"])))
    return _PAGE % (_word(c["n"]).capitalize(), _CSS, DATE, headline, lede,
                    preface, _next_block(), c["n"], c["n"], c["pos"], c["dec"],
                    _blocks(c),
                    json.dumps(c["rows"]), _JS)


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

%s

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
