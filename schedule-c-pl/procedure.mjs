/* Build the walk's hand-over document: one self-contained file.

   WHY THIS EXISTS. The first one was assembled by a script that was written
   once and not saved, so the 43-page document in docs/walkthrough/ could not be
   rebuilt, corrected or brought up to date — a change to the tool meant walking
   the whole job again from scratch. The firm, 7 September 2026, asked for the
   mechanism rather than the artefact: "keep this one, fix the mechanism for the
   next." This is the mechanism.

   WHAT IS SOURCE, AND WHAT IS DERIVED.
     docs/PROCEDURE-schedule-c.md      the steps and the words — the real source
     docs/procedure-route.json         the route picture: seven stages, and the
                                       four things that happen BETWEEN screens
     docs/procedure.css                how the document looks, in print and on
                                       screen
     docs/walkthrough/<run>/*.png      the screenshots, as they came off the
                                       browser: the negatives
     docs/walkthrough/<run>/route-*.jpg the seven route thumbnails. These are
                                       CROPS SOMEBODY CHOSE, so they are source
                                       and not derived — a builder cannot decide
                                       what part of a screen a stage is about.
   Everything else is derived: the screenshots are re-encoded to JPEG, embedded
   as data URIs, and the whole thing comes out as one file that can be forwarded
   to somebody who does not have this repository.

   ON --check AND WHY IT DOES NOT COMPARE BYTES. The JPEG encoder is Chromium's,
   and Chromium's version differs between this machine and CI. Comparing bytes
   would make the check fail for a reason that has nothing to do with the
   document being right. So --check compares the document with its images
   stripped — every word, heading, step and table — and separately asserts that
   every image the Markdown asks for is present and embedded. A stale document
   fails; a differently-compressed one does not.

   Usage:
     node procedure.mjs            rebuild the document
     node procedure.mjs --check    fail if the words have drifted from the source
     node procedure.mjs --pdf      also print it to PDF (A4)                  */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, basename } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
export const DOCS = join(HERE, 'docs');
const MD = join(DOCS, 'PROCEDURE-schedule-c.md');
const ROUTE = join(DOCS, 'procedure-route.json');
const CSS = join(DOCS, 'procedure.css');

/** How wide a screenshot is embedded, and how hard it is squeezed. The document
    is read on screen and printed on A4; past this width neither can show it. */
const IMAGE_WIDTH = 1100;
const JPEG_QUALITY = 0.78;

const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

/** Inline marks, in the order they must be applied: escape first, so a `<` in
    the prose can never become a tag, then BOLD BEFORE ITALIC and lazily.
    A bold span in this document routinely contains an italic one — "**On line 9,
    click *Work it out from miles*.**" — and a bold pattern that refuses to span
    an asterisk leaves that whole sentence on the page as raw markup. It did,
    and it was found by looking at the built page rather than by any assertion,
    which is why `main` now refuses to write a document with a mark left in it. */
