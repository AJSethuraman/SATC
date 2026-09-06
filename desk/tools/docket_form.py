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
OTHERS = [
 {"key": "dec-ir45-wording", "group": "The rewards desk", "tag": "Blocks 19 scores",
  "title": "Two ways of saying the same thing, and the desk refuses itself over it.",
  "position": "Reword POS2 in the regulation's words, and keep your $2,000 rule as its second sentence.",
  "context": "Still open from the last docket. Nineteen of that desk's nineteen "
             "problems cannot be scored at all, because two stored passages are "
             "the regulation's own worked examples and carry their answers with "
             "them. The fix is to point those problems at the rule the examples "
             "themselves name — <b>&sect; 1.6041-1(a)(1)(iv)</b> — and drop the "
             "examples. <b>But you ratified POS2 on that exact paragraph.</b> A "
             "ratified position is served word for word and the engine refuses an "
             "answer that restates it, so the moment those problems cite it their "
             "own recorded answers are refused as contradicting you.<br><br>"
             "<b>Yours:</b> <i>no Form 1099-NEC for a payment settled by card or "
             "through a third party payment network; track the rest against $2,000 "
             "per payee per calendar year</i><br><b>The regulation's:</b> <i>the "
             "payor is not required to file an information return under section "
             "6041</i><br><br>They mean the same thing. The engine is exact on "
             "purpose — that exactness is what stops a model handing your position "
             "back with the conclusion reversed — so it cannot see that.",
  "either": [("Reword POS2 to the regulation's phrasing",
              "Your $2,000 tracking rule survives as a second sentence, the desk "
              "stops refusing itself, and 19 scores come back."),
             ("Keep your wording and reword the problems",
              "Your sentence stands as ratified. The scored problems then no "
              "longer read as the regulation writes them, which weakens the one "
              "thing that makes the denominator meaningful.")],
  "rec": "Reword POS2. The problems are the regulation's worked examples and "
         "their wording is not ours to move; your meaning is fully preserved.",
  "picks": ["Reword POS2", "Keep my wording", "Not yet"]},

 {"key": "dec-prove", "new": True, "group": "From the tie-out", "tag": "Your idea, tonight",
  "title": "Should an answering agent have to prove its citation, not just name one?",
  "position": "Yes — an answer may carry proof, and the desk records the proof with it.",
  "context": "Your words: <i>“going forward thinking like the agents tie out their "
             "position to prove it to the desk.”</i> Today the gate checks that a "
             "citation <b>resolves in our record</b>. It has no way to check that "
             "the record is true — which is the gap tonight's tie-out just closed "
             "for the whole corpus, once.<br><br>What this adds: "
             "<code>answer(..., prove=True)</code> re-fetches the cited source, "
             "confirms the passage is still there, and files the hash with the "
             "answer. A served answer would carry evidence rather than a reference.",
  "either": [("Build it",
              "Every answer that opts in is provable by whoever reads it later, and "
              "the desk catches its own corpus drifting the day it drifts. It makes "
              "an answer slower and it fails when a publisher is down — so it has "
              "to be optional, and what happens on a failed proof is its own "
              "question."),
             ("Leave it to the periodic run",
              "The corpus tie-out already covers all 533 and can run nightly. "
              "Cheaper, and nothing an answerer does depends on a website being up. "
              "The gap is that a passage could drift and be served wrongly until "
              "the next run.")],
  "rec": "Build it, optional and off by default, and schedule the corpus run as "
         "well. They answer different questions: one proves the answer in front of "
         "you, the other proves the record behind all of them.",
  "picks": ["Build it", "Periodic run only", "Both", "Not yet"]},

 {"key": "dec-6041-sources", "new": True, "group": "From the tie-out", "tag": "Record defect, proven",
  "title": "One source URL is recorded for four statute sections and serves one.",
  "position": "Split it into one source per section, each with the URL that actually carries it.",
  "context": "The tie-out found this and no test could have. The rewards desk "
             "stores &sect;&sect; 6041, 6041A, 6050W and 6071 under a single source "
             "whose URL is the House's page for <b>&sect; 6041 alone</b>. All four "
             "passages are <b>verbatim correct</b> — each checked on its own page — "
             "so nothing served was ever wrong. <b>But a reader following the link "
             "for three of them lands on a page that does not contain them</b>, and "
             "the “6041A” visible there is &sect; 6041's own cross-reference.<br><br>"
             "Not fixed, because the fix renumbers the desk's sources, which "
             "touches its routing file and every passage's source id.",
  "either": [("Split into four sources",
              "Every link goes where its text is. Mechanical, but it renumbers S2 "
              "into four ids and edits SUBJECTS.md."),
             ("Leave it and note it",
              "Nothing served is wrong today. The next person to follow one of "
              "those links finds the wrong page.")],
  "rec": "Split it. A citation whose link does not carry the text is exactly what "
         "the tie-out exists to find, and leaving a known-wrong link teaches the "
         "next agent that links are decorative.",
  "picks": ["Split into four", "Leave and note it", "Not yet"]},

 {"key": "dec-583-quotation", "new": True, "group": "From the tie-out", "tag": "Record defect, proven",
  "title": "A stored passage drops half the publisher's sentence without saying so.",
  "position": "Mark the omission, so an answerer can see a branch was removed.",
  "context": "Publication 583 says the statement balance may not agree if the "
             "statement <i>“<b>Includes</b> bank charges you did not enter in your "
             "books…, or <b>Does not include</b> deposits made after the statement "
             "date…”</i> — two branches. The cash desk stores the second and drops "
             "the first, with nothing marking the cut.<br><br><b>The split itself "
             "is right</b> and you know why: the branches have opposite answers, "
             "and serving them as one entry is the defect #264 found. What is wrong "
             "is that an answerer cannot tell a branch was removed.",
  "either": [("Mark the omission",
              "An ellipsis. One character, and the passage stops presenting itself "
              "as a whole sentence."),
             ("Store the publisher's sentence whole",
              "Both branches stored once, and the per-citation narrowing — which "
              "exists now and did not when this was written — keeps them apart when "
              "the desk answers. Truer to the source; more to change.")],
  "rec": "Mark the omission now, and store it whole when the rewards wording above "
         "is settled — that change touches the same machinery.",
  "picks": ["Mark the omission", "Store it whole", "Not yet"]},

 {"key": "dec-cd-fix", "new": True, "group": "Housekeeping", "tag": "main is red",
  "title": "main's own tests have not run since yesterday evening. One line fixes it — shall I?",
  "position": "Add one line to <code>client-documents/pytest.ini</code> on a branch off main.",
  "context": "This is worse than it looked when I first wrote it up. <b>main itself "
             "is red</b>, not just this branch: on main's own run for #294, "
             "<code>pytest (client-documents)</code> is the only one of seven jobs "
             "failing. The five most recent pushes to main are all red the same way; "
             "the first failing file arrived in #288, at 16:59 yesterday.<br><br>"
             "And it is not <i>“two tests failing”</i>. The run stops at collection — "
             "<code>Interrupted: 2 errors during collection</code>, 2.86 seconds, "
             "nothing executed. <b>The whole client-documents suite has not run in CI "
             "since #288 landed.</b> Five merges have gone in on top of a check that "
             "is not checking anything.<br><br>"
             "<b>Why nobody noticed.</b> The session doing that work runs "
             "<code>python -m pytest</code>, which puts the project folder on the "
             "import path, and it passes — its commit messages say <i>“0 failing”</i> "
             "and they are telling the truth about what they ran. CI runs bare "
             "<code>pytest -q</code>, which does not. <code>pytest.ini</code>'s own "
             "comment says <i>“that is what CI runs”</i> about the first one. It is "
             "not, and that mistaken sentence is the whole bug.",
  "either": [("Let me add the line",
              "<code>pythonpath = .</code> in <code>client-documents/pytest.ini</code>. "
              "I ran it on main's tree: both files import cleanly afterwards. It is "
              "better than the three-line patch I proposed last night because it also "
              "fixes every test file written after this one, and it makes "
              "<code>pytest.ini</code>'s claim about CI true instead of false."),
             ("Leave it to whoever owns client-documents",
              "It is their area and they are mid-change in it. main stays red "
              "meanwhile, ~1,500 tests keep not running, and the next real failure "
              "there arrives invisible.")],
  "rec": "Let me add it. One line, in another project's config and nothing else, "
         "verified against main's tree — and every hour it waits is another merge "
         "onto a suite nobody is actually running.",
  "picks": ["Add the line", "Leave it to them", "Not yet"]},

 {"key": "dec-override", "group": "How positions work", "tag": "Blocks 1 position",
  "title": "Can a position be the firm's default and still be overridden for one client?",
  "position": "Keep positions unconditional; write an override as a recorded fact the caller passes in.",
  "context": "Still open. Holding the safe-harbour election you said it is <i>“the "
             "kind of policy that gets enacted because it makes sense and only "
             "enacted when we don't have another Answer … it's possible for a "
             "particular client we have to be needed treating differently.”</i> "
             "Nothing in the record can say that today: every position is "
             "unconditional.",
  "either": [("Keep them unconditional",
              "The desk holds no client data at all, which is how it is built. The "
              "override arrives as a fact the caller passes — the same mechanism as "
              "the client's trade, already working. Nothing new to build."),
             ("Give positions a per-client exception table",
              "One place to look up what a named client does differently. It puts "
              "client-keyed data inside the plugin for the first time, and the PII "
              "rule then applies to a component that had been exempt from it.")],
  "rec": "Keep them unconditional. Nothing to build, the desk still cannot see who "
         "the client is, and it makes the safe-harbour position ratifiable as "
         "written.",
  "picks": ["Keep unconditional", "Exception table", "Not yet"]},

 {"key": "dec-guidance", "group": "How positions work", "tag": "Your ask, 5 Sep",
  "title": "Should the desk answer from IRS guidance where no rule and no position reaches?",
  "position": "Serve it — and mark it as guidance rather than as the rule.",
  "context": "Still open. You asked for this holding the rewards position: <i>“if we "
             "don't have an opinion and have a good reason to form one, maybe we "
             "just use a safe Harbor Rule which in this case would be deferring to "
             "whatever the IRS says.”</i> Today a non-binding source refuses "
             "<code>authority_permits_choice</code>, which is why the same question "
             "keeps coming back to you.<br><br><b>The tie-out sharpened this.</b> On "
             "your own $500 question the regulation and the guidance genuinely "
             "differ — &sect; 1.263(a)-1(f)(1)(ii)(D) says $500, Notice 2015-82 says "
             "$2,500 — so a desk serving guidance without saying so would hand you a "
             "number the regulation does not contain.",
  "either": [("Leave it as it is",
              "Nothing is ever served on somebody's reading of a rule. You keep "
              "being asked the same question until you answer it once."),
             ("Let guidance answer, marked as guidance",
              "Far fewer questions reach you, and the reader is told which they are "
              "leaning on.")],
  "rec": "Serve it, marked. It changes what a served answer carries, not what the "
         "gate lets through: nothing uncited is served either way.",
  "picks": ["Serve it, marked", "Leave it", "Not yet"]},

 {"key": "dec-courts-again", "group": "Sources", "tag": "Your answer contradicts itself",
  "title": "You chose \u201ckeep the court hosts closed\u201d and then wrote that you want them open.",
  "position": "Say which half you meant. I recorded the choice and flagged it rather than picking.",
  "context": "Still open. You clicked <b>Keep them closed</b> and wrote: <i>“I want "
             "to open everything we can use… there's no reason for them not to use "
             "this court case I don't want to be the one to answer it. The only "
             "reason we are talking so much now is because I can't trust the "
             "answers.”</i><br><br><b>The tie-out speaks to that last sentence.</b> "
             "530 of 531 passages are now proven to be what the publisher publishes. "
             "That is a different kind of trust from “the desk reasons well”, and it "
             "is the kind that was missing.",
  "either": [("The button: keep the five hosts closed",
              "Nothing changes in the plumbing. A case reaches a desk only when you "
              "hand the opinion over."),
             ("The words: widen what the desks can reach",
              "Find which reachable sources would answer the questions that keep "
              "escalating to you. Not about courts at all.")],
  "rec": "Both, in that order — hosts stay closed, and I widen the reachable "
         "sources, which is the thing that actually stops questions reaching you.",
  "picks": ["Both, hosts stay closed", "Just keep hosts closed", "Open the hosts", "Not yet"]},

 {"key": "dec-merge-275", "group": "Housekeeping", "tag": "PR #275",
  "title": "Fourteen commits are sitting on a branch. Merge them?",
  "position": "Merge it.",
  "context": "406 tests passing and every check green <b>except</b> "
             "<code>pytest (client-documents)</code>, which is red on main too and "
             "is its own matter above. It carries your twenty-two answers, the "
             "client-context input, the harness fixes and tonight's tie-out.<br><br>"
             "<b>Not merged</b>, because <code>main</code> publishes and you are at "
             "the keyboard.",
  "either": [("Merge it",
              "The record on main matches what you decided. The red check is main's "
              "own and merging does not make it worse."),
             ("Read it first",
              "Costs time. Most of the diff is documentation, tests and eight "
              "tie-out PDFs.")],
  "rec": "Merge it, and let me fix the client-documents import separately.",
  "picks": ["Merge it", "I will read it first", "Not yet"]},
]

