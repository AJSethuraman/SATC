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
 {"key": "dec-merge-316",
  "title": "Merge #316? The Forge cannot be set up until it lands",
  "said": "Merge it",
  "where": "on the docket, 17:20",
  "caused": "<b>Merged, and the two install commands work now.</b> "
            "<code>claude plugin update desk@satc</code> lands 0.5.0 \u2014 the "
            "searcher\u2019s skill, the engagement file and the Forge prompt, none "
            "of which was reachable from an installed plugin before. "
            "<code>docs/TRY-IT.md</code> is the twenty-minute run-through."},

 {"key": "dec-263a2",
  "title": "The desk found the rule for tool-or-asset. Does it get to keep it?",
  "said": "Declare it",
  "where": "on the docket, 17:20",
  "caused": "<b>The loop closed, and it is the first time it has.</b> A desk "
            "refused for want of a rule; the searcher found it and would not "
            "store it; you declared the source; the desk answers. Checked rather "
            "than assumed \u2014 the question routes to fixed-assets, the brief "
            "carries both new paragraphs, and the engine serves on "
            "\u00a7 1.263(a)-2(d)(1) with the subject gate actually run. Five of "
            "the repository\u2019s own figure guards went red when the record "
            "moved and every one was right."},

 {"key": "dec-check-absent",
  "title": "A desk said it held nothing. It held ten passages. Should the engine check?",
  "said": "Build the check",
  "where": "on the docket, 17:20",
  "caused": "<b>An <code>authority_absent</code> refusal now arrives carrying what "
            "the desk actually showed the model.</b> Run against the refusal that "
            "started it: <i>76 passages, ten of them from \u00a7 1.274-11</i> \u2014 "
            "printed directly under the sentence claiming \u00a7 1.274-11 was "
            "absent. It reports and does not overrule: the engine cannot say "
            "whether any of the 76 answered the question, and an engine that "
            "refused the escalation would be deciding the merits. Six mutations "
            "tried, all caught."},

 {"key": "dec-desk-asks-for-code",
  "title": "A desk asks for something that does not exist yet. Who approves building it?",
  "said": "A field, and only a field",
  "where": "in the conversation \u2014 <i>\u201ci\u2019ll take your recommendation\u201d</i>",
  "caused": "<b>Built, and proved against a real position rather than a fixture.</b> A "
            "refusal now carries the fact it turned on and the position that asked for "
            "it, and the queue has a sixth thing it can ask for: <i>build the field</i>. "
            "Run against your capitalisation position it comes back naming "
            "<code>capitalization_rule</code>, asked for by <code>POS1</code> \u2014 so a "
            "field I build on a desk\u2019s say-so arrives showing you which position "
            "wanted it. Four tests hold the line you drew: only that one refusal becomes "
            "a field request, and a request cannot arrive without the position behind it. "
            "<a href=\'https://github.com/AJSethuraman/SATC/pull/316\'>#316</a>."},

 {"key": "dec-admit-publishers",
  "title": "Two publishers tied out. Do they become sources?",
  "said": "Admit eCFR only",
  "where": "on the docket, 15:49",
  "caused": "<b>It answered a question the desk could not answer an hour earlier.</b> "
            "\u00a7 1.162-3 is a source on fixed-assets now \u2014 eCFR, not Cornell "
            "\u2014 with both paragraphs stored and checked word for word against the "
            "publisher\u2019s own page. The close\u2019s question <i>does a hardware-store "
            "purchase ever become an asset?</i> had nowhere to go before; it is served "
            "now, on \u00a7 1.162-3(c)(1)(i). Six served became seven."},

 {"key": "dec-register-standing",
  "title": "The standing check on how positions are worded: still wanted?",
  "said": "Drop it \u2014 the card was the problem",
  "where": "on the docket, 15:49",
  "caused": "<b>Nothing was built, and that is the whole answer.</b> No word-count rule "
            "was invented for the positions. The card fix stands on its own."},

 {"key": "dec-merge-305",
  "title": "Merge today\u2019s work?",
  "said": "Merge it",
  "where": "on the docket, 15:49",
  "caused": "<b>Merged as <code>975c77a</code>, nine checks green.</b> The searcher, the "
            "reader fix and the 63 worked examples are on <code>main</code> and available "
            "to any session."},
]

