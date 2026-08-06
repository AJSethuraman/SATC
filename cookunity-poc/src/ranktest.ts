import { explain, rankMeals } from './rank.js';
import type { Preferences } from './preferences.js';
import type { Meal } from './types.js';

/** Pure tests for the ranking rules — no browser, no network. */

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
  proteins: { chicken: 3, beef: 1, pork: 0 },
  ingredients: { broccoli: 2, cauliflower: -1 },
  exclude: ['anchovy'],
  limits: { maxCalories: 900, minRating: 4.2, minReviewCount: 50 },
  tagBonuses: { 'High Protein': 2, 'High Sodium': -1 },
  weights: { rating: 1.5 },
};

const meal = (over: Partial<Meal>): Meal => ({
  id: 'x',
  name: 'Test Meal',
  calories: 500,
  rating: 4.5,
  reviewCount: 500,
  ...over,
});

const scoreOf = (m: Meal): number => rankMeals([m], prefs).ranked[0]?.score ?? Number.NaN;

// Protein preference ordering — the thing that matters most.
{
  const chicken = scoreOf(meal({ name: 'Grilled Chicken Bowl' }));
  const beef = scoreOf(meal({ name: 'Braised Beef Bowl' }));
  const pork = scoreOf(meal({ name: 'Pulled Pork Bowl' }));
  check('chicken outranks beef', chicken > beef, `${chicken} vs ${beef}`);
  check('beef outranks pork', beef > pork, `${beef} vs ${pork}`);
  check('zero-weight protein adds nothing', pork === scoreOf(meal({ name: 'Plain Bowl' })));
}

// Sides count, and a disliked side can sink an otherwise-liked protein.
{
  const withBroccoli = scoreOf(meal({ name: 'Chicken', sides: ['Broccoli'] }));
  const withCauli = scoreOf(meal({ name: 'Chicken', sides: ['Cauliflower'] }));
  check('liked side beats disliked side', withBroccoli > withCauli, `${withBroccoli} vs ${withCauli}`);
  check('disliked side costs points', withCauli < scoreOf(meal({ name: 'Chicken' })));
}

// Ingredient preferences read the full declaration, wherever the term lands.
{
  const plain = scoreOf(meal({ name: 'Bowl' }));
  const inIngredients = scoreOf(meal({ name: 'Bowl', ingredients: ['Broccoli', 'Rice'] }));
  const inDescription = scoreOf(meal({ name: 'Bowl', description: 'with broccoli' }));
  const inSides = scoreOf(meal({ name: 'Bowl', sides: ['Steamed Broccoli'] }));
  check('matches from the ingredient list', inIngredients > plain);
  check('matches from the description too', inDescription === inIngredients);
  check('matches from the side dish too', inSides === inIngredients);
}

// Protein preferences read identity only. This is the stock trap: the live
// menu declares chicken stock in mole, dirty rice and most pilafs, which had
// salmon, shrimp, pork and beef dishes all scoring as "chicken".
{
  const plain = scoreOf(meal({ name: 'Salmon Bowl', proteinType: ['Salmon'] }));
  const withStock = scoreOf(
    meal({
      name: 'Salmon Bowl',
      proteinType: ['Salmon'],
      ingredients: ['Chicken Stock', 'Rice', 'Salmon'],
    }),
  );
  check('chicken stock does not make it a chicken dish', withStock === plain, `${withStock} vs ${plain}`);
  check(
    'protein type is what counts',
    scoreOf(meal({ name: 'Mystery Bowl', proteinType: ['Chicken Thigh'] })) > scoreOf(meal({ name: 'Mystery Bowl' })),
  );
  check(
    'a protein tag counts too',
    scoreOf(meal({ name: 'Mystery Bowl', tags: ['Chicken'] })) > scoreOf(meal({ name: 'Mystery Bowl' })),
  );
  check('the name still counts', scoreOf(meal({ name: 'Grilled Chicken' })) > scoreOf(meal({ name: 'Grilled Tofu' })));
}

// The most specific matching term wins, so a general like cannot cancel out a
// specific dislike. Live example: "Spinach Cauliflower Puree" scored
// +1 cauliflower -1 puree = 0, and still ranked sixth.
{
  const specific: Preferences = {
    ...prefs,
    ingredients: { cauliflower: 1, puree: -1, 'cauliflower puree': -1.5 },
  };
  const score = (m: Meal): number => rankMeals([m], specific).ranked[0]?.score ?? Number.NaN;
  const plain = score(meal({ name: 'Bowl' }));
  const puree = score(meal({ name: 'Bowl', sides: ['Spinach Cauliflower Puree'] }));
  const whole = score(meal({ name: 'Bowl', sides: ['Roasted Cauliflower'] }));
  check('specific term replaces the general ones', puree === plain - 1.5, `${puree} vs ${plain}`);
  check('the general term still scores on its own', whole === plain + 1, `${whole} vs ${plain}`);
  // Assert on the ingredient reasons only; a rating reason is always present.
  const ingredientReasons = (rankMeals([meal({ name: 'Bowl', sides: ['Cauliflower Puree'] })], specific)
    .ranked[0]?.reasons ?? [])
    .map((r) => r.text)
    .filter((t) => !t.startsWith('rated '));
  check('only the specific reason is shown', ingredientReasons.join(',') === 'cauliflower puree', ingredientReasons.join(','));
}

