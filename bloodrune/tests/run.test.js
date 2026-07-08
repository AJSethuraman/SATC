// Engine seam tests: the full RUN — map choices, combat resolution, XP/leveling,
// loot, flee, camps, and a complete auto-played descent that reaches a terminal.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame } from '../engine/game.js';
import { nextChoices, makeMap } from '../engine/map.js';
import { makeRng } from '../engine/rng.js';

test('a descent offers up to 3 forward directions', () => {
  const game = createGame('d1');
  game.beginDescent();
  const run = game.getRun();
  assert.equal(run.phase, 'map');
  assert.ok(run.choices.length >= 1 && run.choices.length <= 3);
  assert.ok(run.choices.every((c) => c.type && c.glyph));
});

test('the map forces the boss after its length', () => {
  const map = makeMap({ length: 2 });
  map.step = 2;
  const choices = nextChoices(makeRng('z'), map);
  assert.deepEqual(choices.map((c) => c.type), ['boss']);
});

// competent auto-player (block low, AoE the swarm, else biggest hit)
function frontIdx(s) { const m = s.lane.find((x) => x.hp > 0); return m ? m.index : 0; }
function playFight(combat) {
  let guard = 0;
  while (!combat.getState().over && guard++ < 800) {
    let acted = true;
    while (acted) {
      acted = false;
      const s = combat.getState();
      if (s.over) break;
      const aff = s.hand.map((c, i) => ({ c, i })).filter((o) => o.c.cost <= s.hero.mana);
      if (!aff.length) break;
      const living = s.lane.filter((m) => m.hp > 0).length;
      let pick = null;
      if (s.hero.life < s.hero.maxLife * 0.35) pick = aff.find((o) => o.c.block);
      if (!pick && living >= 3) pick = aff.find((o) => o.c.target === 'aoe');
      if (!pick) pick = aff.slice().sort((a, b) => (b.c.damage || 0) - (a.c.damage || 0))[0];
      if (!pick) pick = aff[0];
      combat.playCard(pick.i, pick.c.target === 'single' ? frontIdx(s) : undefined);
      acted = true;
    }
    if (combat.getState().over) break;
    combat.endTurn();
  }
}

test('winning a combat node grants XP + loot and advances the map', () => {
  const game = createGame('combat-seed');
  game.beginDescent();
  // find and pick a combat direction
  const run = game.getRun();
  const ci = run.choices.findIndex((c) => c.type === 'combat');
  const idx = ci >= 0 ? ci : 0;
  const type = run.choices[idx].type;
  game.chooseDirection(idx);
  if (type === 'combat' || type === 'elite' || type === 'boss') {
    playFight(game.getCombat());
    const phase = game.resolveCombat();
    const after = game.getRun();
    if (game.getCombat().getState().result === 'win') {
      assert.ok(after.bag.length >= run.bag.length, 'loot should be added to the bag');
      assert.ok(['reward', 'levelup', 'victory'].includes(phase));
    }
  } else {
    assert.ok(['reward', 'camp'].includes(game.getRun().phase));
  }
});

test('leveling offers 3 options and applying one changes deck or stats', () => {
  // Force levels by playing several fights.
  const game = createGame('lvl-seed');
  game.beginDescent();
  let leveled = false;
  for (let step = 0; step < 6 && !leveled; step++) {
    const run = game.getRun();
    if (run.phase === 'map') {
      const idx = run.choices.findIndex((c) => c.type === 'combat' || c.type === 'elite');
      game.chooseDirection(idx >= 0 ? idx : 0);
    }
    if (game.getRun().phase === 'combat') {
      playFight(game.getCombat());
      game.resolveCombat();
    }
    let cur = game.getRun();
    if (cur.phase === 'levelup') {
      assert.ok(cur.levelupOptions.length >= 1 && cur.levelupOptions.length <= 3);
      const deckBefore = cur.deck.length;
      const statsBefore = JSON.stringify(cur.stats);
      game.pickLevelup(cur.levelupOptions[0].id);
      const nd = game.getRun();
      assert.ok(nd.deck.length !== deckBefore || JSON.stringify(nd.stats) !== statsBefore);
      leveled = true;
    }
    if (game.getRun().phase === 'reward') game.continueFromReward();
    if (game.getRun().phase === 'camp') game.continueFromReward();
    if (game.getRun().phase === 'dead') break;
  }
  assert.ok(leveled, 'several fights should produce at least one level-up');
});

test('fleeing ends the fight without loot and advances', () => {
  const game = createGame('flee-seed');
  game.beginDescent();
  const run = game.getRun();
  const idx = run.choices.findIndex((c) => c.type === 'combat');
  game.chooseDirection(idx >= 0 ? idx : 0);
  if (game.getRun().phase === 'combat') {
    const bagBefore = game.getRun().bag.length;
    game.flee();
    const after = game.getRun();
    assert.equal(after.pendingLoot.length, 0);
    assert.equal(after.bag.length, bagBefore); // no loot from a flee
    assert.ok(['reward', 'dead'].includes(after.phase));
  }
});

function autoRun(game) {
  game.beginDescent();
  let guard = 0;
  while (guard++ < 80) {
    const run = game.getRun();
    if (run.phase === 'victory' || run.phase === 'dead') break;
    if (run.phase === 'map') game.chooseDirection(0);
    else if (run.phase === 'combat') { playFight(game.getCombat()); game.resolveCombat(); }
    else if (run.phase === 'levelup') game.pickLevelup(game.getRun().levelupOptions[0].id);
    else if (run.phase === 'reward' || run.phase === 'camp' || run.phase === 'treasure') game.continueFromReward();
    else break;
  }
  return game.getRun().phase;
}

test('a full auto-played descent reaches a terminal (victory or death) without throwing', () => {
  const end = autoRun(createGame('full-run'));
  assert.ok(['victory', 'dead'].includes(end), `run should terminate, ended at ${end}`);
});

test('the Amazon is a distinct class: base Evasion + an evasion deck', () => {
  const game = createGame('ama', { classId: 'amazon' });
  const run = game.getRun();
  assert.equal(run.className, 'Amazon');
  assert.ok(run.stats.evasion >= 20, 'Amazon has base Evasion');
  assert.ok(run.deck.includes('evade') && run.deck.includes('jab'));
});

test('an Amazon descent also reaches a terminal', () => {
  const end = autoRun(createGame('ama-run', { classId: 'amazon' }));
  assert.ok(['victory', 'dead'].includes(end), `Amazon run should terminate, ended at ${end}`);
});
