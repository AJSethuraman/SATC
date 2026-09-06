/* One place that assembles a finished document, so the PDF and the spreadsheet
   cannot disagree about what they say or when they were made.

   The wording below is the wording a client reads, and it follows the house
   rule for that register: say the thing in words the reader already brought
   with them. No sentence here exists only to protect us — copy.spec.py checks
   that, and checks the length. */

import { compute } from './engine.mjs';
import { statement, worksheet, answers, footing, ROUNDING_NOTE } from './report.mjs';
import { REFUSALS, relevantRefusals } from './helpers.mjs';
import { buildPdf } from './pdf.mjs';
import { buildXlsx } from './xlsx.mjs';

export const FIRM = 'Sethuraman Accounting, Tax & Consulting LLP';
export const SITE = 'satcllp.com';

export const DISCLAIMER =
  'These are your own figures, sorted into the boxes Schedule C uses. It is not '
  + 'a tax return, and it does not say what you are allowed to deduct. Nothing '
  + 'was sent anywhere — it was worked out on your own computer.';

export const INVITATION =
  'If you would rather hand this year to someone, we take on sole traders. '
  + 'Sethuraman Accounting, Tax & Consulting — satcllp.com.';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

/** A date a person reads, built from the parts rather than from a locale, so
    the same input always produces the same document. */
export function longDate(date) {
  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

function pdfStamp(date) {
  const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${date.getFullYear()}${p(date.getMonth() + 1)}${p(date.getDate())}`
    + `${p(date.getHours())}${p(date.getMinutes())}${p(date.getSeconds())}Z`;
}

/** Safe for a download on any operating system, and still recognisable. */
export function fileName(kind, year, businessName) {
  const slug = String(businessName || 'Schedule-C')
    .normalize('NFKD').replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-').slice(0, 48)
    || 'Schedule-C';
  return `${slug}-${year}-${kind}`;
}

/** Everything both writers need, worked out once. */
export function prepare(input, { now = new Date(), rounding = null } = {}) {
  const result = compute(input);
  const mode = rounding || input.rounding || 'cents';
  result.rows = { other: (input.details && input.details.other) || [] };
  const stmt = statement(result, { rounding: mode });
  const sheet = worksheet(result, { rounding: mode });
  const answerRows = answers(result, input);
  const foot = footing(result, mode);
  const meta = {
    firm: FIRM,
    site: SITE,
    title: `Profit and loss ${result.year} — ${input.business?.name || 'sole trader'}`,
    businessName: input.business?.name || '',
    activity: input.business?.activity || '',
    prepared: longDate(now),
    stamp: pdfStamp(now),
    disclaimer: DISCLAIMER,
    invitation: INVITATION,
    refusals: relevantRefusals(result),
    allRefusals: REFUSALS,
  };
  return {
    result, stmt, sheet, answerRows, meta, rounding: mode,
    footingNote: foot.off ? ROUNDING_NOTE : null,
  };
}

export function pdfFor(input, opts = {}) {
  const p = prepare(input, opts);
  if (p.result.blockers.length) {
    throw new Error(p.result.blockers.map((b) => b.message).join(' '));
  }
  return {
    bytes: buildPdf({ ...p, input, include: opts.include || ['statement', 'worksheet'] }),
    name: `${fileName('profit-and-loss', p.result.year, p.meta.businessName)}.pdf`,
    prepared: p,
  };
}

export function xlsxFor(input, opts = {}) {
  const p = prepare(input, opts);
  if (p.result.blockers.length) {
    throw new Error(p.result.blockers.map((b) => b.message).join(' '));
  }
  return {
    bytes: buildXlsx({ ...p, rows: p.result.rows }),
    name: `${fileName('profit-and-loss', p.result.year, p.meta.businessName)}.xlsx`,
    prepared: p,
  };
}
