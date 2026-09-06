/* The line-by-line guide page.

   The tool's page is checked by build.test.mjs. This checks the other artifact
   that ships to satcllp.com — the guide — and it exists mainly for one thing:
   the guide quotes LINE NUMBERS, and line numbers move. The IRS swapped 27a and
   27b for 2025. A guide with the number typed into a sentence would have been
   wrong for two of the three years it covers, and nothing on earth would have
   noticed. So the prose carries `line: '27other'` and the number is looked up.
   These tests are what make that lookup load-bearing rather than decorative. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { loadYear, supportedYears } from '../src/years.mjs';
import { render, resolveLine, GUIDE_YEAR, OUT_FILE } from '../guide/build-guide.mjs';
import { traps, sections, meta, closing } from '../guide/copy.mjs';

const built = () => (existsSync(OUT_FILE) ? readFileSync(OUT_FILE, 'utf8') : '');

test('the committed guide is what the source builds today', () => {
  assert.ok(existsSync(OUT_FILE), `${OUT_FILE} has not been built. Run: npm run build`);
  assert.equal(built(), render(),
    'website/guides/ has drifted from schedule-c-pl/guide/. Run: npm run build');
});

test('other expenses resolves to the line that year really uses', () => {
  // The whole reason the page is generated. 2025 is not a typo.
  const expected = { 2023: '27a', 2024: '27a', 2025: '27b' };
  for (const y of supportedYears()) {
    assert.equal(resolveLine(loadYear(y), '27other').id, expected[y],
      `other expenses is on ${expected[y]} for ${y}`);
  }
});

test('and the built page shows the guide year\'s number, not a remembered one', () => {
  const year = loadYear(GUIDE_YEAR);
  const chips = [...built().matchAll(/<span class="line-no">([^<]+)<\/span>/g)].map((m) => m[1]);
  assert.ok(chips.includes(year.otherExpensesLine),
    `no chip for ${year.otherExpensesLine}, the ${GUIDE_YEAR} other-expenses line`);
  const wrong = year.otherExpensesLine === '27a' ? '27b' : '27a';
  assert.ok(!chips.includes(wrong), `the page chips ${wrong}, which is not a ${GUIDE_YEAR} line`);
});

test('every line the prose points at exists on the form', () => {
  const year = loadYear(GUIDE_YEAR);
  const keys = [...traps.map((t) => t.line),
    ...sections.flatMap((s) => s.items.map((i) => i.line))].filter(Boolean);
  assert.ok(keys.length > 25, `only ${keys.length} lines covered — that is not the form`);
  for (const key of keys) assert.doesNotThrow(() => resolveLine(year, key), `line ${key}`);
});

test('the IRS wording on the page is the IRS wording, not a paraphrase', () => {
  const year = loadYear(GUIDE_YEAR);
  const html = built();
  for (const key of ['1', '9', '26', '30', '27other']) {
    const { irs } = resolveLine(year, key);
    const escaped = irs.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    assert.ok(html.includes(escaped), `the page never quotes the form's own words for ${key}: ${irs}`);
  }
});

test('an item with neither a line nor a title is refused, not rendered blank', () => {
  assert.throws(() => resolveLine(loadYear(GUIDE_YEAR), '99z'),
    /not on the 2025 form/, 'a bad line key has to stop the build');
});

test('the guide asks nothing of any other machine', () => {
  const html = built();
  assert.ok(!/<script/i.test(html), 'the guide has a script tag');
  assert.ok(!/\bfetch\s*\(/.test(html), 'the guide would fetch something');
  assert.ok(!/<link[^>]+rel=["'](?:stylesheet|preload|preconnect)["']/i.test(html));
  assert.ok(!/<img[^>]+src=["']https?:/i.test(html), 'the guide loads a remote image');
  for (const tracker of ['googletagmanager', 'google-analytics', 'gtag(', 'plausible',
    'cloudflareinsights', 'segment.com', 'hotjar', 'facebook.net', 'clarity.ms']) {
    assert.ok(!html.toLowerCase().includes(tracker), `found ${tracker} in the guide`);
  }
});

test('it says who wrote it, what it is not, and where the tool is', () => {
  const html = built();
  for (const phrase of [
    'Sethuraman Accounting, Tax &amp; Consulting',
    'does not make you a client',
    '/tools/schedule-c-profit-and-loss/',
    `Tax year ${GUIDE_YEAR}`,
  ]) assert.ok(html.includes(phrase), `the guide never says: ${phrase}`);
});

test('the figures in the footer come from the year file, not from the prose', () => {
  const year = loadYear(GUIDE_YEAR);
  const html = built();
  assert.ok(html.includes(year.parameters.standardMileage.display));
  assert.ok(html.includes(year.parameters.simplifiedHomeOffice.display));
  const prose = JSON.stringify({ meta, traps, sections, closing });
  assert.ok(!/\b70 cents a mile\b/.test(prose), 'a rate is typed into the prose; it will go stale');
});

test('the page sends a reader who wants more to the firm, tagged where from', () => {
  assert.match(built(), /satcllp\.com\/\?from=schedule-c-guide#intake/,
    'the one link that lets the firm tell the guide worked');
});
