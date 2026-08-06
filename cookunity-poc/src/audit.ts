import type { Preferences } from './preferences.js';
import type { Meal } from './types.js';

/**
 * Every false positive so far had the same shape: a preference term matching
 * text that does not mean what the term means. Chicken stock made salmon a
 * chicken dish; mirin made steak a rice dish; broccolini matched broccoli.
 *
 * Each was caught by eye in a top-15 listing, which only works for terms that
 * happen to surface. This walks every term against the whole menu and reports
 * the distinct strings it matched, so the wrong ones are visible at a glance
 * rather than by luck.
 */

export interface TermAudit {
  section: 'proteins' | 'cuisines' | 'ingredients' | 'tagBonuses' | 'exclude';
  term: string;
  weight: number | null;
  /** How many meals the term fires on. */
  meals: number;
  /** Matches where the term was a modifier, not the head — the false positives. */
  matchedText: string[];
  examples: string[];
  flags: string[];
}

const escape = (term: string): string => term.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Same rule as the ranker: whole words, plural suffix only. */
function mentions(text: string, term: string): boolean {
  return new RegExp(`(^|[^a-z])${escape(term)}(e?s)?([^a-z]|$)`, 'i').test(text);
}

/**
 * Whether the term is the head of the phrase rather than a modifier.
 *
 * This is the real tell for a false positive. "Jasmine Rice" is rice;
 * "Rice Wine" is not. "Steamed Broccoli" is broccoli; "Chicken Stock" is not
 * chicken. Counting distinct matches flags every term with more than one
 * preparation — checking position finds the ones that changed meaning.
 */
function isHeadOfPhrase(text: string, term: string): boolean {
  return new RegExp(`(^|[^a-z])${escape(term)}(e?s)?[^a-z]*$`, 'i').test(text.trim());
}

/** Fields that say what a meal is, mirroring the ranker's identity split. */
const identityFields = (meal: Meal): string[] => [
  meal.name,
  meal.description ?? '',
  meal.category ?? '',
  ...(meal.proteinType ?? []),
  ...(meal.tags ?? []),
];

const contentFields = (meal: Meal): string[] => [
  ...identityFields(meal),
  ...(meal.ingredients ?? []),
  ...(meal.sides ?? []),
];

export function auditTerms(meals: Meal[], prefs: Preferences): TermAudit[] {
  const total = meals.length || 1;
  const report: TermAudit[] = [];

  /**
   * `exact` mirrors how the ranker matches: cuisines and tag bonuses compare
   * whole tags, everything else does word matching. Auditing with a looser
   * rule than the ranker reports matches that never actually score.
   *
   * `checkModifiers` is only meaningful where the ingredient declaration is
   * searched. Cut names like "Chicken Breast" or "Pork Loin" are legitimate,
   * so flagging them in identity fields is noise.
   */
  const scan = (
    section: TermAudit['section'],
    term: string,
    weight: number | null,
    fieldsOf: (meal: Meal) => string[],
    { exact = false, checkModifiers = false }: { exact?: boolean; checkModifiers?: boolean } = {},
  ): void => {
    const modifierMatches = new Set<string>();
    const examples: string[] = [];
    let count = 0;

    for (const meal of meals) {
      const hits = fieldsOf(meal).filter((field) =>
        field && (exact ? field.toLowerCase() === term.toLowerCase() : mentions(field, term)),
      );
      if (!hits.length) continue;
      count += 1;
      if (checkModifiers) {
        for (const hit of hits) {
          // The name and description are human-written and trustworthy; the
          // ingredient declaration is where compound names hide.
          if (hit === meal.name || hit === meal.description) continue;
          if (!isHeadOfPhrase(hit, term)) modifierMatches.add(hit.trim());
        }
      }
      if (examples.length < 3) examples.push(meal.name);
    }

    const flags: string[] = [];
    if (count === 0) flags.push('never fires — dead weight');
    if (count / total > 0.4) flags.push(`fires on ${Math.round((count / total) * 100)}% — weak discriminator`);
    if (modifierMatches.size) {
      flags.push(`matches as a modifier — probably not the actual ingredient`);
    }

    report.push({
      section,
      term,
      weight,
      meals: count,
      matchedText: [...modifierMatches].sort().slice(0, 12),
      examples,
      flags,
    });
  };

  for (const [term, weight] of Object.entries(prefs.proteins)) {
    scan('proteins', term, weight, identityFields);
  }
  for (const [term, weight] of Object.entries(prefs.cuisines ?? {})) {
    scan('cuisines', term, weight, (meal) => meal.tags ?? [], { exact: true });
  }
  for (const [term, weight] of Object.entries(prefs.ingredients)) {
    scan('ingredients', term, weight, contentFields, { checkModifiers: true });
  }
  for (const [term, weight] of Object.entries(prefs.tagBonuses)) {
    scan('tagBonuses', term, weight, (meal) => meal.tags ?? [], { exact: true });
  }
  // Exclusions matter most: an over-firing one silently removes the menu.
  for (const term of prefs.exclude) {
    scan('exclude', term, null, contentFields, { checkModifiers: true });
  }

  return report.sort((a, b) => b.flags.length - a.flags.length || b.meals - a.meals);
}
