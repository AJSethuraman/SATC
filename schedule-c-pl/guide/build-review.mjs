/* Build the markup page: the guide's prose, with a box against every piece.

   The first review copy was the finished page republished as an artifact, on the
   assumption the firm could comment on it in place. They could not — "i can't
   mark it up like this, i need space to give actual feedback right?" — so this
   builds the review surface instead of borrowing one.

   It is GENERATED from copy.mjs, like the guide itself, so the words on the
   markup page are the words that ship, and rebuilding it after a round of edits
   shows the current text rather than the text somebody pasted last week.

   The page carries a `db` capability: each verdict and note is saved as
   feedback/<id>, and this session reads them back with read_db. IDS ARE STABLE
   AND DERIVED FROM THE PROSE'S OWN KEYS (a line number, or a slug of the title)
   so a note written today still points at the same paragraph after an edit that
   reorders the page.

   Usage: node guide/build-review.mjs   → writes the page, prints the path      */

import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadYear } from '../src/years.mjs';
import { meta, traps, sections, closing, yearNote } from './copy.mjs';
import { resolveLine, GUIDE_YEAR } from './build-guide.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = process.env.REVIEW_OUT || join(HERE, '..', 'out');
const OUT_FILE = join(OUT_DIR, 'guide-markup.html');

const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);

/** One reviewable piece: what it says, and where a note about it belongs. */
function piece({ id, kind, where, label, text, ask }) {
  return `      <article class="piece" data-id="${esc(id)}">
        <div class="prose">
          <p class="where"><span class="kind">${esc(kind)}</span>${where ? `<span class="ref">${esc(where)}</span>` : ''}</p>
          ${label ? `<h3>${esc(label)}</h3>` : ''}
          <p class="says">${esc(text)}</p>
          ${ask ? `<p class="aside">${esc(ask)}</p>` : ''}
        </div>
        <div class="mark">
          <div class="picks" data-for="${esc(id)}">
            <button type="button" class="pick ok" data-v="fine">Fine</button>
            <button type="button" class="pick change" data-v="change">Change it</button>
            <button type="button" class="pick cut" data-v="cut">Cut it</button>
          </div>
          <textarea data-note="${esc(id)}" placeholder="Say it the way you would say it, or just say what is wrong."></textarea>
          <p class="state" data-state="${esc(id)}"><span class="txt"></span></p>
        </div>
      </article>`;
}

