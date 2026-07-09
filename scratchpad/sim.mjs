// Headless full-run sim for the real-time arena: drive the run with the engine
// autopilot (movement only), auto-quaff when low, and report win/level/depth.
import { createGame } from '../bloodrune/engine/game.js';

const TICK_CAP = 30 * 90; // 90s of sim per fight max
function playFight(game, equip = true) {
  const combat = game.getCombat();
  let ticks = 0;
  while (!combat.getState().over && ticks < TICK_CAP) {
    const s = combat.getState();
    // auto-quaff: life below 40%, mana below 20% (potions come from the run)
    if (s.hero.life < s.hero.maxLife * 0.4) game.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.2) game.quaff('mana');
    combat.tick(combat.autoInput());
    ticks++;
  }
  return { over: combat.getState().over, result: combat.getState().result, ticks, sec: (ticks / 30).toFixed(1) };
}

function bestWeaponEquip(game) { // grab a weapon upgrade if one dropped (bot plays gear)
  const r = game.getRun();
  for (const it of r.bag) if (it.slot === 'weapon' && it.grants) { game.equipFromBag(it.id); break; }
}
function investAll(game) { const r = game.getRun(); for (const sk of r.tree) if (sk.canInvest) { game.investSkill(sk.id); investAll(game); return; } }

function run(cls, diff, seed) {
  const game = createGame('sim-' + seed, { classId: cls, difficulty: diff });
  game.beginDescent();
  let guard = 0;
  while (guard++ < 60) {
    const r = game.getRun();
    if (r.phase === 'dead') return { win: false, level: r.level, step: r.mapStep, why: 'dead' };
    if (r.phase === 'victory') return { win: true, level: r.level, step: r.mapStep };
    if (r.phase === 'map') { investAll(game); game.chooseDirection(0); continue; }
    if (r.phase === 'combat') { const res = playFight(game); if (!res.over) return { win: false, level: r.level, step: r.mapStep, why: 'stuck', sec: res.sec }; game.resolveCombat(); continue; }
    if (r.phase === 'reward') { bestWeaponEquip(game); investAll(game); game.continueFromReward(); continue; }
    if (r.phase === 'shop') { game.continueFromReward(); continue; }
    if (r.phase === 'prep') { game.beginDescent(); continue; }
  }
  return { win: false, level: game.getRun().level, step: game.getRun().mapStep, why: 'guard' };
}

for (const cls of ['barbarian', 'amazon', 'necromancer']) {
  for (const diff of ['Normal', 'Nightmare', 'Hell']) {
    let wins = 0, deepest = 0, lvls = 0, stuck = 0; const M = 12;
    for (let i = 0; i < M; i++) { const r = run(cls, diff, cls + diff + i); if (r.win) wins++; if (r.why === 'stuck') stuck++; deepest = Math.max(deepest, r.step); lvls += r.level; }
    console.log(`${cls.padEnd(11)} ${diff.padEnd(9)} wins ${wins}/${M}  avgLvl ${(lvls / M).toFixed(1)}  deepest ${deepest}${stuck ? '  STUCK ' + stuck : ''}`);
  }
}
