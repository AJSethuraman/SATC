import { auditTerms } from './audit.js';
import type { Preferences } from './preferences.js';
import type { Meal } from './types.js';

/** Pure tests for the preference audit. No I/O. */

let failures = 0;
function check(label: string, condition: boolean, detail = ''): void {
  if (condition) console.log(`  PASS  ${label}`);
  else {
    failures += 1;
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`);
  }
}

const prefs: Preferences = {
  proteins: { chicken: 3, ostrich: 1 },
  cuisines: { Mexican: 1 },
  ingredients: { rice: 1, broccoli: 1 },
  exclude: ['anchovy'],
  limits: {},
  tagBonuses: { 'High Fat': -0.4 },
  weights: { rating: 1.5 },
};

const meal = (over: Partial<Meal>): Meal => ({ id: over.name ?? 'x', name: 'Meal', ...over });

const menu: Meal[] = [
  meal({ name: 'Chicken Bowl', proteinType: ['Chicken'], ingredients: ['Jasmine Rice'], tags: ['Mexican', 'High Fat'] }),
  meal({ name: 'Soy-Mirin Steak', ingredients: ['Rice Wine', 'Beef'], tags: ['High Fat'] }),
  meal({ name: 'Broccoli Bowl', sides: ['Steamed Broccoli'], tags: ['High Fat'] }),
  meal({ name: 'Caesar', ingredients: ['Anchovy Paste'], tags: ['High Fat'] }),
];

const report = auditTerms(menu, prefs);
const find = (section: string, term: string) => report.find((r) => r.section === section && r.term === term);

// The headline capability: surfacing that "rice" also matched "Rice Wine".
{
  const rice = find('ingredients', 'rice');
  check('counts the meals a term fires on', rice?.meals === 2, String(rice?.meals));
  check(
    'reports only the modifier match, not the legitimate one',
    JSON.stringify(rice?.matchedText) === JSON.stringify(['Rice Wine']),
    JSON.stringify(rice?.matchedText),
  );
  check('flags the modifier match', (rice?.flags ?? []).some((f) => f.includes('modifier')));
}

// Dead weights are worth knowing about — they look like preferences but do nothing.
{
  const ostrich = find('proteins', 'ostrich');
  check('a term that never fires is flagged', (ostrich?.flags ?? []).some((f) => f.includes('never fires')));
  check('and reports zero meals', ostrich?.meals === 0);
}

// A tag on most of the menu cannot discriminate between meals.
{
  const fat = find('tagBonuses', 'High Fat');
  check('a ubiquitous term is flagged as weak', (fat?.flags ?? []).some((f) => f.includes('weak discriminator')));
}

// Clean terms stay quiet, or the report becomes noise.
{
  const broccoli = find('ingredients', 'broccoli');
  // "Steamed Broccoli" is broccoli; the term is the head of the phrase.
  check('a term used as the head noun is not flagged', (broccoli?.flags ?? []).length === 0, JSON.stringify(broccoli?.flags));
  check('a clean term still reports its count', broccoli?.meals === 1);
}

// Exclusions are audited too: an over-firing one silently empties the menu.
{
  const anchovy = find('exclude', 'anchovy');
  check('exclusions are audited', anchovy !== undefined);
  check('exclusions have no weight', anchovy?.weight === null);
  check('exclusion match is found', anchovy?.meals === 1);
}

// Plurals and trailing punctuation must not read as modifier use.
{
  const menu2: Meal[] = [
    meal({ name: 'A', ingredients: ['Green Beans'] }),
    meal({ name: 'B', ingredients: ['Roasted Broccoli.'] }),
  ];
  const r = auditTerms(menu2, { ...prefs, ingredients: { 'green bean': 1, broccoli: 1 } });
  const bean = r.find((x) => x.term === 'green bean');
  const brocc = r.find((x) => x.term === 'broccoli');
  check('a plural head noun is not a modifier', !(bean?.flags ?? []).some((f) => f.includes('modifier')));
  check('trailing punctuation is not a modifier', !(brocc?.flags ?? []).some((f) => f.includes('modifier')));
}

// Protein terms read identity only, matching the ranker's split.
{
  const chicken = find('proteins', 'chicken');
  check('protein audit uses identity fields', chicken?.meals === 1, String(chicken?.meals));
}

// Flagged terms sort first so the report leads with what needs attention.
check('flagged terms sort first', (report[0]?.flags ?? []).length > 0);

console.log(failures === 0 ? '\nAll audit tests passed.\n' : `\n${failures} audit test(s) failed.\n`);
process.exitCode = failures === 0 ? 0 : 1;
