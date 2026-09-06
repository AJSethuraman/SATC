/* Properties, not examples.

   The example tests above check the returns I thought of. These check the ones
   I did not: fast-check throws thousands of shapes at the engine and asserts
   the relationships that must hold for every one of them. When one fails it
   shrinks the input to the smallest case that still breaks, which is usually
   the bug written out in one line.

   The seed is fixed so a failure is reproducible; raise the run count with
   FC_RUNS=5000 npm test when you want a harder look. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fc from 'fast-check';
import { compute, emptyReturn } from '../src/engine.mjs';
import { parseMoney, formatCents, roundToDollars, sumCents, MAX_CENTS } from '../src/money.mjs';
import { mileage, simplifiedHomeOffice, mealsHalf } from '../src/helpers.mjs';
import { loadYear, supportedYears } from '../src/years.mjs';
import { EXPENSE_LINES, COGS_LINES } from '../src/lines.mjs';

const runs = Number(process.env.FC_RUNS || 800);
const CONFIG = { numRuns: runs, seed: 20260906, verbose: false };

/** Cents within the range the tool accepts, positive or negative. */
const money = fc.integer({ min: -50_000_000_00, max: 50_000_000_00 });
const maybeMoney = fc.option(money, { nil: undefined });

/** A whole return, entered at random. */
const aReturn = fc.record({
  year: fc.constantFrom(...supportedYears()),
  entries: fc.dictionary(
    fc.constantFrom('1', '2', '6', ...EXPENSE_LINES.filter((l) => !['27a', '27b'].includes(l)), '30', ...COGS_LINES, '41'),
    money,
    { maxKeys: 20 },
  ),
  otherRows: fc.array(fc.record({ label: fc.string(), cents: money }), { maxLength: 6 }),
}).map(({ year, entries, otherRows }) => {
  const r = emptyReturn(year);
  r.entries = entries;
  r.details = otherRows.length ? { other: otherRows } : {};
  return r;
});

test('line 28 is always exactly the sum of the twenty-four expense lines', () => {
  fc.assert(fc.property(aReturn, (r) => {
    const out = compute(r);
    const parts = EXPENSE_LINES.map((id) => out.line[id].cents);
    assert.equal(out.line['28'].cents, parts.reduce((a, b) => a + b, 0));
  }), CONFIG);
});

test('net profit is always gross income less expenses less the home office', () => {
  fc.assert(fc.property(aReturn, (r) => {
    const { line } = compute(r);
    assert.equal(line['31'].cents, line['7'].cents - line['28'].cents - line['30'].cents);
    assert.equal(line['29'].cents, line['7'].cents - line['28'].cents);
  }), CONFIG);
});

test('cost of goods sold is always Part III, and always reaches line 4', () => {
  fc.assert(fc.property(aReturn, (r) => {
    const { line } = compute(r);
    const available = COGS_LINES.map((id) => line[id].cents).reduce((a, b) => a + b, 0);
    assert.equal(line['40'].cents, available);
    assert.equal(line['42'].cents, available - line['41'].cents);
    assert.equal(line['4'].cents, line['42'].cents);
    assert.equal(line['5'].cents, line['3'].cents - line['42'].cents);
  }), CONFIG);
});

test('other expenses always land on the right line for the year, and never on the other one', () => {
  fc.assert(fc.property(aReturn, (r) => {
    const out = compute(r);
    const slot = out.otherExpensesLine;
    const otherSlot = slot === '27a' ? '27b' : '27a';
    assert.equal(out.line[slot].cents, out.line['48'].cents);
    assert.equal(out.line[otherSlot].source, 'empty');
  }), CONFIG);
});

test('no line is ever NaN, Infinity or a fraction of a cent', () => {
  fc.assert(fc.property(aReturn, (r) => {
    for (const [id, v] of Object.entries(compute(r).line)) {
      assert.ok(Number.isSafeInteger(v.cents), `line ${id} came out ${v.cents}`);
    }
  }), CONFIG);
});

test('adding a dollar to any expense moves the profit down by exactly a dollar', () => {
  fc.assert(fc.property(aReturn, fc.constantFrom(...EXPENSE_LINES.filter((l) => !['27a', '27b'].includes(l))), money,
    (r, id, delta) => {
      const before = compute(r).line['31'].cents;
      const bumped = { ...r, entries: { ...r.entries, [id]: (r.entries[id] || 0) + delta } };
      assert.equal(compute(bumped).line['31'].cents, before - delta);
    }), CONFIG);
});

test('adding a dollar of sales moves the profit up by exactly a dollar', () => {
  fc.assert(fc.property(aReturn, money, (r, delta) => {
    const before = compute(r).line['31'].cents;
    const bumped = { ...r, entries: { ...r.entries, 1: (r.entries['1'] || 0) + delta } };
    assert.equal(compute(bumped).line['31'].cents, before + delta);
  }), CONFIG);
});

test('the same return computed twice gives byte-identical lines', () => {
  fc.assert(fc.property(aReturn, (r) => {
    assert.deepEqual(compute(r).line, compute(structuredClone(r)).line);
  }), CONFIG);
});

