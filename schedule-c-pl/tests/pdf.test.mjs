/* Does the PDF actually open, and does it say what the screen said?

   Every assertion here runs against a file read back by Mozilla's pdf.js — the
   engine Firefox uses to display PDFs. If pdf.js can find the text, a person
   opening the file can see it. Checking our own writer with our own reader
   would prove nothing at all. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pdfFor, prepare, DISCLAIMER, FIRM } from '../src/document.mjs';
import { formatCents } from '../src/money.mjs';
import { readPdf } from './helpers/read-artifacts.mjs';
import { freelancer, reseller, firstYearLoss, sparse, roundingTrap, priorYear, large } from './fixtures.mjs';

const NOW = new Date(2026, 8, 6, 10, 30, 0);
const build = (r, opts = {}) => pdfFor(r, { now: NOW, ...opts });

/** Every figure the statement model intends to print, as it would be printed. */
function figuresIn(prepared) {
  const out = [];
  for (const sec of prepared.stmt.sections) {
    for (const r of [...sec.rows, sec.footer].filter(Boolean)) {
      if (r.source === 'empty') continue;
      out.push({ id: r.id, label: r.label, text: formatCents(r.cents, { dollars: prepared.rounding === 'dollars' }) });
    }
  }
  return out;
}

test('the file is a PDF and pdf.js opens it', async () => {
  const { bytes } = build(freelancer());
  assert.equal(new TextDecoder().decode(bytes.slice(0, 8)), '%PDF-1.4');
  assert.equal(new TextDecoder().decode(bytes.slice(-6)), '%%EOF\n');
  const doc = await readPdf(bytes);
  assert.ok(doc.numPages >= 2, `expected more than one page, got ${doc.numPages}`);
});

test('every figure on the statement reaches the file, on every scenario', async () => {
  for (const make of [freelancer, reseller, firstYearLoss, sparse, priorYear, large]) {
    const { bytes, prepared } = build(make());
    const doc = await readPdf(bytes);
    for (const f of figuresIn(prepared)) {
      assert.ok(doc.text.includes(f.text),
        `${make.name}: line ${f.id} (${f.label}) shows ${f.text} on screen but is not in the PDF`);
    }
  }
});

test('the label and its figure land on the same line of the page', async () => {
  const { bytes, prepared } = build(freelancer());
  const doc = await readPdf(bytes);
  for (const f of figuresIn(prepared).slice(0, 8)) {
    const near = new RegExp(`${f.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^a-zA-Z]{0,12}${f.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`);
    assert.match(doc.text, near, `line ${f.id}: "${f.label}" and ${f.text} are not next to each other`);
  }
});

test('the worksheet carries every line of the form, blanks included', async () => {
  const { bytes, prepared } = build(freelancer());
  const doc = await readPdf(bytes);
  for (const line of prepared.result.yearData.lines) {
    if (line.kind === 'info') continue;
    const words = line.label.split(' ').slice(0, 3).join(' ');
    assert.ok(doc.text.includes(words), `the worksheet is missing line ${line.id} (${words})`);
  }
});

test('a blank line prints blank — a return with one figure has no column of zeros', async () => {
  const doc = await readPdf(build(sparse()).bytes);
  const zeros = (doc.text.match(/\b0\.00\b/g) || []).length;
  assert.equal(zeros, 0, `a nearly empty return printed ${zeros} zeros`);
  assert.ok(doc.text.includes('1,000.00'));
});

test('a loss prints in brackets, the way an accountant writes one', async () => {
  const doc = await readPdf(build(firstYearLoss()).bytes);
  assert.ok(doc.text.includes('(19,540.00)'), 'the loss is not shown in brackets');
  assert.ok(!doc.text.includes('-19,540.00'), 'a minus sign leaked through');
});

test('what the tool would not work out is printed, and only when it applies', async () => {
  const loss = await readPdf(build(firstYearLoss()).bytes);
  assert.ok(loss.text.includes('What this tool did not work out'));
  assert.ok(loss.text.includes('Form 4562'), 'depreciation was entered, so say what was not done');

  const bare = await readPdf(build(sparse()).bytes);
  assert.ok(!bare.text.includes('What this tool did not work out'),
    'a return with one line should not carry four paragraphs of refusals');
});

test('the flags a person should act on are printed', async () => {
  const doc = await readPdf(build(firstYearLoss()).bytes);
  assert.ok(doc.text.includes('Worth checking'));
  assert.ok(doc.text.includes('yours to lose'), 'the at-risk question is not in the document');
});

