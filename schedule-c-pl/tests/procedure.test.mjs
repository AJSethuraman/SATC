/* The walk's hand-over document, and the builder that now produces it.

   The first version of this document was assembled by a script nobody saved, so
   it could not be rebuilt — which meant a change to the tool could not be
   reflected in the training material without walking the whole job again. These
   tests are what stop that happening twice: they hold the builder to the
   Markdown, and they hold the committed document to the builder.

   They do NOT compare bytes. The images are encoded by Chromium, and Chromium's
   version differs between this machine and CI, so a byte check would go red for
   a reason that has nothing to do with the document being right. What is
   compared is every word, and the presence of every picture. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { render, runFolder, outFile, words, DOCS } from '../procedure.mjs';

const MD = readFileSync(join(DOCS, 'PROCEDURE-schedule-c.md'), 'utf8');
const SPEC = JSON.parse(readFileSync(join(DOCS, 'procedure-route.json'), 'utf8'));
const CSS = readFileSync(join(DOCS, 'procedure.css'), 'utf8');
const RUN = runFolder(MD);
const OUT = outFile(RUN);
const built = () => (existsSync(OUT) ? readFileSync(OUT, 'utf8') : '');
// Tags out, then entities back: the document escapes "&", so a test that reads
// it as written would look for "Bell & Son" and find "Bell &amp; Son".
const plain = (html) => words(html)
  .replace(/(?:<style>[\s\S]*?<\/style>)|<[^>]+>/g, ' ')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

test('the committed document says exactly what the procedure says', () => {
  assert.ok(existsSync(OUT), `${OUT} has not been built. Run: node procedure.mjs`);
  assert.equal(words(built()), render(MD, SPEC, CSS, () => 'IMAGE'),
    'the hand-over document has drifted from PROCEDURE-schedule-c.md. Run: node procedure.mjs');
});

test('every picture the procedure asks for is IN the document, not beside it', () => {
  const html = built();
  const wanted = [...MD.matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)].length + SPEC.stages.length;
  assert.equal((html.match(/data:image\/[a-z+]+;base64,/g) || []).length, wanted,
    `the document should carry ${wanted} images`);
  assert.ok(!/<img[^>]+src="(?!data:)/.test(html),
    'an image is linked rather than carried — the document would break when forwarded');
  assert.ok(!/https?:\/\//.test(html.replace(/data:[^"]+/g, '')),
    'the document reaches for the network; it has to work on a machine that has none');
});

test('all thirty-nine steps are in it, in order', () => {
  const inSource = [...MD.matchAll(/^## (Step \d+) · /gm)].map((m) => m[1]);
  const inDoc = [...built().matchAll(/<h2>(Step \d+) · /g)].map((m) => m[1]);
  assert.equal(inSource.length, 39, 'the procedure should have 39 steps');
  assert.deepEqual(inDoc, inSource, 'the document lost or reordered a step');
});

test('a bold sentence with an italic inside it renders as both, not as asterisks', () => {
  // The regression that shipped: "**On line 9, click *Work it out from miles*.**"
  // came out as raw markup, and every assertion in this file at the time passed.
  const md = '# T\n\n**On line 9, click *Work it out from miles*.**\n';
  const html = render(md, { heading: '', lede: '', sub: '', stages: [], notes: [], rows: [] }, '', () => 'X');
  assert.match(html, /<strong>On line 9, click <em>Work it out from miles<\/em>\.<\/strong>/);
  assert.ok(!html.includes('**'), 'markup left on the page');
});

test('nothing anywhere in the built document is still markup', () => {
  assert.equal(plain(built()).match(/\*+/g), null, 'an asterisk survived into the document');
});

test('a block the converter does not understand is refused, never dropped', () => {
  for (const bad of ['- a bullet list', '1. a numbered list', '> a quotation', '```code fence']) {
    assert.throws(() => render(`# T\n\n${bad}\n`, SPEC, '', () => 'X'), /does not handle this block/,
      `${bad} should have been refused`);
  }
});

test('the route accounts for every stage, or the build stops', () => {
  const wrong = { ...SPEC, rows: [3, 3] }; // seven stages, six places
  assert.throws(() => render('<!-- ROUTE -->\n', wrong, '', () => 'X'), /every stage/);
});

test('the run folder is read from the procedure, not configured separately', () => {
  assert.match(runFolder(MD), /walkthrough[/\\]schedule-c-\d{4}-\d{2}-\d{2}$/);
  assert.throws(() => runFolder('# A procedure with no screenshots\n'), /no screenshots/);
});

test('the document names the example, the answer it produces, and the date', () => {
  const text = plain(built());
  for (const phrase of ['Bell & Son Painting', '50,985.95', '6 September 2026']) {
    assert.ok(text.includes(phrase), `the document never says: ${phrase}`);
  }
});
