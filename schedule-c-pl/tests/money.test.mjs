/* Money. Everything here is about the two ways a financial tool loses trust:
   a float that drifts, and a blank that quietly becomes a zero. */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseMoney, roundToDollars, formatCents, formatDollars, sumCents, MAX_CENTS } from '../src/money.mjs';

const ok = (raw, cents) => assert.deepEqual(parseMoney(raw), { ok: true, cents }, `parse ${JSON.stringify(raw)}`);
const no = (raw) => assert.equal(parseMoney(raw).ok, false, `${JSON.stringify(raw)} should be refused`);

test('the shapes people actually type', () => {
  ok('1234.56', 123456);
  ok('1,234.56', 123456);
  ok('$1,234.56', 123456);
  ok(' 1 234.56 ', 123456);
  ok('1234', 123400);
  ok('1234.5', 123450);
  ok('0', 0);
  ok('0.00', 0);
  ok('.5', 50);
  ok('+42', 4200);
});

test('a negative written any of the three ways people write it', () => {
  ok('-500', -50000);
  ok('(500)', -50000);
  ok('($1,234.56)', -123456);
  ok('-0.01', -1);
  ok('(-5)', 500); // brackets round a minus: two negatives
});

test('empty is null, and null is not zero', () => {
  ok('', null);
  ok('   ', null);
  ok(null, null);
  ok(undefined, null);
  assert.notEqual(parseMoney('').cents, 0);
  assert.equal(parseMoney('0').cents, 0);
});

test('rubbish is refused, with a sentence a person can act on', () => {
  for (const bad of ['abc', '1.2.3', '12e5', '--5', '()', '1,2,3.456', '∞', 'NaN', '0x10', '1/2', '5%']) no(bad);
  assert.match(parseMoney('abc').error, /numbers only/);
  assert.match(parseMoney('1.234').error, /two places/);
  assert.match(parseMoney('9'.repeat(20)).error, /too big/);
});

test('three decimal places is refused rather than silently trimmed', () => {
  no('1.234');
  no('0.005');
  ok('1.23', 123);
});

test('the ceiling holds, and everything under it is an exact integer', () => {
  const at = parseMoney(String(MAX_CENTS / 100));
  assert.equal(at.ok, true);
  assert.equal(Number.isSafeInteger(at.cents), true);
  no('99999999999999999999');
});

test('rounding to whole dollars matches the IRS rule, in both directions', () => {
  assert.equal(roundToDollars(1249), 1200);
  assert.equal(roundToDollars(1250), 1300);
  assert.equal(roundToDollars(1299), 1300);
  assert.equal(roundToDollars(-1249), -1200);
  assert.equal(roundToDollars(-1250), -1300);
  assert.equal(roundToDollars(0), 0);
  assert.equal(roundToDollars(49), 0);
  assert.equal(roundToDollars(50), 100);
  assert.equal(roundToDollars(null), null);
  // -1 cent rounds to zero, and zero has no sign.
  assert.ok(Object.is(roundToDollars(-1), 0), 'rounding must not produce -0');
  assert.ok(Object.is(roundToDollars(-49), 0));
  assert.ok(Object.is(roundToDollars(0), 0));
});

test('formatting: brackets for a loss, groups of three, blank for nothing', () => {
  assert.equal(formatCents(123456789), '1,234,567.89');
  assert.equal(formatCents(-123456), '(1,234.56)');
  assert.equal(formatCents(5), '0.05');
  assert.equal(formatCents(null), '');
  assert.equal(formatCents(null, { blank: '—' }), '—');
  assert.equal(formatCents(123456, { dollars: true }), '1,234');
  assert.equal(formatDollars(-123456), '($1,234.56)');
  assert.equal(formatDollars(0), '$0.00');
});

test('adding skips what was never filled in', () => {
  assert.equal(sumCents([100, null, 200, undefined]), 300);
  assert.equal(sumCents([]), 0);
  assert.equal(sumCents([null, null]), 0);
});

test('a hundred additions of a third of a dollar land exactly, which a float would not', () => {
  const cents = Array.from({ length: 100 }, () => 33);
  assert.equal(sumCents(cents), 3300);
  // The same sum in dollars-as-floats is famously not 33.
  const floats = Array.from({ length: 100 }, () => 0.33).reduce((a, b) => a + b, 0);
  assert.notEqual(floats, 33);
});
