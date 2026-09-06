/* The arithmetic, and the cases where a tool that only did arithmetic would be
   wrong: nothing entered, half entered, a loss, a contradiction, a figure on a
   line the filer is not allowed to type into. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compute, emptyReturn } from '../src/engine.mjs';
import { freelancer, reseller, firstYearLoss, sparse, priorYear, large } from './fixtures.mjs';

const c = (d) => Math.round(d * 100);
const cents = (r, id) => compute(r).line[id].cents;

test('a return with nothing in it computes, and says it has nothing', () => {
  const r = emptyReturn(2025);
  const out = compute(r);
  assert.equal(out.hasFigures, false);
  assert.equal(out.blockers.length, 1);
  assert.match(out.blockers[0].message, /Nothing has been entered/);
  for (const id of ['1', '3', '7', '28', '31', '42']) {
    assert.equal(out.line[id].source, 'empty', `line ${id}`);
    assert.equal(out.line[id].cents, 0);
  }
});

test('one line in, everything downstream still knows what is blank', () => {
  const out = compute(sparse());
  assert.equal(out.line['1'].source, 'entered');
  assert.equal(out.line['3'].source, 'computed');
  assert.equal(out.line['4'].source, 'empty', 'no stock, so line 4 stays blank rather than printing zero');
  assert.equal(out.line['30'].source, 'empty');
  assert.equal(out.line['31'].cents, c(1000));
});

test('the full chain, line by line, on a real return', () => {
  const out = compute(freelancer());
  assert.equal(out.line['3'].cents, c(94_250) - c(1_100));
  assert.equal(out.line['5'].cents, out.line['3'].cents - out.line['4'].cents);
  assert.equal(out.line['7'].cents, out.line['5'].cents + c(420));
  assert.equal(out.line['27b'].cents, c(599.88) + c(214.20) + c(325));
  assert.equal(out.line['48'].cents, out.line['27b'].cents);
  assert.equal(out.line['29'].cents, out.line['7'].cents - out.line['28'].cents);
  assert.equal(out.line['31'].cents, out.line['29'].cents - out.line['30'].cents);
  assert.equal(out.line['31'].cents, 7_324_454);
});

test('cost of goods sold flows through Part III into line 4 and out to line 5', () => {
  const out = compute(reseller());
  const available = c(42_800) + c(96_215.44) + c(3_200) + c(1_845.10) + c(2_610);
  assert.equal(out.line['40'].cents, available);
  assert.equal(out.line['42'].cents, available - c(38_950.25));
  assert.equal(out.line['4'].cents, out.line['42'].cents, 'line 4 is line 42');
  assert.equal(out.line['5'].cents, out.line['3'].cents - out.line['42'].cents);
  assert.ok(out.line['31'].cents > 0);
});

test('a loss comes out negative and is not clamped to zero', () => {
  const out = compute(firstYearLoss());
  assert.equal(out.line['31'].cents, -c(19_540));
  assert.ok(out.line['31'].cents < 0);
});

test('a loss with line 32 unanswered is flagged, and answering it clears the flag', () => {
  const r = firstYearLoss();
  const flagged = compute(r).notices.filter((n) => n.line === '32' && n.level === 'warn');
  assert.equal(flagged.length, 1);
  r.atRisk = 'all';
  assert.equal(compute(r).notices.filter((n) => n.line === '32').length, 0);
  r.atRisk = 'some';
  assert.match(compute(r).notices.find((n) => n.line === '32').message, /6198/);
});

test('a profit never asks the at-risk question', () => {
  const out = compute(freelancer());
  assert.equal(out.notices.filter((n) => n.line === '32').length, 0);
});

test('a total typed over a list that already adds up is refused, not silently picked', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(1000), 8: c(500) };
  r.details = { 8: [{ label: 'Flyers', cents: c(300) }] };
  const out = compute(r);
  assert.equal(out.blockers.length, 1);
  assert.match(out.blockers[0].message, /both a total typed in and a list/);
});

test('a figure typed onto a worked-out line is refused', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(1000), 28: c(999) };
  const out = compute(r);
  assert.ok(out.blockers.some((b) => b.line === '28' && /worked out/.test(b.message)));
});

test('other expenses move to line 27a for 2023 and stay off 27b', () => {
  const out = compute(priorYear());
  assert.equal(out.otherExpensesLine, '27a');
  assert.equal(out.line['27a'].cents, c(599.88) + c(214.20) + c(325));
  assert.equal(out.line['27b'].source, 'empty');
  assert.equal(out.line['31'].cents, compute(freelancer()).line['31'].cents,
    'the same figures give the same profit whichever line they sit on');
});

test('big figures stay exact', () => {
  const out = compute(large());
  assert.equal(out.line['28'].cents, 123_456_789_01 + 111_111_111_11);
  assert.equal(out.line['31'].cents, 987_654_321_09 - 123_456_789_01 - 111_111_111_11);
  assert.equal(Number.isSafeInteger(out.line['31'].cents), true);
});

test('a negative expense is allowed but noticed', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(5000), 8: -c(120) };
  const out = compute(r);
  assert.equal(out.line['8'].cents, -12000);
  assert.ok(out.notices.some((n) => n.line === '8' && /negative/.test(n.message)));
});

test('refunds bigger than sales are noticed rather than refused', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(100), 2: c(400) };
  const out = compute(r);
  assert.equal(out.line['3'].cents, -c(300));
  assert.ok(out.notices.some((n) => n.line === '2'));
});

test('closing stock above what was available is noticed', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(1000), 35: c(100), 41: c(900) };
  const out = compute(r);
  assert.equal(out.line['42'].cents, -c(800));
  assert.ok(out.notices.some((n) => n.line === '41'));
});

test('the square-foot home office method cannot push a business into a loss', () => {
  const r = emptyReturn(2025);
  r.homeOfficeMethod = 'simplified';
  r.entries = { 1: c(2_000), 8: c(1_500), 30: c(1_500) };
  const out = compute(r);
  const warn = out.notices.find((n) => n.line === '30' && n.level === 'warn');
  assert.ok(warn, 'expected a warning');
  assert.equal(warn.cap, c(500), 'the cap is line 29');
  // It warns; it does not quietly change the figure.
  assert.equal(out.line['30'].cents, c(1_500));
  assert.equal(out.line['31'].cents, -c(1_000));
});

test('the same cap does not fire when the deduction fits', () => {
  const r = emptyReturn(2025);
  r.homeOfficeMethod = 'simplified';
  r.entries = { 1: c(9_000), 8: c(1_500), 30: c(1_500) };
  assert.equal(compute(r).notices.filter((n) => n.line === '30').length, 0);
});

test('car expenses with no miles recorded is flagged', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(5_000), 9: c(1_200) };
  assert.ok(compute(r).notices.some((n) => n.line === '9'));
  r.vehicle = { businessMiles: 1700 };
  assert.equal(compute(r).notices.filter((n) => n.line === '9').length, 0);
});

test('more than nine other-expense rows is flagged, nine is not', () => {
  const rows = (n) => Array.from({ length: n }, (_, i) => ({ label: `Item ${i}`, cents: 100 }));
  const r = emptyReturn(2025);
  r.entries = { 1: c(1_000) };
  r.details = { other: rows(9) };
  assert.equal(compute(r).notices.filter((n) => n.line === '48').length, 0);
  r.details = { other: rows(10) };
  assert.equal(compute(r).notices.filter((n) => n.line === '48').length, 1);
});

test('computing twice gives the identical answer', () => {
  const r = freelancer();
  assert.deepEqual(compute(r).line, compute(r).line);
});

test('an unknown tax year is refused and says why', () => {
  const r = emptyReturn(1999);
  assert.throws(() => compute(r), /does not have tax year 1999/);
  assert.throws(() => compute(r), /27a and 27b/);
});

test('every line is a finite integer number of cents, on every fixture', () => {
  for (const make of [freelancer, reseller, firstYearLoss, sparse, priorYear, large]) {
    const out = compute(make());
    for (const [id, value] of Object.entries(out.line)) {
      assert.ok(Number.isSafeInteger(value.cents), `line ${id} is ${value.cents}`);
    }
  }
});

test('line 28 equals the sum of what the statement shows under expenses', () => {
  for (const make of [freelancer, reseller, firstYearLoss, large]) {
    const out = compute(make());
    const parts = out.yearData.byId.get('28').formula.of.map((id) => out.line[id].cents);
    assert.equal(out.line['28'].cents, parts.reduce((a, b) => a + b, 0));
  }
});

test('an entry of exactly zero is kept as an answer, not treated as blank', () => {
  const r = emptyReturn(2025);
  r.entries = { 1: c(1_000), 22: 0 };
  const out = compute(r);
  assert.equal(out.line['22'].source, 'entered');
  assert.equal(out.line['22'].cents, 0);
});
