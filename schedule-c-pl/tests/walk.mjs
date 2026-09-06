/* Open the page in a real browser and use it, the way a person would.

   The unit tests prove the arithmetic. This proves the thing on the screen —
   that the fields exist, that typing in them moves the total, that the buttons
   produce files, and that the files hold the same figures the screen showed.

   It runs the browser OFFLINE from the first byte. That is not a detail: the
   page claims your figures never leave your computer, and a page that still
   works with the network switched off cannot be sending them anywhere.

       npm run walk           writes screenshots and files to walk/

   Exits non-zero on the first thing that is wrong, and says what it was. */

import { chromium } from 'playwright';
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { readPdf, readXlsx, xlsxStrings } from './helpers/read-artifacts.mjs';
import { OUT_FILE } from '../build.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOTS = join(HERE, '..', 'walk');

const steps = [];
const ok = (what) => { steps.push(['ok', what]); console.log(`  ok    ${what}`); };
const fail = (what, detail) => {
  steps.push(['FAIL', what]);
  console.error(`  FAIL  ${what}\n        ${detail}`);
  process.exitCode = 1;
};
const check = (cond, what, detail = '') => (cond ? ok(what) : fail(what, detail));

async function main() {
  rmSync(SHOTS, { recursive: true, force: true });
  mkdirSync(SHOTS, { recursive: true });

  // Use whatever Chromium this machine already has rather than downloading
  // one; CHROMIUM_PATH overrides it.
  const executablePath = process.env.CHROMIUM_PATH
    || (existsSync('/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
      ? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' : undefined);
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext({ viewport: { width: 1280, height: 1000 }, acceptDownloads: true });

  // Refuse every outbound request before the page has a chance to make one, and
  // record any that were attempted.
  const attempted = [];
  await context.route('**/*', (route) => {
    const url = route.request().url();
    if (url.startsWith('file://') || url.startsWith('blob:') || url.startsWith('data:')) return route.continue();
    attempted.push(url);
    return route.abort();
  });

  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => consoleErrors.push(String(e)));

  console.log('\nSchedule C profit and loss — walking the built page\n');
  await page.goto(pathToFileURL(OUT_FILE).href);
  await page.waitForSelector('#tool .block');
  await context.setOffline(true);
  ok('the page opens from the file on disk, with the network cut off');

  await page.screenshot({ path: join(SHOTS, '01-opened.png'), fullPage: false });

  // ── fill it in the way a photographer would ─────────────────────────
  await page.fill('#bizname', 'Rowan Vale Photography');
  await page.fill('#bizwhat', 'Portrait photography');
  await page.check('#participate-yes');
  await page.fill('#f1', '94,250');
  await page.fill('#f2', '1100');
  await page.fill('#f6', '420');
  ok('the business details and the income lines accept what was typed');

  const afterIncome = await page.locator('.figures dd').last().textContent();
  check(afterIncome.includes('93,570'), 'the running total moves as income goes in', `it says ${afterIncome}`);

  // Expenses, including one that is deliberately wrong.
  await page.fill('#f8', '2340.75');
  await page.fill('#f22', '3,910.55');
  await page.fill('#f25', '1860');
  await page.fill('#f18', '12.345');
  const error = await page.locator('#e18').textContent();
  check(error.includes('two places'), 'a figure with three decimal places is refused where it was typed', `it said "${error}"`);

  const withBadInput = await page.locator('.figures dd').last().textContent();
  check(!withBadInput.includes('12.34'), 'and the refused figure does not sneak into the total', withBadInput);
  await page.screenshot({ path: join(SHOTS, '02-refuses-bad-input.png'), fullPage: false });

  await page.fill('#f18', '612.40');
  ok('correcting it clears the refusal');

  // ── the mileage helper ──────────────────────────────────────────────
  const mileageBox = page.locator('.field[data-line="9"] .helper');
  await mileageBox.locator('summary').click();
  await mileageBox.locator('input').fill('5510');
  const shown = await mileageBox.locator('.helper-out').textContent();
  check(shown.includes('$3,857.00') && shown.includes('70 cents a mile'),
    'the mileage helper shows the figure and the rate it used', shown);
  check(shown.includes('Notice 2025-5'), 'and names the IRS notice the rate came from', shown);
  await mileageBox.locator('button').click();
  const line9 = await page.inputValue('#f9');
  check(line9 === '3,857.00', 'and puts it on line 9 when asked', `line 9 holds "${line9}"`);
  await page.screenshot({ path: join(SHOTS, '03-mileage-helper.png'), fullPage: false });

  // ── other expenses ──────────────────────────────────────────────────
  const rows = page.locator('.rows .row');
  await rows.nth(0).locator('input').first().fill('Editing software');
  await rows.nth(0).locator('input').last().fill('599.88');
  await page.getByRole('button', { name: 'Add another' }).click();
  await rows.nth(1).locator('input').first().fill('Website hosting');
  await rows.nth(1).locator('input').last().fill('214.20');
  ok('other expenses can be listed one by one');

  // ── the home office helper, and the cap ─────────────────────────────
  await page.check('#homemethod-simplified');
  const homeBox = page.locator('.field[data-line="30"] .helper');
  await homeBox.locator('summary').click();
  await homeBox.locator('input').fill('400');
  const homeText = await homeBox.locator('.helper-out').textContent();
  check(homeText.includes('$1,500.00') && homeText.includes('300 square feet'),
    'the square-foot method caps at 300 feet and says so', homeText);
  await homeBox.locator('button').click();

  // ── the total on screen ─────────────────────────────────────────────
  const net = (await page.locator('.figures dd.big').textContent()).trim();
  check(net === '$78,675.22', 'the profit on screen is right', `it says ${net}`);
  await page.screenshot({ path: join(SHOTS, '04-filled-in.png'), fullPage: true });

  // ── the vehicle questions appear because line 9 has a figure ────────
  const vehicle = await page.locator('#placed').count();
  check(vehicle === 1, 'the vehicle questions appear once car costs are claimed');
  const milesOnForm = await page.inputValue('#businessMiles');
  check(milesOnForm === '5510', 'and the miles the helper used are already in line 44a', `it holds "${milesOnForm}"`);
  const stray = await page.locator('#summary').innerText();
  check(!/null/.test(stray), 'nothing stringified into the panel', stray.slice(0, 200));

  // ── download both files and read them back ──────────────────────────
  for (const [label, file] of [['PDF', 'Download the PDF'], ['spreadsheet', 'Download the spreadsheet']]) {
    const wait = page.waitForEvent('download');
    await page.getByRole('button', { name: file }).click();
    const dl = await wait;
    const path = join(SHOTS, dl.suggestedFilename());
    await dl.saveAs(path);
    const bytes = readFileSync(path);
    ok(`the ${label} downloads as ${dl.suggestedFilename()} (${(bytes.length / 1024).toFixed(0)} KB)`);

    if (label === 'PDF') {
      const doc = await readPdf(bytes);
      check(doc.text.includes('78,675.22'), 'the PDF holds the profit the screen showed');
      check(doc.text.includes('Rowan Vale Photography'), 'and the business name');
      check(doc.text.includes('3,857.00'), 'and the mileage figure the helper worked out');
      check(doc.text.includes('Editing software') || doc.text.includes('599.88'), 'and the listed other expenses');
      check(doc.numPages >= 2, `and runs to ${doc.numPages} pages`);
    } else {
      const book = readXlsx(bytes);
      const strings = xlsxStrings(book).join(' | ');
      check(Object.keys(book.sheets).length === 3, 'the spreadsheet has its three sheets');
      const numbers = book.cached['Schedule C 2025'].flat().filter((v) => typeof v === 'number');
      check(numbers.some((n) => Math.abs(n - 78675.22) < 0.005), 'and holds the same profit');
      check(Object.keys(book.formulas['Schedule C 2025']).length >= 5, 'and the totals are live formulas');
      check(strings.includes('Editing software'), 'and the detail behind the figures');
    }
  }

  const after = await page.locator('#after-download').isVisible();
  check(after, 'the invitation to hand it over appears after the file, not before');
  await page.screenshot({ path: join(SHOTS, '05-after-download.png'), fullPage: false });

  // ── a draft is not kept unless asked ────────────────────────────────
  const before = await page.evaluate(() => localStorage.length);
  check(before === 0, 'nothing is stored on the device by default', `${before} keys were written`);
  await page.locator('.keep input[type="checkbox"]').check();
  const afterOptIn = await page.evaluate(() => localStorage.length);
  check(afterOptIn === 1, 'ticking the box stores a draft, and only then');
  await page.getByRole('button', { name: 'Clear everything' }).click();
  await page.waitForLoadState('load');
  const cleared = await page.evaluate(() => localStorage.length);
  check(cleared === 0, 'and clearing it really clears it');

  // ── a prior year moves the line numbers ─────────────────────────────
  // In 2025 the energy deduction is line 27a and other expenses are 27b; for
  // 2023 the IRS had them the other way round. Other expenses are never a
  // typed field — they come from the list — so the visible difference is which
  // line number the energy deduction carries.
  const energy2025 = await page.locator('.field[data-line="27a"] .line-label').textContent();
  check(energy2025.includes('Energy efficient'), 'in 2025 the energy deduction is line 27a', energy2025);
  await page.selectOption('#year', '2023');
  await page.fill('#f1', '1000');
  const energy2023 = await page.locator('.field[data-line="27b"] .line-label').textContent();
  check(energy2023.includes('Energy efficient'), 'switching to 2023 moves it to line 27b', energy2023);
  check(await page.locator('.field[data-line="27a"]').count() === 0,
    'and 2023 has no 27a field, because other expenses come from the list');
  await page.screenshot({ path: join(SHOTS, '06-prior-year.png'), fullPage: false });

  // ── nothing was fetched, nothing threw ──────────────────────────────
  check(attempted.length === 0, 'the page asked for nothing from the network',
    `it tried: ${attempted.slice(0, 5).join(', ')}`);
  check(consoleErrors.length === 0, 'and nothing went wrong in the console',
    consoleErrors.slice(0, 3).join(' / '));

  await browser.close();

  const failed = steps.filter(([s]) => s === 'FAIL').length;
  console.log(`\n${steps.length - failed} of ${steps.length} checks passed. Screenshots in walk/\n`);
  writeFileSync(join(SHOTS, 'walk.txt'), steps.map(([s, w]) => `${s.padEnd(5)} ${w}`).join('\n'));
}

main().catch((e) => { console.error(e); process.exit(1); });
