"""Render the tie-out as one self-contained document per desk, then a PDF.

WHAT THE SHAPE IS FOR. The firm, 5 September 2026, handed a tie-out that had been
run properly and filed as a note with six images beside it: *"i assumed that you
understood the final product of tie out and walk would basically be a PDF that
shows how everything tied out? and explains it and makes it easy to follow?"*
Nothing had been left out of that note. The shape was wrong. So: one file, every
picture inside it, opening on a diagram of how the dots connect.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import record                                               # noqa: E402
import tieout                                               # noqa: E402

OUT = HERE / "tie-outs"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
RUN_DATE = date.today().isoformat()

#: What I believe, per difference, and why. A difference reported without a side
#: is half a finding: the skill's rule is say which you believe, or say you
#: cannot tell -- and never plug it.
BELIEVED = {
 "IRS Pub. 583 (12/2024), \"Reconciling the checking account\" — what the statement did not yet include": (
   "the publisher",
   "Ours is a PARTIAL QUOTATION and nothing on the page says so. Publication 583 "
   "gives two branches — <i>“Includes bank charges you did not enter in your books "
   "and subtract from your checkbook balance, or</i> <b>Does not include deposits "
   "made after the statement date…”</b> — and this passage keeps the second and "
   "drops the first without an ellipsis. The split itself is deliberate and right: "
   "the two branches have opposite answers, which is why they are cited apart, and "
   "serving them as one entry is the defect #264 found. What is wrong is that an "
   "answerer reading this cannot tell a branch was removed. <b>Fix: mark the "
   "omission</b> — an ellipsis, or store the publisher's sentence whole and let the "
   "per-citation narrowing separate them, which now exists."),
 "IRS Tangible Property Final Regulations, \"A de minimis safe harbor election\" — Note on Notice 2015-82 (sentence rejoined across the page's inline link)": (
   "us",
   "The page renders <i>“the Internal Revenue Service in Notice 2015-82 <b>PDF</b> "
   "increased the de minimis safe harbor threshold…”</i>. The word <b>PDF</b> is the "
   "label irs.gov appends to a link to a PDF; it is not part of the sentence. Our "
   "stored text drops it and reads as the sentence a person would read aloud, and "
   "the citation already says the sentence was rejoined across the link. <b>I "
   "believe ours</b>, and the difference is recorded rather than normalised away, "
   "because a rule that silently deleted words from a publisher's page would be a "
   "much worse thing to own than this one."),
}


def esc(t):
    return html.escape(str(t))


DIAGRAM = """
<figure class="fig">
<svg viewBox="0 0 1040 420" role="img" aria-label="The same passage travels two
roads: the production road from the publisher through our stored file into the
brief an answerer reads, and the check road straight from the publisher's own
document today. They meet at the comparison, and the verdict is read off it.">
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
      markerHeight="7" orient="auto-start-reverse">
    <polygon points="0,0 10,5 0,10" fill="#2C4A63"/></marker>
   <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
      markerHeight="7" orient="auto-start-reverse">
    <polygon points="0,0 10,5 0,10" fill="#8C2F39"/></marker></defs>

  <text x="20" y="26" class="lbl">THE PUBLISHER</text>
  <rect x="20" y="40" width="230" height="86" class="box src"/>
  <text x="36" y="68" class="h">eCFR · irs.gov</text>
  <text x="36" y="90" class="s">uscode.house.gov</text>
  <text x="36" y="110" class="s">as of %(as_of)s</text>

  <text x="300" y="26" class="lbl">THE PRODUCTION ROAD — what an answerer is handed</text>
  <text x="20" y="146" class="s">the only thing here</text>
  <text x="20" y="164" class="s">we do not control</text>
  <rect x="300" y="40" width="200" height="86" class="box"/>
  <text x="316" y="66" class="h">extracted/*.md</text>
  <text x="316" y="88" class="s">stored when the desk</text>
  <text x="316" y="106" class="s">was built</text>

  <rect x="560" y="40" width="200" height="86" class="box"/>
  <text x="576" y="66" class="h">ask.brief()</text>
  <text x="576" y="88" class="s">the text an answering</text>
  <text x="576" y="106" class="s">agent actually reads</text>

  <line x1="250" y1="83" x2="292" y2="83" class="ln" marker-end="url(#a)"/>
  <line x1="500" y1="83" x2="552" y2="83" class="ln" marker-end="url(#a)"/>
  <text x="256" y="74" class="e">stored once</text>
  <text x="506" y="74" class="e">rendered</text>

  <text x="300" y="196" class="lblr">THE CHECK — one request, today</text>
  <path d="M 135 178 L 135 248 L 292 248" class="lnr" marker-end="url(#ar)"/>
  <text x="146" y="240" class="er">fetched now, hashed</text>
  <rect x="300" y="210" width="200" height="76" class="box chk"/>
  <text x="316" y="238" class="h">the document today</text>
  <text x="316" y="260" class="s">XML · HTML · PDF text</text>

  <rect x="560" y="180" width="200" height="126" class="box cmp"/>
  <text x="576" y="208" class="h">the comparison</text>
  <text x="576" y="232" class="s">ours (from the brief)</text>
  <text x="576" y="252" class="s">theirs (from the fetch)</text>
  <text x="576" y="276" class="s">verdict read off it</text>
  <line x1="500" y1="248" x2="552" y2="248" class="lnr" marker-end="url(#ar)"/>
  <path d="M 660 126 L 660 172" class="ln" marker-end="url(#a)"/>

  <rect x="820" y="180" width="190" height="126" class="box"/>
  <text x="836" y="208" class="h">TIED</text>
  <text x="836" y="232" class="h" fill="#8C2F39">DIFFERS</text>
  <text x="836" y="256" class="h" fill="#8A5A16">COULD NOT</text>
  <text x="836" y="284" class="s">one of three, never a note</text>
  <line x1="760" y1="243" x2="812" y2="243" class="ln" marker-end="url(#a)"/>

  <text x="20" y="360" class="s">The red road is the one that makes this evidence rather than a second opinion: it touches a
  document nobody here can edit.</text>
  <text x="20" y="382" class="s">The blue road ends at the brief on purpose — that is the artifact an answerer opens, and the
  last hop is the one it depends on.</text>
</svg>
<figcaption>The same passage, two roads. They meet at the comparison, and the
verdict is read off that block rather than written ahead of it.</figcaption>
</figure>
"""


def roster(lines):
    t = Counter(l["verdict"] for l in lines)
    how = Counter(l["how"] for l in lines if l["verdict"] == "TIED")
    return t, how


def line_rows(lines):
    out = []
    for l in sorted(lines, key=lambda x: (x["verdict"] != "DIFFERS",
                                          x["verdict"] != "COULD NOT",
                                          x["citation"])):
        cls = {"TIED": "ok", "DIFFERS": "no", "COULD NOT": "hm"}[l["verdict"]]
        note = l["how"] if l["verdict"] == "TIED" else (
            l["obstacle"] or f"stops at “{l['stopped_at']}”")
        out.append(f"<tr><td class='v {cls}'>{esc(l['verdict'])}</td>"
                   f"<td class='c'>{esc(l['citation'])}</td>"
                   f"<td class='n'>{l['stored_chars']:,}</td>"
                   f"<td class='m'>{esc(note)}</td></tr>")
    return "\n".join(out)


def five_links(l, ours):
    """The exemplar, worked link by link, with the evidence in the page."""
    believed = BELIEVED.get(l["citation"])
    verdict_cls = {"TIED": "ok", "DIFFERS": "no", "COULD NOT": "hm"}[l["verdict"]]
    diff = (f"<p class='diff'><b>Which side I believe: {esc(believed[0])}.</b> "
            f"{believed[1]}</p>") if believed else ""
    return f"""
<div class="links">
  <h3>1 · The figure — and where a reader sees it</h3>
  <p>Not a row of a database: the paragraph of authority the desk hands an
  answering agent under the citation <code>{esc(l['citation'])}</code>. It is read
  out of <code>ask.brief()</code>, which is the text that agent opens, and it is
  {l['stored_chars']:,} characters long.</p>
  <pre class="ours">{esc(ours)}</pre>

  <h3>2 · The call — copy-pastable, with the real values in it</h3>
  <pre class="cmd">curl -sS --compressed "{esc(l['url'])}"</pre>
  <p class="meta">Fetched {esc(l['fetched_at'])} · {l['doc_bytes']:,} bytes ·
  SHA-256 <code>{esc(l['sha256'])}</code></p>

  <h3>3 · The derivation — what happens between the two</h3>
  <p>The response is turned into plain text: an XML or HTML document has its
  inline tags closed up and its block tags turned into a space, a PDF is read
  page by page. Both sides are then folded the same way — Unicode normalised, and
  the typographic quotes and dashes publishers vary between renderings mapped to
  their plain forms. <b>Nothing else is changed.</b> The stored text either occurs
  in the publisher's document or it does not.</p>

  <h3>4 · The independent source — captured, not summarised</h3>
  <p>The publisher's own words around the match, quoted verbatim out of the bytes
  whose hash is printed above. <b>A reader re-fetches that URL, recomputes the
  hash, and gets the same digits</b> — which is a check a photograph cannot
  offer.</p>
  <pre class="theirs">{esc(l['excerpt'])}</pre>

  <h3>5 · The comparison</h3>
  <pre class="cmp">ours    (ask.brief → {esc(l['citation'])[:52]})
        {l['stored_chars']:>6,} characters
theirs  ({esc(l['url'])[:56]})
        {l['matched_chars']:>6,} of them found, verbatim, in the document fetched above
diff    {esc('none' if l['verdict'] == 'TIED' else str(l['stored_chars'] - l['matched_chars']) + ' characters not found')}</pre>
  <p class="verdict {verdict_cls}">{esc(l['verdict'])}{
    ' — ' + esc({'exact': 'the publisher’s characters exactly',
                 'spacing': 'exact once whitespace is ignored, which is declared below'
                 }.get(l['how'], '')) if l['verdict'] == 'TIED' else ''}</p>
  {diff}
</div>"""


CSS = """
@page { size: A4; margin: 14mm 13mm; }
* { box-sizing: border-box }
body { font: 10.5pt/1.5 "Public Sans", -apple-system, "Segoe UI", sans-serif;
       color: #14181D; margin: 0; background: #fff; }
h1 { font: 600 25pt/1.1 Newsreader, Georgia, serif; margin: 0 0 6px; }
h2 { font: 600 15pt/1.2 Newsreader, Georgia, serif; margin: 26px 0 8px;
     border-top: 2px solid #14181D; padding-top: 9px; page-break-after: avoid; }
h3 { font: 700 9pt/1.3 "Public Sans", sans-serif; letter-spacing: .09em;
     text-transform: uppercase; color: #5B6472; margin: 18px 0 5px;
     page-break-after: avoid; }
.eyebrow { font: 700 8pt/1 "Public Sans"; letter-spacing: .16em;
           text-transform: uppercase; color: #7A8494; }
p { margin: 7px 0; max-width: 74ch }
code, pre { font-family: "JetBrains Mono", ui-monospace, Menlo, monospace; }
pre { font-size: 8.4pt; line-height: 1.45; white-space: pre-wrap;
      word-break: break-word; padding: 9px 11px; margin: 7px 0;
      border: 1px solid #DCDCD6; background: #F7F7F4; page-break-inside: avoid; }
pre.ours { border-left: 3px solid #2C4A63 }
pre.theirs { border-left: 3px solid #2C6650 }
pre.cmd { background: #14181D; color: #E6E9EC; border-color: #14181D }
pre.cmp { background: #fff; border-left: 3px solid #14181D }
code { font-size: .88em }
.meta { font-size: 8.4pt; color: #5B6472 }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 8px 0 }
th { text-align: left; border-bottom: 1.5px solid #14181D; padding: 4px 6px;
     font-size: 7.6pt; letter-spacing: .08em; text-transform: uppercase; color: #5B6472 }
td { border-bottom: 1px solid #E9E9E4; padding: 4px 6px; vertical-align: top }
td.v { font-weight: 700; font-size: 7.6pt; letter-spacing: .05em; white-space: nowrap }
td.c { font-family: "JetBrains Mono", monospace; font-size: 7.8pt }
td.n { text-align: right; font-variant-numeric: tabular-nums; color: #5B6472 }
td.m { color: #5B6472 }
.ok { color: #2C6650 } .no { color: #8C2F39 } .hm { color: #8A5A16 }
.verdict { font: 700 12pt/1.3 "Public Sans"; margin: 9px 0 }
.diff { border-left: 3px solid #8C2F39; background: #F9EFEF; padding: 9px 12px;
        page-break-inside: avoid }
.stats { display: flex; gap: 0; border-top: 1px solid #DCDCD6;
         border-bottom: 1px solid #DCDCD6; margin: 10px 0 }
.stat { flex: 1; padding: 9px 10px 8px 0 }
.stat b { display: block; font: 600 19pt/1.05 Newsreader, Georgia, serif;
          font-variant-numeric: tabular-nums }
.stat span { font-size: 7.4pt; letter-spacing: .06em; text-transform: uppercase;
             color: #7A8494; font-weight: 700 }
.fig { margin: 14px 0; page-break-inside: avoid }
.fig svg { width: 100%; height: auto }
figcaption { font-size: 8.6pt; color: #5B6472; margin-top: 5px }
.box { fill: #fff; stroke: #14181D; stroke-width: 1.4 }
.box.src { fill: #F3E3E4; stroke: #8C2F39 }
.box.chk { fill: #F3E3E4; stroke: #8C2F39 }
.box.cmp { fill: #EDF1F4; stroke: #2C4A63; stroke-width: 2 }
.h { font: 700 12px "Public Sans"; fill: #14181D }
.s { font: 10.5px "Public Sans"; fill: #4A5563 }
.lbl { font: 700 9px "Public Sans"; letter-spacing: .1em; fill: #7A8494 }
.lblr { font: 700 9px "Public Sans"; letter-spacing: .1em; fill: #8C2F39 }
.ln { stroke: #2C4A63; stroke-width: 1.8; fill: none }
.lnr { stroke: #8C2F39; stroke-width: 1.8; fill: none; stroke-dasharray: 6 4 }
.e { font: 9.5px "JetBrains Mono", monospace; fill: #2C4A63 }
.er { font: 9.5px "JetBrains Mono", monospace; fill: #8C2F39 }
.links { page-break-inside: auto }
ul { max-width: 74ch } li { margin: 5px 0 }
"""


HOW_TO_RUN = """
<h2>How to run this yourself</h2>
<p>Every step below has the real values already in it. Nothing here needs me.</p>
<h3>1 · Re-run the whole check</h3>
<pre class="cmd">cd desk &amp;&amp; python -B tools/tieout.py</pre>
<p>It fetches every source live and writes <code>tie-outs/findings.json</code>.
Expect it to take a few minutes: it pauses between requests rather than hammering
the publishers.</p>
<h3>2 · Rebuild these documents from that run</h3>
<pre class="cmd">cd desk &amp;&amp; python -B tools/tieout_exhibit.py</pre>
<h3>3 · Check one line by hand, without either script</h3>
<p>Take any row in the roster, fetch its URL, and look for the text yourself:</p>
<pre class="cmd">curl -sS --compressed "%(url)s" | shasum -a 256</pre>
<p>If that hash matches the one printed with the exemplar above, you are reading
the same bytes this document read. Then search the document for the passage —
the desk prints it under that citation in the brief:</p>
<pre class="cmd">cd desk &amp;&amp; python -B -c "import sys; sys.path.insert(0,'.'); import ask, record, pathlib; \\
print(ask.brief('show me', record.load(pathlib.Path('desks/%(desk)s'))))" | less</pre>
"""


def exhibit(desk_name, lines, ours_by_citation) -> str:
    tally, how = roster(lines)
    n = len(lines)
    diffs = [l for l in lines if l["verdict"] == "DIFFERS"]
    couldnt = [l for l in lines if l["verdict"] == "COULD NOT"]
    # THE SAMPLE OF ONE IS NOT THE EASY ONE. A difference if there is one; the
    # longest passage otherwise, because a long one has the most places to be
    # wrong and proves the most by tying.
    exemplar = diffs[0] if diffs else max(lines, key=lambda l: l["stored_chars"])
    sources = sorted({(l["source_id"], l["source_title"], l["url"]) for l in lines})

    worked = "".join(
        f"<h2>Difference {i + 1} of {len(diffs)} — {esc(d['citation'][:70])}</h2>"
        + five_links(d, ours_by_citation.get(d["citation"], ""))
        for i, d in enumerate(diffs) if d is not exemplar)

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Tie-out — {esc(desk_name)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Public+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>{CSS}</style></head><body>
<div class="eyebrow">Tie-out · Sethuraman Accounting, Tax &amp; Consulting · {RUN_DATE}</div>
<h1>{esc(desk_name)}</h1>
<p>Every passage this desk hands to an answering agent, put back to the publisher
that wrote it. <b>The question is not whether our tests pass.</b> It is whether the
authority we serve is what the authority actually says — which no test in this
repository can answer, because they all read the same stored files.</p>

{DIAGRAM % {"as_of": tieout.as_of()}}

<h2>The roster</h2>
<div class="stats">
  <div class="stat"><b>{tally.get('DIFFERS', 0)}</b><span>differs</span></div>
  <div class="stat"><b>{tally.get('COULD NOT', 0)}</b><span>could not</span></div>
  <div class="stat"><b>{tally.get('TIED', 0)} of {n}</b><span>tied</span></div>
  <div class="stat"><b>{len(sources)}</b><span>sources fetched live</span></div>
</div>
<p>Of the <b>{tally.get('TIED', 0)}</b> that tied, <b>{how.get('exact', 0)}</b> matched the
publisher's characters exactly, <b>{how.get('spacing', 0)}</b> matched only once
whitespace was ignored, and <b>{how.get('elided', 0)}</b> carry a marked omission
and were checked segment by segment, in order. All three are declared, and
explained under what this does not prove.</p>
<p class="meta">{how.get('exact', 0)} + {how.get('spacing', 0)} +
{how.get('elided', 0)} = {how.get('exact', 0) + how.get('spacing', 0) + how.get('elided', 0)},
which is the tied count above. THE SENTENCE USED TO NAME TWO OF THE THREE and so
did not add up — 43 and 4 against 49 tied on the cash desk, with the two marked
omissions unaccounted for. A breakdown that does not sum to its own total is the
failure this exhibit exists to catch, printed by the exhibit.</p>

<h2>The sample of one, worked end to end</h2>
<p>{"The difference, because a difference is the thing worth showing." if diffs
    else "The longest passage on this desk, because a long one has the most places to be wrong."}</p>
{five_links(exemplar, ours_by_citation.get(exemplar["citation"], ""))}
{worked}

<h2>Every passage on this desk</h2>
<table><thead><tr><th>verdict</th><th>citation</th><th>chars</th><th>how / why</th></tr></thead>
<tbody>{line_rows(lines)}</tbody></table>

<h2>The sources, and that they can disagree with us</h2>
<ul>{"".join(f"<li><b>{esc(sid)}</b> — {esc(t)}<br><code>{esc(u)}</code></li>"
             for sid, t, u in sources)}</ul>
<p>Not one of these is ours. None is a cache, a fixture or a second copy of our own
record — which is the test the tie-out skill puts first: <b>could this disagree with
me?</b> Each one can, and two of them did.</p>

{HOW_TO_RUN % {"url": exemplar["url"], "desk": desk_name}}

<h2>What it found</h2>
{FOUND}

<h2>What I got wrong</h2>
{WRONG}

<h2>What this does not prove</h2>
{LIMITS}
</body></html>"""


FOUND = """
<p><b>Nothing, and that sentence had to be earned three times over.</b> All 531
passages the seven desks hand an answering agent are, today, what the publisher
publishes: <b>0 differs, 0 could not</b>. The run this morning said 533 and two;
the one before it said 88 differences. What changed in between is the record and
the checker, and both are worth reading before this figure is believed.</p>

<p><b>The three findings this run closed, each fixed in the record rather than in
the check.</b></p>
<ul>
<li><b>Right text, wrong link — three passages.</b> The rewards desk stored
§ 6041, § 6041A, § 6050W and § 6071 under ONE source whose recorded URL is the
House's granule for <b>§ 6041 only</b>. All four bodies were <b>verbatim
correct</b>, so nothing served was ever wrong and no test in the repository could
have seen it — a reader following the citation for three of the four simply
landed on a page that did not contain it. <b>Only opening the link finds this.</b>
Split into four sources, four URLs, each verified live; and the record now has a
test comparing the URL a citation is really on with the URL its source claims.</li>
<li><b>A partial quotation that did not say it was one.</b> Publication 583's
sentence has two branches and the cash desk stored the second without marking the
omission. The split is right — the branches have opposite answers, which is the
defect #264 found — but an answerer could not tell a branch had been removed.
Marked now with <code>[...]</code>, and the mark is CHECKED rather than excused:
every segment must appear in the live document, in order.</li>
<li><b>A publisher's interface text inside a quotation.</b> irs.gov appends the
word <b>PDF</b> to links that point at PDFs, and one sits mid-sentence on the
tangible-property page. Ours dropped it. This was judged in our favour this
morning and left; it is the same unmarked omission as Pub 583, and it is marked
now. It was the last difference in the corpus.</li>
</ul>
<p><b>What "nothing" is worth here.</b> Three of the 531 tied only because a
marked omission was checked segment by segment, and 13 tied only once whitespace
was ignored. Both are declared, both are counted on each desk's own sheet, and
neither is silently folded into the headline. A clean run that hides how it got
clean is the thing this exhibit exists not to be.</p>
"""

WRONG = """
<p><b>The first run reported 88 differences and 34 of them were mine.</b> The
extractor replaced every markup tag with a space, so eCFR's
<code>election&lt;/I&gt;—(1)</code> came back as <code>election -(1)</code> and
<code>601.601(d)(2)(ii)(&lt;I&gt;b&lt;/I&gt;)</code> as
<code>( b )</code>. A checker that invents differences is worse than no checker,
because somebody goes and "fixes" the record to match it. Inline tags now close
up and only block tags become a space.</p>
<p><b>Then it reported 18, and 16 of those were mine too.</b> pypdf reads a kerned
two-column IRS page as <code>Y ou</code> and hyphenates <code>infor-­mation</code>
across a line break, and irs.gov puts block markup inside a sentence. Those are
rendering artefacts of the extractor, not differences in what was published — so
the comparison now runs twice, and the exhibit says which pass carried each line
rather than quietly folding them together.</p>
<p><b>I could not capture the sources as photographs, and the skill asks for
photographs.</b> This machine's browser cannot reach the publishers even when
pointed at the egress proxy — <code>ERR_CONNECTION_RESET</code> — while the HTTP
client reaches them fine. Attempted, failed, recorded. What is here instead is the
document itself: its SHA-256, its length, the moment it was fetched and the
publisher's own words quoted around each match. For text that is the stronger
evidence, because a reader can recompute the hash and a screenshot cannot be
re-verified at all.</p>
"""

LIMITS = """
<ul>
<li><b>It proves the words, not the reading.</b> That § 1.263(a)-1(f)(1)(ii)(D)
says $500 is now established. Whether $500 is the number that governs a client is a
question about Notice 2015-82 and about the firm's election, and no fetch settles
it.</li>
<li><b>It proves containment, not completeness.</b> The check asks whether our
passage occurs in the publisher's document. It does not ask whether we stored the
<i>whole</i> of what that citation covers — a passage could be a true fragment of a
paragraph whose second half changes its meaning. Publication 583 above is exactly
that failure caught by accident, not by design.</li>
<li><b>The whitespace-ignoring pass can hide a genuinely missing space.</b> 13
lines tied only on that pass. Each is named in the roster as <code>spacing</code>
so nobody has to take it on trust.</li>
<li><b>The regulations were fetched as of %(as_of)s, not today.</b> eCFR's
versioner refuses a future date and this is the last date known good on it. A
regulation amended between that date and now would not show here.</li>
<li><b>One reading, not two.</b> The skill asks for a second rendering where one
exists — the XML and the rendered page, the PDF and the HTML. Only one rendering
per source was read. A digit or a word wrong in <i>both</i> our copy and the one
rendering we read would pass.</li>
<li><b>Nothing here touches whether a desk answers well.</b> This is about the
authority it is given. A desk with a perfect corpus can still reason badly from
it, and that is what the scoreboard is for.</li>
</ul>
"""


def summary(all_lines, per_desk) -> str:
    tally, how = roster(all_lines)
    n = len(all_lines)
    rows = ""
    for name, lines in per_desk:
        t, h = roster(lines)
        rows += (f"<tr><td class='c'>{esc(name)}</td>"
                 f"<td class='n'>{len(lines)}</td>"
                 f"<td class='n no'>{t.get('DIFFERS', 0) or ''}</td>"
                 f"<td class='n hm'>{t.get('COULD NOT', 0) or ''}</td>"
                 f"<td class='n ok'>{t.get('TIED', 0)}</td>"
                 f"<td class='n'>{h.get('spacing', 0) or ''}</td></tr>")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Tie-out — the whole stored corpus</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Public+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>{CSS}</style></head><body>
<div class="eyebrow">Tie-out · Sethuraman Accounting, Tax &amp; Consulting · {RUN_DATE}</div>
<h1>Is what the desks say the authority says<br>what the authority says?</h1>
<p>Every one of the <b>{n}</b> passages the seven desks hand to an answering agent,
fetched back from the publisher that wrote it and compared. <b>No test in this
repository can answer this</b>, because every test reads the same stored files: a
passage transcribed wrongly is stored wrongly, served wrongly and asserted
wrongly, and every green stays green.</p>

{DIAGRAM % {"as_of": tieout.as_of()}}

<h2>The roster</h2>
<div class="stats">
  <div class="stat"><b>{tally.get('DIFFERS', 0)}</b><span>differs</span></div>
  <div class="stat"><b>{tally.get('COULD NOT', 0)}</b><span>could not</span></div>
  <div class="stat"><b>{tally.get('TIED', 0)} of {n}</b><span>tied</span></div>
  <div class="stat"><b>{how.get('spacing', 0)}</b><span>tied on spacing only</span></div>
</div>
<table><thead><tr><th>desk</th><th>passages</th><th>differs</th><th>could not</th>
<th>tied</th><th>of those, spacing</th></tr></thead><tbody>{rows}</tbody></table>
<p>{"Read the differences first; the" if tally.get('DIFFERS', 0) or tally.get('COULD NOT', 0) else "Nothing here differs, so read what it took to get there rather than the roster. The"} {tally.get('TIED', 0)} that agree are not what
anybody needs to read. Each desk has its own exhibit beside this one, with its
sample of one worked link by link.</p>

<h2>What it found</h2>
{FOUND}

<h2>What I got wrong</h2>
{WRONG}

<h2>What this does not prove</h2>
{LIMITS % {"as_of": tieout.as_of()}}
</body></html>"""


def render_pdf(html_path: Path, pdf_path: Path):
    subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                    "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    "--virtual-time-budget=20000", f"file://{html_path}"],
                   check=True, capture_output=True, timeout=300)


if __name__ == "__main__":
    rows = json.loads((OUT / "findings.json").read_text(encoding="utf-8"))
    ours = {}
    for d in sorted((HERE / "desks").iterdir()):
        if (d / "SOURCES.md").is_file():
            ours.update(tieout.brief_passages(record.load(d)))

    per_desk = []
    for name in sorted({r["desk"] for r in rows}):
        lines = [r for r in rows if r["desk"] == name]
        per_desk.append((name, lines))
        h = OUT / f"TIE-OUT-{name}-{RUN_DATE}.html"
        h.write_text(exhibit(name, lines, ours).replace(
            "%(as_of)s", tieout.as_of()), encoding="utf-8")
        render_pdf(h, h.with_suffix(".pdf"))
        print(f"  {name:34} {len(lines):>4} passages -> {h.with_suffix('.pdf').name}")

    h = OUT / f"TIE-OUT-all-desks-{RUN_DATE}.html"
    h.write_text(summary(rows, per_desk), encoding="utf-8")
    render_pdf(h, h.with_suffix(".pdf"))
    print(f"  {'SUMMARY':34} {len(rows):>4} passages -> {h.with_suffix('.pdf').name}")