// Exclusions are the opposite: a trace amount in the declaration must catch.
{
  const run = (m: Meal) => rankMeals([m], prefs);
  check(
    'exclusion catches a trace ingredient',
    run(meal({ name: 'Caesar Bowl', ingredients: ['Anchovy Paste', 'Romaine'] })).excluded.length === 1,
  );
}

// Word-boundary matching, so substrings do not fire by accident.
{
  const plain = scoreOf(meal({ name: 'Plain Bowl' }));
  check('exact word matches', scoreOf(meal({ name: 'Beef Bowl' })) > plain);
  check('"chicken" does not match "chickpea"', scoreOf(meal({ name: 'Chickpea Stew' })) === plain);
  // The bug this guards: broccolini is a different vegetable from broccoli.
  check(
    '"broccoli" does not match "broccolini"',
    scoreOf(meal({ name: 'Bowl', sides: ['Roasted Broccolini'] })) === plain,
  );
  check(
    'plurals still match',
    scoreOf(meal({ name: 'Bowl', sides: ['Roasted Broccoli Florets'] })) === plain + 2,
  );
  // Compare against a baseline rather than an absolute: the stock test meal
  // carries a 4.5 rating, which contributes points of its own.
  {
    const withBean = (m: Meal): number =>
      rankMeals([m], { ...prefs, ingredients: { 'green bean': 1.5 } }).ranked[0]?.score ?? Number.NaN;
    check(
      'multi-word plurals still match',
      withBean(meal({ name: 'Bowl', sides: ['Green Beans'] })) === withBean(meal({ name: 'Bowl' })) + 1.5,
    );
  }
}

// Hard gates.
{
  const run = (m: Meal) => rankMeals([m], prefs);
  check('over-calorie meal excluded', run(meal({ calories: 1200 })).excluded.length === 1);
  check('low-rated meal excluded', run(meal({ rating: 3.9 })).excluded.length === 1);
  check('thin-review meal excluded', run(meal({ reviewCount: 4 })).excluded.length === 1);
  check('excluded term drops the meal', run(meal({ description: 'with anchovy butter' })).excluded.length === 1);
  check(
    'missing rating is not treated as failing',
    run(meal({ rating: null, reviewCount: null })).ranked.length === 1,
  );
  check(
    'exclusion states its reason',
    (run(meal({ calories: 1200 })).excluded[0]?.why ?? '').includes('calorie'),
  );
}

// Tag bonuses stand in for the macros the API does not send.
{
  const highProtein = scoreOf(meal({ name: 'Bowl', tags: ['High Protein'] }));
  const salty = scoreOf(meal({ name: 'Bowl', tags: ['High Sodium'] }));
  const plain = scoreOf(meal({ name: 'Bowl' }));
  check('high-protein tag helps', highProtein === plain + 2, `${highProtein} vs ${plain}`);
  check('high-sodium tag hurts', salty === plain - 1, `${salty} vs ${plain}`);
}

// Rating is measured from 4.0 so an average meal contributes nothing.
// The minRating gate has to be lifted here, or a 4.0 meal never gets scored.
{
  const noGate: Preferences = { ...prefs, limits: { ...prefs.limits, minRating: undefined } };
  const at = (rating: number): number =>
    rankMeals([meal({ name: 'Bowl', rating })], noGate).ranked[0]?.score ?? Number.NaN;
  check('4.0 contributes zero', at(4.0) === 0, String(at(4.0)));
  check('5.0 adds the full rating weight', at(5.0) === 1.5, String(at(5.0)));
  check('below 4.0 is a penalty', at(3.5) === -0.75, String(at(3.5)));
  check('the rating gate still excludes 4.0 by default', scoreOf(meal({ rating: 4.0 })) !== 0);
}

// Ordering and explanations.
{
  const result = rankMeals(
    [
      meal({ name: 'Cauliflower Pork Bowl' }),
      meal({ name: 'Chicken Broccoli Bowl', tags: ['High Protein'] }),
      meal({ name: 'Beef Bowl' }),
    ],
    prefs,
  );
  check('best meal sorts first', result.ranked[0]?.meal.name === 'Chicken Broccoli Bowl');
  check('worst meal sorts last', result.ranked[2]?.meal.name === 'Cauliflower Pork Bowl');
  const top = result.ranked[0];
  const text = top ? explain(top) : '';
  check('explanation names the protein', text.includes('chicken'), text);
  check('explanation names the side', text.includes('broccoli'), text);
  check('explanation is signed', text.includes('+3'), text);
  check(
    'explanation leads with the biggest factor',
    text.startsWith('+3 chicken'),
    text,
  );
}

console.log(failures === 0 ? '\nAll ranking tests passed.\n' : `\n${failures} ranking test(s) failed.\n`);
process.exitCode = failures === 0 ? 0 : 1;
