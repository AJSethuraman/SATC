/** Which extraction path produced the data. */
export type Approach = 'api' | 'embedded' | 'dom';

export interface Meal {
  id: string | null;
  name: string;
  description?: string | null;
  chef?: string | null;
  price?: number | null;
  currency?: string | null;
  rating?: number | null;
  reviewCount?: number | null;
  calories?: number | null;
  protein?: number | null;
  carbs?: number | null;
  fat?: number | null;
  tags?: string[];
  category?: string | null;
  imageUrl?: string | null;
  sourceUrl?: string | null;
}

export interface MealsFile {
  capturedAt: string;
  approach: Approach;
  /** URL or selector the meals came from, so a stale capture is traceable. */
  source: string;
  mealCount: number;
  meals: Meal[];
}

/** A JSON response that scored high enough to look like meal data. */
export interface ApiCandidate {
  url: string;
  method: string;
  status: number;
  /** Heuristic score — higher means the payload looks more like a meal list. */
  score: number;
  /** Dotted path to the array inside the payload, '' for a top-level array. */
  path: string;
  itemCount: number;
  /** Keys seen on the first item, for the discovery report. */
  sampleKeys: string[];
  /** Whether the request carried an Authorization header vs. relying on cookies. */
  usedAuthHeader: boolean;
}
