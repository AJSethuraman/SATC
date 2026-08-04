import type { Page } from 'playwright';
import { installEvaluateShim } from './evaluate-shim.js';
import type { Meal } from './types.js';

export interface ScrapeResult {
  meals: Meal[];
  /** The signature of the repeating element the cards were found under. */
  cardSignature: string | null;
  candidatesConsidered: number;
}

/**
 * Extract meals from the rendered DOM without hardcoded selectors.
 *
 * The site's markup is not knowable ahead of time (class names are hashed and
 * change between deploys), so instead of guessing selectors this finds the
 * repeating structure: elements that contain a price, grouped by their tag and
 * class shape. The largest such group is the menu grid, and each member is a
 * meal card. Fields are then read off each card by role (heading, link, image)
 * and by regex over the card's text.
 */
export async function scrapeMeals(page: Page): Promise<ScrapeResult> {
  await installEvaluateShim(page);
  return page.evaluate(() => {
    const PRICE_RE = /\$\s?(\d{1,3}(?:\.\d{2})?)/;

    const signatureOf = (el: Element): string => {
      const classes = Array.from(el.classList)
        // Hashed/utility classes churn between deploys; keep the shape, not the hash.
        .map((c) => c.replace(/[0-9a-f]{6,}/gi, '#'))
        .sort()
        .join('.');
      return `${el.tagName}|${classes}`;
    };

    const textOf = (el: Element | null | undefined): string =>
      (el?.textContent ?? '').replace(/\s+/g, ' ').trim();

    // Elements that directly render a price, i.e. the innermost price node.
    const priceNodes = Array.from(document.querySelectorAll('*')).filter((el) => {
      if (!PRICE_RE.test(textOf(el))) return false;
      return !Array.from(el.children).some((child) => PRICE_RE.test(textOf(child)));
    });

    // For each price node, walk up to a plausible card: an ancestor that also
    // contains a link or an image, and isn't yet the whole page.
    const cardsBySignature = new Map<string, Element[]>();
    for (const node of priceNodes) {
      let current: Element | null = node.parentElement;
      let hops = 0;
      while (current && hops < 8) {
        const hasAnchor = current.querySelector('a') !== null;
        const hasImage = current.querySelector('img') !== null;
        const text = textOf(current);
        if ((hasAnchor || hasImage) && text.length > 10 && text.length < 2000) {
          const sig = signatureOf(current);
          const bucket = cardsBySignature.get(sig) ?? [];
          if (!bucket.includes(current)) bucket.push(current);
          cardsBySignature.set(sig, bucket);
          break;
        }
        current = current.parentElement;
        hops += 1;
      }
    }

    let bestSignature: string | null = null;
    let bestCards: Element[] = [];
    for (const [sig, els] of cardsBySignature) {
      if (els.length > bestCards.length) {
        bestSignature = sig;
        bestCards = els;
      }
    }

    // Several patterns below use alternation ("42g protein" vs "protein: 42"),
    // so the captured value may land in any group — take the first one set.
    const num = (match: RegExpMatchArray | null): number | null => {
      if (!match) return null;
      for (const group of match.slice(1)) {
        if (group === undefined) continue;
        const parsed = Number.parseFloat(group);
        if (Number.isFinite(parsed)) return parsed;
      }
      return null;
    };

    const meals = bestCards.map((card): Meal => {
      const text = textOf(card);
      const heading = card.querySelector('h1, h2, h3, h4, h5, h6');
      const anchor = card.querySelector('a');
      const image = card.querySelector('img');

      // Prefer a heading; fall back to the anchor text, then the longest line.
      let name = textOf(heading) || textOf(anchor);
      if (!name) {
        const lines = text.split(/(?=[A-Z])/).map((s) => s.trim());
        name = lines.sort((a, b) => b.length - a.length)[0] ?? '';
      }
      name = name.replace(PRICE_RE, '').trim();

      const href = anchor?.getAttribute('href') ?? null;
      const rating = num(text.match(/([0-5](?:\.\d)?)\s*(?:★|stars?\b|out of 5)/i));
      const reviewCount = num(text.match(/\(?\s*(\d[\d,]*)\s*(?:reviews?|ratings?)\s*\)?/i));

      return {
        id: card.getAttribute('data-id') ?? card.getAttribute('id') ?? href,
        name,
        price: num(text.match(PRICE_RE)),
        currency: PRICE_RE.test(text) ? 'USD' : null,
        rating,
        reviewCount: reviewCount === null ? null : Math.round(reviewCount),
        calories: num(text.match(/(\d{2,4})\s*(?:cal\b|calories\b|kcal\b)/i)),
        protein: num(text.match(/(?:protein\D{0,8}(\d{1,3})|(\d{1,3})\s*g\s*protein)/i)),
        carbs: num(text.match(/(?:carbs?\D{0,8}(\d{1,3})|(\d{1,3})\s*g\s*carbs?)/i)),
        fat: num(text.match(/(?:fat\D{0,8}(\d{1,3})|(\d{1,3})\s*g\s*fat)/i)),
        chef: null,
        imageUrl: image?.getAttribute('src') ?? null,
        sourceUrl: href ? new URL(href, document.baseURI).href : null,
      };
    });

    return {
      meals: meals.filter((meal) => meal.name.length > 0),
      cardSignature: bestSignature,
      candidatesConsidered: priceNodes.length,
    };
  });
}

/**
 * Scroll to the bottom repeatedly so lazy-loaded / infinite-scroll menus finish
 * rendering. Stops when the page height stops growing or the cap is reached.
 */
export async function loadAllContent(page: Page, maxScrolls = 25): Promise<void> {
  await installEvaluateShim(page);
  let lastHeight = 0;
  for (let i = 0; i < maxScrolls; i += 1) {
    const height = await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
      return document.body.scrollHeight;
    });
    if (height === lastHeight) return;
    lastHeight = height;
    // Human-paced: give the page room to fetch the next page of results.
    await page.waitForTimeout(1200);
  }
}
