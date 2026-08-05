import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { PATHS } from './config.js';
import { loadPreferences, PREFERENCES_PATH } from './preferences.js';
import { rankMeals } from './rank.js';
import { writeJson } from './session.js';
import { fitWeights, samplesToLabel, type Label } from './tune.js';
import type { MealsFile } from './types.js';

const FEEDBACK_PATH = path.join(path.dirname(PREFERENCES_PATH), 'feedback.json');

function loadLabels(): Label[] {
  if (!fs.existsSync(FEEDBACK_PATH)) return [];
  return JSON.parse(fs.readFileSync(FEEDBACK_PATH, 'utf8')) as Label[];
}

async function main(): Promise<void> {
  if (!fs.existsSync(PATHS.meals)) {
    throw new Error(`No ${PATHS.meals}. Run "npm run poc" first.`);
  }
  const file = JSON.parse(fs.readFileSync(PATHS.meals, 'utf8')) as MealsFile;
  const prefs = loadPreferences();
  const labels = loadLabels();

  const countArg = process.argv.indexOf('--count');
  const wanted = countArg === -1 ? 12 : Number(process.argv[countArg + 1] ?? 12);
  const applyOnly = process.argv.includes('--apply');

  if (!applyOnly) {
    const { ranked } = rankMeals(file.meals, prefs);
    const already = new Set(labels.map((label) => label.id));
    const queue = samplesToLabel(ranked, wanted, already);

    if (queue.length === 0) {
      console.log('\n  Nothing left to label. Run with --apply to refit.\n');
    } else {
      console.log(`\n  ${labels.length} meals already rated. Rating ${queue.length} more.`);
      console.log('  y = would eat it, n = would not, s = skip, q = stop\n');

      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      for (const [index, meal] of queue.entries()) {
        console.log(`  ${index + 1}/${queue.length}  ${meal.name}`);
        console.log(`         ${meal.description ?? ''}`);
        console.log(
          `         ${meal.chef ?? 'unknown chef'} · ${meal.calories ?? '?'} cal · ${meal.rating ?? '?'}★ · ${(meal.tags ?? []).slice(0, 4).join(', ')}`,
        );
        const answer = (await rl.question('         y/n/s/q > ')).trim().toLowerCase();
        console.log('');
        if (answer === 'q') break;
        if (answer === 'y' || answer === 'n') {
          labels.push({
            id: meal.id ?? meal.name,
            verdict: answer === 'y' ? 'like' : 'dislike',
            name: meal.name,
          });
        }
      }
      rl.close();
      writeJson(FEEDBACK_PATH, labels);
      console.log(`  Saved ${labels.length} ratings to ${FEEDBACK_PATH}\n`);
    }
  }

  const likes = labels.filter((l) => l.verdict === 'like').length;
  if (likes === 0 || likes === labels.length) {
    console.log('  Need at least one "yes" and one "no" before weights can be fitted.\n');
    return;
  }

  const result = fitWeights(file.meals, prefs, labels);
  console.log(`  Fitted on ${result.labelled} ratings — agrees with ${Math.round(result.accuracy * 100)}% of them\n`);

  if (result.changes.length === 0) {
    console.log('  No weight moved enough to matter.\n');
  } else {
    console.log('  What changed:');
    for (const change of result.changes.slice(0, 20)) {
      const direction = change.to > change.from ? '↑' : '↓';
      const evidence = `${change.liked} yes / ${change.disliked} no`;
      console.log(
        `    ${direction} ${change.section}.${change.term}: ${change.from} → ${change.to}  (${evidence})`,
      );
    }
    console.log('');
  }

  if (result.untouched.length) {
    console.log(`  No evidence yet for: ${result.untouched.join(', ')}\n`);
  }

  // Never overwrite hand-written preferences without a way back.
  const backup = `${PREFERENCES_PATH}.bak`;
  fs.copyFileSync(PREFERENCES_PATH, backup);
  writeJson(PREFERENCES_PATH, result.preferences);
  console.log(`  Wrote ${PREFERENCES_PATH} (previous saved to ${path.basename(backup)})`);
  console.log('  Run "npm run rank" to see the new order.\n');
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
