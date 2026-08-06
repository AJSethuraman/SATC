import type { Preferences } from './preferences.js';
import type { Meal } from './types.js';

export interface Reason {
  /** Signed contribution to the score. */
  points: number;
  text: string;
}

export interface RankedMeal {
  meal: Meal;
  score: number;
  reasons: Reason[];
}

export interface Excluded {
  meal: Meal;
  why: string;
}

export interface RankResult {
  ranked: RankedMeal[];
  excluded: Excluded[];
}

/**
 * What the meal *is*: name, description, cuisine, protein type and tags.
 *
 * Deliberately excludes the ingredient list. CookUnity ships a full
 * declaration listing every trace component, and stock is the trap: mole,
 * dirty rice and most pilafs contain chicken stock, so matching protein
 * preferences against ingredients labelled a salmon dish, a shrimp dish and a
 * beef dish all as "chicken". Protein type and tags state the real answer
 * ("Salmon", "Fish", "Poultry", "Chicken Thigh").
 */
function identityText(meal: Meal): string {
  return [
    meal.name,
    meal.description ?? '',
    meal.category ?? '',
    ...(meal.proteinType ?? []),
    ...(meal.tags ?? []),
  ]
    .join(' | ')
    .toLowerCase();
}

/**
 * Everything, including the full ingredient declaration and sides. Used for
 * ingredient preferences — where a trace mention is a genuine hit — and for
 * exclusions, where catching trace amounts is the entire point.
 */
function fullText(meal: Meal): string {
  return [identityText(meal), ...(meal.ingredients ?? []), ...(meal.sides ?? [])]
    .join(' | ')
    .toLowerCase();
}

/**
 * Match a term on whole-word boundaries, allowing only a plural suffix.
 *
 * Both ends have to be anchored: without a trailing boundary "broccoli" fires
 * on "broccolini", which is a different vegetable. But a bare boundary would
 * miss "beets" and "green beans", so an optional s/es is permitted — and
 * nothing else.
 */