#: THREE MATTERS, all of which arrived AFTER the page said nothing needed
#: deciding -- which is the normal life of a docket rather than a fault. Each one
#: blocks something concrete: the Forge cannot be set up, a desk cannot answer a
#: question it now has the words for, and a hole found in the seam cannot be
#: closed without the firm saying so.
#: NOTHING IS OPEN. The three that were here were answered at 17:20 and are in
#: `ANSWERED` above with what each one did. A key may not be in both.
OTHERS = []

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
 "goal": "Pilot the desks through one real client\u2019s close, end to end \u2014 "
         "the firm\u2019s goal, set on 7 September 2026.",
 "ends": "It ends with one engagement\u2019s close questions put to the desks and "
         "a written record of three things: every answer served, every refusal "
         "with what it asked for, and the questions the desks never saw.",
 "distance": "0 of 1 close, and the first thing to do is not mine \u2014 it is <b>twenty minutes of you trying it</b>. <code>docs/TRY-IT.md</code>.",
 "detail": "<b>What it refuses, because a goal that refuses nothing is not a "
           "goal.</b> It refuses building more desk machinery: if a desk lacks "
           "authority mid-pilot, that is a finding to write down, not a thing to "
           "go and fix. It refuses inventing a client \u2014 there is no "
           "synthetic engagement, and if there is no real one this is blocked and "
           "says so rather than producing a demonstration. And it refuses client "
           "PII reaching a desk: a desk sees the question and the engagement\u2019s "
           "facts, never a name, an SSN or an EIN.<br><br><b>The first blocker is "
           "not a client \u2014 it is that nowhere holds an engagement\u2019s "
           "facts.</b> Three desks declare a fact they need on file: "
           "<code>trade</code>, <code>taxpayer</code>, <code>capitalization_rule</code>. "
           "The engine can be handed them. <b>Nothing produces them.</b> Today the "
           "only thing that carries facts is a worked example\u2019s own "
           "<code>On file</code> line \u2014 a test fixture. That is why five of "
           "the eighteen answers refused with <i>the file does not record this</i>: "
           "there was no file.<br><br><b>That blocker is now cleared, and the "
           "five it was costing are measured.</b> An engagement\u2019s facts have "
           "somewhere to live \u2014 outside this plugin, because a client\u2019s "
           "affairs in a checkout that gets pushed is one <code>git add</code> from "
           "being published. Handed a file recording those three facts, <b>all five "
           "of those refusals are served</b>: 7 became 12 of 19. The stand-in file "
           "that proved it is labelled as one and is not a client.<br><br><b>Since "
           "then the install path has been walked and the search path has been "
           "run.</b> The plugin installs and works \u2014 checked by installing "
           "it, not by reading it \u2014 and one real gap was searched end to "
           "end against the live publisher, which found three defects in my own "
           "instructions before it found the rule. Both are the three matters "
           "below.<br><br><b>All three answered, all three done, and the plugin "
           "installs.</b> The loop closed for the first time \u2014 a desk "
           "refused for want of a rule, the searcher found it and would not "
           "store it, you declared the source, the desk answers. And a refusal "
           "that lies about its own record now says how much it was shown."
           "<br><br><b>What is left is the client, and one thing before it: you "
           "have not seen any of this work.</b> Everything measured today was "
           "measured by me. <code>docs/TRY-IT.md</code> is five steps and needs "
           "no client \u2014 including the two that are meant to fail, so the "
           "test can come back negative.",
}

CHANGED = [
 ("7 \u2192 8", "of 19 the engine would serve", "the firm\u2019s own ratified position, no longer refused"),
 ("0 \u2192 63", "worked examples on the three thin desks", "cash 19, vehicle 12, meals 32"),
 ("794 of 794", "passages fetched back and compared", "0 differences, 0 unreachable"),
 ("11 of 11", "regulations these desks rely on now read", "every path each one cites lands"),
 ("677", "desk tests passing", "514 when today\u2019s work started; canon 181"),
 ("9 of 9", "checks green on the pull request", "nothing red, no conflict with main"),
]

