/* A tax figure with no citation is folklore, and folklore in a CPA's tool is
   the thing that ends a licence. This is the gate that keeps one out.

   It is also the January test: add next year's file, run this, and it tells
   you what you forgot. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadYear, supportedYears, hasYear } from '../src/years.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const YEAR_DIR = join(HERE, '..', 'years');

test('the years on disk are exactly the years on offer', () => {
  const onDisk = readdirSync(YEAR_DIR).filter((f) => /^\d{4}\.mjs$/.test(f))
    .map((f) => Number(f.slice(0, 4))).sort((a, b) => b - a);
  assert.deepEqual(supportedYears(), onDisk,
    'a year file was added without being registered in src/years.mjs, or the other way round');
});

test('every parameter of every year names the page it came from', () => {
  for (const year of supportedYears()) {
    const y = loadYear(year);
    const params = Object.entries(y.parameters);
    assert.ok(params.length >= 3, `${year} has only ${params.length} parameters`);
    for (const [name, p] of params) {
      assert.match(p.source || '', /^https:\/\/www\.irs\.gov\//,
        `${year} ${name} has no irs.gov source`);
      assert.ok((p.cite || '').length > 8, `${year} ${name} has no citation`);
      assert.ok((p.display || '').length > 0, `${year} ${name} has nothing to show a reader`);
    }
  }
});

test('every year names the form it was built from, and when that was read', () => {
  for (const year of supportedYears()) {
    const { form } = loadYear(year);
    assert.match(form.source, /^https:\/\/www\.irs\.gov\//);
    assert.match(form.instructions, /^https:\/\/www\.irs\.gov\//);
    assert.match(form.retrieved, /^\d{4}-\d{2}-\d{2}$/);
    assert.match(form.revision, new RegExp(String(year)));
  }
});

test('a mileage rate is a whole number of tenths of a cent, in a sane range', () => {
  for (const year of supportedYears()) {
    const { periods } = loadYear(year).parameters.standardMileage;
    assert.ok(periods.length >= 1);
    for (const p of periods) {
      assert.ok(Number.isInteger(p.tenthCents), `${year} rate is not an integer`);
      assert.ok(p.tenthCents > 300 && p.tenthCents < 1500, `${year} rate ${p.tenthCents} looks wrong`);
      assert.match(p.from, new RegExp(`^${year}-`));
      assert.match(p.through, new RegExp(`^${year}-`));
    }
  }
});

test('the rates are the ones the IRS published, year by year', () => {
  // Cross-checked against irs.gov/tax-professionals/standard-mileage-rates
  // on 6 September 2026. These are the numbers, not a formula.
  assert.equal(loadYear(2023).parameters.standardMileage.periods[0].tenthCents, 655);
  assert.equal(loadYear(2024).parameters.standardMileage.periods[0].tenthCents, 670);
  assert.equal(loadYear(2025).parameters.standardMileage.periods[0].tenthCents, 700);
});

test('the square-foot method is $5 up to 300 feet in every year we support', () => {
  for (const year of supportedYears()) {
    const p = loadYear(year).parameters.simplifiedHomeOffice;
    assert.equal(p.ratePerSqFtCents, 500);
    assert.equal(p.maxSqFt, 300);
  }
});

test('meals are half, and the years that are not half are named', () => {
  for (const year of supportedYears()) {
    const p = loadYear(year).parameters.mealsDeductiblePercent;
    assert.equal(p.percent, 50);
    assert.match(p.caveat, /80%/, 'the hours-of-service exception has to travel with the figure');
  }
});

test('an unsupported year is refused, and the refusal explains itself', () => {
  assert.equal(hasYear(2019), false);
  assert.equal(hasYear(2025), true);
  for (const year of [2019, 2026, 'banana', null]) {
    assert.throws(() => loadYear(year), /does not have tax year/, `year ${year}`);
  }
  try {
    loadYear(2026);
  } catch (e) {
    assert.match(e.message, /2025, 2024, 2023/, 'it should say what it does have');
    assert.match(e.message, /will not guess/, 'and say why it will not improvise');
  }
});

test('every year is marked final or draft, and nothing draft is on offer by accident', () => {
  for (const year of supportedYears()) {
    const y = loadYear(year);
    assert.ok(['final', 'draft'].includes(y.status), `${year} status is ${y.status}`);
  }
});