function mentions(text: string, term: string): boolean {
  const escaped = term.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(^|[^a-z])${escaped}(e?s)?([^a-z]|$)`, 'i').test(text);
}

/** Hard gates. Returns the reason for dropping the meal, or null to keep it. */
function disqualify(meal: Meal, text: string, prefs: Preferences): string | null {
  for (const term of prefs.exclude) {
    if (mentions(text, term)) return `excluded: contains "${term}"`;
  }
  const { maxCalories, minRating, minReviewCount } = prefs.limits;
  if (maxCalories !== undefined && (meal.calories ?? 0) > maxCalories) {
    return `over calorie limit (${meal.calories} > ${maxCalories})`;
  }
  // A missing rating is not a failing rating — keep it and let it score low.
  if (minRating !== undefined && meal.rating !== null && meal.rating !== undefined) {
    if (meal.rating < minRating) return `rated below ${minRating} (${meal.rating})`;
  }
  if (minReviewCount !== undefined && meal.reviewCount !== null && meal.reviewCount !== undefined) {
    if (meal.reviewCount < minReviewCount) {
      return `too few reviews (${meal.reviewCount} < ${minReviewCount})`;
    }
  }
  return null;
}

/** Which preference terms a meal activates, independent of their weights. */
export interface Features {
  /** A meal has one protein identity; overlapping terms must not stack. */
  protein: string | null;
  /** Likewise one cuisine, though the menu often tags three. */
  cuisine: string | null;
  ingredients: string[];
  tags: string[];
  /** Rating measured from 4.0, so an average meal contributes nothing. */
  ratingDelta: number;
}

/**
 * Of several matching terms, pick the one that should speak for the meal: the
 * strongest dislike if there is one, otherwise the strongest like. Avoidance
 * outranks attraction — a dish you won't eat is not redeemed by also being
 * something you would.
 */
function dominant(matches: string[], weights: Record<string, number>): string | null {
  if (!matches.length) return null;
  const negative = matches.filter((term) => (weights[term] ?? 0) < 0);
  const pool = negative.length ? negative : matches;
  return pool.reduce((best, term) =>
    Math.abs(weights[term] ?? 0) > Math.abs(weights[best] ?? 0) ? term : best,
  );
}

/**
 * Separating "which terms fired" from "what they are worth" is what lets the
 * same code both score a meal and learn weights from feedback.
 */
export function featuresOf(meal: Meal, prefs: Preferences): Features {
  const identity = identityText(meal);
  const everything = fullText(meal);

  // Salmon is also fish; without this, salmon outscores chicken purely by
  // matching two terms.
  const protein = dominant(
    Object.keys(prefs.proteins).filter((term) => mentions(identity, term)),
    prefs.proteins,
  );

  // Cuisine tags stack three-deep on some meals, which let tag-count outweigh
  // both the protein and a stated dislike. One cuisine per meal.
  const cuisineWeights = prefs.cuisines ?? {};
  const cuisine = dominant(
    Object.keys(cuisineWeights).filter((name) =>
      (meal.tags ?? []).some((tag) => tag.toLowerCase() === name.toLowerCase()),
    ),
    cuisineWeights,
  );

  // The most specific matching term wins. "cauliflower puree" matches both
  // "cauliflower" (+1) and "puree" (-1), netting zero — but the dish is
  // precisely the form being avoided, so the general terms must not score.
  const matchedIngredients = Object.keys(prefs.ingredients).filter((term) => mentions(everything, term));

  return {
    protein,
    cuisine,
    ingredients: matchedIngredients.filter(
      (term) => !matchedIngredients.some((other) => other !== term && other.includes(term)),
    ),
    tags: Object.keys(prefs.tagBonuses).filter((tag) =>
      (meal.tags ?? []).some((t) => t.toLowerCase() === tag.toLowerCase()),
    ),
    ratingDelta: typeof meal.rating === 'number' ? meal.rating - 4 : 0,
  };
}

export function rankMeals(meals: Meal[], prefs: Preferences): RankResult {
  const ranked: RankedMeal[] = [];
  const excluded: Excluded[] = [];

  for (const meal of meals) {
    // Exclusions read the full text: a trace amount still disqualifies.
    const why = disqualify(meal, fullText(meal), prefs);
    if (why) {
      excluded.push({ meal, why });
      continue;
    }

    const features = featuresOf(meal, prefs);
    const reasons: Reason[] = [];

    if (features.protein) {
      const points = prefs.proteins[features.protein] ?? 0;
      if (points !== 0) reasons.push({ points, text: features.protein });
    }
    if (features.cuisine) {
      const points = (prefs.cuisines ?? {})[features.cuisine] ?? 0;
      if (points !== 0) reasons.push({ points, text: features.cuisine.toLowerCase() });
    }
    for (const term of features.ingredients) {
      const points = prefs.ingredients[term] ?? 0;
      if (points !== 0) reasons.push({ points, text: term });
    }
    for (const tag of features.tags) {
      const points = prefs.tagBonuses[tag] ?? 0;
      if (points !== 0) reasons.push({ points, text: tag.toLowerCase() });
    }
    if (features.ratingDelta !== 0) {
      const points = Number((features.ratingDelta * prefs.weights.rating).toFixed(2));
      if (points !== 0) reasons.push({ points, text: `rated ${meal.rating}` });
    }

    const score = Number(reasons.reduce((sum, r) => sum + r.points, 0).toFixed(2));
    ranked.push({ meal, score, reasons });
  }

  ranked.sort((a, b) => b.score - a.score || (b.meal.rating ?? 0) - (a.meal.rating ?? 0));
  return { ranked, excluded };
}

/** One line of plain English explaining why a meal placed where it did. */
export function explain(entry: RankedMeal): string {
  const ordered = [...entry.reasons].sort((a, b) => Math.abs(b.points) - Math.abs(a.points));
  const parts = ordered.map((r) => `${r.points > 0 ? '+' : ''}${r.points} ${r.text}`);
  return parts.length ? parts.join(', ') : 'nothing matched your preferences';
}
