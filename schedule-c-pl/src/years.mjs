/* Which tax years this tool will answer for, and the refusal when it is asked
   about one it does not know.

   Adding January's year is meant to be dull: copy last year's file, change the
   three or four figures, add one line here, run the tests. YEAR-UPDATE.md is
   the runbook and tests/years.test.mjs is what stops a year shipping with an
   uncited number in it. */

import { YEAR_2023 } from '../years/2023.mjs';
import { YEAR_2024 } from '../years/2024.mjs';
import { YEAR_2025 } from '../years/2025.mjs';
import { buildLines } from './lines.mjs';

const YEARS = new Map([YEAR_2025, YEAR_2024, YEAR_2023].map((y) => [y.year, y]));

/** Newest first — the order the year picker shows them in. */
export function supportedYears() {
  return [...YEARS.keys()].sort((a, b) => b - a);
}

export function hasYear(year) {
  return YEARS.has(Number(year));
}

/** Throws rather than falling back to the nearest year it does know. A
    Schedule C filled in against the wrong year's line numbers is a confident
    wrong answer, which is worse than no answer. */
export function loadYear(year) {
  const data = YEARS.get(Number(year));
  if (!data) {
    throw new Error(
      `This tool does not have tax year ${year} on file. It has ` +
      `${supportedYears().join(', ')}. It will not guess a year's line numbers ` +
      `from another year's — the IRS moved lines 27a and 27b in 2025.`,
    );
  }
  const structure = buildLines(data.otherExpensesLine);
  return { ...data, ...structure };
}
