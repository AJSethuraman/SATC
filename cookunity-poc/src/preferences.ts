import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './config.js';

/**
 * What you like, what you don't, and what disqualifies a meal outright.
 *
 * Everything is matched case-insensitively against the meal's whole text —
 * name, description, ingredients, sides, protein type, cuisine and tags —
 * because the backend spreads the same fact across different fields depending
 * on the meal. "broccoli" catches it whether it lands in the ingredient list
 * or only in the description.
 */
export interface Preferences {
  /** Protein preferences. Positive is good, negative is bad, 0 is neutral. */
  proteins: Record<string, number>;
  /** Ingredient and preparation preferences, same scale. */
  ingredients: Record<string, number>;
  /** Any meal matching one of these is excluded outright, with a reason. */
  exclude: string[];
  limits: {
    maxCalories?: number;
    minRating?: number;
    /** Drop meals with few reviews — a 5.0 from 3 people is not a signal. */
    minReviewCount?: number;
  };
  /** Coarse nutrition buckets from the tag list, since real macros are absent. */
  tagBonuses: Record<string, number>;
  weights: {
    /** How much a rating above 4.0 is worth, per star. */
    rating: number;
  };
}

export const PREFERENCES_PATH = path.join(ROOT, 'preferences.json');

export function loadPreferences(filePath = PREFERENCES_PATH): Preferences {
  if (!fs.existsSync(filePath)) {
    throw new Error(`No preferences file at ${filePath}.`);
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8')) as Preferences;
}
