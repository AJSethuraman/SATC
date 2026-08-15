import type { ApiCandidate, Meal } from './types.js';

/**
 * Key patterns used to recognise meal-shaped objects and to map them onto Meal.
 * Matching is case-insensitive and ignores separators, so `protein_grams`,
 * `proteinGrams` and `Protein Grams` all hit the same pattern.
 */
const FIELD_PATTERNS = {
  id: [/^id$/, /^_id$/, /^uuid$/, /^sku$/, /^slug$/, /^productid$/, /^mealid$/],
  name: [/^name$/, /^title$/, /^mealname$/, /^productname$/, /^displayname$/],
  description: [/^description$/, /^shortdescription$/, /^subtitle$/, /^summary$/],
  chef: [/^chef$/, /^chefname$/, /^brand$/, /^brandname$/, /^creator$/],
  price: [/^price$/, /^baseprice$/, /^unitprice$/, /^amount$/, /^pricecents$/, /^listprice$/],
  premiumFee: [/^premiumfee$/, /^surcharge$/, /^upcharge$/, /^extrafee$/],
  currency: [/^currency$/, /^currencycode$/],
  rating: [/^rating$/, /^avgrating$/, /^averagerating$/, /^stars$/, /^score$/],
  reviewCount: [/^reviewcount$/, /^reviews$/, /^numreviews$/, /^ratingcount$/, /^totalreviews$/],
  calories: [/^calories$/, /^kcal$/, /^energy$/, /^caloriecount$/],
  protein: [/^protein$/, /^proteins$/, /^proteingrams$/, /^proteing$/],
  carbs: [/^carbs$/, /^carbohydrates$/, /^carbohydrate$/, /^carbsgrams$/, /^totalcarbs$/],
  fat: [/^fat$/, /^fats$/, /^totalfat$/, /^fatgrams$/],
  category: [/^category$/, /^cuisine$/, /^cuisines$/, /^categories$/, /^mealtype$/, /^categoryname$/],
  imageUrl: [/^image$/, /^imageurl$/, /^thumbnail$/, /^photo$/, /^picture$/, /^imgurl$/],
  tags: [/^tags$/, /^labels$/, /^badges$/, /^dietarytags$/, /^attributes$/, /^allergens$/],
  // Deliberately not /^protein$/ — that is the macro in grams, not the animal.
  proteinType: [/^meattype$/, /^proteintype$/, /^meat$/],
  ingredients: [/^ingredients$/, /^ingredientsdata$/, /^ingredientlist$/, /^ingredient$/],
  sides: [/^sidedish$/, /^sidedishes$/, /^sides$/, /^side$/],
  warnings: [/^warning$/, /^warnings$/, /^allergens$/, /^allergenwarning$/],
} as const;

type FieldName = keyof typeof FIELD_PATTERNS;

/** Fields whose presence is evidence that an object is a meal, with weights. */
const SCORE_WEIGHTS: Partial<Record<FieldName, number>> = {
  name: 3,
  price: 3,
  calories: 4,
  protein: 4,
  carbs: 2,
  fat: 2,
  chef: 3,
  rating: 1,
  description: 1,
  imageUrl: 1,
  id: 1,
};

const normalizeKey = (key: string): string => key.toLowerCase().replace(/[\s_\-.]/g, '');

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/**
 * Find a value for `field` on `obj`, descending one level into nested objects
 * (nutrition blocks like `{ nutritionalInfo: { calories: 500 } }` are common).
 */
function findField(obj: Record<string, unknown>, field: FieldName): unknown {
  const patterns = FIELD_PATTERNS[field];
  for (const [key, value] of Object.entries(obj)) {
    if (patterns.some((p) => p.test(normalizeKey(key)))) {
      if (value !== null && value !== undefined && !isPlainObject(value)) return value;
      // A matching key holding an object (e.g. `price: { amount: 1399 }`) —
      // take the first primitive inside it.
      if (isPlainObject(value)) {
        const inner = Object.values(value).find((v) => typeof v === 'number' || typeof v === 'string');
        if (inner !== undefined) return inner;
      }
    }
  }
  for (const value of Object.values(obj)) {
    if (isPlainObject(value)) {
      for (const [key, nested] of Object.entries(value)) {
        if (patterns.some((p) => p.test(normalizeKey(key)))) {
          if (nested !== null && nested !== undefined && !isPlainObject(nested)) return nested;
        }
      }
    }
  }
  return undefined;
}