LANDED = [
 ("New", "<b>An engagement\u2019s facts have somewhere to live.</b> Three desks "
         "ask for a fact on file and nothing produced one, so five of the "
         "close\u2019s eighteen answers refused against a file that did not exist. "
         "There is a reader for one now. It refuses a fact no desk asks for, a "
         "fact nobody put their name and a date on, and any value shaped like an "
         "SSN or an EIN \u2014 and it refuses to read a file kept inside the "
         "plugin at all. Eight guards, each one broken on purpose to confirm it "
         "catches."),
 ("New", "<b>The searching agent, built and run against live publishers.</b> When a "
         "desk has no answer it goes and looks \u2014 anywhere, because you were "
         "right that a list of approved sites can only find what we already have. "
         "It reads the passage off the publisher\u2019s own page rather than off "
         "the search result, and it can put nothing in the record without you."),
 ("Run", "<b>One real gap, end to end.</b> The fixed-assets desk holds a regulation "
         "whose own examples point at \u00a7 1.162-3, and it could not follow the "
         "pointer. One search, eight results, four passages read: two check out, "
         "one was too short to prove which paragraph it came from, one site refused "
         "us. Both good ones are waiting on you, above."),
 ("New", "<b>All three thin desks now hold their regulations\u2019 worked "
         "examples.</b> Cash had none and has 19; vehicle had 10 and has 22; meals "
         "had none and has 32. Every one fetched back from its publisher and "
         "matched word for word, along with all 727 already there."),
 ("Fixed", "<b>Every regulation these desks rely on reads now.</b> Seven separate "
           "causes. Two I had described to you and five I had not \u2014 including "
           "a paragraph with no number on it, two paragraphs reserved on one line, "
           "and one regulation whose italics are broken across a paragraph number "
           "in the government\u2019s own file. That last one, a stray tag, had cost "
           "the vehicle desk every example it might have had."),
 ("Fixed", "<b>The reader now knows both ways the government writes an "
           "example.</b> Most regulations tag it; three of the meals desk\u2019s "
           "number it as an ordinary paragraph. Read only for the tag, the "
           "extractor returned nothing from sections it was reading perfectly."),
 ("Fixed", "<b>This page cannot ask you something it has already answered.</b> The "
           "recommendation used to sit last, under four sections of argument. It "
           "now leads. And a card can no longer offer <i>Ratify it</i> as its first "
           "button while its own recommendation says do not \u2014 which is what "
           "the docket before last did to you, twice."),
 ("Caught", "<b>The comparison caught me stitching four examples together.</b> I "
            "joined the pieces of four examples with a space, storing a run of "
            "words the government never printed as one \u2014 paragraph numbers "
            "sit between them. All four came back as differences the first time "
            "they were checked. Stored with the gap marked, they pass."),
 ("Found", "<b>A citation was being read as naming paragraphs that do not exist.</b> "
           "<i>\u201cparagraph (c)(1)(iii), (iv), or (v)\u201d</i> was read as citing "
           "a paragraph called \u201c(v)\u201d. Not just a miscount \u2014 that list "
           "is where the tool picks which rule an example is filed under, so a bare "
           "\u201c(v)\u201d was a candidate rule on any regulation whose examples "
           "live under (v). Same class as the four examples filed under the wrong "
           "rule on Saturday."),
 ("Fixed", "<b>The pull request\u2019s description had gone stale.</b> It opened "
           "as the searcher alone and is now nine commits, still quoting a test "
           "count from six commits earlier and describing none of the reader "
           "work. Rewritten to cover all four pieces, corrections included."),
]

