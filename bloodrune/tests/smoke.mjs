// Headless UI smoke for the M1 tracer bullet. Serves bloodrune/ over HTTP
// (native ES modules don't load over file://), drives a full fight to a win in
// a real browser, equips the loot drop, and asserts ZERO console errors.
//
// Run:  node tests/smoke.mjs      (needs Playwright + Chromium available)
// This is intentionally NOT a `node --test` file — the engine suite stays pure
// and dependency-free; this one needs a browser. Skips cleanly if Playwright
// isn't installed so it never blocks the pure tests.

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  try {
    ({ chromium } = require('/opt/node22/lib/node_modules/playwright/index.js'));
  } catch {
    console.log('SKIP: Playwright not available — engine tests still cover the logic.');
    process.exit(0);
  }
}

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json',
  '.css': 'text/css', '.mjs': 'text/javascript' };

function serve(root) {
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent(req.url.split('?')[0]);
    let filePath = path.join(root, urlPath === '/' ? '/index.html' : urlPath);
    if (!filePath.startsWith(root)) { res.writeHead(403); return res.end(); }
    fs.readFile(filePath, (err, data) => {
      if (err) { res.writeHead(404); return res.end('not found'); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(filePath)] || 'application/octet-stream' });
      res.end(data);
    });
  });
  return new Promise((resolve) => server.listen(0, () => resolve(server)));
}

function fail(msg) { console.error('FAIL:', msg); process.exitCode = 1; }

const server = await serve(ROOT);
const port = server.address().port;
const url = `http://127.0.0.1:${port}/`;

const errors = [];
let browser;
try {
  browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));

  await page.addInitScript(() => { window.__seed = 'smoke'; });
  await page.goto(url);
  await page.waitForFunction(() => window.__bloodrune && window.__bloodrune.run);

  // 1) Prep screen: open the inventory and equip a bag item; the equip must
  //    change the character's stats (gear->stats seam).
  const lifeBefore = await page.evaluate(() => window.__bloodrune.run.stats.maxLife);
  await page.click('#openInv');
  await page.waitForSelector('.bag-item');
  await page.evaluate(() => {
    // equip the +Life helm if present, else the first bag item
    const helm = document.querySelector('.bag-item[data-id="horned_helm"]') || document.querySelector('.bag-item');
    helm.click();
  });
  const lifeAfter = await page.evaluate(() => window.__bloodrune.run.stats.maxLife);
  if (!(lifeAfter > lifeBefore)) fail(`equipping did not raise Life (${lifeBefore} -> ${lifeAfter})`);
  await page.click('#closeInv');

  // 2) Enter the fight and drive it greedily to a win (render is synchronous).
  await page.click('#enter');
  await page.waitForFunction(() => window.__bloodrune.screen === 'combat' && !!window.__bloodrune.state);
  const result = await page.evaluate(() => {
    function clickAffordable() {
      const st = window.__bloodrune.state;
      if (!st || st.over) return false;
      for (let i = 0; i < st.hand.length; i++) {
        if (st.hand[i].cost <= st.hero.mana) {
          const btn = document.querySelector(`.card[data-i="${i}"]`);
          if (!btn) return false;
          btn.click();
          return true;
        }
      }
      return false;
    }
    let guard = 0;
    while (window.__bloodrune.state && !window.__bloodrune.state.over && guard++ < 400) {
      while (clickAffordable()) { /* keep spending the Mana pool */ }
      if (window.__bloodrune.state.over) break;
      const et = document.getElementById('endTurn');
      if (et) et.click(); else break;
    }
    return { result: window.__bloodrune.state ? window.__bloodrune.state.result : null };
  });

  if (result.result !== 'win') fail(`expected a win, got ${result.result}`);

  const won = await page.evaluate(() => window.__bloodrune.screen === 'won' && !!window.__bloodrune.won);
  if (!won) fail('run did not reach the "won" screen');

  // 3) Loot landed in the bag: open the inventory again and confirm it's there.
  await page.click('#openInv');
  await page.waitForSelector('.bag-item');
  const bagCount = await page.evaluate(() => window.__bloodrune.run.bag.length);
  if (bagCount < 1) fail('no loot in bag after a win');

  if (errors.length) fail(`console/page errors: ${JSON.stringify(errors)}`);

  if (process.exitCode) {
    console.error('Smoke FAILED.');
  } else {
    console.log(`PASS: equip raised Life ${lifeBefore}->${lifeAfter}, fight won, ${bagCount} item(s) in bag, zero console errors.`);
  }
} catch (e) {
  fail(e.message);
} finally {
  if (browser) await browser.close();
  server.close();
}
