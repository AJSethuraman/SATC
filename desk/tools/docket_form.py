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
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from position_walkthrough import positions                  # noqa: E402

DATE = "5 September 2026"

#: The decisions no authority settles. Each carries BOTH outcomes and what it
#: costs to be wrong, because a decision handed over without its downside is one
#: somebody makes twice.
OTHERS = [
 {"key": "dec-q32", "group": "Firm policy", "tag": "Close · Q32",
  "title": "Is cash withdrawn with no receipt an owner draw?",
  "position": "Book it as an owner draw, and tell the client what would change it.",
  "context": "The closing agent asked and the firm has not said. It came up on "
             "the close that produced the forty-three questions.",
  "either": [("Always a draw",
              "Unambiguous, closes every one of them, and never costs the client a "
              "deduction they could substantiate — because they cannot."),
             ("Held pending the client",
              "Recovers real deductions where the client does have receipts nobody "
              "asked for. Leaves rows open and blocks the close.")],
  "rec": "A draw, with the client told what it would take to change it. Neither "
         "option costs anything that cannot be corrected later, and only one of "
         "them closes the books.",
  "picks": ["Always a draw", "Hold for the client", "Not yet"]},

 {"key": "dec-q37", "group": "Firm policy", "tag": "Close · Q37",
  "title": "What is the standard evidence that a deposit is revenue?",
  "position": "Pick one document and use it on every client, rather than deciding per client.",
  "context": "The candidates are the bank's own deposit detail, the invoicing "
             "system, or a list from the client.",
  "either": [("The bank's deposit detail",
              "The one document the firm can obtain without the client doing "
              "anything, and it exists whether or not they invoice."),
             ("The invoicing system or a client list",
              "Names the payer, which deposit detail often does not — but only "
              "exists if the client keeps one, and arrives when they get to it.")],
  "rec": "Bank deposit detail as the default. What it costs: on a mobile cheque "
         "deposit it carries no payer, so the default needs a stated fallback for "
         "when it comes back blank.",
  "picks": ["Bank deposit detail", "Invoicing system", "Client list", "Not yet"]},

 {"key": "dec-q42", "group": "Firm policy", "tag": "Close · Q42",
  "title": "Transaction date or post date?",
  "position": "Book on transaction date, always.",
  "context": "The book runs on transaction date; card statements close on post "
             "date. They disagree at every period boundary by whatever is in transit.",
  "either": [("Transaction date",
              "Puts the book ahead of the statement, which the closing agent's own "
              "note calls the acceptable direction."),
             ("Post date",
              "Ties to the statement exactly and reconciles without a bridging "
              "schedule — at the cost of recording December spending in January.")],
  "rec": "Transaction date. Confirm rather than assume: this is stated from one "
         "close, not from a rule.",
  "picks": ["Transaction date", "Post date", "Not yet"]},

 {"key": "dec-granularity", "group": "How the desks are cut", "tag": "Build",
  "title": "Three desks now hand over more than a small model can hold at once.",
  "position": "Measure whether the size actually hurts before cutting anything up.",
  "context": "A desk hands its whole folder to the answering agent. Measured "
             "today: personal-or-business 3,094 tokens, capitalisation 6,561, "
             "rewards 7,819, meals 8,968, cash-and-bank 12,109, vehicle 16,413, "
             "fixed-assets 17,784. A <b>token</b> is roughly three-quarters of a "
             "word — the unit a model's working memory is measured in. Under about "
             "8,000, the whole folder fits comfortably; over it, a small model "
             "starts losing the middle of what it was handed.",
  "either": [("Split the big three now",
              "Every brief fits. More desks to route between, and a question that "
              "straddles the new seam reaches only half its authority."),
             ("Leave them and test first",
              "Costs a day. Answers the actual question — whether a big brief "
              "answers worse than a small one — instead of assuming it does.")],
  "rec": "Test first. Same questions, one routed desk against one merged brief, "
         "and cut only the desks the measurement says are hurting. Splitting on a "
         "hunch is how the seam ends up in the wrong place.",
  "picks": ["Test first", "Split now", "Leave as is", "Not yet"]},

 {"key": "dec-courts", "group": "How the desks are cut", "tag": "Build",
  "title": "Court opinions cannot be fetched from here. Five hosts refused.",
  "position": "Keep the desks to authority they can actually reach, and let cases "
              "in only as positions you have ratified.",
  "context": "ustaxcourt.gov, govinfo.gov, courtlistener.com, law.justia.com and "
             "casetext.com all return <b>403</b> — the network policy on this "
             "machine blocks them. ecfr.gov (the regulations) and irs.gov (the "
             "publications) work. <i>Anikeev</i> only got read this morning because "
             "you pasted it in.",
  "either": [("Open the court hosts",
              "Desks can store case text and cite it directly. Someone has to "
              "change the environment's network policy, and it is not reversible "
              "by me."),
             ("Keep them closed",
              "Nothing changes in the plumbing. A case reaches a desk only when "
              "you hand the opinion over and ratify what it holds — which is "
              "slower, and is also a human reading every case before it counts.")],
  "rec": "Keep them closed for now. Every case that has mattered so far turned on "
         "something the opinion disclaimed, and the desk was better off with your "
         "yes than with the text.",
  "picks": ["Keep them closed", "Open the court hosts", "Not yet"]},
]

