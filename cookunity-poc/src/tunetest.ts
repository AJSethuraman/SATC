import { featuresOf, rankMeals } from './rank.js';
import { fitWeights, samplesToLabel, type Label } from './tune.js';
import type { Preferences } from './preferences.js';
import type { Meal } from './types.js';

/** Pure tests for feature extraction and weight fitting. No I/O. */

let failures = 0;

function check(label: string, condition: boolean, detail = ''): void {
  if (condition) {
    console.log(`  PASS  ${label}`);
  } else {
    failures += 1;
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`);
  }
}

const prefs: Preferences = {
  proteins: { chicken: 3, salmon: 2, fish: 1.5, beef: 1, pork: -2 },
  cuisines: { Mexican: 1, Italian: 1 },
  ingredients: { broccoli: 2, cauliflower: -1 },
  exclude: [],
  limits: {},
  tagBonuses: { 'High Protein': 2 },
  weights: { rating: 1.5 },
};

const meal = (over: Partial<Meal>): Meal => ({
  id: over.name ?? 'x',
  name: 'Test Meal',
  calories: 500,
  rating: 4.5,
  reviewCount: 500,
  ...over,
});

const scoreOf = (m: Meal, p: Preferences = prefs): number =>
  rankMeals([m], p).ranked[0]?.score ?? Number.NaN;

// The double-count bug: salmon is also fish, and stacked to 3.5 vs chicken's 3.
{
  const salmon = meal({ name: 'Roasted Salmon', proteinType: ['Salmon'], tags: ['Fish'] });
  const chicken = meal({ name: 'Roasted Chicken', proteinType: ['Chicken Thigh'] });
  const features = featuresOf(salmon, prefs);
  check('only one protein term fires', features.protein === 'salmon', String(features.protein));
  check('chicken now outranks salmon', scoreOf(chicken) > scoreOf(salmon), `${scoreOf(chicken)} vs ${scoreOf(salmon)}`);
  check(
    'the salmon reason is not doubled',
    (rankMeals([salmon], prefs).ranked[0]?.reasons ?? []).filter((r) => ['salmon', 'fish'].includes(r.text))
      .length === 1,
  );
}

// A disliked protein wins over a liked one — avoidance should dominate.
{
  const surfAndTurf = meal({ name: 'Chicken and Pork Bowl' });
  const features = featuresOf(surfAndTurf, prefs);
  check('dislike beats like when both match', features.protein === 'pork', String(features.protein));
  check('and the score reflects it', scoreOf(surfAndTurf) < scoreOf(meal({ name: 'Plain Bowl' })));
}

// Fitting.
const menu = [
  meal({ name: 'Chicken One', proteinType: ['Chicken'] }),
  meal({ name: 'Chicken Two', proteinType: ['Chicken'] }),
  meal({ name: 'Cauliflower Bowl', ingredients: ['Cauliflower'] }),
  meal({ name: 'Cauliflower Two', ingredients: ['Cauliflower'] }),
  meal({ name: 'Beef One', proteinType: ['Beef'] }),
];
const labels: Label[] = [
  { id: 'Chicken One', verdict: 'like' },
  { id: 'Chicken Two', verdict: 'like' },
  { id: 'Cauliflower Bowl', verdict: 'dislike' },
  { id: 'Cauliflower Two', verdict: 'dislike' },
];

{
  const result = fitWeights(menu, prefs, labels);
  const chicken = result.preferences.proteins['chicken'] ?? 0;
  const cauliflower = result.preferences.ingredients['cauliflower'] ?? 0;
  check('liking chicken raises its weight', chicken > prefs.proteins['chicken']!, `${chicken}`);
  check('disliking cauliflower lowers its weight', cauliflower < prefs.ingredients['cauliflower']!, `${cauliflower}`);
  check('changes are reported', result.changes.length > 0);
  check(
    'a change carries its evidence',
    (result.changes.find((c) => c.term === 'chicken')?.liked ?? 0) === 2,
  );
  check('accuracy is reported', result.accuracy === 1, String(result.accuracy));
  check('label count is reported', result.labelled === 4, String(result.labelled));
}

// Terms nothing was labelled about must not drift.
{
  const result = fitWeights(menu, prefs, labels);
  check('unexercised term is unchanged', result.preferences.proteins['salmon'] === prefs.proteins['salmon']);
  check('unexercised term is flagged', result.untouched.includes('proteins:salmon'));
  check('exercised term is not flagged', !result.untouched.includes('proteins:chicken'));
}

// The prior holds: one rating must not flip a stated preference on its head.
{
  const result = fitWeights(menu, prefs, [{ id: 'Beef One', verdict: 'dislike' }, ...labels]);
  const beef = result.preferences.proteins['beef'] ?? 0;
  const prior = prefs.proteins['beef']!;
  check('one dislike moves the weight down', beef < prior, String(beef));
  check('but does not flip its sign', beef > 0, String(beef));
}

// Evidence accumulates: two consistent ratings move a weight further than one.
{
  const one = fitWeights(menu, prefs, [{ id: 'Cauliflower Bowl', verdict: 'dislike' }]);
  const two = fitWeights(menu, prefs, [
    { id: 'Cauliflower Bowl', verdict: 'dislike' },
    { id: 'Cauliflower Two', verdict: 'dislike' },
  ]);
  const oneW = one.preferences.ingredients['cauliflower'] ?? 0;
  const twoW = two.preferences.ingredients['cauliflower'] ?? 0;
  check('more evidence moves a weight further', twoW < oneW, `${twoW} vs ${oneW}`);
}

// Cuisine weights are fitted too, not silently ignored.
{
  const cuisineMenu = [
    meal({ name: 'Mex One', tags: ['Mexican'] }),
    meal({ name: 'Mex Two', tags: ['Mexican'] }),
    meal({ name: 'It One', tags: ['Italian'] }),
    meal({ name: 'It Two', tags: ['Italian'] }),
  ];
  const result = fitWeights(cuisineMenu, prefs, [
    { id: 'Mex One', verdict: 'like' },
    { id: 'Mex Two', verdict: 'like' },
    { id: 'It One', verdict: 'dislike' },
    { id: 'It Two', verdict: 'dislike' },
  ]);
  check(
    'liked cuisine rises',
    (result.preferences.cuisines?.['Mexican'] ?? 0) > prefs.cuisines!['Mexican']!,
    String(result.preferences.cuisines?.['Mexican']),
  );
  check(
    'disliked cuisine falls',
    (result.preferences.cuisines?.['Italian'] ?? 0) < prefs.cuisines!['Italian']!,
    String(result.preferences.cuisines?.['Italian']),
  );
  check('cuisine changes are reported', result.changes.some((c) => c.section === 'cuisines'));
}

// Determinism — same labels, same weights, every time.
{
  const a = fitWeights(menu, prefs, labels).preferences;
  const b = fitWeights(menu, prefs, labels).preferences;
  check('fitting is deterministic', JSON.stringify(a) === JSON.stringify(b));
}

// Fitting must not mutate the caller's preferences.
{
  const before = JSON.stringify(prefs);
  fitWeights(menu, prefs, labels);
  check('input preferences are not mutated', JSON.stringify(prefs) === before);
}

// Unknown ids are skipped rather than throwing.
{
  const result = fitWeights(menu, prefs, [...labels, { id: 'does-not-exist', verdict: 'like' }]);
  check('unknown label id is ignored', result.labelled === 4, String(result.labelled));
}

// Sampling spreads across the ranking instead of clustering at the top.
{
  const ranked = menu.map((m, i) => ({ meal: m, score: 10 - i }));
  const picked = samplesToLabel(ranked, 3, new Set());
  check('sampling returns the asked-for count', picked.length === 3, String(picked.length));
  check('sampling includes the top', picked[0]?.name === 'Chicken One');
  check('sampling reaches the bottom', picked[picked.length - 1]?.name === 'Beef One');
  check(
    'already-rated meals are skipped',
    !samplesToLabel(ranked, 3, new Set(['Chicken One'])).some((m) => m.name === 'Chicken One'),
  );
}

console.log(failures === 0 ? '\nAll tuning tests passed.\n' : `\n${failures} tuning test(s) failed.\n`);
process.exitCode = failures === 0 ? 0 : 1;
