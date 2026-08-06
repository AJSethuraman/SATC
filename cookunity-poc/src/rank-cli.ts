import fs from 'node:fs';
import path from 'node:path';
import { PATHS } from './config.js';
import { loadPreferences, PREFERENCES_PATH } from './preferences.js';
import { explain, rankMeals } from './rank.js';
import { writeJson } from './session.js';
import type { MealsFile } from './types.js';

function main(): void {
  if (!fs.existsSync(PATHS.meals)) {
    throw new Error(`No ${PATHS.meals}. Run "npm run poc" first.`);
  }
  const file = JSON.parse(fs.readFileSync(PATHS.meals, 'utf8')) as MealsFile;
  const prefs = loadPreferences();

  const topArg = process.argv.indexOf('--top');
  const top = topArg === -1 ? 15 : Number(process.argv[topArg + 1] ?? 15);

  const { ranked, excluded } = rankMeals(file.meals, prefs);

  // The menu rotates weekly, so a stale capture recommends meals that are no
  // longer orderable — and does it silently, which is the dangerous part.
  const ageDays = Math.floor((Date.now() - Date.parse(file.capturedAt)) / 86_400_000);
  const staleness = ageDays >= 7 ? `  ⚠ ${ageDays} days old — re-run "npm run poc" before trusting this` : '';
  console.log(`\n  ${file.mealCount} meals from ${file.capturedAt.slice(0, 10)}${staleness}`);
  console.log(`  ${excluded.length} filtered out, ${ranked.length} ranked`);
  console.log(`  Preferences: ${PREFERENCES_PATH}\n`);

  ranked.slice(0, top).forEach((entry, index) => {
    const { meal } = entry;
    const chef = meal.chef ? ` — ${meal.chef}` : '';
    console.log(`  ${String(index + 1).padStart(2)}. [${entry.score.toFixed(2)}] ${meal.name}${chef}`);
    console.log(`      ${meal.description ?? ''}`);
    console.log(`      ${explain(entry)}`);
    console.log('');
  });

  // Why things were dropped is as useful as why things won — it is how you
  // notice a limit is set too tight.
  const byReason = new Map<string, number>();
  for (const drop of excluded) {
    const key = drop.why.replace(/\(.*\)/, '').trim();
    byReason.set(key, (byReason.get(key) ?? 0) + 1);
  }
  if (byReason.size) {
    console.log('  Filtered out:');
    for (const [reason, count] of [...byReason].sort((a, b) => b[1] - a[1])) {
      console.log(`    ${count.toString().padStart(4)}  ${reason}`);
    }
  }

  const outPath = path.join(PATHS.output, 'ranked.json');
  writeJson(outPath, {
    rankedAt: new Date().toISOString(),
    menuCapturedAt: file.capturedAt,
    kept: ranked.length,
    filtered: excluded.length,
    meals: ranked.map((entry) => ({
      score: entry.score,
      name: entry.meal.name,
      chef: entry.meal.chef,
      calories: entry.meal.calories,
      rating: entry.meal.rating,
      why: explain(entry),
      id: entry.meal.id,
    })),
  });
  console.log(`\n  Wrote ${outPath}\n`);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