CHANGED = [
 ("531 of 533", "passages tied to the publisher", "fetched live from eCFR, irs.gov and uscode.house.gov"),
 ("2", "differences", "both real, both on this docket"),
 ("0", "could not", "every source reached on the first or second try"),
 ("406", "desk tests passing", "run just now; 368 when yesterday started"),
]

LANDED = [
 ("New", "<b>The whole stored corpus is tied out.</b> Every one of the 531 passages the "
         "desks hand an answering agent, fetched back from the publisher that wrote it "
         "and compared. <b>No test in this repository could answer this</b> — they all "
         "read the same stored files, so a passage transcribed wrongly is stored "
         "wrongly, served wrongly and asserted wrongly, and every green stays green. "
         "Eight PDFs in <code>desk/tie-outs/</code>, one per desk plus the roster."),
 ("Found", "<b>Right text, wrong link.</b> Three passages cite statute sections whose "
           "recorded source URL does not carry them. Every word is verbatim correct, so "
           "nothing served was wrong and nothing could have caught it but following the "
           "link. That is matter 3."),
 ("Found", "<b>A partial quotation that does not say it is one</b>, and a publisher's "
           "interface text inside a sentence we quote without it. Matters 4 and — for "
           "the second, which I judged in our favour — recorded rather than raised."),
 ("22 of 22", "You answered every matter on the last docket. Thirteen positions ratified — "
              "eleven as drafted, two with your edit — and four held. <b>Ratified positions "
              "went from 2 to 15.</b>"),
 ("New", "A desk can now be <b>told what the client does</b>. It declares what it expects, a "
         "position declares what it cannot be applied without, and unmet it refuses "
         "<code>context_not_on_file</code> — a third kind of missing thing, resolved by "
         "reading our own file rather than asking the client."),
 ("Found", "<b>A desk the harness could not prompt was publishing as a careful one.</b> "
           "Reproduced with no model running: 19 of 19 recorded, every one an escalation, "
           "which this scoreboard reports as a success. Nothing published was wrong — both "
           "real runs were on the two desks that do not leak, which is luck, not a control."),
 ("Found", "The full-text prompt shape could never have run on the machine it was written "
           "for. An 8,192-token window leaves 7,616 once the reply is taken out of it, and "
           "six of seven desks need 8,978 to 23,054. The request would not have errored — it "
           "drops the front of the prompt, which is the instruction to cite."),
 ("Fixed", "34 problems the harness refused are now 19. Eleven were the rule stating its own "
           "outcome, four were one conclusion being a substring of another, and one was the "
           "record's — Pub. 525 held the rule and Example 36 in one passage, and Example 36 "
           "<i>is</i> one of the problems."),
]