test('whole-dollar mode says why a column may not add up — but only when it does not', async () => {
  const trap = roundingTrap(); trap.rounding = 'dollars';
  const off = await readPdf(build(trap).bytes);
  assert.ok(off.text.includes('a column can look a dollar out'), 'the rounding note is missing');

  // A return entered in whole dollars has nothing to round, so the note would
  // be noise. (A return with real cents almost always trips it — that is the
  // IRS rule working, not a bug.)
  const clean = { ...freelancer(), rounding: 'dollars', entries: { 1: 5000000, 8: 100000, 25: 250000 }, details: {} };
  const fine = await readPdf(build(clean).bytes);
  assert.ok(!fine.text.includes('a column can look a dollar out'),
    'the rounding note appeared on a document whose columns add up');
});

test('the whole-dollar total follows the IRS rule: add the cents, round once', async () => {
  const trap = roundingTrap(); trap.rounding = 'dollars';
  const doc = await readPdf(build(trap).bytes);
  // Ten expenses of 49 cents each. Rounded one at a time they are all zero;
  // added first they come to $4.90, which rounds to $5.
  assert.ok(doc.text.includes('Total expenses before home office (28) 5'), doc.text.slice(0, 400));
});

test('the firm, the year and the plain-English caveat are all on it', async () => {
  const doc = await readPdf(build(freelancer()).bytes);
  assert.ok(doc.text.includes(FIRM));
  assert.ok(doc.text.includes('satcllp.com'));
  assert.ok(doc.text.includes('Tax year 2025'));
  assert.ok(doc.text.includes('Rowan Vale Photography'));
  for (const phrase of DISCLAIMER.split('. ')) {
    assert.ok(doc.text.includes(phrase.replace(/\.$/, '')), `the document does not say: ${phrase}`);
  }
});

test('nothing was dropped or turned into a question mark on its way into the file', async () => {
  for (const make of [freelancer, reseller, firstYearLoss]) {
    const doc = await readPdf(build(make()).bytes);
    assert.ok(!doc.text.includes('?'), `${make.name}: a character could not be encoded`);
  }
});

test('a prior year prints its own line numbers, not this year\'s', async () => {
  const doc = await readPdf(build(priorYear()).bytes);
  assert.ok(doc.text.includes('2023 Schedule C worksheet'));
  assert.ok(doc.text.includes('Other expenses (27a)'), 'other expenses should be on 27a for 2023');
  assert.ok(!doc.text.includes('Other expenses (27b)'));
});

test('a long list of other expenses runs onto more pages and loses nothing', async () => {
  const r = freelancer();
  r.details = { other: Array.from({ length: 60 }, (_, i) => ({ label: `Sundry item number ${i + 1}`, cents: (i + 1) * 137 })) };
  const { bytes, prepared } = build(r);
  const doc = await readPdf(bytes);
  assert.ok(doc.numPages >= 3, `expected the document to run on, got ${doc.numPages} pages`);
  for (const f of figuresIn(prepared)) {
    assert.ok(doc.text.includes(f.text), `line ${f.id} fell off the page`);
  }
  assert.ok(doc.text.includes('Sundry item number 60'), 'the last detail row is missing');
});

test('only the statement, or only the worksheet, if that is what was asked for', async () => {
  const only = await readPdf(build(freelancer(), { include: ['statement'] }).bytes);
  assert.ok(only.text.includes('Profit and loss'));
  assert.ok(!only.text.includes('Schedule C worksheet'));

  const sheet = await readPdf(build(freelancer(), { include: ['worksheet'] }).bytes);
  assert.ok(sheet.text.includes('Schedule C worksheet'));
  assert.ok(!sheet.text.includes('Net sales'), 'the statement wording leaked into a worksheet-only document');
});

test('the same figures on the same day give byte-identical files', () => {
  const a = build(freelancer()).bytes;
  const b = build(freelancer()).bytes;
  assert.deepEqual(Buffer.from(a), Buffer.from(b));
});

test('a return with nothing in it produces no document at all', () => {
  const empty = { ...sparse(), entries: {} };
  assert.throws(() => build(empty), /Nothing has been entered/);
});

test('the file is named after the business and the year', () => {
  assert.equal(build(freelancer()).name, 'Rowan-Vale-Photography-2025-profit-and-loss.pdf');
  const odd = freelancer();
  odd.business.name = 'Ann & Co. / Bakery <2025>';
  assert.match(build(odd).name, /^Ann-Co-Bakery-2025-2025-profit-and-loss\.pdf$/);
  const none = freelancer();
  none.business.name = '';
  assert.equal(build(none).name, 'Schedule-C-2025-profit-and-loss.pdf');
});