test('a line nobody entered never reports itself as entered', () => {
  fc.assert(fc.property(aReturn, (r) => {
    const out = compute(r);
    for (const l of out.yearData.lines) {
      if (l.kind !== 'entry') continue;
      const wasTyped = r.entries[l.id] !== undefined;
      const hasList = l.id === out.otherExpensesLine;
      if (!wasTyped && !hasList) assert.equal(out.line[l.id].source, 'empty', `line ${l.id}`);
    }
  }), CONFIG);
});

test('what is printed can always be read back as the same money', () => {
  fc.assert(fc.property(fc.integer({ min: -MAX_CENTS, max: MAX_CENTS }), (cents) => {
    const printed = formatCents(cents);
    const read = parseMoney(printed);
    assert.equal(read.ok, true, `could not read back ${printed}`);
    assert.equal(read.cents, cents);
  }), CONFIG);
});

test('parsing never throws, whatever a person types', () => {
  fc.assert(fc.property(fc.string({ maxLength: 40 }), (s) => {
    const out = parseMoney(s);
    assert.ok(typeof out.ok === 'boolean');
    if (out.ok && out.cents !== null) assert.ok(Number.isSafeInteger(out.cents));
    else if (!out.ok) assert.ok(out.error.length > 0);
  }), CONFIG);
});

test('rounding to dollars never moves a figure by more than fifty cents, and never produces -0', () => {
  fc.assert(fc.property(fc.integer({ min: -MAX_CENTS, max: MAX_CENTS }), (cents) => {
    const r = roundToDollars(cents);
    assert.equal(Math.abs(r % 100), 0, 'a rounded figure is a whole number of dollars');
    assert.ok(!Object.is(r, -0), 'and never negative zero');
    assert.ok(Math.abs(r - cents) <= 50);
    assert.equal(Math.sign(r) === 0 || Math.sign(r) === Math.sign(cents), true);
  }), CONFIG);
});

test('rounding to dollars never reorders two figures', () => {
  fc.assert(fc.property(money, money, (a, b) => {
    if (a <= b) assert.ok(roundToDollars(a) <= roundToDollars(b));
  }), CONFIG);
});

test('the whole-dollar column can only ever be out by half a dollar per line', () => {
  // This is the rounding note in the documents, stated as a bound. If it ever
  // fails, the note is understating the problem.
  fc.assert(fc.property(fc.array(money, { minLength: 1, maxLength: 24 }), (values) => {
    const roundedParts = sumCents(values.map(roundToDollars));
    const roundedTotal = roundToDollars(sumCents(values));
    assert.ok(Math.abs(roundedParts - roundedTotal) <= 50 * values.length);
  }), CONFIG);
});

test('mileage never decreases as the miles go up, and matches the rate exactly', () => {
  fc.assert(fc.property(fc.constantFrom(...supportedYears()), fc.nat({ max: 500_000 }), fc.nat({ max: 1000 }),
    (year, miles, more) => {
      const y = loadYear(year);
      const a = mileage({ miles, yearData: y });
      const b = mileage({ miles: miles + more, yearData: y });
      assert.ok(b.cents >= a.cents);
      const tenths = miles * y.parameters.standardMileage.periods[0].tenthCents;
      assert.equal(a.cents, Math.floor(tenths / 10) + (tenths % 10 >= 5 ? 1 : 0));
    }), CONFIG);
});

test('the square-foot method never returns more than the cap, whatever the input', () => {
  fc.assert(fc.property(fc.nat({ max: 90_000 }), (sqft) => {
    const out = simplifiedHomeOffice({ sqft, yearData: loadYear(2025) });
    assert.ok(out.cents <= 150000);
    assert.equal(out.cents, Math.min(sqft, 300) * 500);
  }), CONFIG);
});

test('half of meals is never more than what was spent, and never the wrong sign', () => {
  fc.assert(fc.property(money, (spent) => {
    const out = mealsHalf({ spentCents: spent, yearData: loadYear(2025) });
    assert.ok(Math.abs(out.cents) <= Math.abs(spent));
    if (spent !== 0) assert.equal(Math.sign(out.cents) === 0 || Math.sign(out.cents) === Math.sign(spent), true);
  }), CONFIG);
});

test('a return that is refused is refused for a reason it can name', () => {
  fc.assert(fc.property(aReturn, (r) => {
    const out = compute(r);
    for (const b of out.blockers) assert.ok(b.message && b.message.length > 5);
    if (out.hasFigures) assert.ok(!out.blockers.some((b) => /Nothing has been entered/.test(b.message)));
  }), CONFIG);
});

test('an empty entries object and a missing one behave the same', () => {
  fc.assert(fc.property(fc.constantFrom(...supportedYears()), (year) => {
    const a = emptyReturn(year);
    const b = emptyReturn(year);
    delete b.entries;
    delete b.details;
    assert.deepEqual(compute(a).line, compute(b).line);
  }), CONFIG);
});

test('unused stress: every fixture-sized random return produces every line', () => {
  fc.assert(fc.property(aReturn, maybeMoney, (r, extra) => {
    if (extra !== undefined) r.entries['22'] = extra;
    const out = compute(r);
    assert.equal(Object.keys(out.line).length, out.yearData.lines.length);
  }), CONFIG);
});
