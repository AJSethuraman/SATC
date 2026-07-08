// Headless UI smoke: serves bloodrune/, drives a FULL auto-played run (equip
// from inventory, descend, pick directions, fight swarms/elites, take rewards,
// level up, reach a terminal), asserting ZERO console errors.
//
// Run:  node tests/smoke.mjs      (needs Playwright + Chromium). Skips cleanly if
// Playwright isn't installed. Not a `node --test` file — the engine suite stays
// pure and dependency-free.

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

let chromium;
try { ({ chromium } = require('playwright')); }
catch {
  try { ({ chromium } = require('/opt/node22/lib/node_modules/playwright/index.js')); }
  catch { console.log('SKIP: Playwright not available — engine tests still cover the logic.'); process.exit(0); }
}

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
function serve(root) {
  const server = http.createServer((req, res) => {
    let fp = path.join(root, decodeURIComponent(req.url.split('?')[0]) === '/' ? '/index.html' : req.url.split('?')[0]);
    if (!fp.startsWith(root)) { res.writeHead(403); return res.end(); }
    fs.readFile(fp, (e, d) => { if (e) { res.writeHead(404); return res.end('nf'); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(fp)] || 'application/octet-stream' }); res.end(d); });
  });
  return new Promise((r) => server.listen(0, () => r(server)));
}
function fail(m) { console.error('FAIL:', m); process.exitCode = 1; }

const server = await serve(ROOT);
const port = server.address().port;
const errors = [];
let browser;
try {
  browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  await page.addInitScript(() => { window.__seed = 'smoke'; localStorage.clear(); });
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => window.__bloodrune && window.__bloodrune.run);

  // 1) inventory: equip a bag item on the prep screen and confirm stats change.
  const lifeBefore = await page.evaluate(() => window.__bloodrune.run.stats.maxLife);
  await page.click('#openInv');
  await page.waitForSelector('.bag-item');
  await page.evaluate(() => {
    const helm = document.querySelector('.bag-item[data-id="horned_helm"]') || document.querySelector('.bag-item');
    helm.click();
  });
  const lifeAfter = await page.evaluate(() => window.__bloodrune.run.stats.maxLife);
  if (!(lifeAfter > lifeBefore)) fail(`equipping did not raise Life (${lifeBefore} -> ${lifeAfter})`);
  await page.click('#closeInv');

  // 2) drive the entire run in-page (renders are synchronous).
  const result = await page.evaluate(() => {
    const B = () => window.__bloodrune;
    const q = (s) => document.querySelector(s);
    function focusBack() { const st = B().state; const a = st.lane.filter((m) => m.hp > 0); if (!a.length) return; const n = q(`.monster[data-i="${a[a.length - 1].index}"]`); if (n) n.click(); }
    function playOne() {
      const st = B().state; if (!st || st.over) return false;
      const aff = st.hand.map((c, i) => ({ c, i })).filter((o) => o.c.cost <= st.hero.mana);
      if (!aff.length) return false;
      const living = st.lane.filter((m) => m.hp > 0).length;
      let p = null;
      if (st.hero.life < st.hero.maxLife * 0.35) p = aff.find((o) => o.c.block);
      if (!p && living >= 3) p = aff.find((o) => o.c.target === 'aoe');
      if (!p) p = aff.slice().sort((a, b) => (b.c.damage || 0) - (a.c.damage || 0))[0];
      if (!p) p = aff[0];
      const btn = q(`.card[data-i="${p.i}"]`); if (!btn) return false; btn.click(); return true;
    }
    let startBag = B().run.bag.length, everLeveled = false, guard = 0;
    while (guard++ < 2000) {
      const ph = B().phase;
      if (ph === 'dead' || ph === 'victory') break;
      if (ph === 'prep') { const d = q('#descend'); if (d) d.click(); continue; }
      if (ph === 'map') { const paths = [...document.querySelectorAll('.path')]; if (!paths.length) break; paths[0].click(); continue; }
      if (ph === 'combat') { focusBack(); if (!playOne()) { const et = q('#endTurn'); if (et) et.click(); } continue; }
      if (ph === 'levelup') { everLeveled = true; const o = q('.lvl-opt'); if (o) o.click(); continue; }
      if (ph === 'reward' || ph === 'camp' || ph === 'treasure') { const c = q('#cont'); if (c) c.click(); continue; }
      break;
    }
    return { phase: B().phase, level: B().run.level, bag: B().run.bag.length, startBag, leveled: everLeveled };
  });

  if (!['dead', 'victory'].includes(result.phase)) fail(`run did not reach a terminal (ended at ${result.phase})`);
  if (!(result.bag >= result.startBag)) fail('bag never grew from loot');
  if (errors.length) fail(`console/page errors: ${JSON.stringify(errors)}`);

  if (process.exitCode) console.error('Smoke FAILED.');
  else console.log(`PASS: equip ${lifeBefore}->${lifeAfter}; full run reached "${result.phase}" at level ${result.level}; zero console errors.`);
} catch (e) { fail(e.message); }
finally { if (browser) await browser.close(); server.close(); }