test('the statement and the worksheet never disagree about the profit', async () => {
  for (const make of [freelancer, reseller, firstYearLoss, large]) {
    const { bytes, prepared } = build(make());
    const doc = await readPdf(bytes);
    const net = formatCents(prepared.result.netProfitCents);
    const shown = (doc.text.match(new RegExp(net.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
    assert.ok(shown >= 2, `${make.name}: the net profit ${net} appears ${shown} time(s); it should be on both documents`);
  }
});

test('prepare and pdfFor agree about what is in the document', () => {
  const r = freelancer();
  const direct = prepare(r, { now: NOW });
  const viaPdf = build(r).prepared;
  assert.equal(direct.result.netProfitCents, viaPdf.result.netProfitCents);
  assert.equal(direct.meta.prepared, '6 September 2026');
});

test('nothing on the page overlaps anything else, and nothing runs off the edge', async () => {
  // A hand-written PDF writer gets its layout wrong in exactly two ways: a long
  // label runs under the figure beside it, or a line runs past the margin. Text
  // extraction cannot see either, so this checks where the glyphs actually are.
  const LEFT = 54, RIGHT = 558, PAGE_W = 612;
  for (const make of [freelancer, reseller, priorYear, large]) {
    const doc = await readPdf(build(make()).bytes);
    for (const [n, page] of doc.boxes.entries()) {
      for (const box of page) {
        assert.ok(box.x >= LEFT - 1, `${make.name} p${n + 1}: "${box.str.slice(0, 30)}" starts at ${box.x.toFixed(0)}, left of the margin`);
        assert.ok(box.x + box.w <= PAGE_W - 40, `${make.name} p${n + 1}: "${box.str.slice(0, 30)}" ends at ${(box.x + box.w).toFixed(0)}, past the margin`);
      }
      // Two runs share a line if their baselines are within a point of each
      // other. On the same line, one must end before the next begins.
      const byLine = new Map();
      for (const box of page) {
        const key = Math.round(box.y);
        if (!byLine.has(key)) byLine.set(key, []);
        byLine.get(key).push(box);
      }
      for (const [y, runs] of byLine) {
        runs.sort((a, b) => a.x - b.x);
        for (let i = 1; i < runs.length; i += 1) {
          const before = runs[i - 1];
          const gap = runs[i].x - (before.x + before.w);
          assert.ok(gap > -1,
            `${make.name} p${n + 1} at y=${y}: "${before.str.slice(0, 28)}" overlaps "${runs[i].str.slice(0, 28)}" by ${(-gap).toFixed(1)}pt`);
        }
      }
    }
    assert.ok(doc.boxes.flat().length > 40, `${make.name}: only ${doc.boxes.flat().length} text runs — did the page render?`);
  }
});

test('the money column is right-aligned to the same edge on every row', async () => {
  const doc = await readPdf(build(freelancer()).bytes);
  const rightEdges = doc.boxes.flat()
    .filter((b) => /^\(?[\d,]+\.\d{2}\)?$/.test(b.str.trim()))
    .map((b) => b.x + b.w);
  assert.ok(rightEdges.length > 15, `expected a column of figures, found ${rightEdges.length}`);
  const spread = Math.max(...rightEdges) - Math.min(...rightEdges);
  assert.ok(spread < 1, `the figures end at edges spread over ${spread.toFixed(2)}pt — the column is ragged`);
});

test('every IRS label reaches the page whole — nothing is cut', async () => {
  // lines.test.mjs verifies 52 of 55 labels word-for-word against the official
  // IRS PDF going IN. Nothing looked at what came OUT, and the writer cut any
  // label over 78 characters -- clipping five of them, line 6 by one character,
  // so the worksheet and the spreadsheet disagreed about what the form says.
  // Words rather than whole strings, because a wrapped label has the figure
  // extracted between its two halves.
  for (const make of [freelancer, reseller, priorYear]) {
    const { bytes, prepared } = build(make());
    const doc = await readPdf(bytes);
    assert.ok(!doc.text.includes('…'), `${make.name}: a label was cut short`);
    for (const line of prepared.result.yearData.lines) {
      if (line.kind === 'info') continue;
      for (const word of line.label.split(/\s+/)) {
        const bare = word.replace(/[^A-Za-z0-9$%().,'-]/g, '');
        if (bare.length < 4) continue;
        assert.ok(doc.text.includes(bare),
          `${make.name}: line ${line.id} lost the word "${bare}" from "${line.label}"`);
      }
    }
  }
});
