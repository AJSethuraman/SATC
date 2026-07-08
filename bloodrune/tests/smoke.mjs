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
  await page.waitForFunction(() => window.__bloodrune && window.__bloodrune.state);

  // Drive a full fight greedily inside the page (render is synchronous).
  const result = await page.evaluate(() => {
    function clickAffordable() {
      const st = window.__bloodrune.state;
      if (st.over) return false;
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
    while (!window.__bloodrune.state.over && guard++ < 400) {
      while (clickAffordable()) { /* keep spending Mana */ }
      if (window.__bloodrune.state.over) break;
      document.getElementById('endTurn').click();
    }
    return { result: window.__bloodrune.state.result };
  });

  if (result.result !== 'win') fail(`expected a win, got ${result.result}`);

  // Loot overlay should offer an EQUIP button.
  const deckBefore = await page.evaluate(() => window.__bloodrune.run.deck.slice().sort());
  await page.waitForSelector('#equip', { timeout: 3000 });
  await page.click('#equip');

  const after = await page.evaluate(() => ({
    won: !!window.__bloodrune.won,
    deck: window.__bloodrune.run.deck.slice().sort(),
  }));

  if (!after.won) fail('run did not reach the "won" state after equipping');
  const changed = JSON.stringify(after.deck) !== JSON.stringify(deckBefore);
  if (!changed) fail(`deck composition did not change on equip: ${JSON.stringify(deckBefore)}`);

  if (errors.length) fail(`console/page errors: ${JSON.stringify(errors)}`);

  if (process.exitCode) {
    console.error('Smoke FAILED.');
  } else {
    console.log(`PASS: fight won, deck changed on equip (${deckBefore.join(',')} -> ${after.deck.join(',')}), zero console errors.`);
  }
} catch (e) {
  fail(e.message);
} finally {
  if (browser) await browser.close();
  server.close();
}
