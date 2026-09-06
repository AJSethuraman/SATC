/* The Schedule C line structure.

   Every `label` below is the wording on the IRS form itself, taken from the
   accessibility text inside the official PDF rather than retyped from memory.
   The extraction script and the raw output for each year are in ../evidence/,
   and tests/lines.test.mjs asserts this table still matches them. That is the
   whole defence against a line label quietly going stale.

   One thing genuinely moves between years and it is not cosmetic: for 2023 and
   2024 line 27a is "Other expenses (from line 48)" and 27b is the energy
   efficient commercial buildings deduction. For 2025 the IRS SWAPPED them. A
   tool that hardcodes either arrangement is wrong for half the years it
   supports, so the slot is a parameter — see `buildLines(otherExpensesLine)`.

   `label`  — what the form says. Used on the Schedule C worksheet.
   `plLabel`— what a person says. Used on the profit and loss statement.
   `kind`   — 'entry' the filer types it, 'computed' we work it out,
              'info' it is not money (a date, a method, a yes/no).           */

export const ENERGY_LABEL = 'Energy efficient commercial bldgs deduction (attach Form 7205)';
export const OTHER_LABEL = 'Other expenses (from line 48)';

/** The 24 expense lines that line 28 adds up, in form order. */
export const EXPENSE_LINES = [
  '8', '9', '10', '11', '12', '13', '14', '15', '16a', '16b', '17', '18',
  '19', '20a', '20b', '21', '22', '23', '24a', '24b', '25', '26', '27a', '27b',
];

/** Part III lines that line 40 adds up. */
export const COGS_LINES = ['35', '36', '37', '38', '39'];

