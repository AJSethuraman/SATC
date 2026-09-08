/* Tax year 2024. Every figure below carries the page it came from, and
   tests/years.test.mjs refuses to load a year whose parameter has no source.
   A tax number without a citation is folklore. */
export const YEAR_2024 = {
  year: 2024,
  status: 'final',
  form: {
    title: 'Schedule C (Form 1040) — Profit or Loss From Business',
    revision: '2024, Cat. No. 11334P',
    source: 'https://www.irs.gov/pub/irs-prior/f1040sc--2024.pdf',
    instructions: 'https://www.irs.gov/pub/irs-prior/i1040sc--2024.pdf',
    retrieved: '2026-09-06',
  },
  // 2024 keeps the older arrangement: other expenses on 27a.
  otherExpensesLine: '27a',
  parameters: {
    standardMileage: {
      // Held as tenths of a cent so 65.5 is an integer, and as periods because
      // the IRS has split a year mid-way before and did so again for 2026.
      periods: [{ from: '2024-01-01', through: '2024-12-31', tenthCents: 670 }],
      display: '67 cents a mile',
      source: 'https://www.irs.gov/tax-professionals/standard-mileage-rates',
      cite: 'IRS Notice 2024-08 (announced in IR-2023-239)',
    },
    simplifiedHomeOffice: {
      ratePerSqFtCents: 500,
      maxSqFt: 300,
      display: '$5 a square foot',
      source: 'https://www.irs.gov/pub/irs-prior/i1040sc--2024.pdf',
      cite: '2024 Instructions for Schedule C, line 30 (Simplified Method)',
    },
    mealsDeductiblePercent: {
      percent: 50,
      display: 'half of what you spent',
      source: 'https://www.irs.gov/pub/irs-prior/i1040sc--2024.pdf',
      cite: '2024 Instructions for Schedule C, line 24b',
      caveat: 'Some meals are not half. Drivers under federal hours-of-service rules deduct 80%, and a few meals count in full.',
    },
  },
};
