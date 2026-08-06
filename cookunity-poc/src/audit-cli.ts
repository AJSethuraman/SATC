import fs from 'node:fs';
import { PATHS } from './config.js';
import { auditTerms } from './audit.js';
import { loadPreferences } from './preferences.js';
import type { MealsFile } from './types.js';

function main(): void {
  if (!fs.existsSync(PATHS.meals)) {
    throw new Error(`No ${PATHS.meals}. Run "npm run poc" first.`);
  }
  const file = JSON.parse(fs.readFileSync(PATHS.meals, 'utf8')) as MealsFile;
  const prefs = loadPreferences();
  const report = auditTerms(file.meals, prefs);

  const onlyFlagged = !process.argv.includes('--all');
  const rows = onlyFlagged ? report.filter((row) => row.flags.length) : report;

  console.log(`\n  Auditing ${report.length} preference terms against ${file.mealCount} meals`);
  console.log(onlyFlagged ? '  Showing only terms worth a look — pass --all for everything.\n' : '\n');

  if (!rows.length) {
    console.log('  Nothing flagged.\n');
    return;
  }

  for (const row of rows) {
    const weight = row.weight === null ? 'hard filter' : `weight ${row.weight}`;
    console.log(`  ${row.section}.${row.term}  (${weight}, ${row.meals} meals)`);
    for (const flag of row.flags) console.log(`      ! ${flag}`);
    if (row.matchedText.length > 1) {
      console.log(`      matched: ${row.matchedText.join(' · ')}`);
    }
    if (row.examples.length) console.log(`      e.g. ${row.examples.join('; ')}`);
    console.log('');
  }

  console.log('  A term matching several distinct strings is the usual tell: if "rice"');
  console.log('  also matched "Rice Wine", add \'"rice wine": 0\' to suppress it.\n');
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
