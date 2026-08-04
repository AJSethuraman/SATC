import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { extractEmbeddedJson, watchForMealApis, type Capture } from './capture.js';
import { mealFromJson } from './detect.js';
import { scrapeMeals } from './scrape.js';
import { launchChromium, openSession } from './session.js';
import type { Meal } from './types.js';

/**
 * Verifies the extraction machinery against a local fixture site: API capture,
 * embedded-JSON capture, DOM scraping, session persistence, and HAR recording.
 *
 * This does NOT verify anything about CookUnity itself — the fixture is not a
 * copy of their markup. It proves the plumbing works, so that a real run only
 * has to answer "does the site expose the data", not "does this code run".
 */

let failures = 0;

function check(label: string, condition: boolean, detail = ''): void {
  if (condition) {
    console.log(`  PASS  ${label}`);
  } else {
    failures += 1;
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`);
  }
}

function checkMealShape(label: string, meals: Meal[]): void {
  const named = meals.filter((m) => m.name.length > 0).length;
  const priced = meals.filter((m) => typeof m.price === 'number' && m.price > 0).length;
  const withMacros = meals.filter((m) => m.calories !== null && m.protein !== null).length;
  check(`${label}: 12 meals`, meals.length === 12, `got ${meals.length}`);
  check(`${label}: all named`, named === meals.length, `${named}/${meals.length}`);
  check(`${label}: all priced`, priced === meals.length, `${priced}/${meals.length}`);
  check(`${label}: macros present`, withMacros === meals.length, `${withMacros}/${meals.length}`);
}

async function main(): Promise<void> {
  const fixtureUrl = new URL('../fixture/serve.mjs', import.meta.url).href;
  const { startFixture } = await import(fixtureUrl);
  const fixture = await startFixture();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cookunity-poc-'));
  console.log(`\nSelf-test against ${fixture.baseUrl}\n`);

  try {
    // 1. API detection — the page fetches /api/meals in the background.
    {
      const browser = await launchChromium(true);
      const context = await browser.newContext();
      const page = await context.newPage();
      const captures: Capture[] = [];
      watchForMealApis(page, captures);
      await page.goto(`${fixture.baseUrl}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);

      check('API: meal endpoint detected', captures.length > 0, `${captures.length} candidates`);
      const best = captures.sort((a, b) => b.candidate.score - a.candidate.score)[0];
      if (best) {
        check('API: found nested array path', best.candidate.path === 'data.menu.products', best.candidate.path);
        const meals = best.items.map(mealFromJson).filter((m): m is Meal => m !== null);
        checkMealShape('API', meals);
        // Cents-vs-dollars normalisation: fixture sends 1199 for $11.99.
        check('API: price normalised from cents', meals[0]?.price === 11.99, String(meals[0]?.price));
        check('API: chef read from nested object', meals[0]?.chef === 'Maria Alvarez', String(meals[0]?.chef));
        check('API: tags captured', (meals[0]?.tags?.length ?? 0) === 2, JSON.stringify(meals[0]?.tags));
      }
      await context.close();
      await browser.close();
    }

    // 2. Embedded JSON — no API call, menu serialised into __NEXT_DATA__.
    {
      const browser = await launchChromium(true);
      const page = await browser.newPage();
      await page.goto(`${fixture.baseUrl}/embedded`, { waitUntil: 'domcontentloaded' });
      const embedded = await extractEmbeddedJson(page);
      check('Embedded: __NEXT_DATA__ parsed', embedded !== null);
      if (embedded) {
        const meals = embedded.items.map(mealFromJson).filter((m): m is Meal => m !== null);
        checkMealShape('Embedded', meals);
      }
      await browser.close();
    }

    // 3. DOM scraping — no JSON anywhere, only rendered cards.
    {
      const browser = await launchChromium(true);
      const page = await browser.newPage();
      await page.goto(`${fixture.baseUrl}/dom-only`, { waitUntil: 'domcontentloaded' });
      const scraped = await scrapeMeals(page);
      check('DOM: repeating card structure found', scraped.cardSignature !== null, String(scraped.cardSignature));
      checkMealShape('DOM', scraped.meals);
      const first = scraped.meals[0];
      check('DOM: name from heading', first?.name === 'Chicken Tikka Masala', String(first?.name));
      check('DOM: price parsed', first?.price === 11.99, String(first?.price));
      check('DOM: calories parsed', first?.calories === 420, String(first?.calories));
      check('DOM: protein parsed', first?.protein === 28, String(first?.protein));
      check('DOM: carbs parsed', first?.carbs === 30, String(first?.carbs));
      check('DOM: fat parsed', first?.fat === 12, String(first?.fat));
      check('DOM: rating parsed', first?.rating === 4.2, String(first?.rating));
      check('DOM: review count parsed', first?.reviewCount === 120, String(first?.reviewCount));
      check('DOM: detail link captured', Boolean(first?.sourceUrl?.includes('/meal/meal-1000')), String(first?.sourceUrl));
      await browser.close();
    }

    // 4. Session persistence + HAR — the reliability claim the POC has to make.
    {
      const storageStatePath = path.join(tmp, 'storage-state.json');
      const harPath = path.join(tmp, 'session.har');

      const first = await openSession({ headless: true, harPath, storageStatePath });
      const page = await first.context.newPage();
      await page.goto(`${fixture.baseUrl}/`, { waitUntil: 'domcontentloaded' });
      check('Session: first run starts cold', first.reusedSession === false);
      // Stand in for what a real login leaves behind.
      await page.evaluate(() => localStorage.setItem('cu_session', 'token-abc123'));
      await first.context.addCookies([
        { name: 'cu_auth', value: 'cookie-xyz', url: fixture.baseUrl },
      ]);
      await first.close();

      check('Session: storage state written', fs.existsSync(storageStatePath));
      check('HAR: file written', fs.existsSync(harPath));
      check('HAR: non-trivial size', (fs.statSync(harPath).size ?? 0) > 1000, `${fs.statSync(harPath).size} bytes`);

      const second = await openSession({ headless: true, storageStatePath, requireSavedSession: true });
      check('Session: second run reuses saved state', second.reusedSession === true);
      const page2 = await second.context.newPage();
      await page2.goto(`${fixture.baseUrl}/`, { waitUntil: 'domcontentloaded' });
      const restoredToken = await page2.evaluate(() => localStorage.getItem('cu_session'));
      const cookies = await second.context.cookies(fixture.baseUrl);
      check('Session: localStorage restored', restoredToken === 'token-abc123', String(restoredToken));
      check(
        'Session: cookie restored',
        cookies.some((c) => c.name === 'cu_auth' && c.value === 'cookie-xyz'),
        cookies.map((c) => c.name).join(','),
      );
      await second.close();
    }

    // 5. requireSavedSession must refuse to run cold rather than hang on a prompt.
    {
      let refused = false;
      try {
        await openSession({
          headless: true,
          requireSavedSession: true,
          storageStatePath: path.join(tmp, 'does-not-exist.json'),
        });
      } catch {
        refused = true;
      }
      check('Session: --require-session fails fast when cold', refused);
    }
  } finally {
    await fixture.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  console.log(failures === 0 ? '\nAll self-tests passed.\n' : `\n${failures} self-test(s) failed.\n`);
  process.exitCode = failures === 0 ? 0 : 1;
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