export function render() {
  const year = loadYear(GUIDE_YEAR);
  const parts = [];
  const ids = [];
  const add = (p) => { ids.push(p.id); parts.push(piece(p)); };

  const group = (title, note, body) => parts.push(
    `    <section class="group"><h2>${esc(title)}</h2>${note ? `<p class="note">${esc(note)}</p>` : ''}\n${body}\n    </section>`,
  );

  // 1 · The top of the page
  let body = [
    piece({ id: 'meta-strap', kind: 'Strapline', label: meta.title, text: meta.strap }),
    ...meta.intro.map((t, i) => piece({ id: `meta-intro-${i + 1}`, kind: 'Opening', text: t })),
    piece({ id: 'meta-tool', kind: 'Box pointing at the tool', text: meta.toolNudge }),
  ].join('\n');
  ids.push('meta-strap', ...meta.intro.map((_, i) => `meta-intro-${i + 1}`), 'meta-tool');
  group('What a reader sees first', 'The title, the promise, and the nudge toward the free tool.', body);

  // 2 · The eight traps
  body = traps.map((t) => {
    const line = resolveLine(year, t.line);
    const id = `trap-${line.id}`;
    ids.push(id);
    return piece({ id, kind: 'Trap', where: `Line ${line.id} · ${line.plain}`, label: t.title, text: t.body });
  }).join('\n');
  group('The eight that cost the most', 'These sit at the top of the page, before the form. The claim is that each one is money.', body);

  // 3 · The form, section by section
  for (const sec of sections) {
    body = sec.items.map((item) => {
      const line = item.line ? resolveLine(year, item.line) : null;
      const id = line ? `line-${line.id}` : `q-${slug(item.title)}`;
      ids.push(id);
      return piece({
        id,
        kind: line ? 'Box on the form' : 'Question',
        where: line ? `Line ${line.id} · the form calls it "${line.irs}"` : '',
        label: line ? line.plain : item.title,
        text: item.body,
        ask: item.ask,
      });
    }).join('\n');
    group(sec.heading, sec.blurb, body);
  }

  // 4 · The close
  body = [
    ...closing.body.map((t, i) => piece({ id: `close-${i + 1}`, kind: 'Closing', text: t })),
    piece({ id: 'close-cta', kind: 'The button', text: closing.cta }),
    piece({ id: 'year-note', kind: 'The year note', text: yearNote }),
  ].join('\n');
  ids.push(...closing.body.map((_, i) => `close-${i + 1}`), 'close-cta', 'year-note');
  group('Where the page stops, and the handover', 'The part that says what we do and what the page will not do.', body);

  return `<title>Schedule C Guide Markup</title>
<style>
:root{
  --navy:#132437; --slate:#29405b; --gold:#c0a265;
  --ink:#17202b; --muted:#5a6775; --faint:#8794a3;
  --page:#fbfaf7; --card:#fff; --line:#dfe3e8; --rule:#eceef1;
  --warm:#fdf8ee; --warm-line:#e8dcc0;
  --ok:#2f6b4f; --change:#8a6a1f; --cut:#8c3a2b;
  --serif:Georgia,'Times New Roman',serif;
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --navy:#0d1926; --slate:#8fb0d6; --gold:#d3b478;
  --ink:#e6ebf1; --muted:#9aa8b8; --faint:#7b8898;
  --page:#0f1720; --card:#161f2a; --line:#26313f; --rule:#202a36;
  --warm:#1d2430; --warm-line:#3a3527;
  --ok:#7fc4a1; --change:#d8b466; --cut:#e08b76;
}}
:root[data-theme="dark"]{
  --navy:#0d1926; --slate:#8fb0d6; --gold:#d3b478;
  --ink:#e6ebf1; --muted:#9aa8b8; --faint:#7b8898;
  --page:#0f1720; --card:#161f2a; --line:#26313f; --rule:#202a36;
  --warm:#1d2430; --warm-line:#3a3527;
  --ok:#7fc4a1; --change:#d8b466; --cut:#e08b76;
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.6 var(--sans)}
h1,h2,h3{font-family:var(--serif);font-weight:600;line-height:1.22;margin:0;text-wrap:balance}
:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}

.wrap{max-width:76rem;margin:0 auto;padding:0 1.4rem}
header.top{background:var(--navy);color:#eef2f7;border-bottom:4px solid var(--gold);padding:1.9rem 0 1.7rem}
header.top .eyebrow{margin:0 0 .9rem;font:600 .72rem/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--gold)}
header.top h1{font-size:clamp(1.5rem,3.6vw,2rem);color:#fff;margin-bottom:.5rem}
header.top p{margin:0;color:#c3cfdc;max-width:46rem;font-size:.98rem}
.bar{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:.6rem 0}
.bar .wrap{display:flex;flex-wrap:wrap;gap:.6rem 1rem;align-items:center;justify-content:space-between}
.count{font:600 .82rem/1.4 var(--mono);color:var(--muted)}
.count b{color:var(--ink)}
.legend{font-size:.8rem;color:var(--muted)}
.legend i{font-style:normal;font-weight:600}

.group{padding:2rem 0 .5rem;border-top:1px solid var(--line);margin-top:1.6rem}
.group:first-of-type{border-top:0;margin-top:0}
.group h2{font-size:1.3rem;margin-bottom:.25rem}
.group > .note{margin:.1rem 0 1.2rem;color:var(--muted);font-size:.93rem}

.piece{display:grid;gap:1rem;padding:1.1rem 0;border-top:1px solid var(--rule)}
.piece:first-of-type{border-top:0}
@media(min-width:62rem){.piece{grid-template-columns:1fr 22rem;gap:1.6rem}}
.prose{min-width:0}
.where{margin:0 0 .35rem;display:flex;flex-wrap:wrap;gap:.45rem;align-items:baseline}
.kind{font:600 .66rem/1.7 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);background:var(--rule);border-radius:2px;padding:0 .4rem}
.ref{font:.76rem/1.5 var(--mono);color:var(--faint)}
.prose h3{font-size:1.05rem;margin:0 0 .3rem}
.says{margin:0}
.aside{margin:.6rem 0 0;border-left:2px solid var(--gold);background:var(--warm);padding:.5rem .8rem;font-size:.95rem}
.mark{min-width:0}
.picks{display:flex;gap:.4rem;margin-bottom:.5rem}
.pick{flex:1;font:600 .82rem/1.3 var(--sans);cursor:pointer;background:var(--card);color:var(--muted);border:1px solid var(--line);border-radius:2px;padding:.42rem .3rem;transition:background .12s,border-color .12s,color .12s}
.pick:hover{border-color:var(--slate);color:var(--ink)}
.pick.ok[aria-pressed="true"]{background:var(--ok);border-color:var(--ok);color:#fff}
.pick.change[aria-pressed="true"]{background:var(--change);border-color:var(--change);color:#fff}
.pick.cut[aria-pressed="true"]{background:var(--cut);border-color:var(--cut);color:#fff}
textarea{width:100%;min-height:3.4rem;resize:vertical;font:inherit;font-size:.93rem;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:2px;padding:.5rem .6rem}
textarea::placeholder{color:var(--faint)}
.state{margin:.35rem 0 0;font:500 .76rem/1.4 var(--mono);color:var(--muted);min-height:1.1rem}
.piece.marked{padding-left:.9rem;border-left:3px solid var(--line);margin-left:-1.2rem}
.piece[data-verdict="fine"]{border-left-color:var(--ok)}
.piece[data-verdict="change"]{border-left-color:var(--change)}
.piece[data-verdict="cut"]{border-left-color:var(--cut)}
.piece[data-verdict="cut"] .says{text-decoration:line-through;text-decoration-color:var(--cut);opacity:.7}

.banner{background:var(--warm);border:1px solid var(--warm-line);border-left:3px solid var(--gold);padding:.8rem 1rem;margin:1.4rem 0 0;font-size:.94rem}
footer{padding:2.2rem 0 3rem;margin-top:2rem;border-top:1px solid var(--line);color:var(--muted);font-size:.87rem}
</style>

<header class="top">
  <div class="wrap">
    <p class="eyebrow">Sethuraman Accounting, Tax &amp; Consulting</p>
    <h1>Mark up the Schedule C guide</h1>
    <p>Every piece of the page is below, in the order a reader meets it, with a box against each one. Mark what you want changed and write it however you like — half a sentence is enough. It saves as you type.</p>
  </div>
</header>

<div class="bar"><div class="wrap">
  <span class="count"><b id="done">0</b> of <b>${ids.length}</b> marked</span>
  <span class="legend"><i>Fine</i> · leave it · <i>Change it</i> · say what it should say · <i>Cut it</i> · it should not be on the page</span>
</div></div>

<main class="wrap">
  <div id="dbwarn" class="banner" hidden>Nothing can be saved from this view. Send your notes in the chat instead.</div>
${parts.join('\n')}
</main>

<footer class="wrap">
  <p>The words above are the ones that would ship, taken straight from the page's source. Anything you mark comes back to me and I make the change, rebuild the page, and put it back in front of you.</p>
  <p>Tax year ${GUIDE_YEAR}. Line numbers are looked up per year rather than typed, so they are not something to proofread here.</p>
</footer>

<script>
const IDS = ${JSON.stringify(ids)};
const local = {};
let db = null;
const timers = {};

const card = (id) => document.querySelector('.piece[data-id="' + CSS.escape(id) + '"]');

function paint(id) {
  const c = card(id); if (!c) return;
  const d = local[id] || {};
  c.querySelectorAll('.pick').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === d.verdict)));
  const ta = c.querySelector('textarea');
  if (typeof d.note === 'string' && document.activeElement !== ta) ta.value = d.note;
  const marked = Boolean(d.verdict || d.note);
  c.classList.toggle('marked', marked);
  if (d.verdict) c.dataset.verdict = d.verdict; else delete c.dataset.verdict;
  c.querySelector('.state .txt').textContent = marked ? (d.saved === false ? 'Not saved' : 'Saved') : '';
  document.getElementById('done').textContent = IDS.filter((i) => {
    const x = local[i] || {}; return x.verdict || x.note;
  }).length;
}

async function save(id) {
  const d = Object.assign({ verdict: '', note: '' }, local[id]);
  d.at = new Date().toISOString();
  delete d.saved;
  local[id] = d;
  paint(id);
  // Never say "Saved" when nothing was saved. Without the store — an unpublished
  // copy, a revoked capability — the mark lives only in this tab, and the page
  // has to say so rather than reassure.
  if (!db) { local[id].saved = false; paint(id); return; }
  try { await db.doc('feedback/' + id).set(d); } catch (e) { local[id].saved = false; paint(id); }
}

document.querySelectorAll('.pick').forEach((btn) => {
  btn.addEventListener('click', () => {
    const id = btn.closest('.picks').dataset.for;
    const cur = local[id] || {};
    local[id] = Object.assign({}, cur, { verdict: cur.verdict === btn.dataset.v ? '' : btn.dataset.v });
    save(id);
  });
});
document.querySelectorAll('textarea[data-note]').forEach((ta) => {
  ta.addEventListener('input', () => {
    const id = ta.dataset.note;
    local[id] = Object.assign({}, local[id] || {}, { note: ta.value });
    clearTimeout(timers[id]);
    timers[id] = setTimeout(() => save(id), 700);
  });
  ta.addEventListener('blur', () => { clearTimeout(timers[ta.dataset.note]); save(ta.dataset.note); });
});

IDS.forEach((id) => { local[id] = { verdict: '', note: '' }; paint(id); });

(async () => {
  // The claude runtime exists only inside the artifact viewer. Opened as a
  // plain file — which is how this page is looked at before it is published —
  // it is simply absent, and that has to show as 'nothing will save' rather than
  // as an uncaught error nobody sees.
  db = typeof claude === 'undefined' ? null : await claude.use('db');
  if (!db) { document.getElementById('dbwarn').hidden = false; return; }
  // One listener over the whole collection: a listener per piece would be
  // dozens of subscriptions for a page that changes a few rows at a time.
  db.collection('feedback').onSnapshot(
    (snap) => {
      snap.docs.forEach((doc) => {
        if (!IDS.includes(doc.id)) return;
        local[doc.id] = Object.assign({ verdict: '', note: '' }, doc.data());
        paint(doc.id);
      });
    },
    () => { document.getElementById('dbwarn').hidden = false; },
  );
})();
</script>
`;
}

function main() {
  const html = render();
  mkdirSync(OUT_DIR, { recursive: true });
  writeFileSync(OUT_FILE, html);
  console.log(`wrote ${OUT_FILE} — ${(html.length / 1024).toFixed(0)} KB`);
}

if (process.argv[1] && process.argv[1].endsWith('build-review.mjs')) main();
