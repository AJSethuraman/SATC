/* Build the line-by-line guide page.

   The prose lives in copy.mjs and is the file to edit. The LINE NUMBERS AND IRS
   WORDING are not in the prose — they are looked up here, from the same
   years/*.mjs the tool computes with. That is not tidiness: the IRS swapped
   lines 27a and 27b for 2025, so a guide with the number typed into a sentence
   would have been wrong for two of the three years it covers, and nothing would
   have noticed. Write `line: '27other'` and the right number appears.

   Same rules as the tool's page: one self-contained file, no network requests,
   no analytics, no web fonts. `--check` fails if the committed page is not what
   this produces today. */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadYear } from '../src/years.mjs';
import { meta, traps, sections, closing, yearNote } from './copy.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const GUIDE_YEAR = 2025;
export const OUT_DIR = join(HERE, '..', '..', 'website', 'guides', 'schedule-c-line-by-line');
export const OUT_FILE = join(OUT_DIR, 'index.html');
const TOOL_URL = '/tools/schedule-c-profit-and-loss/';

const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** Resolve a copy entry's `line` to the real number and both wordings. */
export function resolveLine(year, key) {
  if (!key) return null;
  const id = key === '27other' ? year.otherExpensesLine : key;
  const line = year.byId.get(id);
  if (!line) throw new Error(`copy.mjs refers to line ${key}, which is not on the ${year.year} form`);
  return { id, plain: line.plLabel, irs: line.label };
}

function renderItem(year, item) {
  const line = resolveLine(year, item.line);
  const title = line ? line.plain : item.title;
  if (!title) throw new Error('a copy item has neither a line nor a title');
  return `        <article class="item">
          <h3>${line ? `<span class="line-no">${esc(line.id)}</span>` : ''}${esc(title)}</h3>
          ${line ? `<p class="irs">The form calls it: <span>${esc(line.irs)}</span></p>` : ''}
          <p>${esc(item.body)}</p>
          ${item.ask ? `<p class="ask">${esc(item.ask)}</p>` : ''}
        </article>`;
}

