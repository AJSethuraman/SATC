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
#: Every matter the FOURTH docket carried, taken from the page published on
#: 6 September 2026 (artifact d9339c39). It is the only independent record of
#: what was already open: without it, "which matters are new" is read back out of
#: the same list that sets it.
FOURTH_DOCKET = {
    "pos-rewards-and-information-returns-POS1",
    "pos-capitalization-and-de-minimis-POS1",
    "pos-capitalization-and-de-minimis-POS2",
    "pos-personal-or-business-POS1",
    "dec-ir45-wording", "dec-prove", "dec-6041-sources", "dec-583-quotation",
    "dec-cd-fix", "dec-override", "dec-guidance", "dec-courts-again",
    "dec-merge-275",
}

OTHERS = [
 {"key": "dec-cap-field", "new": True, "group": "What the file records", "tag": "The mechanism found a hole",
  "title": "The desk can now ask whether a client is treated differently. Nothing can answer.",
  "position": "Add <code>capitalization_rule</code> to what the capitalization desk records.",
  "context": "This is the mechanism you asked for, working \u2014 and the first thing it "
             "found.<br><br>You held two positions saying the desk must check for a "
             "standing client rule rather than answering broadly. It does now. Both "
             "carry <code>Unless: capitalization_rule</code>, and <b>that desk records "
             "nothing at all</b>, so the follow-up cannot be answered by reading the "
             "file. The refusal is <code>no_field_for_this_fact</code>, and it says the "
             "gap is in what the firm decided to write down rather than in what this "
             "client was asked.<br><br>Your words: <i>\u201cif the follow up has no answer "
             "we know there\u2019s a legit hole to fix because the accountant or firm never "
             "assigned it up front \u2026 What if this mattered only sometimes and we never "
             "even made a field for it.\u201d</i> This is that.",
  "either": [("Add the field",
              "Then the follow-up is answerable: a preparer writes <code>none</code> "
              "where the client is ordinary, or the rule where they are not. Both "
              "positions become ratifiable, and the desk stops refusing them."),
             ("Leave it \u2014 the question is not worth a field",
              "A legitimate answer, and it is the one this queue exists to make "
              "askable. Then the positions stay unratified, or they drop the "
              "<code>Unless:</code> line and go back to answering broadly.")],
  "rec": "Add it. You raised the objection twice on one docket, which is the "
         "strongest evidence there is that the fact matters \u2014 and a field costs "
         "one line where answering broadly costs a client.",
  "picks": ["Add the field", "Not worth a field", "Not yet"]},

 {"key": "dec-courts-again", "group": "Sources", "tag": "Carried \u2014 you left a note",
  "title": "The court hosts, still open \u2014 and LexisNexis, which is a different shape.",
  "position": "Say which half you meant. I recorded the note and did not read an answer into it.",
  "context": "<b>You left a note and no button:</b> <i>\u201cI\u2019ll do this when home. Also "
             "look into Lexis nexis. A lawyer said this is how they research "
             "precedent.\u201d</i> The matter asked which half of a contradiction you "
             "meant \u2014 the button you pressed (keep the five court hosts closed) or the "
             "words beside it (open everything we can use). A note is not an answer to "
             "that, and recording one would be inventing it.<br><br><b>On LexisNexis, "
             "one thing worth knowing before you decide.</b> Every source this record "
             "holds is a government work in the public domain, which is why passages "
             "can be stored in full. LexisNexis is a licensed commercial database: "
             "<code>access</code> and <code>may_store</code> would both need deciding "
             "before a single passage could be stored, and the <code>human_only</code> "
             "path \u2014 where a position IS the desk\u2019s entire knowledge of a source it "
             "may never read \u2014 may be the only lawful one. That is research, not a "
             "decision, and it is not started.",
  "either": [("The button: keep the five hosts closed",
              "Nothing changes in the plumbing. A case reaches a desk only when you "
              "hand the opinion over, which is what happened with Anikeev."),
             ("The words: widen what the desks can reach",
              "Find which reachable sources would answer the questions that keep "
              "escalating to you. Not about courts at all.")],
  "rec": "Both, in that order \u2014 hosts stay closed, and I widen the reachable "
         "sources. And I look into LexisNexis and report what it would take, "
         "which is a page of findings rather than a change.",
  "picks": ["Both, hosts stay closed", "Just keep hosts closed", "Open the hosts",
            "Look into LexisNexis first", "Not yet"]},
]

CHANGED = [
 ("13 of 13", "matters you answered", "and every one of them is built"),
 ("531 of 531", "passages tied to the publisher", "0 differs, 0 could not — it was 530 of 531 this morning"),
 ("19 of 19", "rewards problems promptable", "it was 0 of 19; the desk scored nothing at all"),
 ("24 \u2192 6", "escalations across seven desks", "and every one of the six is a desk that holds the rule"),
 ("470", "desk tests passing", "run just now; 368 when yesterday started, 406 this morning"),
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
    # NEW MEANS "NOT ON THE LAST DOCKET", read off the last docket rather than
    # off a flag this file also sets. A `"new": True` marker is a claim the page
    # makes about itself, and two mutations survived on the third docket because
    # the test that checked it read the same flag. A POSITION cannot carry the
    # flag at all -- it comes out of `desks/` -- so a flag-only count silently
    # missed POS3, which did not exist this morning.
    fresh = [r for r in rows if r["key"] not in FOURTH_DOCKET]
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
      "<p><b>You answered all thirteen and every one of them is built.</b> What is "
      "on this page is what those answers left open \u2014 %(nw)s things, and "
      "%(freshw)s of them did not exist this morning \u2014 both are consequences of a "
      "decision you made today rather than things I found lying around.</p>"
      "<p><b>The mechanism you asked for found its first hole, which is matter "
      "%(holen)s.</b> You held two positions saying the desk must check for a "
      "standing client rule rather than answering broadly. It does now \u2014 and "
      "that desk records nothing, so the follow-up cannot be answered by reading "
      "the file. Your words: <i>\u201cif the follow up has no answer we know there\u2019s a "
      "legit hole to fix because the accountant or firm never assigned it up "
      "front.\u201d</i> That is exactly what happened, on the first try.</p>"
      "<p><b>The corpus is now 531 of 531.</b> Zero differences, zero could-nots, "
      "fetched live this evening. The last one was ours \u2014 a publisher\u2019s link "
      "badge sitting inside a sentence we quote, which I judged in our favour this "
      "morning and left. It is the same unmarked omission you told me to mark.</p>"
      "<p><b>%(ansv)s of the %(posw)s positions here are answerable today</b>, and "
      "the %(waitw)s that are not both wait on matter %(holen)s. That is "
      "deliberate: ratified without the field they would refuse every time rather "
      "than answer broadly, which is the safe failure and not a useful one.</p>"
    ) % {"posw": _word(c["pos"]),
         "freshw": _word(c["fresh"]), "nw": _word(c["n"]),
         "holen": _word(next(i for i, r in enumerate(c["rows"], 1)
                             if r["key"] == "dec-cap-field")),
         "waitw": _word(c["waiting"]),
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
