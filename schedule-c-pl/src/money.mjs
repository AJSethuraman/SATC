/* Money is integer cents. There is no float in this file and there is none in
   the engine, because a P&L that is off by a cent is a P&L nobody trusts.

   Absence is not zero. A line the user never touched returns null, and null
   travels all the way to the page, where it renders as blank rather than as
   $0.00. "I have no vehicle expenses" and "I have not filled that in yet" are
   different facts and the tool is not allowed to merge them. */

// About $100 billion. Chosen so that every total in the engine — at most ~40
// lines added together — stays far below Number.MAX_SAFE_INTEGER (9.007e15)
// and every integer is therefore exact. A sole proprietorship above this is
// not a typo we should accept quietly.
export const MAX_CENTS = 9_999_999_999_999;

const CLEAN = /[\s  ,$]/g;
// Accepts '.5' and '5.' too — people type both.
const SHAPE = /^[+-]?(\d+(\.\d*)?|\.\d+)$/;

/** Parse user text into cents. Never throws, never guesses, never rounds
    silently. Returns one of:
      { ok: true,  cents: null }      the field is empty
      { ok: true,  cents: <integer> }
      { ok: false, error: '<plain sentence>' } */
export function parseMoney(raw) {
  if (raw === null || raw === undefined) return { ok: true, cents: null };
  let s = String(raw).replace(CLEAN, '');
  if (s === '') return { ok: true, cents: null };

  // Accountants write a negative in parentheses and so do bank exports.
  let negative = false;
  if (s.startsWith('(') && s.endsWith(')')) { negative = true; s = s.slice(1, -1); }
  if (s === '') return { ok: false, error: 'That looks like empty brackets.' };

  if (!SHAPE.test(s)) return { ok: false, error: 'Use numbers only, like 1234.56' };
  if (s.startsWith('-')) { negative = !negative; s = s.slice(1); }
  else if (s.startsWith('+')) s = s.slice(1);

  const [whole, frac = ''] = s.split('.');
  const wholeDigits = whole === '' ? '0' : whole;
  if (frac.length > 2) return { ok: false, error: 'Cents only go to two places.' };
  if (wholeDigits.length > 15) return { ok: false, error: 'That number is too big for this tool.' };

  const cents = Number(wholeDigits) * 100 + Number((frac + '00').slice(0, 2));
  if (cents > MAX_CENTS) return { ok: false, error: 'That number is too big for this tool.' };
  return { ok: true, cents: negative ? -cents : cents };
}

/** Whole dollars, the way the IRS asks for them: under 50 cents drops, 50
    through 99 goes up. Symmetric about zero, so a loss rounds the same way a
    profit does. Returns cents that are a whole number of dollars. */
export function roundToDollars(cents) {
  if (cents === null || cents === undefined) return null;
  const sign = cents < 0 ? -1 : 1;
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100) + (abs % 100 >= 50 ? 1 : 0);
  // `|| 0` is not cosmetic: -1 cent rounds to -0, which is a different value
  // from 0 to Object.is, to a strict assertion, and to anything that keys off
  // the sign. A property test found it. No figure leaves here as -0.
  return sign * dollars * 100 || 0;
}

/** Add, treating an untouched line as nothing rather than as zero. Returns a
    number always — a total of nothing is zero, and that is a real answer. */
export function sumCents(values) {
  let total = 0;
  for (const v of values) if (v !== null && v !== undefined) total += v;
  return total;
}

const GROUPS = /\B(?=(\d{3})+(?!\d))/g;

/** Format for a screen or a document. `dollars: true` drops the cents; it does
    NOT round — round first with roundToDollars if that is what you meant. */
export function formatCents(cents, { dollars = false, blank = '' } = {}) {
  if (cents === null || cents === undefined) return blank;
  const negative = cents < 0;
  const abs = Math.abs(cents);
  const whole = String(Math.floor(abs / 100)).replace(GROUPS, ',');
  const body = dollars ? whole : `${whole}.${String(abs % 100).padStart(2, '0')}`;
  return negative ? `(${body})` : body;
}

/** The same figure with a currency mark, for prose and for headline numbers. */
export function formatDollars(cents, opts = {}) {
  if (cents === null || cents === undefined) return opts.blank ?? '';
  const body = formatCents(cents, opts);
  return body.startsWith('(') ? `($${body.slice(1)}` : `$${body}`;
}
