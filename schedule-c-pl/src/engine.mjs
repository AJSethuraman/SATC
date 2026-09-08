/* Work out every line of a Schedule C from what the filer typed.

   Three rules hold everywhere in here:

   1. Exact integers. Cents in, cents out, no float touches a total.
   2. Empty is not zero. A line nobody filled in keeps `source: 'empty'` all the
      way to the page, where it prints blank. A line someone deliberately
      entered as zero prints 0.00.
   3. It refuses rather than picking. Two figures that disagree — a total typed
      over a list that already adds up — is a blocker, not a coin toss.

   What it will not do is decide anything. Nothing here asks whether a cost is
   deductible; it adds up figures the filer brought and puts them on the line
   the form puts them on. Where a rule does exist and is pure arithmetic on a
   published IRS figure, it lives in helpers.mjs and the filer opts into it. */

import { sumCents } from './money.mjs';
import { loadYear } from './years.mjs';
import { EXPENSE_LINES } from './lines.mjs';

export function emptyReturn(year = 2025) {
  return {
    year,
    business: { name: '', activity: '' },
    accountingMethod: 'cash',
    materiallyParticipated: null,
    entries: {},
    details: {},
    vehicle: {},
    inventory: { method: null, changed: null },
    atRisk: null,
    homeOfficeMethod: null,
    rounding: 'cents',
  };
}

const EMPTY = { cents: 0, source: 'empty' };

export function compute(input) {
  const yearData = loadYear(input.year);
  const { byId, otherExpensesLine } = yearData;
  const entries = input.entries || {};
  const details = input.details || {};
  const blockers = [];
  const notices = [];
  const note = (line, message) => notices.push({ level: 'note', line, message });
  const warn = (line, message, extra = {}) => notices.push({ level: 'warn', line, message, ...extra });

  // ── detail lists ────────────────────────────────────────────────────
  // A list of rows may stand behind an entry line. If it does, it wins and the
  // line is not separately typeable. Both at once is a contradiction we refuse.
  const detailTotals = new Map();
  for (const [key, rows] of Object.entries(details)) {
    if (!Array.isArray(rows) || rows.length === 0) continue;
    detailTotals.set(key, sumCents(rows.map((r) => r.cents)));
  }

  const resolving = new Set();
  const resolved = new Map();

  function valueOf(id) {
    if (resolved.has(id)) return resolved.get(id);
    if (resolving.has(id)) throw new Error(`line ${id} depends on itself`);
    resolving.add(id);
    const out = derive(id);
    resolving.delete(id);
    resolved.set(id, out);
    return out;
  }

  function derive(id) {
    const line = byId.get(id);
    if (!line) throw new Error(`no line ${id} on the ${yearData.year} Schedule C`);

    if (line.kind === 'entry') {
      const typed = entries[id];
      const listed = detailTotals.get(id);
      if (listed !== undefined && typed !== undefined && typed !== null) {
        blockers.push({
          line: id,
          message: `Line ${id} has both a total typed in and a list of items. Keep one.`,
        });
        return EMPTY;
      }
      if (listed !== undefined) return { cents: listed, source: 'detail' };
      if (typed === undefined || typed === null) return EMPTY;
      return { cents: typed, source: 'entered' };
    }

    if (line.kind === 'info') return EMPTY;

    // computed
    if (entries[id] !== undefined && entries[id] !== null) {
      blockers.push({
        line: id,
        message: `Line ${id} is worked out from the other lines, so it cannot be typed in.`,
      });
    }
    const f = line.formula;
    if (!f) return EMPTY;

    if (f.op === 'detail') {
      const listed = detailTotals.get(f.of[0]);
      if (listed === undefined) return EMPTY;
      return { cents: listed, source: 'detail' };
    }
    const parts = f.of.map(valueOf);
    const anyFilled = parts.some((p) => p.source !== 'empty');
    let cents;
    if (f.op === 'sum') cents = sumCents(parts.map((p) => p.cents));
    else if (f.op === 'sub') cents = parts[0].cents - parts[1].cents;
    else if (f.op === 'copy') cents = parts[0].cents;
    else throw new Error(`unknown formula ${f.op} on line ${id}`);
    return { cents, source: anyFilled ? 'computed' : 'empty' };
  }

  const line = {};
  for (const l of yearData.lines) line[l.id] = valueOf(l.id);

  // ── what the filer should know, said plainly ────────────────────────
  const v = (id) => line[id].cents;
  const filled = (id) => line[id].source !== 'empty';
  const miles = Number(input.vehicle?.businessMiles ?? NaN);

  if (v('9') !== 0 && !(Number.isFinite(miles) && miles > 0)) {
    note('9', 'Schedule C asks how many miles you drove. Add them under vehicle details.');
  }
  /* THE COSTLIEST MISTAKE ON THIS FORM, and the tool took it in silence while
     flagging Form 4562 -- worth a few dollars -- one line above. Taking the
     mileage rate means the vehicle's running costs are already inside it;
     claiming them again on 15 or 21 is the classic double-count.

     This is NOT the tool deciding what is deductible (DECISIONS.md section 2).
     It is the place the tool already speaks up about figures that look
     inconsistent with each other, and nothing it currently flags is more
     inconsistent than this. */
  if (Number.isFinite(miles) && miles > 0 && (v('15') !== 0 || v('21') !== 0)) {
    note('9', "The mileage rate already covers your vehicle's insurance, fuel and repairs. "
      + 'Check you have not counted those again on lines 15 or 21.');
  }
  if (v('13') !== 0) {
    note('13', 'Depreciation usually means Form 4562 goes with the return too.');
  }
  if (v(yearData.energyLine) !== 0) {
    note(yearData.energyLine, 'This one needs Form 7205 attached.');
  }
  if (filled('1') && v('2') > v('1')) {
    note('2', 'Refunds to customers come to more than sales. Worth a second look.');
  }
  for (const id of EXPENSE_LINES) {
    if (filled(id) && v(id) < 0) {
      note(id, `Line ${id} is a negative number. That happens with a refund — check it is meant.`);
    }
  }
  if (filled('41') && v('41') > v('40')) {
    note('41', 'Closing stock is worth more than everything you had to sell, so cost of goods sold came out below zero.');
  }
  if (input.homeOfficeMethod === 'simplified' && v('30') > 0) {
    const room = Math.max(v('29'), 0);
    if (v('30') > room) {
      warn('30', 'The square-foot method cannot push your business into a loss.', { cap: room });
    }
  }
  if (v('31') < 0) {
    if (input.atRisk === null || input.atRisk === undefined) {
      warn('32', 'You have a loss, so Schedule C asks whether all the money in the business was yours to lose.');
    } else if (input.atRisk === 'some') {
      note('32', 'Some of the money was not at risk, so Form 6198 goes with the return and the loss may be cut back.');
    }
    if (input.materiallyParticipated === false) {
      note('31', 'You said you did not work in the business regularly, which limits how much of the loss you can use this year.');
    }
  }
  const otherRows = (details.other || []).length;
  if (otherRows > 9) {
    note('48', 'Schedule C has room for nine of these. More than that goes on an attached list.');
  }

  const hasFigures = yearData.lines.some((l) => l.kind === 'entry' && line[l.id].source !== 'empty');
  if (!hasFigures) {
    blockers.push({ line: null, message: 'Nothing has been entered yet.' });
  }

  return {
    year: yearData.year,
    yearData,
    line,
    notices,
    blockers,
    hasFigures,
    otherExpensesLine,
    netProfitCents: v('31'),
  };
}
