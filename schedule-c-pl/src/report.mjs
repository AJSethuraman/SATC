/* Turn a computed return into the two things a person actually wants.

   They are two documents because they have two readers. The profit and loss
   statement is for the filer, a bank, a landlord — it reads like a statement
   and never says "line 27b". The Schedule C worksheet is for whoever prepares
   the return — it is the form's own order, its own wording, every line
   including the empty ones, so a figure can be copied across without anyone
   having to work out where it goes.

   Both come from one computation, so they cannot disagree.

   Whole-dollar mode follows the 1040 instructions exactly: add with the cents
   in, round only the total. That is deliberately NOT the same as rounding each
   figure and adding the rounded ones, and it means a printed column can be a
   dollar off from its own printed total. Rather than hide that, `footing`
   below reports it and the documents print a line saying why. */

import { formatCents, roundToDollars, sumCents } from './money.mjs';
import { EXPENSE_LINES, COGS_LINES } from './lines.mjs';
import { REFUSALS } from './helpers.mjs';

export const ROUNDING_NOTE =
  'Figures are rounded to whole dollars. The IRS asks for the cents to be added '
  + 'in and only the total rounded, so a column can look a dollar out.';

/** One presented figure: the exact cents, and the string the reader sees. */
export function present(cents, rounding, { blank = '' } = {}) {
  if (cents === null || cents === undefined) return { cents: null, text: blank };
  const shown = rounding === 'dollars' ? roundToDollars(cents) : cents;
  return { cents: shown, text: formatCents(shown, { dollars: rounding === 'dollars' }) };
}

function row(result, id, { force = false, negate = false } = {}) {
  const line = result.yearData.byId.get(id);
  const value = result.line[id];
  if (!force && value.source === 'empty') return null;
  return {
    id,
    label: line.plLabel,
    formLabel: line.label,
    cents: value.cents,
    source: value.source,
    negate,
  };
}

const compact = (rows) => rows.filter(Boolean);

/** The profit and loss statement. Reads top to bottom like a statement. */
export function statement(result, { rounding = 'cents' } = {}) {
  const R = (id, opts) => row(result, id, opts);
  const has = (ids) => ids.some((id) => result.line[id].source !== 'empty');
  const sections = [];

  sections.push({
    heading: 'Income',
    rows: compact([R('1'), R('2', { negate: true })]),
    footer: R('3', { force: true }),
  });

  const cogsUsed = has([...COGS_LINES, '41']);
  if (cogsUsed) {
    sections.push({
      heading: 'Cost of goods sold',
      rows: compact([...COGS_LINES.map((id) => R(id)), R('40', { force: true }), R('41', { negate: true })]),
      footer: R('42', { force: true }),
    });
    sections.push({ heading: 'Gross profit', rows: [], footer: R('5', { force: true }) });
  }

  if (result.line['6'].source !== 'empty') {
    sections.push({ heading: 'Other income', rows: compact([R('6')]), footer: null });
  }
  sections.push({ heading: 'Gross income', rows: [], footer: R('7', { force: true }) });

  sections.push({
    heading: 'Expenses',
    rows: compact(EXPENSE_LINES.map((id) => R(id))),
    footer: R('28', { force: true }),
  });

  const homeUsed = result.line['30'].source !== 'empty';
  sections.push({
    heading: 'Result',
    rows: compact([homeUsed ? R('29', { force: true }) : null, homeUsed ? R('30') : null]),
    footer: R('31', { force: true }),
    final: true,
  });

  return { kind: 'statement', title: 'Profit and loss', sections, rounding };
}

