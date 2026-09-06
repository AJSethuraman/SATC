/* Tax year 2025. Every figure below carries the page it came from, and
   tests/years.test.mjs refuses to load a year whose parameter has no source.
   A tax number without a citation is folklore. */
export const YEAR_2025 = {
  year: 2025,
  status: 'final',
  form: {
    title: 'Schedule C (Form 1040) — Profit or Loss From Business',
    revision: '2025, created 4/3/25, Cat. No. 11334P',
    source: 'https://www.irs.gov/pub/irs-pdf/f1040sc.pdf',
    instructions: 'https://www.irs.gov/instructions/i1040sc',
    retrieved: '2026-09-06',
  },
  // 2025 is the year the IRS swapped 27a and 27b.
  otherExpensesLine: '27b',
  parameters: {
    standardMileage: {
      // Held as tenths of a cent so 65.5 is an integer, and as periods because
      // the IRS has split a year mid-way before and did so again for 2026.
      periods: [{ from: '2025-01-01', through: '2025-12-31', tenthCents: 700 }],
      display: '70 cents a mile',
      source: 'https://www.irs.gov/pub/irs-drop/n-25-05.pdf',
      cite: 'IRS Notice 2025-5 (announced in IR-2024-312)',
    },
    simplifiedHomeOffice: {
      ratePerSqFtCents: 500,
      maxSqFt: 300,
      display: '$5 a square foot',
      source: 'https://www.irs.gov/instructions/i1040sc',
      cite: '2025 Instructions for Schedule C, line 30 (Simplified Method)',
    },
    mealsDeductiblePercent: {
      percent: 50,
      display: 'half of what you spent',
      source: 'https://www.irs.gov/instructions/i1040sc',
      cite: '2025 Instructions for Schedule C, line 24b',
      caveat: 'Some meals are not half. Drivers under federal hours-of-service rules deduct 80%, and a few meals count in full.',
    },
  },
};
