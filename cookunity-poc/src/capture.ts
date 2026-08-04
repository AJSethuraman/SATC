import type { Page } from 'playwright';
import { SITE } from './config.js';
import { candidateFromHit, findMealArray } from './detect.js';
import { installEvaluateShim } from './evaluate-shim.js';
import type { ApiCandidate } from './types.js';

export interface Capture {
  candidate: ApiCandidate;
  items: Record<string, unknown>[];
}

/**
 * Listen to every JSON response the page receives and keep the ones whose
 * payload contains a meal-shaped array. This is Approach A: if the site fetches
 * its menu as data, we read the data rather than the rendered HTML.
 */
export function watchForMealApis(page: Page, captures: Capture[]): void {
  page.on('response', (response) => {
    void (async () => {
      const url = response.url();
      if (SITE.ignoreHostPattern.test(url)) return;

      const contentType = response.headers()['content-type'] ?? '';
      if (!contentType.includes('json')) return;

      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        return; // Streaming, redirected, or already-consumed body.
      }

      const hit = findMealArray(payload);
      if (!hit) return;

      const request = response.request();
      const headers = await request.allHeaders().catch(() => ({}) as Record<string, string>);
      captures.push({
        candidate: candidateFromHit(hit, {
          url,
          method: request.method(),
          status: response.status(),
          usedAuthHeader: Boolean(headers['authorization']),
        }),
        items: hit.items,
      });
    })();
  });
}

/**
 * Approach A-prime: the menu is often serialised into the HTML itself
 * (`__NEXT_DATA__`, `__NUXT__`, or a JSON-LD block) rather than fetched.
 */
export async function extractEmbeddedJson(page: Page): Promise<Capture | null> {
  await installEvaluateShim(page);
  const blobs = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script'))
      .map((script) => script.textContent ?? '')
      .filter((text) => text.length > 200 && text.length < 5_000_000)
      .filter((text) => text.includes('{')),
  );

  let best: Capture | null = null;
  for (const blob of blobs) {
    const start = blob.indexOf('{');
    if (start === -1) continue;
    let payload: unknown;
    try {
      payload = JSON.parse(blob.slice(start));
    } catch {
      continue;
    }
    const hit = findMealArray(payload);
    if (!hit) continue;
    const capture: Capture = {
      candidate: candidateFromHit(hit, {
        url: `${page.url()} (embedded <script>)`,
        method: 'EMBEDDED',
        status: 200,
        usedAuthHeader: false,
      }),
      items: hit.items,
    };
    if (!best || capture.candidate.score > best.candidate.score) best = capture;
  }
  return best;
}
