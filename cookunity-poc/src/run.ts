import { extractEmbeddedJson, watchForMealApis, type Capture } from './capture.js';
import { PATHS, SETTLE_MS, SITE } from './config.js';
import { mealFromJson } from './detect.js';
import { loadAllContent, scrapeMeals } from './scrape.js';
import {
  ensureOutputDir,
  hasSavedSession,
  isCdpMode,
  openSession,
  waitForManualLogin,
  writeJson,
} from './session.js';
import type { Meal, MealsFile } from './types.js';

async function main(): Promise<void> {
  const mode = process.argv[2] === 'discover' ? 'discover' : 'extract';
  const requireSavedSession = process.argv.includes('--require-session');

  ensureOutputDir();
  // In CDP mode the operator logged in themselves before we attached.
  const startedWithSession = isCdpMode() || hasSavedSession();

  const session = await openSession({
    ...(isCdpMode() ? {} : { harPath: PATHS.har }),
    requireSavedSession,
  });
  const page = await session.context.newPage();
  const captures: Capture[] = [];
  watchForMealApis(page, captures);

  try {
    await page.goto(SITE.baseUrl, { waitUntil: 'domcontentloaded' });

    if (!startedWithSession) {
      await waitForManualLogin();
    } else {
      console.log('  Reusing saved session — no login prompt.');
    }

    let scraped: Awaited<ReturnType<typeof scrapeMeals>> | null = null;
    let visited = '';

    for (const menuPath of SITE.menuPaths) {
      const url = new URL(menuPath, SITE.baseUrl).href;
      console.log(`  Visiting ${url}`);
      await page.goto(url, { waitUntil: 'domcontentloaded' }).catch(() => undefined);
      await page.waitForTimeout(SETTLE_MS);
      await loadAllContent(page);
      visited = page.url();

      scraped = await scrapeMeals(page);
      if (captures.length > 0 || scraped.meals.length >= 5) break;
    }

    const embedded = captures.length === 0 ? await extractEmbeddedJson(page) : null;
    const apiBest = [...captures].sort((a, b) => b.candidate.score - a.candidate.score)[0] ?? null;
    const jsonBest = apiBest ?? embedded;

    // Prefer structured data; fall back to the DOM only when neither exists.
    let meals: Meal[] = [];
    let approach: MealsFile['approach'] = 'dom';
    let source = visited;

    if (jsonBest) {
      meals = jsonBest.items
        .map((item) => mealFromJson(item))
        .filter((meal): meal is Meal => meal !== null);
      approach = jsonBest.candidate.method === 'EMBEDDED' ? 'embedded' : 'api';
      source = jsonBest.candidate.url;
    }
    if (meals.length === 0 && scraped) {
      meals = scraped.meals;
      approach = 'dom';
      source = `${visited} (DOM cards: ${scraped.cardSignature ?? 'none'})`;
    }

    const result: MealsFile = {
      capturedAt: new Date().toISOString(),
      approach,
      source,
      mealCount: meals.length,
      meals,
    };
    writeJson(PATHS.meals, result);

    writeJson(PATHS.discovery, {
      capturedAt: new Date().toISOString(),
      reusedSession: session.reusedSession,
      apiCandidates: captures.map((c) => c.candidate).sort((a, b) => b.score - a.score),
      embeddedCandidate: embedded?.candidate ?? null,
      domCardSignature: scraped?.cardSignature ?? null,
      domMealCount: scraped?.meals.length ?? 0,
      harPath: isCdpMode() ? null : PATHS.har,
    });

    console.log(`\n  Approach that worked: ${approach}`);
    console.log(`  Meals extracted: ${meals.length}`);
    console.log(`  Source: ${source}`);
    console.log(`  Wrote ${PATHS.meals}`);
    console.log(`  Wrote ${PATHS.discovery} (API candidates for FINDINGS.md)`);
    console.log(isCdpMode() ? '  HAR: skipped (attached to an existing browser)' : `  HAR: ${PATHS.har}`);
    if (mode === 'discover') {
      console.log('\n  Discovery mode: review output/discovery.json for endpoint details.');
    }
  } finally {
    await session.close();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
