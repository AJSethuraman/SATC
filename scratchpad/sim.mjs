// Headless SURVIVAL sim: drop in, drive the movement autopilot, auto-quaff, invest
// level-ups greedily, and report how far the run gets before the boss/death.
import { createGame } from '../bloodrune/engine/game.js';

const CAP_TICKS = 30 * 60 * 12; // 12 min hard cap
function investAll(g) { const r = g.getRun(); for (const sk of r.tree) if (sk.canInvest) { g.investSkill(sk.id); return investAll(g); } }

function runOne(cls, diff, seed) {
  const g = createGame('sv-' + seed, { classId: cls, difficulty: diff });
  g.startRun();
  const cb = g.getCombat();
  let t = 0, drops = 0;
  while (!cb.getState().over && t++ < CAP_TICKS) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.4) g.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.15) g.quaff('mana');
    cb.tick(cb.autoInput());
    const sync = g.syncArena(); drops += sync.loot.length;
    if (sync.leveled) investAll(g);
  }
  const s = cb.getState(); const r = g.getRun();
  return { over: s.over, result: s.result, min: (s.time / 60).toFixed(1), level: r.level, kills: s.tally.kills, drops, bag: r.bag.length,
    equipped: Object.values(r.equipment).filter(Boolean).length };
}

for (const cls of ['barbarian', 'amazon', 'necromancer', 'sorceress']) {
  for (const diff of ['Normal', 'Nightmare', 'Hell']) {
    let wins = 0, mins = 0, lvls = 0, kills = 0, drops = 0, timeouts = 0; const M = 6;
    for (let i = 0; i < M; i++) { const r = runOne(cls, diff, cls + diff + i);
      if (r.result === 'win') wins++; if (!r.over) timeouts++; mins += +r.min; lvls += r.level; kills += r.kills; drops += r.drops; }
    console.log(`${cls.padEnd(11)} ${diff.padEnd(9)} win ${wins}/${M}  avgMin ${(mins / M).toFixed(1)}  avgLvl ${(lvls / M).toFixed(1)}  kills ${(kills / M) | 0}  drops ${(drops / M).toFixed(1)}${timeouts ? '  TIMEOUT ' + timeouts : ''}`);
  }
}