/** How strongly a single object resembles a meal. */
function scoreObject(obj: Record<string, unknown>): number {
  let score = 0;
  for (const [field, weight] of Object.entries(SCORE_WEIGHTS) as [FieldName, number][]) {
    if (findField(obj, field) !== undefined) score += weight;
  }
  return score;
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const match = value.replace(/,/g, '').match(/-?\d+(\.\d+)?/);
    if (match) {
      const parsed = Number.parseFloat(match[0]);
      return Number.isFinite(parsed) ? parsed : null;
    }
  }
  return null;
}

function toStringOrNull(value: unknown): string | null {
  if (typeof value === 'string') return value.trim() || null;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return null;
}

/**
 * Coerce a field into a list of strings. These fields (ingredients, sides,
 * meat type) arrive in whatever shape the backend felt like: a comma-joined
 * string, a flat array, or an array of objects with a name.
 */
function toStringList(value: unknown): string[] | undefined {
  const out: string[] = [];
  const push = (item: unknown): void => {
    if (typeof item === 'string') {
      // Split joined strings, but keep multi-word entries like "Chicken Thigh".
      for (const part of item.split(/[,;|]/)) {
        const trimmed = part.trim();
        if (trimmed) out.push(trimmed);
      }
    } else if (isPlainObject(item)) {
      const name = toStringOrNull(findField(item, 'name'));
      if (name) out.push(name);
    }
  };

  if (Array.isArray(value)) value.forEach(push);
  else if (isPlainObject(value)) Object.values(value).forEach(push);
  else push(value);

  return out.length ? Array.from(new Set(out)) : undefined;
}

function toTags(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const tags = value
    .map((item) => {
      if (typeof item === 'string') return item;
      if (isPlainObject(item)) return toStringOrNull(findField(item, 'name'));
      return null;
    })
    .filter((tag): tag is string => Boolean(tag));
  return tags.length ? tags : undefined;
}

/**
 * Prices arrive as either dollars (13.99) or integer cents (1399). Values that
 * are whole numbers of implausible size for a single meal are treated as cents.
 */
function normalizePrice(value: unknown): number | null {
  const raw = toNumber(value);
  if (raw === null) return null;
  if (Number.isInteger(raw) && raw >= 200) return raw / 100;
  return raw;
}

/**
 * Nutrition frequently arrives as a list of label/value pairs
 * (`[{name: 'Protein', value: '45g'}]`) rather than an object with macro keys,
 * which `findField` cannot see into. Flatten any such list into a lookup.
 */
function nutritionPairs(obj: Record<string, unknown>): Map<string, unknown> {
  const pairs = new Map<string, unknown>();
  for (const [key, value] of Object.entries(obj)) {
    if (!/nutrition|nutrient|macro/i.test(key) || !Array.isArray(value)) continue;
    for (const entry of value) {
      if (!isPlainObject(entry)) continue;
      const label = entry['name'] ?? entry['label'] ?? entry['key'] ?? entry['title'];
      const amount = entry['value'] ?? entry['amount'] ?? entry['qty'] ?? entry['quantity'];
      if (typeof label === 'string' && amount !== undefined) {
        pairs.set(normalizeKey(label), amount);
      }
    }
  }
  return pairs;
}

/** Chef is often split across `chef_firstname` / `chef_lastname`. */
function composeChef(obj: Record<string, unknown>): string | null {
  let first: string | null = null;
  let last: string | null = null;
  for (const [key, value] of Object.entries(obj)) {
    const normalized = normalizeKey(key);
    if (/^cheffirst/.test(normalized)) first = toStringOrNull(value);
    if (/^cheflast/.test(normalized)) last = toStringOrNull(value);
  }
  const joined = [first, last].filter(Boolean).join(' ').trim();
  return joined || toStringOrNull(findField(obj, 'chef'));
}