export function buildLines(otherExpensesLine) {
  if (otherExpensesLine !== '27a' && otherExpensesLine !== '27b') {
    throw new Error(`other expenses must sit on 27a or 27b, not ${otherExpensesLine}`);
  }
  const energyLine = otherExpensesLine === '27a' ? '27b' : '27a';
  const L = (id, part, kind, label, plLabel, extra = {}) =>
    ({ id, part, kind, label, plLabel, ...extra });

  const lines = [
    // ── Part I · Income ────────────────────────────────────────────────
    L('1', 'I', 'entry', 'Gross receipts or sales', 'Sales and receipts', { group: 'revenue' }),
    L('2', 'I', 'entry', 'Returns and allowances', 'Less: returns and allowances', { group: 'revenue', negates: true }),
    L('3', 'I', 'computed', 'Subtract line 2 from line 1', 'Net sales', { group: 'revenue', formula: { op: 'sub', of: ['1', '2'] }, subtotal: true }),
    L('4', 'I', 'computed', 'Cost of goods sold (from line 42)', 'Cost of goods sold', { group: 'cogs', formula: { op: 'copy', of: ['42'] }, negates: true }),
    L('5', 'I', 'computed', 'Gross profit. Subtract line 4 from line 3', 'Gross profit', { group: 'cogs', formula: { op: 'sub', of: ['3', '4'] }, subtotal: true }),
    L('6', 'I', 'entry', 'Other income, including federal and state gasoline or fuel tax credit or refund', 'Other income', { group: 'revenue' }),
    L('7', 'I', 'computed', 'Gross income. Add lines 5 and 6', 'Gross income', { group: 'revenue', formula: { op: 'sum', of: ['5', '6'] }, subtotal: true }),

    // ── Part II · Expenses ─────────────────────────────────────────────
    L('8', 'II', 'entry', 'Advertising', 'Advertising'),
    L('9', 'II', 'entry', 'Car and truck expenses', 'Car and truck', { helper: 'mileage' }),
    L('10', 'II', 'entry', 'Commissions and fees', 'Commissions and fees'),
    L('11', 'II', 'entry', 'Contract labor', 'Contract labour and subcontractors'),
    L('12', 'II', 'entry', 'Depletion', 'Depletion'),
    L('13', 'II', 'entry', 'Depreciation and section 179 expense deduction (not included in Part III)', 'Depreciation and equipment written off'),
    L('14', 'II', 'entry', 'Employee benefit programs (other than on line 19)', 'Employee benefits'),
    L('15', 'II', 'entry', 'Insurance (other than health)', 'Insurance'),
    L('16a', 'II', 'entry', 'Interest: Mortgage (paid to banks, etc.)', 'Mortgage interest'),
    L('16b', 'II', 'entry', 'Interest: Other', 'Other interest'),
    L('17', 'II', 'entry', 'Legal and professional services', 'Legal and professional fees'),
    L('18', 'II', 'entry', 'Office expense', 'Office expenses'),
    L('19', 'II', 'entry', 'Pension and profit-sharing plans', 'Pension and profit sharing'),
    L('20a', 'II', 'entry', 'Rent or lease: Vehicles, machinery, and equipment', 'Rent: vehicles and equipment'),
    L('20b', 'II', 'entry', 'Rent or lease: Other business property', 'Rent: property'),
    L('21', 'II', 'entry', 'Repairs and maintenance', 'Repairs and maintenance'),
    L('22', 'II', 'entry', 'Supplies (not included in Part III)', 'Supplies'),
    L('23', 'II', 'entry', 'Taxes and licenses', 'Taxes and licences'),
    L('24a', 'II', 'entry', 'Travel and meals: Travel', 'Travel'),
    L('24b', 'II', 'entry', 'Travel and meals: Deductible meals', 'Meals (deductible part)', { helper: 'meals' }),
    L('25', 'II', 'entry', 'Utilities', 'Utilities'),
    L('26', 'II', 'entry', 'Wages (less employment credits)', 'Wages'),
    // 27a always comes before 27b on the page. Which of them is "other
    // expenses" is what moves between years, not their order.
    ...['27a', '27b'].map((slot) => (slot === otherExpensesLine
      ? L(slot, 'II', 'computed', OTHER_LABEL, 'Other expenses', { formula: { op: 'copy', of: ['48'] }, fromDetail: 'other' })
      : L(slot, 'II', 'entry', ENERGY_LABEL, 'Energy efficient buildings deduction'))),
    L('28', 'II', 'computed', 'Total expenses before expenses for business use of home. Add lines 8 through 27b', 'Total expenses before home office', { formula: { op: 'sum', of: EXPENSE_LINES }, subtotal: true }),
    L('29', 'II', 'computed', 'Tentative profit or (loss). Subtract line 28 from line 7', 'Profit before home office', { formula: { op: 'sub', of: ['7', '28'] }, subtotal: true }),
    L('30', 'II', 'entry', 'Expenses for business use of your home', 'Business use of your home', { helper: 'home' }),
    L('31', 'II', 'computed', 'Net profit or (loss). Subtract line 30 from line 29', 'Net profit or (loss)', { formula: { op: 'sub', of: ['29', '30'] }, total: true }),
    L('32', 'II', 'info', 'If you have a loss, check the box that describes your investment in this activity', 'Investment at risk'),

    // ── Part III · Cost of Goods Sold ──────────────────────────────────
    L('33', 'III', 'info', 'Method(s) used to value closing inventory', 'Inventory valuation method'),
    L('34', 'III', 'info', 'Was there any change in determining quantities, costs, or valuations between opening and closing inventory?', 'Change in inventory method'),
    L('35', 'III', 'entry', "Inventory at beginning of year. If different from last year's closing inventory, attach explanation", 'Opening inventory'),
    L('36', 'III', 'entry', 'Purchases less cost of items withdrawn for personal use', 'Purchases', { helper: 'purchases' }),
    L('37', 'III', 'entry', 'Cost of labor. Do not include any amounts paid to yourself', 'Cost of labour'),
    L('38', 'III', 'entry', 'Materials and supplies', 'Materials and supplies'),
    L('39', 'III', 'entry', 'Other costs', 'Other costs'),
    L('40', 'III', 'computed', 'Add lines 35 through 39', 'Goods available', { formula: { op: 'sum', of: COGS_LINES }, subtotal: true }),
    L('41', 'III', 'entry', 'Inventory at end of year', 'Closing inventory', { negates: true }),
    L('42', 'III', 'computed', 'Cost of goods sold. Subtract line 41 from line 40', 'Cost of goods sold', { formula: { op: 'sub', of: ['40', '41'] }, total: true }),

    // ── Part IV · Information on Your Vehicle ──────────────────────────
    L('43', 'IV', 'info', 'When did you place your vehicle in service for business purposes?', 'Vehicle first used for business'),
    // The form asks 44a/b/c as one sentence with three boxes. Split here so
    // each figure gets its own line, which is why these three are the only
    // labels in this table that are not the form's own words.
    L('44a', 'IV', 'info', 'Business miles', 'Business miles', { reworded: true }),
    L('44b', 'IV', 'info', 'Commuting miles', 'Commuting miles', { reworded: true }),
    L('44c', 'IV', 'info', 'Other miles', 'Other miles', { reworded: true }),
    L('45', 'IV', 'info', 'Was your vehicle available for personal use during off-duty hours?', 'Available for personal use'),
    L('46', 'IV', 'info', 'Do you (or your spouse) have another vehicle available for personal use?', 'Another vehicle available'),
    L('47a', 'IV', 'info', 'Do you have evidence to support your deduction?', 'Evidence kept'),
    L('47b', 'IV', 'info', 'If "Yes," is the evidence written?', 'Evidence is written'),

    // ── Part V · Other Expenses ────────────────────────────────────────
    L('48', 'V', 'computed', `Total other expenses. Enter here and on line ${otherExpensesLine}`, 'Total other expenses', { formula: { op: 'detail', of: ['other'] }, total: true }),
  ];

  const byId = new Map(lines.map((l) => [l.id, l]));
  return { lines, byId, otherExpensesLine, energyLine };
}
