/* The page that actually ships.

   Everything else in this folder tests the source. This tests the artifact: the
   single file that gets served from satcllp.com. The claim printed on that page
   is that your figures never leave your computer, and the only way that claim
   stays true is if something checks the shipped bytes every time. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { render, bundle, findNetworkCalls, OUT_FILE } from '../build.mjs';

const built = () => (existsSync(OUT_FILE) ? readFileSync(OUT_FILE, 'utf8') : '');

test('the committed page is what the source builds today', () => {
  assert.ok(existsSync(OUT_FILE), `${OUT_FILE} has not been built. Run: npm run build`);
  assert.equal(built(), render(),
    'the page in website/ has drifted from the source in schedule-c-pl/. Run: npm run build');
});

test('the shipped page asks nothing of any other machine', () => {
  const leaks = findNetworkCalls(built());
  assert.deepEqual(leaks, [], `the page would talk to: ${leaks.join(', ')}`);
});

test('and carries no analytics of any kind', () => {
  const html = built().toLowerCase();
  for (const tracker of ['googletagmanager', 'google-analytics', 'gtag(', 'plausible',
    'cloudflareinsights', 'segment.com', 'hotjar', 'facebook.net', 'clarity.ms']) {
    assert.ok(!html.includes(tracker), `found ${tracker} in the shipped page`);
  }
});

test('it is one file — nothing to fetch alongside it', () => {
  const html = built();
  // The bundled spreadsheet writer contains the literal "<styleSheet", so the
  // tag has to end at a space or a bracket for this count to mean anything.
  assert.equal((html.match(/<script[\s>]/g) || []).length, 1, 'there should be exactly one script tag');
  assert.equal((html.match(/<style[\s>]/g) || []).length, 1, 'and exactly one style tag');
  assert.ok(!/<script[^>]+src=/i.test(html));
  assert.ok(!/<link[^>]+rel=["']stylesheet/i.test(html));
});

test('the page names its firm, its purpose and what it is not', () => {
  const html = built();
  for (const phrase of [
    'Sethuraman Accounting, Tax &amp; Consulting',
    'satcllp.com',
    'Schedule C profit and loss',
    'not a tax return',
    'does not make you a client',
  ]) assert.ok(html.includes(phrase), `the page never says: ${phrase}`);
});

test('the tax years on the page are the years the engine supports', () => {
  const html = built();
  assert.match(html, /Tax years 2023, 2024 and 2025/);
});

test('the page works without a network, so it must not need one to start', () => {
  const html = built();
  assert.ok(html.includes('Turn your internet off and this page still works'),
    'the offline claim is the proof a reader can run themselves — keep it on the page');
});

test('two modules never quietly share a name once the files are flattened', () => {
  assert.doesNotThrow(() => bundle());
});

test('the whole engine is in the file, not just the page around it', () => {
  const html = built();
  for (const marker of ['function compute(', 'function buildPdf(', 'function buildXlsx(',
    'Energy efficient commercial bldgs deduction', 'YEAR_2023', 'YEAR_2025']) {
    assert.ok(html.includes(marker), `the bundle is missing ${marker}`);
  }
});

test('no import or export survived the flattening', () => {
  const code = bundle();
  assert.ok(!/^\s*import\s/m.test(code), 'an import statement survived and would break the page');
  assert.ok(!/^\s*export\s/m.test(code), 'an export statement survived and would break the page');
});

test('the page is small enough to load on a phone', () => {
  const kb = built().length / 1024;
  assert.ok(kb < 250, `the page is ${kb.toFixed(0)} KB`);
  assert.ok(kb > 40, `the page is only ${kb.toFixed(0)} KB — something did not make it in`);
});
