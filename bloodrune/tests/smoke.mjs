// Headless UI smoke: serves bloodrune/, drives a full auto-played run through the
// real DOM (class select -> descend -> surrounded combat -> reward + skill tree
// -> ... -> terminal), asserting ZERO console errors. Skips if Playwright absent.

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let chromium;
try { ({ chromium } = require('playwright')); }
catch { try { ({ chromium } = require('/opt/node22/lib/node_modules/playwright/index.js')); } catch { console.log('SKIP: Playwright not available.'); process.exit(0); } }

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
function serve(root) { const s = http.createServer((q, r) => { const fp = path.join(root, decodeURIComponent(q.url.split('?')[0]) === '/' ? '/index.html' : q.url.split('?')[0]); if (!fp.startsWith(root)) { r.writeHead(403); return r.end(); } fs.readFile(fp, (e, d) => { if (e) { r.writeHead(404); return r.end('nf'); } r.writeHead(200, { 'Content-Type': TYPES[path.extname(fp)] || 'application/octet-stream' }); r.end(d); }); }); return new Promise((res) => s.listen(0, () => res(s))); }
function fail(m) { console.error('FAIL:', m); process.exitCode = 1; }

const server = await serve(ROOT); const port = server.address().port; const errors = []; let browser;
try {
  browser = await chromium.launch(); const page = await browser.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  await page.addInitScript(() => { window.__seed = 'smoke'; localStorage.clear(); });
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => window.__bloodrune && window.__bloodrune.game);

  // pick Necromancer (exercises summons) then drive the whole run via the DOM.
  await page.click('.pill[data-class="necromancer"]');
  const out = await page.evaluate(() => {
    const B = () => window.__bloodrune; const q = (s) => document.querySelector(s);
    function combatTurn() {
      const st = B().state; if (!st) return;
      const caster = st.enemies.find((e) => e.hp > 0 && e.role === 'caster'); const liv = st.enemies.filter((e) => e.hp > 0);
      const tgt = caster || liv[0]; if (tgt) { const n = q(`.mob[data-uid="${tgt.uid}"]`); if (n) n.click(); }
      let acted = true;
      while (acted) { acted = false; const s = B().state; if (!s || s.over) break;
        const ab = s.hero.abilities; const pref = ['raise_skeleton', 'raise_golem', 'teeth', 'bone_spear', 'strafe', 'cleave', 'whirlwind', 'power_shot', 'arrow', 'charge', 'pierce', 'smite', 'zeal', 'strike'];
        let idx = -1;
        if (s.hero.summons.length < 3) { const i = ab.findIndex((a) => a.id === 'raise_skeleton' && a.cost <= s.hero.mana); if (i >= 0) idx = i; }
        if (idx < 0) for (const id of pref) { const i = ab.findIndex((a) => a.id === id && a.cost <= s.hero.mana); if (i >= 0) { idx = i; break; } }
        if (idx >= 0) { const b = q(`.card[data-i="${idx}"]:not([disabled])`); if (b) { b.click(); acted = true; } }
      }
      const e = q('#end'); if (e) e.click();
    }
    let guard = 0;
    while (guard++ < 1500) {
      const ph = B().phase;
      if (ph === 'dead' || ph === 'victory') break;
      if (ph === 'prep') { q('#descend').click(); continue; }
      if (ph === 'map') { const p = q('.path'); if (!p) break; p.click(); continue; }
      if (ph === 'combat') { combatTurn(); continue; }
      if (ph === 'reward') {
        if (B().run.skillPoints > 0) { const t = q('#openTree'); if (t) { t.click(); // learn/level reach+summons
          for (let k = 0; k < 8 && B().run.skillPoints > 0; k++) { const btn = document.querySelector('[data-inv]:not([disabled])'); if (btn) btn.click(); else break; } const cx = q('#cx'); if (cx) cx.click(); } }
        const c = q('#cont'); if (c) c.click(); continue;
      }
      break;
    }
    return { phase: B().phase, level: B().run.level, wins: 0 };
  });

  if (!['dead', 'victory'].includes(out.phase)) fail(`run did not terminate (at ${out.phase})`);
  if (errors.length) fail(`console errors: ${JSON.stringify(errors)}`);
  if (process.exitCode) console.error('Smoke FAILED.');
  else console.log(`PASS: full run reached "${out.phase}" at level ${out.level}; zero console errors.`);
} catch (e) { fail(e.message); } finally { if (browser) await browser.close(); server.close(); }
