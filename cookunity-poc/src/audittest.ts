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

// --- regressions found by running the audit against the live menu ---

// Cuisines and tag bonuses match whole tags in the ranker, so the audit must
// too. Substring matching reported "American" on 150 meals when the ranker
// only ever scores the 87 tagged exactly that.
{
  const tagged: Meal[] = [
    meal({ name: 'A', tags: ['American'] }),
    meal({ name: 'B', tags: ['Latin American'] }),
  ];
  const r = auditTerms(tagged, { ...prefs, cuisines: { American: 1 }, tagBonuses: { American: 1 } });
  check('cuisine audit matches whole tags only', r.find((x) => x.section === 'cuisines')?.meals === 1);
  check('tag audit matches whole tags only', r.find((x) => x.section === 'tagBonuses')?.meals === 1);
}

// Cut names are legitimate, and proteins never scan the ingredient
// declaration, so the modifier check is noise there.
{
  const cuts: Meal[] = [meal({ name: 'Roast', proteinType: ['Chicken Thigh', 'Chicken Breast'] })];
  const r = auditTerms(cuts, { ...prefs, proteins: { chicken: 3 } });
  const chicken = r.find((x) => x.term === 'chicken');
  check('cut names do not flag a protein', !(chicken?.flags ?? []).some((f) => f.includes('modifier')));
  check('the protein still counts the meal', chicken?.meals === 1);
}

// But the ingredient declaration is still checked.
{
  const r = auditTerms([meal({ name: 'Steak', ingredients: ['Potato Starch'] })], {
    ...prefs,
    ingredients: { potato: 1 },
  });
  check('ingredient modifiers are still flagged', (r.find((x) => x.term === 'potato')?.flags ?? []).some((f) => f.includes('modifier')));
}

console.log(failures === 0 ? 'Audit regressions passed.\n' : `${failures} audit regression(s) failed.\n`);
process.exitCode = failures === 0 ? 0 : 1;

// --- the audit must reflect what the ranker actually does ---

// Once '"rice wine": 0' claims the match, "rice" must stop reporting it, or
// the audit nags forever about a false positive its own advice already fixed.
{
  const menu3: Meal[] = [
    meal({ name: 'Steak', ingredients: ['Rice Wine', 'Beef'] }),
    meal({ name: 'Bowl', ingredients: ['Jasmine Rice'] }),
  ];
  const withSuppression = auditTerms(menu3, { ...prefs, ingredients: { rice: 1, 'rice wine': 0 } });
  const rice = withSuppression.find((x) => x.term === 'rice');
  check('a claimed match is not counted for the general term', rice?.meals === 1, String(rice?.meals));
  // Only the modifier flag should clear; a 1-of-2 menu still trips frequency.
  check(
    'and no longer flagged as a modifier',
    !(rice?.flags ?? []).some((f) => f.includes('modifier')),
    JSON.stringify(rice?.flags),
  );
  check('nor reports the claimed string', rice?.matchedText.length === 0, JSON.stringify(rice?.matchedText));

  const withoutSuppression = auditTerms(menu3, { ...prefs, ingredients: { rice: 1 } });
  check(
    'without the suppression it is still flagged',
    (withoutSuppression.find((x) => x.term === 'rice')?.flags ?? []).some((f) => f.includes('modifier')),
  );
}

// The suppressor itself absorbs modifier matches by design.
{
  const r = auditTerms([meal({ name: 'A', ingredients: ['Rice Wine Vinegar'] })], {
    ...prefs,
    ingredients: { rice: 1, 'rice wine': 0 },
  });
  check(
    'a zero-weight term is not flagged for doing its job',
    !(r.find((x) => x.term === 'rice wine')?.flags ?? []).some((f) => f.includes('modifier')),
  );
}

console.log(failures === 0 ? 'Audit fidelity checks passed.\n' : `${failures} audit fidelity check(s) failed.\n`);
process.exitCode = failures === 0 ? 0 : 1;