export function render() {
  const year = loadYear(GUIDE_YEAR);
  const rate = year.parameters.standardMileage.display;
  const home = year.parameters.simplifiedHomeOffice.display;

  const trapCards = traps.map((t) => {
    const line = resolveLine(year, t.line);
    return `        <article class="trap">
          <h3><span class="line-no">${esc(line.id)}</span>${esc(t.title)}</h3>
          <p>${esc(t.body)}</p>
        </article>`;
  }).join('\n');

  const body = sections.map((sec) => `      <section class="block">
        <h2>${esc(sec.heading)}</h2>
        ${sec.blurb ? `<p class="blurb">${esc(sec.blurb)}</p>` : ''}
${sec.items.map((i) => renderItem(year, i)).join('\n')}
      </section>`).join('\n');

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(meta.title)} — ${GUIDE_YEAR} | SATC</title>
<meta name="description" content="${esc(meta.strap)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://satcllp.com/guides/schedule-c-line-by-line/">
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E%3Crect%20width='32'%20height='32'%20fill='%23132437'/%3E%3Cpath%20d='M6%206%20H20%20V13%20H13%20V20%20H6%20Z'%20fill='none'%20stroke='%23fff'%20stroke-width='3'/%3E%3Crect%20x='21'%20y='21'%20width='6'%20height='6'%20fill='%23C0A265'/%3E%3C/svg%3E">
<style>
:root{--navy:#132437;--navy-2:#29405b;--gold:#c0a265;--ink:#17202b;--muted:#5a6775;--line:#dfe3e8;--page:#fbfaf7;--card:#fff;--warm:#fdf8ee;--serif:Georgia,'Times New Roman',serif;--sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.62 var(--sans);-webkit-text-size-adjust:100%}
a{color:var(--navy-2)}
h1,h2,h3{font-family:var(--serif);font-weight:600;line-height:1.22;text-wrap:balance}
.wrap{max-width:46rem;margin:0 auto;padding:0 1.5rem}
.top{background:var(--navy);color:#f4f1ea;padding:2.4rem 0 2.6rem;border-bottom:4px solid var(--gold)}
.firm{margin:0 0 1.3rem;font-size:.8rem;letter-spacing:.11em;text-transform:uppercase;color:var(--gold)}
.firm a{color:inherit;text-decoration:none}
.top h1{margin:0 0 .7rem;font-size:clamp(1.9rem,4.6vw,2.7rem);color:#fff}
.strap{margin:0 0 1.4rem;font-size:1.06rem;color:#dbe3ec}
.year{display:inline-block;font:500 .78rem/1 var(--mono);letter-spacing:.06em;background:var(--navy-2);color:#fff;padding:.4rem .6rem;border-radius:2px}
.intro{padding:2.2rem 0 .5rem}
.intro p{font-size:1.04rem}
.tool{background:var(--warm);border:1px solid #e8dcc0;border-left:3px solid var(--gold);padding:1.1rem 1.2rem;margin:1.6rem 0}
.tool p{margin:0 0 .7rem}
.tool a.cta{display:inline-block;background:var(--navy);color:#fff;text-decoration:none;padding:.55rem 1rem;border-radius:2px}
.block{padding:2.2rem 0 .4rem;border-top:1px solid var(--line);margin-top:2.2rem}
.block h2{font-size:1.5rem;margin:0 0 .4rem}
.blurb{margin:0 0 1.4rem;color:var(--muted)}
.item{margin:0 0 1.7rem}
.item h3{font-size:1.1rem;margin:0 0 .3rem;display:flex;gap:.55rem;align-items:baseline}
.line-no{flex:none;font:600 .72rem/1.7 var(--mono);color:var(--muted);background:#eef1f4;border-radius:2px;padding:0 .4rem;min-width:2.2rem;text-align:center}
.irs{margin:.15rem 0 .5rem;font-size:.85rem;color:var(--muted)}
.irs span{font-family:var(--mono);font-size:.93em}
.item p{margin:0 0 .5rem}
.ask{border-left:2px solid var(--gold);padding-left:.85rem;color:var(--ink);background:#fffdf8}
.traps{display:grid;gap:1rem;margin:1.2rem 0 0}
@media(min-width:44rem){.traps{grid-template-columns:1fr 1fr}}
.trap{background:var(--card);border:1px solid var(--line);padding:1rem 1.1rem}
.trap h3{font-size:1rem;margin:0 0 .4rem;display:flex;gap:.5rem;align-items:baseline}
.trap p{margin:0;font-size:.93rem;color:#333b45}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--navy-2);padding:1rem 1.1rem;margin:2rem 0;font-size:.94rem}
.close{background:var(--navy);color:#e8eef5;margin-top:2.6rem;padding:2.4rem 0}
.close h2{color:#fff;margin:0 0 .8rem}
.close p{max-width:42rem}
.close a.cta{display:inline-block;background:var(--gold);color:#2b2107;font-weight:600;text-decoration:none;padding:.6rem 1.1rem;border-radius:2px;margin-top:.6rem}
.foot{padding:2rem 0 3rem;color:var(--muted);font-size:.87rem}
</style>
</head>
<body>

<header class="top">
  <div class="wrap">
    <p class="firm"><a href="https://satcllp.com/">Sethuraman Accounting, Tax &amp; Consulting</a></p>
    <h1>${esc(meta.title)}</h1>
    <p class="strap">${esc(meta.strap)}</p>
    <span class="year">Tax year ${GUIDE_YEAR}</span>
  </div>
</header>

<main>
  <div class="wrap intro">
${meta.intro.map((p) => `    <p>${esc(p)}</p>`).join('\n')}

    <div class="tool">
      <p>${esc(meta.toolNudge)}</p>
      <a class="cta" href="${TOOL_URL}">Open the free Schedule C tool</a>
    </div>
  </div>

  <div class="wrap">
    <section class="block" style="border-top:0;margin-top:0">
      <h2>The eight that cost the most</h2>
      <p class="blurb">If you read nothing else on this page, read these. Each one is money, not paperwork.</p>
      <div class="traps">
${trapCards}
      </div>
    </section>

${body}

    <div class="note"><strong>One thing that moved.</strong> ${esc(yearNote)}</div>
  </div>
</main>

<section class="close">
  <div class="wrap">
    <h2>${esc(closing.heading)}</h2>
${closing.body.map((p) => `    <p>${esc(p)}</p>`).join('\n')}
    <a class="cta" href="https://satcllp.com/?from=schedule-c-guide#intake">${esc(closing.cta)}</a>
  </div>
</section>

<footer class="wrap foot">
  <p>Written by Sethuraman Accounting, Tax &amp; Consulting LLP. It explains what the boxes on Schedule C are for. It is not advice about your own return, and reading it does not make you a client of ours.</p>
  <p>Figures on this page are the ${GUIDE_YEAR} ones: ${esc(rate)} for business miles, ${esc(home)} for the square-foot home office method. <a href="${TOOL_URL}">The tool</a> · <a href="https://satcllp.com/">satcllp.com</a></p>
</footer>
</body>
</html>
`;
}

function main() {
  const html = render();
  for (const [re, what] of [[/\bfetch\s*\(/, 'fetch('], [/<script/i, 'a script'],
    [/<link[^>]+rel=["'](?:stylesheet|preload|preconnect)["']/i, 'an external stylesheet'],
    [/<img[^>]+src=["']https?:/i, 'a remote image']]) {
    if (re.test(html)) { console.error(`refusing to build: the guide would use ${what}`); process.exit(2); }
  }
  if (process.argv.includes('--check')) {
    const existing = existsSync(OUT_FILE) ? readFileSync(OUT_FILE, 'utf8') : '';
    if (existing !== html) {
      console.error('website/guides/schedule-c-line-by-line/index.html is not what the source builds today. Run: npm run build');
      process.exit(1);
    }
    console.log(`guide up to date — ${(html.length / 1024).toFixed(0)} KB`);
    return;
  }
  mkdirSync(OUT_DIR, { recursive: true });
  writeFileSync(OUT_FILE, html);
  console.log(`wrote ${OUT_FILE} — ${(html.length / 1024).toFixed(0)} KB, no network calls`);
}

if (process.argv[1] && process.argv[1].endsWith('build-guide.mjs')) main();