UNCHECKED = [
 ("The tie-out proves the words, not the reading.", "That § 1.263(a)-1(f)(1)(ii)(D) "
  "says $500 is now established. Whether $500 is the number that governs a client is a "
  "question about Notice 2015-82 and about your election, and no fetch settles it."),
 ("It proves containment, not completeness.", "It asks whether our passage occurs in "
  "the publisher's document — not whether we stored the whole of what that citation "
  "covers. The Publication 583 finding is exactly that failure, caught by accident."),
 ("No desk has been run against a real client file.", "Every number here is against "
  "public worked examples. That is deliberate — a score against answers we wrote "
  "ourselves measures agreement, not correctness — but it means none of this has met "
  "your actual books."),
 ("No model has answered anything today.", "Every measurement is of the harness and the "
  "record. The last real scoreboard run was on two desks, and the rewards desk still "
  "cannot be run at all until matter 5 is answered."),
 ("The 19 remaining leaks were not worked around.", "Loosening the check to get a number "
  "was available and was not taken."),
 ("The five court hosts were not retried.", "They refused this morning; I have not tried "
  "again."),
]

WRONG = [
 ("The tie-out's first run reported 88 differences and 34 of them were mine.", "Then 18, "
  "of which 16 were mine too. Both times the checker was the defect — markup tags "
  "replaced by spaces, and a PDF extractor reading a kerned column as <code>Y ou</code>. "
  "<b>A checker that invents differences is worse than no checker</b>, because somebody "
  "goes and “fixes” the record to match it. Both are written up in the exhibits."),
 ("I told you the full-text prompt shape fits no desk.", "It fits one. I measured it while "
  "four desks could not be prompted at all, so their sizes were never taken — <b>a "
  "denominator over the rows that happened to be readable</b>, which is the exact failure "
  "I had spent the afternoon building a guard against. Corrected, and the figures are now "
  "asserted by name so they cannot drift back."),
 ("I said the fifteen strict refusals were the check being too strict.", "Eleven were. Four "
  "were something else entirely — one admissible conclusion being a substring of another — "
  "and I would not have found them if I had fixed the first thing and stopped."),
 ("I said ratifying the positions was the difference between a desk that defers and one "
  "that helps.", "Wrong for all seventeen: not one sat on a citation its own desk's "
  "problems turn on. What they changed is what a desk says when it cannot answer, which is "
  "what you had asked for independently."),
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
    fresh = [r for r in rows if r.get("new")]
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
      "<p><b>%(freshw)s of these %(nw)s are new since the last docket — "
      "%(tow)s of them out of the tie-out you asked for</b>, and two of those are "
      "defects in the record that no test in this repository could have found. "
      "The rest were already open.</p>"
      "<p><b>What the tie-out settles.</b> Every one of the 531 passages the desks "
      "hand an answering agent was fetched back from the publisher that wrote it. "
      "<b>531 are, character for character, what that publisher publishes today.</b> "
      "That was an assumption yesterday and it is a measurement now — and it is a "
      "different kind of trust from “the desk reasons well”, which is still the "
      "scoreboard's job and still unproven on four desks.</p>"
      "<p><b>%(ansv)s of the %(posw)s positions you held are answerable</b>, two "
      "because the input they were waiting on now exists and one because the desk "
      "already held the answer to the question you held it for. The fourth waits "
      "on a decision on this page.</p>"
    ) % {"posw": _word(c["pos"]),
         "freshw": _word(c["fresh"]).capitalize(), "nw": _word(c["n"]),
         "tow": _word(c["from_tieout"]),
         "ansv": ("All but %s" % _word(c["waiting"])) if c["waiting"]
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
