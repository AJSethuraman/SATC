/* The three calculators, and the line they are not allowed to cross.

   Each one is arithmetic on a published IRS figure. None of them decides
   whether the filer may use it — that choice is made before the number gets
   here, and the tests below check that the tool says so rather than implying
   an answer. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mileage, simplifiedHomeOffice, mealsHalf, netPurchases, REFUSALS, relevantRefusals } from '../src/helpers.mjs';
import { loadYear, supportedYears } from '../src/years.mjs';
import { compute } from '../src/engine.mjs';
import { firstYearLoss, freelancer, sparse } from './fixtures.mjs';

const y2025 = loadYear(2025);
const y2024 = loadYear(2024);
const y2023 = loadYear(2023);

test('mileage uses the right rate for the right year', () => {
  assert.equal(mileage({ miles: 1000, yearData: y2025 }).cents, 70000);
  assert.equal(mileage({ miles: 1000, yearData: y2024 }).cents, 67000);
  assert.equal(mileage({ miles: 1000, yearData: y2023 }).cents, 65500);
});

test('a half-cent rate stays exact over an odd number of miles', () => {
  // 65.5 cents x 1 mile is 65.5 cents. Rounded to the nearest cent that is 66,
  // and a float would have made this 65.49999999999999.
  assert.equal(mileage({ miles: 1, yearData: y2023 }).cents, 66);
  assert.equal(mileage({ miles: 3, yearData: y2023 }).cents, 197); // 196.5 -> 197
  assert.equal(mileage({ miles: 2, yearData: y2023 }).cents, 131);
});

test('mileage says what it did, and where the rate comes from', () => {
  const out = mileage({ miles: 12_345, yearData: y2025 });
  assert.equal(out.cents, 864_150); // 12,345 miles at 70 cents is $8,641.50
  assert.match(out.basis, /12,345 business miles at 70 cents a mile/);
  assert.match(out.cite, /Notice 2025-5/);
});

test('mileage refuses what it cannot answer', () => {
  for (const bad of ['', null, undefined, 'abc', NaN, 1.5, -10, 99_999_999]) {
    assert.equal(mileage({ miles: bad, yearData: y2025 }).ok, false, `miles=${bad}`);
  }
  assert.match(mileage({ miles: 1.5, yearData: y2025 }).error, /Whole miles/);
  assert.match(mileage({ miles: -1, yearData: y2025 }).error, /negative/);
});

test('a year whose rate changed part-way through is refused rather than averaged', () => {
  const split = structuredClone(y2025);
  split.parameters.standardMileage.periods = [
    { from: '2026-01-01', through: '2026-06-30', tenthCents: 725 },
    { from: '2026-07-01', through: '2026-12-31', tenthCents: 760 },
  ];
  const out = mileage({ miles: 1000, yearData: split });
  assert.equal(out.ok, false);
  assert.match(out.error, /split across the two periods/);
});

test('the square-foot method caps at 300 square feet and says it capped', () => {
  assert.equal(simplifiedHomeOffice({ sqft: 120, yearData: y2025 }).cents, 60000);
  assert.equal(simplifiedHomeOffice({ sqft: 300, yearData: y2025 }).cents, 150000);
  const over = simplifiedHomeOffice({ sqft: 900, yearData: y2025 });
  assert.equal(over.cents, 150000);
  assert.equal(over.capped, true);
  assert.match(over.basis, /the most this method counts/);
  assert.equal(simplifiedHomeOffice({ sqft: 0, yearData: y2025 }).cents, 0);
});

test('the square-foot method refuses fractions, negatives and nonsense', () => {
  for (const bad of ['', null, 'big', 12.5, -1, 200_000]) {
    assert.equal(simplifiedHomeOffice({ sqft: bad, yearData: y2025 }).ok, false, `sqft=${bad}`);
  }
});

test('half of meals rounds up on the half cent and carries its own caveat', () => {
  assert.equal(mealsHalf({ spentCents: 1000, yearData: y2025 }).cents, 500);
  assert.equal(mealsHalf({ spentCents: 1001, yearData: y2025 }).cents, 501);
  assert.equal(mealsHalf({ spentCents: 1, yearData: y2025 }).cents, 1);
  assert.equal(mealsHalf({ spentCents: -1001, yearData: y2025 }).cents, -501);
  assert.match(mealsHalf({ spentCents: 1000, yearData: y2025 }).caveat, /80%/);
});

test('half of meals refuses anything that is not already cents', () => {
  for (const bad of [null, undefined, 12.5, '100']) {
    assert.equal(mealsHalf({ spentCents: bad, yearData: y2025 }).ok, false, `${bad}`);
  }
});

test('purchases net off what the owner took for themselves', () => {
  assert.equal(netPurchases({ purchasesCents: 100000, personalUseCents: 15000 }).cents, 85000);
  assert.equal(netPurchases({ purchasesCents: 100000, personalUseCents: null }).cents, 100000);
  assert.equal(netPurchases({ purchasesCents: null }).ok, false);
});

test('the refusals name a line, say why, and say what to do instead', () => {
  assert.ok(REFUSALS.length >= 4);
  for (const r of REFUSALS) {
    assert.ok(r.line && r.subject && r.because && r.instead, `incomplete refusal for line ${r.line}`);
    assert.ok(r.instead.length > 10);
  }
  assert.deepEqual(REFUSALS.map((r) => r.line).sort(), ['13', '30', '32', '9']);
});

test('a document only carries the refusals that bear on it', () => {
  const bare = relevantRefusals(compute(sparse()));
  assert.deepEqual(bare, [], 'a one-line return has nothing to refuse');

  const loss = relevantRefusals(compute(firstYearLoss()));
  assert.deepEqual(loss.map((r) => r.line).sort(), ['13', '32'], 'depreciation entered, and it lost money');

  const pro = relevantRefusals(compute(freelancer()));
  assert.deepEqual(pro.map((r) => r.line).sort(), ['30', '9']);
});

test('every supported year carries a rate, a square-foot figure and a meals percentage', () => {
  for (const year of supportedYears()) {
    const y = loadYear(year);
    assert.ok(mileage({ miles: 100, yearData: y }).ok, `${year} mileage`);
    assert.ok(simplifiedHomeOffice({ sqft: 100, yearData: y }).ok, `${year} home office`);
    assert.ok(mealsHalf({ spentCents: 100, yearData: y }).ok, `${year} meals`);
  }
});