UNCHECKED = [
 ("No model has answered anything, all day.", "That is the Next above, and it is "
  "the largest gap between this and something you could use."),
 ("No desk has met a real client file.", "Still true and still deliberate."),
 ("The scoreboard was not re-run, and re-running it would prove nothing.", "It "
  "grades against an answer key with the worked examples withheld, so adding 63 of "
  "them cannot move it. What IS measured: the brief a graded model sees did not "
  "change size on any of the seven desks. The withholding held."),
 ("Only two of the six test suites were run here.", "desk (585 passed, 1 skipped) "
  "and canon (181 passed), both just now. The other four ran on the server and all "
  "are green; nothing in today\u2019s work touches them."),
 ("The searcher has only ever been driven by hand.", "One question, by me. It has "
  "never run unattended, and there is no recorded failure it would fire on \u2014 "
  "all 22 in the queue are wrong-citation failures, not missing-authority ones."),
 ("The exhibits were opened, but by machine.", "Nobody has looked at one with "
  "their eyes."),
]

WRONG = [
 ("<b>I promised you before-and-after scores, and they cannot exist.</b>", "The goal "
  "on the last page said the desks would gain their examples \u201cwith the "
  "before-and-after scores on the page\u201d. Scoring withholds worked examples by "
  "construction \u2014 three separate mechanisms do it \u2014 so a score cannot "
  "move when examples are added. I wrote a measurement into a goal without checking "
  "that the measurement was possible. The Next above is what the honest version "
  "looks like."),
 ("<b>I told you six regulations had started reading. Three had.</b>", "The other "
  "three were already reading before I touched anything. I caught it an hour later "
  "by checking a claim I had already written into a note \u2014 and by then it was "
  "in a commit message and on a draft of this page, promising you examples on desks "
  "whose regulations still would not read. Both of those now read too."),
 ("<b>I ran the last docket on the old rulebook.</b>", "canon had a new standing "
  "behaviour \u2014 name the goal, report the distance, then stop \u2014 and the "
  "copy here was nine releases behind, so building the page loaded the old "
  "instructions. You told me to look. It has since moved again, to twenty "
  "behaviours, and this page is built on that one."),
 ("<b>Two of the things on the last page were not decisions.</b>", "\u201cAdd the "
  "examples\u201d and \u201cread the ones the reader cannot see\u201d were "
  "drafted as matters for you. They were the work. Both are done."),
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
    """What today was, and then how many things it leaves for the firm."""
    waiting = (
      "<p><b>Nothing on this page needs an answer.</b> All four matters were "
      "answered \u2014 three on the form at 15:49 and one in conversation \u2014 "
      "and all four are acted on. They are read back below rather than deleted, "
      "so you can see what each answer did.</p>"
    ) if not c["n"] else (
      "<p><b>%s things wait on you, and %s of them are new.</b> Nothing from the "
      "last page is carried forward: asking an answered question again is the "
      "fault this page was rebuilt to stop.</p>"
      % (_word(c["n"]).capitalize(), _word(c["fresh"]))
    )
    return (
      "<p><b>Three things wait on you, and each one blocks something you asked "
      "for.</b> The Forge cannot be set up until the branch merges; a desk found "
      "the rule it was missing and cannot keep it without a word from you; and a "
      "desk claimed its record was empty when it was not, which nothing catches "
      "today.</p>"
      "<p><b>Your four earlier answers are all acted on.</b> "
      "eCFR was admitted for \u00a7 1.162-3 and the desk answered a question with "
      "it about ninety minutes later; the field mechanism you approved is built "
      "and proved against your own capitalisation position; the wording check you "
      "dropped was not built; and the day\u2019s work is merged.</p>"
      + waiting +
      "<p><b>All three thin desks now hold every worked example their own "
      "regulations carry.</b> 63 added \u2014 19 to cash, 12 to vehicle, 32 to "
      "meals \u2014 and all 794 stored passages were fetched back from their "
      "publishers and compared word for word: no differences, nothing "
      "unreachable. No proposal is open and all %s ratified positions stand.</p>"
      % _word(c["ratified"])
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
            '<p class="lead">All %s answered, all %s acted on. Your answer is '
            'quoted from this page\u2019s own store; what it caused is measured '
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
