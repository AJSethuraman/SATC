/* Does the line table still say what the IRS form says?

   The labels in src/lines.mjs are not typed from memory — they come out of the
   official PDF for each year, and evidence/ holds both the extraction script
   and its raw output. This test re-reads that evidence and refuses to let the
   table drift away from it.

   It also pins the one thing that genuinely moves between years: for 2023 and
   2024 other expenses land on line 27a, and for 2025 the IRS swapped 27a and
   27b. Getting that wrong puts a real figure on the wrong line of a real
   return, which is the worst thing this tool could do. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadYear, supportedYears } from '../src/years.mjs';
import { EXPENSE_LINES, COGS_LINES, OTHER_LABEL, ENERGY_LABEL } from '../src/lines.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const evidenceFor = (year) => readFileSync(join(HERE, '..', 'evidence', `f1040sc-${year}-labels.txt`), 'utf8');

/** Squash both sides to the letters and digits that carry the meaning, after
    undoing the two things the PDF's accessibility text does to the wording:
    it spells Part III as "Part I I I", and it reads "(see instructions)" out
    loud on lines where the printed form abbreviates it. */
function normalise(s) {
  return s
    .replace(/\(see instr(uctions)?\.?\)/gi, ' ')
    .replace(/\bpart i i i\b/gi, 'part iii')
    .replace(/\bpart i i\b/gi, 'part ii')
    .replace(/:\s*[a-c]\.\s*/g, ': ')
    .replace(/^\s*\d+[a-c]?\.\s*/, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

/** Index the form's own text by the line it belongs to, so each label is
    checked against ITS line rather than against the page as a whole. */
function evidenceByLine(year) {
  const byId = new Map();
  for (const raw of evidenceFor(year).split('\n')) {
    // A row can carry more than one line — the Part II heading and line 8 are
    // spoken as one string — so every "8." in the row opens a line. It runs to
    // the end of the row rather than to the next marker, because the form's
    // own wording contains line numbers ("Subtract line 4 from line 3.") and
    // truncating there would cut a label in half.
    for (const mark of raw.matchAll(/(?<![^\s])(\d+[a-c]?)\.\s/g)) {
      const id = mark[1];
      const from = mark.index + mark[0].length;
      byId.set(id, `${byId.get(id) || ''} ${normalise(raw.slice(from))}`);
    }
  }
  return byId;
}

for (const year of supportedYears()) {
  test(`${year} · every money line is worded the way the IRS form words it`, () => {
    const y = loadYear(year);
    const byId = evidenceByLine(year);
    // The form prints a continuation line (16b, 20b, 24b) with only its own
    // half of the wording; the parent line carries the rest. Our label joins
    // the two with a colon, so each half is checked where the form puts it.
    const root = (id) => id.replace(/[a-c]$/, '');
    const textFor = (id) => (byId.get(id) || '') + ' ' + (byId.get(root(id)) || '');
    const checked = [];
    const reworded = [];
    for (const line of y.lines) {
      if (line.reworded) { reworded.push(line.id); continue; }
      const whole = normalise(line.label);
      let found = textFor(line.id).includes(whole);
      if (!found && line.label.includes(': ')) {
        const cut = line.label.lastIndexOf(': ');
        const parent = normalise(line.label.slice(0, cut));
        const child = normalise(line.label.slice(cut + 2));
        found = (byId.get(line.id) || byId.get(root(line.id)) || '').includes(child)
          && (byId.get(root(line.id)) || '').includes(parent);
      }
      assert.ok(found, `line ${line.id} of the ${year} form does not say "${line.label}"`);
      checked.push(line.id);
    }
    // Report the denominator rather than a bare pass.
    assert.equal(checked.length + reworded.length, y.lines.length);
    assert.equal(reworded.length, 3, 'only 44a/b/c should be reworded');
    console.log(`      ${year}: ${checked.length} labels word-for-word from the IRS PDF, ${reworded.length} reworded (${reworded.join(', ')})`);
  });
}

test('other expenses sit on 27a for 2023 and 2024, and on 27b for 2025', () => {
  for (const [year, slot] of [[2023, '27a'], [2024, '27a'], [2025, '27b']]) {
    const y = loadYear(year);
    assert.equal(y.otherExpensesLine, slot, `${year} other expenses`);
    assert.equal(y.byId.get(slot).label, OTHER_LABEL);
    assert.equal(y.byId.get(y.energyLine).label, ENERGY_LABEL);
    assert.notEqual(y.energyLine, slot);
    assert.match(y.byId.get('48').label, new RegExp(`line ${slot}$`));
  }
});

test('line 28 adds exactly the 24 expense lines, no more and no fewer', () => {
  for (const year of supportedYears()) {
    const y = loadYear(year);
    assert.deepEqual(y.byId.get('28').formula.of, EXPENSE_LINES);
    assert.equal(EXPENSE_LINES.length, 24);
    const partII = y.lines.filter((l) => l.part === 'II' && l.kind !== 'info'
      && !['28', '29', '30', '31'].includes(l.id)).map((l) => l.id);
    assert.deepEqual(partII, EXPENSE_LINES, `${year} Part II expense lines`);
  }
});

test('line 40 adds lines 35 to 39 and nothing else', () => {
  const y = loadYear(2025);
  assert.deepEqual(y.byId.get('40').formula.of, COGS_LINES);
  assert.deepEqual(COGS_LINES, ['35', '36', '37', '38', '39']);
});

test('every computed line names lines that exist', () => {
  for (const year of supportedYears()) {
    const y = loadYear(year);
    for (const line of y.lines) {
      if (!line.formula || line.formula.op === 'detail') continue;
      for (const ref of line.formula.of) {
        assert.ok(y.byId.has(ref), `line ${line.id} of ${year} refers to line ${ref}, which is not on the form`);
      }
    }
  }
});

test('a line table can only be built with other expenses on 27a or 27b', async () => {
  const { buildLines } = await import('../src/lines.mjs');
  assert.throws(() => buildLines('27c'), /27a or 27b/);
  assert.throws(() => buildLines(''), /27a or 27b/);
});
