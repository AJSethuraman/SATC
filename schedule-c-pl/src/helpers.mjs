/* Three optional calculators, and a clear account of why there are only three.

   The tool organises figures the filer already has. It does not decide what is
   deductible. So a calculator only earns its place here if it is (a) pure
   arithmetic on a published IRS figure and (b) something the filer has already
   decided to use. Standard mileage, the simplified home office method and the
   fifty percent on meals all pass. Everything else — actual vehicle costs,
   depreciation, Form 8829, the at-risk limit — does not, and REFUSALS below
   says so out loud rather than leaving a silence the user has to interpret. */

import { MAX_CENTS } from './money.mjs';

const fail = (error) => ({ ok: false, error });

function rateForYear(yearData) {
  const periods = yearData.parameters.standardMileage.periods;
  if (periods.length !== 1) return null; // a split year needs miles per period
  return periods[0].tenthCents;
}

/** Business miles × the year's rate. Miles are whole miles; the IRS rate is
    held in tenths of a cent so 65.5 never becomes a float. */
export function mileage({ miles, yearData }) {
  const n = Number(miles);
  if (miles === '' || miles === null || miles === undefined || !Number.isFinite(n)) {
    return fail('Enter the business miles you drove.');
  }
  if (!Number.isInteger(n)) return fail('Whole miles, please.');
  if (n < 0) return fail('Miles cannot be negative.');
  if (n > 5_000_000) return fail('That is more miles than this tool will accept.');

  const tenthCents = rateForYear(yearData);
  if (tenthCents === null) {
    return fail(
      'The rate changed part-way through this year, so the miles have to be ' +
      'split across the two periods. Work it out and enter the total.',
    );
  }
  const raw = n * tenthCents; // tenths of a cent, exact
  const cents = Math.floor(raw / 10) + (raw % 10 >= 5 ? 1 : 0);
  return {
    ok: true,
    cents,
    basis: `${n.toLocaleString('en-US')} business miles at ${yearData.parameters.standardMileage.display}`,
    cite: yearData.parameters.standardMileage.cite,
  };
}

/** The simplified method: $5 a square foot, capped at 300 square feet. It does
    NOT apply the gross income limit — the engine does that, because the limit
    depends on line 29 and this function has never seen line 29. */
export function simplifiedHomeOffice({ sqft, yearData }) {
  const n = Number(sqft);
  if (sqft === '' || sqft === null || sqft === undefined || !Number.isFinite(n)) {
    return fail('Enter the square feet you use for business.');
  }
  if (!Number.isInteger(n)) return fail('Whole square feet, please.');
  if (n < 0) return fail('Square feet cannot be negative.');
  if (n > 100_000) return fail('That is larger than this method allows for.');

  const { ratePerSqFtCents, maxSqFt, display } = yearData.parameters.simplifiedHomeOffice;
  const counted = Math.min(n, maxSqFt);
  return {
    ok: true,
    cents: counted * ratePerSqFtCents,
    basis: counted < n
      ? `${maxSqFt} square feet at ${display} — the most this method counts`
      : `${counted} square feet at ${display}`,
    capped: counted < n,
    cite: yearData.parameters.simplifiedHomeOffice.cite,
  };
}

/** Half of what was spent on meals. The caveat travels with the answer, because
    a driver under hours-of-service rules deducts 80% and this would be wrong. */
export function mealsHalf({ spentCents, yearData }) {
  if (spentCents === null || spentCents === undefined) return fail('Enter what you spent on meals.');
  if (!Number.isInteger(spentCents)) return fail('Enter what you spent on meals.');
  if (Math.abs(spentCents) > MAX_CENTS) return fail('That number is too big for this tool.');

  const { percent, display, caveat, cite } = yearData.parameters.mealsDeductiblePercent;
  const sign = spentCents < 0 ? -1 : 1;
  const abs = Math.abs(spentCents) * percent;
  const cents = sign * (Math.floor(abs / 100) + (abs % 100 >= 50 ? 1 : 0));
  return { ok: true, cents, basis: display, caveat, cite };
}

/** Gross purchases less what the owner took for themselves — line 36 is
    already a net figure on the form, and people forget the second half. */
export function netPurchases({ purchasesCents, personalUseCents }) {
  if (purchasesCents === null || purchasesCents === undefined) return fail('Enter what you bought.');
  const personal = personalUseCents ?? 0;
  return {
    ok: true,
    cents: purchasesCents - personal,
    basis: 'what you bought, less anything you took for yourself',
  };
}

/** What this tool will not work out, and what to use instead. Shown in the
    interface and printed on the worksheet, so a filer is never left to assume
    a blank line means zero. */
export const REFUSALS = [
  {
    line: '9',
    subject: 'Car and truck costs, if you are not using the mileage rate',
    because: 'Adding up petrol, repairs and depreciation needs the cost of the vehicle and the share of miles that were for business.',
    instead: 'Work out the deduction the way you always do, or use the mileage rate above.',
  },
  {
    line: '13',
    subject: 'Depreciation and equipment written off',
    because: 'It depends on what each item cost, when you started using it, and what you have already claimed in earlier years.',
    instead: 'Take the figure from your depreciation schedule or Form 4562 and type it in.',
  },
  {
    line: '30',
    subject: 'Business use of your home, the detailed way',
    because: 'The detailed method needs your mortgage or rent, taxes, insurance, utilities and repairs, split by floor area.',
    instead: 'Use Form 8829 and enter the result, or use the square-foot method above.',
  },
  {
    line: '32',
    subject: 'Whether a loss is one you can actually use this year',
    because: 'That depends on money you have at risk, on other income, and on rules that reach outside this form.',
    instead: 'This tool shows the loss. Whether you can take it all this year is a question for your return.',
  },
];

/** The refusals that bear on this particular return. All four on every
    document is noise; the one about depreciation on a return with $9,800 of
    it is the whole point. */
export function relevantRefusals(result) {
  const has = (id) => result.line[id] && result.line[id].source !== 'empty' && result.line[id].cents !== 0;
  return REFUSALS.filter((r) => {
    if (r.line === '32') return result.line['31'].cents < 0;
    return has(r.line);
  });
}
