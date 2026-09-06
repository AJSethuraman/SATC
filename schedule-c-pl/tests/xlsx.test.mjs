/* Does the spreadsheet open, and is it a working spreadsheet rather than a
   picture of one?

   Everything here is read back by openpyxl, a Python library with no knowledge
   of this project. It reads the file twice — once for the formulas and once for
   the values Excel would show — which is what lets the last test check that our
   SUM formulas actually add up the cells they point at. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { xlsxFor, DISCLAIMER } from '../src/document.mjs';
import { centsToDecimal } from '../src/xlsx.mjs';
import { readXlsx, xlsxStrings } from './helpers/read-artifacts.mjs';
import { freelancer, reseller, firstYearLoss, sparse, priorYear, large } from './fixtures.mjs';

const NOW = new Date(2026, 8, 6, 10, 30, 0);
const build = (r, opts = {}) => xlsxFor(r, { now: NOW, ...opts });
const near = (a, b, why) => assert.ok(Math.abs(a - b) < 0.005, `${why}: ${a} vs ${b}`);

test('the file is a zip that openpyxl opens, with the three sheets', () => {
  const { bytes } = build(freelancer());
  assert.deepEqual([...bytes.slice(0, 2)], [0x50, 0x4b], 'not a zip');
  const book = readXlsx(bytes);
  assert.deepEqual(Object.keys(book.sheets), ['Profit and loss', 'Schedule C 2025', 'Detail']);
});

test('every figure on the statement is in the workbook as a number, not as text', () => {
  for (const make of [freelancer, reseller, firstYearLoss, sparse, priorYear, large]) {
    const { bytes, prepared } = build(make());
    const book = readXlsx(bytes);
    const numbers = book.sheets['Profit and loss'].flat().filter((c) => typeof c === 'number');
    for (const sec of prepared.stmt.sections) {
      for (const row of [...sec.rows, sec.footer].filter(Boolean)) {
        if (row.source === 'empty') continue;
        const want = Number(centsToDecimal(row.cents));
        assert.ok(numbers.some((n) => Math.abs(n - want) < 0.005),
          `${make.name}: line ${row.id} (${want}) is not a number in the spreadsheet`);
      }
    }
  }
});

test('the worksheet sheet holds every line, and blanks stay empty cells', () => {
  const { bytes, prepared } = build(sparse());
  const book = readXlsx(bytes);
  const rows = book.sheets['Schedule C 2025'];
  const byLine = new Map(rows.filter((r) => r[0]).map((r) => [String(r[0]), r]));
  assert.ok(byLine.has('1') && byLine.has('31') && byLine.has('42') && byLine.has('48'));
  assert.equal(byLine.get('1')[2], 1000);
  assert.equal(byLine.get('4')[2], null, 'line 4 has no figure, so its cell must be empty rather than zero');
  assert.equal(byLine.get('42')[2], null);
  assert.equal(prepared.result.line['4'].source, 'empty');
});

test('the totals are live formulas, and the formulas point at the right rows', () => {
  const { bytes } = build(freelancer());
  const book = readXlsx(bytes);
  const sheetName = 'Schedule C 2025';
  const formulas = book.formulas[sheetName];
  const rows = book.sheets[sheetName];
  const rowOf = new Map();
  rows.forEach((r, i) => { if (r[0] && !rowOf.has(String(r[0]))) rowOf.set(String(r[0]), i + 1); });

  const at = (id) => `C${rowOf.get(id)}`;
  assert.equal(formulas[at('3')], `=${at('1')}-${at('2')}`);
  assert.equal(formulas[at('7')], `=${at('5')}+${at('6')}`);
  assert.equal(formulas[at('28')], `=SUM(${at('8')}:${at('27b')})`);
  assert.equal(formulas[at('29')], `=${at('7')}-${at('28')}`);
  assert.equal(formulas[at('31')], `=${at('29')}-${at('30')}`);
  assert.equal(formulas[at('27b')], `=${at('48')}`);
});

test('each formula, worked out from the cells it names, gives the value stored beside it', () => {
  // The independent check: read the referenced cells, do the arithmetic here,
  // and compare with the cached number the file carries.
  for (const make of [freelancer, reseller, firstYearLoss]) {
    const { bytes, prepared } = build(make());
    const book = readXlsx(bytes);
    const name = `Schedule C ${prepared.result.year}`;
    const cached = book.cached[name];
    const value = (ref) => {
      const row = Number(ref.slice(1));
      const cell = cached[row - 1][2];
      return typeof cell === 'number' ? cell : 0;
    };
    const entries = Object.entries(book.formulas[name]);
    assert.ok(entries.length >= 5, `${make.name}: expected several formulas, found ${entries.length}`);
    for (const [ref, formula] of entries) {
      const body = formula.slice(1);
      let want;
      const range = body.match(/^SUM\(C(\d+):C(\d+)\)$/);
      if (range) {
        want = 0;
        for (let r = Number(range[1]); r <= Number(range[2]); r += 1) {
          const cell = cached[r - 1][2];
          if (typeof cell === 'number') want += cell;
        }
      } else if (/^C\d+-C\d+$/.test(body)) {
        const [a, b] = body.split('-');
        want = value(a) - value(b);
      } else if (/^C\d+\+C\d+$/.test(body)) {
        const [a, b] = body.split('+');
        want = value(a) + value(b);
      } else if (/^C\d+$/.test(body)) {
        want = value(body);
      } else {
        throw new Error(`unrecognised formula ${formula}`);
      }
      near(value(ref), want, `${make.name}: ${ref} holds ${formula}`);
    }
  }
});

test('the stored total agrees with the engine, to the cent', () => {
  for (const make of [freelancer, reseller, firstYearLoss, large]) {
    const { bytes, prepared } = build(make());
    const book = readXlsx(bytes);
    const rows = book.cached[`Schedule C ${prepared.result.year}`];
    const net = rows.find((r) => String(r[0]) === '31');
    near(net[2], Number(centsToDecimal(prepared.result.netProfitCents)), `${make.name} net profit`);
  }
});

test('the detail sheet carries the other-expense rows, the answers and the caveat', () => {
  const { bytes } = build(freelancer());
  const strings = xlsxStrings(readXlsx(bytes));
  const joined = strings.join(' | ');
  assert.ok(joined.includes('Editing software'));
  assert.ok(joined.includes('Website hosting'));
  assert.ok(joined.includes('Business miles (line 44a)'));
  assert.ok(joined.includes('5,510') || joined.includes('5510'));
  assert.ok(joined.includes(DISCLAIMER.slice(0, 40)));
});

test('unanswered questions say so rather than looking like a no', () => {
  const strings = xlsxStrings(readXlsx(build(sparse()).bytes)).join(' | ');
  assert.ok(strings.includes('Not answered'), 'a blank answer should say it is blank');
});

test('a prior year puts other expenses on line 27a in the spreadsheet too', () => {
  const { bytes } = build(priorYear());
  const book = readXlsx(bytes);
  const rows = book.sheets['Schedule C 2023'];
  const line27a = rows.find((r) => String(r[0]) === '27a');
  const line27b = rows.find((r) => String(r[0]) === '27b');
  assert.match(String(line27a[1]), /Other expenses/);
  assert.match(String(line27b[1]), /Energy efficient/);
  // 27a carries a formula, so read the number from the cached view.
  const cached = book.cached['Schedule C 2023'];
  const idx = rows.findIndex((r) => String(r[0]) === '27a');
  assert.equal(typeof cached[idx][2], 'number');
  assert.equal(line27b[2], null, 'the energy deduction line was not used, so it stays empty');
});

test('whole-dollar mode stores whole dollars', () => {
  const r = freelancer(); r.rounding = 'dollars';
  const book = readXlsx(build(r).bytes);
  for (const row of book.sheets['Profit and loss']) {
    for (const cell of row) {
      if (typeof cell === 'number') assert.equal(Number.isInteger(cell), true, `${cell} is not a whole dollar`);
    }
  }
});

test('the same figures on the same day give byte-identical files', () => {
  assert.deepEqual(Buffer.from(build(freelancer()).bytes), Buffer.from(build(freelancer()).bytes));
});

test('a business name with characters XML hates does not break the file', () => {
  const r = freelancer();
  r.business.name = 'Ann & Sons <Bakery> "Best" in town';
  r.details = { other: [{ label: 'Item & <thing>', cents: 100 }] };
  const book = readXlsx(build(r).bytes);
  const joined = xlsxStrings(book).join(' | ');
  assert.ok(joined.includes('Ann & Sons <Bakery>'), 'the ampersand and brackets should survive as characters');
  assert.ok(!joined.includes(''), 'the control character should have been dropped');
});

test('a return with nothing in it produces no spreadsheet at all', () => {
  assert.throws(() => build({ ...sparse(), entries: {} }), /Nothing has been entered/);
});

test('the file is named after the business and the year', () => {
  assert.equal(build(freelancer()).name, 'Rowan-Vale-Photography-2025-profit-and-loss.xlsx');
});