function inline(text) {
  return esc(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
}

/** Split into blank-line-separated blocks, keeping table rows together. */
function blocks(md) {
  const out = [];
  let buf = [];
  for (const line of md.split('\n')) {
    if (line.trim() === '') { if (buf.length) { out.push(buf); buf = []; } } else buf.push(line);
  }
  if (buf.length) out.push(buf);
  return out;
}

function table(rows) {
  const cells = (r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
  const head = cells(rows[0]);
  const body = rows.slice(2).map(cells); // rows[1] is the |---|---| divider
  return `<table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join('')}</tr></thead>`
    + `<tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function routeBlock(spec, src) {
  const stage = (s) => `<figure class="stage"><div class="stage-head">`
    + `<span class="letter">${esc(s.letter)}</span>`
    + `<span class="stage-title">${esc(s.title)}</span>`
    + `<span class="stage-steps">${esc(s.steps)}</span></div>`
    + `<img src="${src(s.image)}" alt="${esc(s.title)}">`
    + `<figcaption>${esc(s.caption)}</figcaption></figure>`;
  const arrow = '<div class="arrow" aria-hidden="true">&#8594;</div>';
  const rows = [];
  let i = 0;
  for (const n of spec.rows) {
    const group = spec.stages.slice(i, i + n);
    i += n;
    let row = group.map(stage).join(arrow);
    // A short last row keeps the columns of the rows above it.
    for (let pad = n; pad < Math.max(...spec.rows); pad += 1) {
      row += '<div class="arrow" style="visibility:hidden">&#8594;</div>'
        + '<div class="spacer" aria-hidden="true"></div>';
    }
    rows.push(`<div class="stage-row">${row}</div>`);
  }
  if (i !== spec.stages.length) throw new Error('procedure-route.json: rows do not account for every stage');
  return `<section class="route"><h2 class="route-h">${esc(spec.heading)}</h2>`
    + `<p class="route-lede">${esc(spec.lede)}</p>`
    + rows.join('<div class="turn" aria-hidden="true">&#8595;</div>')
    + `<h3 class="route-sub">${esc(spec.sub)}</h3><div class="notes">`
    + spec.notes.map((n) => `<div class="note"><b>${esc(n.what)}</b><span>${esc(n.then)}</span></div>`).join('')
    + `</div></section>`;
}

/** The document, given a way to turn an image filename into a src. Pure — the
    only thing that touches a browser is the encoder passed in. */
export function render(md, spec, css, src) {
  const body = [];
  let step = null;
  const closeStep = () => { if (step) { body.push('</section>'); step = null; } };

  for (const b of blocks(md)) {
    const first = b[0];
    if (first.startsWith('<!-- ROUTE -->')) { closeStep(); body.push(routeBlock(spec, src)); continue; }
    if (first.startsWith('# ')) { closeStep(); body.push(`<h1>${inline(first.slice(2))}</h1>`); continue; }
    if (first.startsWith('## ')) {
      closeStep();
      body.push('<section class="step">');
      step = true;
      body.push(`<h2>${inline(first.slice(3))}</h2>`);
      continue;
    }
    if (first.startsWith('![')) {
      const m = first.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (!m) throw new Error(`cannot read the image reference: ${first}`);
      body.push(`<figure class="shot"><img src="${src(basename(m[2]))}" alt="${esc(m[1])}"></figure>`);
      continue;
    }
    if (first.startsWith('|')) { body.push(table(b)); continue; }
    if (/^-{3,}$/.test(first.trim())) { closeStep(); body.push('<hr>'); continue; }
    // Anything the converter does not understand is a refusal, not a silent
    // drop: a step quietly missing from a procedure is the whole failure this
    // document exists to prevent.
    if (/^(\s*[-*+]\s|\s*\d+\.\s|>|```|<)/.test(first)) {
      throw new Error(`procedure.mjs does not handle this block, and will not guess:\n${first}`);
    }
    body.push(`<p>${inline(b.join(' '))}</p>`);
  }
  closeStep();

  const title = (md.match(/^# (.+)$/m) || [, 'Procedure'])[1].split(' — ')[0];
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">\n`
    + `<title>${esc(title)} — procedure</title>\n<style>\n${css}\n</style>\n</head>\n`
    + `<body><div class="page">${body.join('')}</div></body></html>\n`;
}

/** The run this document is built from, read from the Markdown's own image
    references rather than configured — one fewer thing to keep in step. */
export function runFolder(md) {
  const m = md.match(/!\[[^\]]*\]\((walkthrough\/[^/]+)\//);
  if (!m) throw new Error('the procedure has no screenshots in it');
  return join(DOCS, m[1]);
}

export function outFile(runDir) {
  return join(runDir, `PROCEDURE-schedule-c-${basename(runDir).replace(/^schedule-c-/, '')}.html`);
}

/** Everything but the pictures. This is the part that must not drift, and the
    part a check can compare across two machines with different browsers. */
export const words = (html) => html.replace(/data:image\/[a-z+]+;base64,[A-Za-z0-9+/=]+/g, 'IMAGE');

async function encodeAll(runDir, names) {
  const { chromium } = await import('playwright');
  const executablePath = process.env.CHROMIUM_PATH
    || (existsSync('/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
      ? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' : undefined);
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();
  const out = new Map();
  for (const name of names) {
    const file = join(runDir, name);
    if (!existsSync(file)) throw new Error(`the procedure asks for ${name}, which is not in ${basename(runDir)}`);
    const raw = readFileSync(file);
    const type = name.endsWith('.png') ? 'png' : 'jpeg';
    if (type === 'jpeg') { out.set(name, `data:image/jpeg;base64,${raw.toString('base64')}`); continue; }
    const src = `data:image/png;base64,${raw.toString('base64')}`;
    /* eslint-disable no-undef */
    const jpeg = await page.evaluate(async ([dataUrl, width, quality]) => {
      const img = new Image();
      await new Promise((ok, no) => { img.onload = ok; img.onerror = no; img.src = dataUrl; });
      const scale = Math.min(1, width / img.naturalWidth);
      const c = document.createElement('canvas');
      c.width = Math.round(img.naturalWidth * scale);
      c.height = Math.round(img.naturalHeight * scale);
      const ctx = c.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.drawImage(img, 0, 0, c.width, c.height);
      return c.toDataURL('image/jpeg', quality);
    }, [src, IMAGE_WIDTH, JPEG_QUALITY]);
    out.set(name, jpeg);
  }
  await browser.close();
  return out;
}

function imagesWanted(md, spec) {
  const shots = [...md.matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)].map((m) => basename(m[1]));
  return [...spec.stages.map((s) => s.image), ...shots];
}

async function main() {
  const md = readFileSync(MD, 'utf8');
  const spec = JSON.parse(readFileSync(ROUTE, 'utf8'));
  const css = readFileSync(CSS, 'utf8');
  const runDir = runFolder(md);
  const out = outFile(runDir);
  const wanted = imagesWanted(md, spec);

  if (process.argv.includes('--check')) {
    if (!existsSync(out)) { console.error(`${out} has not been built. Run: node procedure.mjs`); process.exit(1); }
    const built = readFileSync(out, 'utf8');
    const fresh = render(md, spec, css, () => 'IMAGE');
    if (words(built) !== fresh) {
      console.error('the hand-over document no longer says what PROCEDURE-schedule-c.md says. Run: node procedure.mjs');
      process.exit(1);
    }
    const embedded = (built.match(/data:image\/[a-z+]+;base64,/g) || []).length;
    if (embedded !== wanted.length) {
      console.error(`the document embeds ${embedded} images; the source asks for ${wanted.length}`);
      process.exit(1);
    }
    if (/<img[^>]+src="(?!data:)/.test(built)) {
      console.error('the document links to an image instead of carrying it — it would break when forwarded');
      process.exit(1);
    }
    console.log(`procedure up to date — ${wanted.length} images, ${(built.length / 1024 / 1024).toFixed(1)} MB, one file`);
    return;
  }

  const images = await encodeAll(runDir, wanted);
  const html = render(md, spec, css, (name) => {
    const uri = images.get(name);
    if (!uri) throw new Error(`no image for ${name}`);
    return uri;
  });
  if (/<img[^>]+src="(?!data:)/.test(html) || /https?:\/\//.test(html.replace(/data:[^"]+/g, ''))) {
    console.error('refusing to write a hand-over document that needs the network');
    process.exit(2);
  }
  const leftover = words(html).replace(/(?:<style>[\s\S]*?<\/style>)|<[^>]+>/g, '').match(/\*+[^*\n]{0,60}/g);
  if (leftover) {
    console.error(`refusing to write a document with Markdown left in it: ${leftover.slice(0, 3).join(' · ')}`);
    process.exit(2);
  }
  writeFileSync(out, html);
  console.log(`wrote ${out} — ${wanted.length} images, ${(html.length / 1024 / 1024).toFixed(1)} MB, one file`);

  if (process.argv.includes('--pdf')) {
    const { chromium } = await import('playwright');
    const executablePath = process.env.CHROMIUM_PATH
      || (existsSync('/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        ? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' : undefined);
    const browser = await chromium.launch(executablePath ? { executablePath } : {});
    const page = await browser.newPage();
    await page.goto(`file://${out}`, { waitUntil: 'load' });
    const pdf = out.replace(/\.html$/, '.pdf');
    await page.pdf({ path: pdf, format: 'A4', printBackground: true });
    await browser.close();
    console.log(`printed ${pdf}`);
  }
}

if (process.argv[1] && process.argv[1].endsWith('procedure.mjs')) main();