/** The Schedule C worksheet. Form order, form wording, blanks left blank. */
export function worksheet(result, { rounding = 'cents' } = {}) {
  const { yearData } = result;
  const parts = [];
  const moneyParts = [
    ['I', 'Part I · Income'],
    ['II', 'Part II · Expenses'],
    ['III', 'Part III · Cost of goods sold'],
  ];
  for (const [part, heading] of moneyParts) {
    const rows = yearData.lines
      .filter((l) => l.part === part && l.kind !== 'info')
      .map((l) => ({
        id: l.id,
        label: l.label,
        cents: result.line[l.id].cents,
        source: result.line[l.id].source,
        computed: l.kind === 'computed',
      }));
    parts.push({ heading, rows });
  }

  const other = (result.rows?.other) || [];
  parts.push({
    heading: `Part V · Other expenses (carried to line ${result.otherExpensesLine})`,
    rows: other.map((r, i) => ({ id: String(i + 1), label: r.label, cents: r.cents, source: 'entered' }))
      .concat([{ id: '48', label: yearData.byId.get('48').label, cents: result.line['48'].cents, source: result.line['48'].source, computed: true }]),
  });

  return { kind: 'worksheet', title: `${yearData.year} Schedule C worksheet`, parts, rounding };
}

/** Part IV and the yes/no answers — facts, not figures, but a preparer needs
    them and a blank one is a question that gets asked later. */
export function answers(result, input) {
  const yes = (v) => (v === true ? 'Yes' : v === false ? 'No' : 'Not answered');
  const num = (v) => (v === '' || v === null || v === undefined || !Number.isFinite(Number(v))
    ? 'Not answered' : Number(v).toLocaleString('en-US'));
  const veh = input.vehicle || {};
  const rows = [
    { label: 'Accounting method', value: { cash: 'Cash', accrual: 'Accrual', other: 'Other' }[input.accountingMethod] || 'Not answered' },
    { label: 'Worked in the business regularly (line G)', value: yes(input.materiallyParticipated) },
    { label: 'All the money in it was yours to lose (line 32)',
      value: result.line['31'].cents >= 0 ? 'Does not apply — the year made a profit'
        : input.atRisk === 'all' ? 'Yes'
          : input.atRisk === 'some' ? 'No — some was not at risk' : 'Not answered' },
    { label: 'Vehicle first used for business (line 43)', value: veh.placedInService || 'Not answered' },
    { label: 'Business miles (line 44a)', value: num(veh.businessMiles) },
    { label: 'Commuting miles (line 44b)', value: num(veh.commutingMiles) },
    { label: 'Other miles (line 44c)', value: num(veh.otherMiles) },
    { label: 'Vehicle available for personal use (line 45)', value: yes(veh.personalUse) },
    { label: 'Another vehicle available (line 46)', value: yes(veh.anotherVehicle) },
    { label: 'Records kept to back it up (line 47a)', value: yes(veh.evidence) },
    { label: 'Those records are written (line 47b)', value: yes(veh.evidenceWritten) },
  ];

  /* NOT ASKED IS NOT NOT ANSWERED. Lines 33 and 34 have no control anywhere on
     the page: engine.mjs sets both to null and nothing ever writes to them, so
     every document this tool has ever produced reported them "Not answered" and
     no code path could say otherwise -- sending a preparer to chase a client for
     answers to questions nobody was asked. They now appear only when the filer
     actually used the stock section, and line 32 says it does not apply on a
     profit rather than pretending it was skipped. */
  const heldStock = ['35', '36', '37', '38', '39', '41']
    .some((id) => result.line[id] && result.line[id].source !== 'empty');
  if (heldStock) {
    rows.push(
      { label: 'How closing stock was valued (line 33)', value: { cost: 'Cost', lower: 'Lower of cost or market', other: 'Other' }[input.inventory?.method] || 'Not answered' },
      { label: 'Change in how stock was counted or valued (line 34)', value: yes(input.inventory?.changed) },
    );
  }
  return rows;
}

/** Does a printed column add up to its printed total? In cents it always does.
    In whole dollars it may not, and this is how the documents know to say so. */
export function footing(result, rounding) {
  if (rounding !== 'dollars') return { off: false, lines: [] };
  const checks = [
    ['28', EXPENSE_LINES],
    ['40', COGS_LINES],
  ];
  const off = [];
  for (const [totalId, parts] of checks) {
    const shownParts = sumCents(parts.map((id) => roundToDollars(result.line[id].cents)));
    const shownTotal = roundToDollars(result.line[totalId].cents);
    if (shownParts !== shownTotal) off.push(totalId);
  }
  return { off: off.length > 0, lines: off };
}

export const REFUSAL_NOTES = REFUSALS;