/** Category fields may hold a list (`cuisines: ['Mexican']`) instead of a string. */
function toCategory(value: unknown): string | null {
  if (Array.isArray(value)) {
    const first = value[0];
    if (typeof first === 'string') return first;
    if (isPlainObject(first)) return toStringOrNull(findField(first, 'name'));
    return null;
  }
  return toStringOrNull(value);
}

export function mealFromJson(obj: Record<string, unknown>): Meal | null {
  const name = toStringOrNull(findField(obj, 'name'));
  if (!name) return null;

  const nutrition = nutritionPairs(obj);
  /** Direct key first, then the flattened nutrition label/value list. */
  const macro = (field: FieldName, ...labels: string[]): number | null => {
    const direct = toNumber(findField(obj, field));
    if (direct !== null) return direct;
    for (const label of labels) {
      const hit = nutrition.get(label);
      if (hit !== undefined) return toNumber(hit);
    }
    return null;
  };

  const price = normalizePrice(findField(obj, 'price'));
  return {
    id: toStringOrNull(findField(obj, 'id')),
    name,
    description: toStringOrNull(findField(obj, 'description')),
    chef: composeChef(obj),
    price,
    premiumFee: normalizePrice(findField(obj, 'premiumFee')),
    // Assume USD when a price is present but no currency is stated — every
    // known CookUnity store prices in dollars.
    currency: toStringOrNull(findField(obj, 'currency')) ?? (price === null ? null : 'USD'),
    rating: toNumber(findField(obj, 'rating')),
    reviewCount: toNumber(findField(obj, 'reviewCount')),
    calories: macro('calories', 'calories', 'energy'),
    protein: macro('protein', 'protein', 'totalprotein'),
    carbs: macro('carbs', 'carbs', 'carbohydrates', 'totalcarbohydrate', 'totalcarbohydrates'),
    fat: macro('fat', 'fat', 'totalfat'),
    tags: toTags(findField(obj, 'tags')),
    category: toCategory(findField(obj, 'category')),
    proteinType: toStringList(findField(obj, 'proteinType')),
    ingredients: toStringList(findField(obj, 'ingredients')),
    sides: toStringList(findField(obj, 'sides')),
    warnings: toStringList(findField(obj, 'warnings')),
    imageUrl: toStringOrNull(findField(obj, 'imageUrl')),
  };
}

export interface ArrayHit {
  path: string;
  items: Record<string, unknown>[];
  score: number;
}

/**
 * Walk a decoded JSON payload and return the array of objects that looks most
 * like a meal list. Score is the mean per-object score times a small bonus for
 * longer arrays, so a 40-meal menu outranks a 2-item "recommended" teaser.
 */
export function findMealArray(payload: unknown, maxDepth = 6): ArrayHit | null {
  let best: ArrayHit | null = null;

  const walk = (node: unknown, path: string, depth: number): void => {
    if (depth > maxDepth || node === null || typeof node !== 'object') return;

    if (Array.isArray(node)) {
      const objects = node.filter(isPlainObject);
      if (objects.length >= 2 && objects.length === node.length) {
        const sample = objects.slice(0, 10);
        const mean = sample.reduce((sum, item) => sum + scoreObject(item), 0) / sample.length;
        if (mean >= 6) {
          const score = mean * (1 + Math.min(objects.length, 60) / 60);
          if (!best || score > best.score) best = { path, items: objects, score };
        }
      }
      node.forEach((item, index) => walk(item, `${path}[${index}]`, depth + 1));
      return;
    }

    for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
      walk(value, path ? `${path}.${key}` : key, depth + 1);
    }
  };

  walk(payload, '', 0);
  return best;
}

export function candidateFromHit(
  hit: ArrayHit,
  meta: { url: string; method: string; status: number; usedAuthHeader: boolean },
): ApiCandidate {
  return {
    url: meta.url,
    method: meta.method,
    status: meta.status,
    score: Math.round(hit.score * 10) / 10,
    path: hit.path,
    itemCount: hit.items.length,
    sampleKeys: Object.keys(hit.items[0] ?? {}).slice(0, 30),
    usedAuthHeader: meta.usedAuthHeader,
  };
}