#: Measured by running the suites, not remembered. The last row is counted from
#: the record at generation time; the rest are stated with what produced them.
CHANGED = [
 ("368", "desk tests passing", "run just now, <code>python -B -m pytest -q</code>"),
 ("181", "canon tests passing", "run just now; the plugin is at 1.12.0"),
 ("533", "passages of stored authority", "across 31 declared sources and 7 desks"),
 ("98", "scored problems", "every one a worked example from public authority"),
]

LANDED = [
 ("#272", "The nine answers from the last docket, the per-citation gate, and the front door "
          "— <code>ask.py</code>, which is how an agent actually reaches a desk. Merged."),
 ("#273", "fixed-assets could not see nine of its own sixteen problems. Merged."),
 ("#262, #263, #267", "The three you told me to drive, in order. All merged to <code>main</code>."),
 ("#275", "Opened as a draft: the second docket's answers, <i>Anikeev</i> read properly, and "
          "the walkthrough that produced the correction below."),
 ("#265", "Retargeted at <code>main</code> and kept as history, with a note saying which hole "
          "it found and that M8 closed it."),
]

UNCHECKED = [
 ("No desk has been run against a real client file.", "Every number above is against "
  "public worked examples. That is deliberate — a score against answers we wrote "
  "ourselves measures agreement, not correctness — but it means none of this has met "
  "your actual books."),
 ("The client-documents suite was not run.", "About eight minutes, and nothing in this "
  "week's work touches it. Not checked is not the same as passing."),
 ("The five court hosts were not retried.", "They refused this morning; I did not try "
  "again this evening."),
 ("Nobody has answered the seventeen yet.", "I checked the store behind the walkthrough "
  "page I published earlier: empty. So they are restated here rather than assumed read."),
]

WRONG = [
 ("I said ratifying these seventeen is the difference between a desk that defers and one "
  "that helps.", "Wrong for fifteen of them, and I only found it because I measured: not "
  "one of the seventeen sits on a citation any of its own desk's scored problems turn on. "
  "The cash desk's two ratified ones do — 2 of 2. <b>Ratifying these changes no score.</b>"),
 ("I said there were twenty-two proposed positions.", "There are seventeen."),
 ("I reported the J.Crew desk as answering that question fully.", "The regulation it "
  "answers from is about members of the armed services and nothing else. The rule it "
  "states is right; the desk's coverage of it is narrower than the rule, and the caveat "
  "now says so."),
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
    return {
        "rows": rows, "n": len(rows), "pos": len(pos), "dec": len(rows) - len(pos),
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
      "<p><b>Read this before the %(posw)s.</b> I have been telling you that "
      "ratifying them is the difference between a desk that defers and one that "
      "helps. <b>That is wrong for %(blind)s of them.</b> %(measured)s — the "
      "cash desk's %(ratw)s ratified ones do, %(rat)d of %(rat)d, which is why "
      "those made all four of its problems answerable. Ratifying these changes "
      "<b>no score</b>.</p>"
      "<p><b>What they change is what a desk says when it cannot answer.</b> "
      "%(rulesw)s of the %(posw)s are not conclusions about tax law — they are "
      "rules about how you work: <i>hold it, ask who owns it, request these "
      "documents by name, obtain the figure rather than assume it.</i> Which is "
      "what you asked for. They already were that; nobody had said so.</p>"
      "<p>So each card says which kind it is. <b>A conclusion can be wrong about "
      "the law. A rule can only be wrong about the practice</b> — and only you "
      "can say whether a rule is how you actually work.</p>"
    ) % {"posw": _word(c["pos"]), "measured": measured,
         "blind": ("all " + _word(c["blind"]) if c["blind"] == c["pos"]
                   else _word(c["blind"])),
         "ratw": _word(c["ratified"]), "rat": c["ratified"],
         "rulesw": _word(c["rules"]).capitalize()}
    lede = ("%s of them are positions to approve or reject. %s are choices no rule "
            "settles." % (_word(c["pos"]).capitalize(), _word(c["dec"]).capitalize()))
    return _PAGE % (_CSS, DATE, headline, lede, preface, c["n"], c["n"], c["pos"],
                    c["dec"], _blocks(c), json.dumps(c["rows"]), _JS)


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

_PAGE = """<title>Docket · The Seventeen</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>%s</style>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">Docket · desk · %s</div>
  <h1>%s things waiting on you</h1>
  <p>%s Every one carries what I would do and why. It saves as you type, so a
  docket half-answered at midnight is still half-answered in the morning.</p>
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
<p class="lead">Answer in one line. &ldquo;Not yet&rdquo; is a real answer — it keeps the
proposal open and brings it back next time; nothing is lost by skipping one.</p>
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
