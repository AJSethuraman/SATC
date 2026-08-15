import { featuresOf } from './rank.js';
import type { Preferences } from './preferences.js';
import type { Meal } from './types.js';

export type Verdict = 'like' | 'dislike';

export interface Label {
  id: string;
  verdict: Verdict;
  /** Kept for the report, so a weight change can name the meals behind it. */
  name?: string;
}

export interface WeightChange {
  section: 'proteins' | 'cuisines' | 'ingredients' | 'tagBonuses' | 'weights';
  term: string;
  from: number;
  to: number;
  liked: number;
  disliked: number;
}

export interface FitResult {
  preferences: Preferences;
  changes: WeightChange[];
  /** Terms no labelled meal exercised — untouched, and worth surfacing. */
  untouched: string[];
  /** Share of labels the fitted weights rank on the correct side of zero. */
  accuracy: number;
  labelled: number;
}

export interface FitOptions {
  learningRate?: number;
  /** Pull back toward the hand-written weights; your stated intent is a prior. */
  regularisation?: number;
  epochs?: number;
  /** Weights are clamped to ±this, so one label cannot dominate. */
  clamp?: number;
}

const sigmoid = (x: number): number => 1 / (1 + Math.exp(-x));
const round = (x: number): number => Number(x.toFixed(3));

/**
 * Fit preference weights to thumbs up/down on real meals.
 *
 * Logistic regression over the same features the ranker scores with, pulled
 * toward the existing hand-written weights. The pull matters: with a dozen
 * labels the data alone would happily conclude that beef is worth -4 because
 * the two beef meals you saw were mediocre. Your stated preferences are the
 * prior; feedback adjusts them rather than replacing them.
 *
 * Deterministic — no random init, no shuffling — so the same labels always
 * produce the same weights.
 */
