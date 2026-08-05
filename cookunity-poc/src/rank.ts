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

export function rankMeals(meals: Meal[], prefs: Preferences): RankResult {
  const ranked: RankedMeal[] = [];
  const excluded: Excluded[] = [];

  for (const meal of meals) {
    const identity = identityText(meal);
    const everything = fullText(meal);

    // Exclusions read the full text: a trace amount still disqualifies.
    const why = disqualify(meal, everything, prefs);
    if (why) {
      excluded.push({ meal, why });
      continue;
    }

    const reasons: Reason[] = [];

    // What the protein is matters most — it is the first thing you react to.
    // Identity only, so chicken stock does not make it a chicken dish.
    for (const [term, points] of Object.entries(prefs.proteins)) {
      if (points !== 0 && mentions(identity, term)) {
        reasons.push({ points, text: `${term}` });
      }
    }

    // What it comes with matters nearly as much, and here the ingredient list
    // is the right place to look.
    for (const [term, points] of Object.entries(prefs.ingredients)) {
      if (points !== 0 && mentions(everything, term)) {
        reasons.push({ points, text: `${term}` });
      }
    }

    // Coarse nutrition buckets, standing in for macros the API does not send.
    for (const [tag, points] of Object.entries(prefs.tagBonuses)) {
      if (points !== 0 && (meal.tags ?? []).some((t) => t.toLowerCase() === tag.toLowerCase())) {
        reasons.push({ points, text: tag.toLowerCase() });
      }
    }

    // Rating, measured from 4.0 so an average meal contributes nothing.
    if (typeof meal.rating === 'number') {
      const points = Number(((meal.rating - 4) * prefs.weights.rating).toFixed(2));
      if (points !== 0) {
        reasons.push({ points, text: `rated ${meal.rating}` });
      }
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