export function fitWeights(
  meals: Meal[],
  prefs: Preferences,
  labels: Label[],
  options: FitOptions = {},
): FitResult {
  // Tuned so a single rating nudges a weight (~0.3-0.5) without flipping its
  // sign, while a term rated consistently several times moves properly. The
  // deviation from the prior scales with how often a term was exercised.
  const learningRate = options.learningRate ?? 0.15;
  const regularisation = options.regularisation ?? 0.2;
  const epochs = options.epochs ?? 200;
  const clamp = options.clamp ?? 5;

  const byId = new Map(meals.map((meal) => [meal.id ?? meal.name, meal]));
  const examples = labels
    .map((label) => {
      const meal = byId.get(label.id);
      return meal ? { meal, features: featuresOf(meal, prefs), target: label.verdict === 'like' ? 1 : 0 } : null;
    })
    .filter((x): x is NonNullable<typeof x> => x !== null);

  // Working copy; the prior stays pinned to the original values.
  const prior = structuredClone(prefs);
  const fitted = structuredClone(prefs);

  const counts = new Map<string, { liked: number; disliked: number }>();
  const bump = (term: string, target: number): void => {
    const current = counts.get(term) ?? { liked: 0, disliked: 0 };
    if (target === 1) current.liked += 1;
    else current.disliked += 1;
    counts.set(term, current);
  };
  for (const example of examples) {
    if (example.features.protein) bump(`proteins:${example.features.protein}`, example.target);
    if (example.features.cuisine) bump(`cuisines:${example.features.cuisine}`, example.target);
    for (const term of example.features.ingredients) bump(`ingredients:${term}`, example.target);
    for (const tag of example.features.tags) bump(`tagBonuses:${tag}`, example.target);
  }

  const scoreOf = (features: ReturnType<typeof featuresOf>): number => {
    let total = features.ratingDelta * fitted.weights.rating;
    if (features.protein) total += fitted.proteins[features.protein] ?? 0;
    if (features.cuisine) total += (fitted.cuisines ?? {})[features.cuisine] ?? 0;
    for (const term of features.ingredients) total += fitted.ingredients[term] ?? 0;
    for (const tag of features.tags) total += fitted.tagBonuses[tag] ?? 0;
    return total;
  };

  for (let epoch = 0; epoch < epochs; epoch += 1) {
    for (const { features, target } of examples) {
      const error = target - sigmoid(scoreOf(features));
      const step = learningRate * error;
      if (features.protein && features.protein in fitted.proteins) {
        fitted.proteins[features.protein] = (fitted.proteins[features.protein] ?? 0) + step;
      }
      if (features.cuisine && fitted.cuisines && features.cuisine in fitted.cuisines) {
        fitted.cuisines[features.cuisine] = (fitted.cuisines[features.cuisine] ?? 0) + step;
      }
      for (const term of features.ingredients) {
        fitted.ingredients[term] = (fitted.ingredients[term] ?? 0) + step;
      }
      for (const tag of features.tags) {
        fitted.tagBonuses[tag] = (fitted.tagBonuses[tag] ?? 0) + step;
      }
      fitted.weights.rating += step * features.ratingDelta;
    }

    // Decay toward the stated preferences, and keep every weight bounded.
    const pull = (value: number, priorValue: number): number =>
      Math.max(-clamp, Math.min(clamp, value - regularisation * (value - priorValue)));
    for (const key of Object.keys(fitted.proteins)) {
      fitted.proteins[key] = pull(fitted.proteins[key] ?? 0, prior.proteins[key] ?? 0);
    }
    for (const key of Object.keys(fitted.cuisines ?? {})) {
      fitted.cuisines![key] = pull(fitted.cuisines![key] ?? 0, prior.cuisines?.[key] ?? 0);
    }
    for (const key of Object.keys(fitted.ingredients)) {
      fitted.ingredients[key] = pull(fitted.ingredients[key] ?? 0, prior.ingredients[key] ?? 0);
    }
    for (const key of Object.keys(fitted.tagBonuses)) {
      fitted.tagBonuses[key] = pull(fitted.tagBonuses[key] ?? 0, prior.tagBonuses[key] ?? 0);
    }
    fitted.weights.rating = pull(fitted.weights.rating, prior.weights.rating);
  }

  const changes: WeightChange[] = [];
  const record = (section: WeightChange['section'], term: string, from: number, to: number): void => {
    if (round(from) === round(to)) return;
    const seen = counts.get(`${section}:${term}`) ?? { liked: 0, disliked: 0 };
    changes.push({ section, term, from: round(from), to: round(to), ...seen });
  };
  for (const key of Object.keys(fitted.proteins)) {
    fitted.proteins[key] = round(fitted.proteins[key] ?? 0);
    record('proteins', key, prior.proteins[key] ?? 0, fitted.proteins[key] ?? 0);
  }
  for (const key of Object.keys(fitted.cuisines ?? {})) {
    fitted.cuisines![key] = round(fitted.cuisines![key] ?? 0);
    record('cuisines', key, prior.cuisines?.[key] ?? 0, fitted.cuisines![key] ?? 0);
  }
  for (const key of Object.keys(fitted.ingredients)) {
    fitted.ingredients[key] = round(fitted.ingredients[key] ?? 0);
    record('ingredients', key, prior.ingredients[key] ?? 0, fitted.ingredients[key] ?? 0);
  }
  for (const key of Object.keys(fitted.tagBonuses)) {
    fitted.tagBonuses[key] = round(fitted.tagBonuses[key] ?? 0);
    record('tagBonuses', key, prior.tagBonuses[key] ?? 0, fitted.tagBonuses[key] ?? 0);
  }
  fitted.weights.rating = round(fitted.weights.rating);
  record('weights', 'rating', prior.weights.rating, fitted.weights.rating);

  changes.sort((a, b) => Math.abs(b.to - b.from) - Math.abs(a.to - a.from));

  const untouched = [
    ...Object.keys(prior.proteins).map((k) => `proteins:${k}`),
    ...Object.keys(prior.cuisines ?? {}).map((k) => `cuisines:${k}`),
    ...Object.keys(prior.ingredients).map((k) => `ingredients:${k}`),
    ...Object.keys(prior.tagBonuses).map((k) => `tagBonuses:${k}`),
  ].filter((key) => !counts.has(key));

  const correct = examples.filter(({ features, target }) => {
    const predicted = scoreOf(features) > 0 ? 1 : 0;
    return predicted === target;
  }).length;

  return {
    preferences: fitted,
    changes,
    untouched,
    accuracy: examples.length ? correct / examples.length : 0,
    labelled: examples.length,
  };
}

/**
 * Pick meals worth asking about: spread across the score range rather than
 * only the top, since labelling fifteen meals you already rank highly teaches
 * the model nothing about what you dislike.
 */
export function samplesToLabel(ranked: { meal: Meal; score: number }[], count: number, already: Set<string>): Meal[] {
  const pool = ranked.filter((entry) => !already.has(entry.meal.id ?? entry.meal.name));
  if (pool.length <= count) return pool.map((entry) => entry.meal);

  const picked: Meal[] = [];
  // Even strides through the ranked list: top, upper-middle, middle, and so on.
  for (let i = 0; i < count; i += 1) {
    const index = Math.round((i * (pool.length - 1)) / (count - 1 || 1));
    const entry = pool[index];
    if (entry && !picked.includes(entry.meal)) picked.push(entry.meal);
  }
  return picked;
}
