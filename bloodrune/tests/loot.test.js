// Engine seam tests: the inventory/equipment model, gear->deck and gear->stats
// seams, and the seeded loot roll. Uses a competent auto-player to prove the
// (now much larger) swarm encounters are winnable.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, deriveDeck, deriveStats } from '../engine/game.js';
import { CLASSES, ITEMS, M1_DROP_TABLE } from '../engine/content.js';

const barb = CLASSES.barbarian;

test('deriveDeck = class base cards + cards granted by equipped gear (any slot)', () => {
  const eq = { weapon: ITEMS.worn_axe, offhand: ITEMS.grim_fetish }; // fetish grants War Cry
  const deck = deriveDeck(barb, eq);
  assert.equal(deck.filter((c) => c === 'strike').length, 2); // from worn_axe
  assert.equal(deck.includes('warcry'), true); // from off-hand, not a weapon
});

test('deriveStats sums passive mods (incl. Accuracy) from every equipped slot', () => {
  const eq = { helm: ITEMS.horned_helm, body: ITEMS.chainmail, amulet: ITEMS.sigil_of_wrath,
    ring1: ITEMS.hunters_band };
  const s = deriveStats(barb, eq);
  assert.equal(s.maxLife, barb.maxLife + 10 + 14);
  assert.equal(s.startBlock, 1);
  assert.equal(s.maxMana, barb.maxMana + 1);
  assert.equal(s.plusSkills, 2);
  assert.equal(s.accuracy, barb.accuracy + 8); // hunters_band +8 Accuracy
});

test('equipping from the bag rebuilds deck AND stats; displaced gear returns to bag', () => {
  const game = createGame('inv');
  assert.equal(game.getRun().deck.includes('smite'), false);
  // starting bag contains a war_maul (grants Smite) and a horned_helm (+10 Life)
  assert.equal(game.equipFromBag('war_maul').ok, true);
  const afterWeapon = game.getRun();
  assert.equal(afterWeapon.deck.includes('smite'), true);
  assert.equal(afterWeapon.bag.some((i) => i.id === 'worn_axe'), true); // old weapon back in bag
  assert.equal(game.equipFromBag('horned_helm').ok, true);
  assert.equal(game.getRun().stats.maxLife, barb.maxLife + 10);
});

test('unequipping returns the item to the bag and reverts stats', () => {
  const game = createGame('inv2');
  game.equipFromBag('horned_helm');
  assert.equal(game.getRun().stats.maxLife, barb.maxLife + 10);
  assert.equal(game.unequip('helm').ok, true);
  assert.equal(game.getRun().stats.maxLife, barb.maxLife);
  assert.equal(game.getRun().bag.some((i) => i.id === 'horned_helm'), true);
});

test('rings fill the first free finger', () => {
  const game = createGame('rings');
  game.equipFromBag('hunters_band');
  const run = game.getRun();
  assert.ok(run.equipment.ring1 && run.equipment.ring1.id === 'hunters_band');
  assert.equal(run.equipment.ring2, null);
});

test('same seed => same loot drop (determinism)', () => {
  const a = playToLoot('seed-A');
  const b = playToLoot('seed-A');
  assert.equal(a.getRun().pendingLoot.id, b.getRun().pendingLoot.id);
});

test('winning a swarm drops loot into the bag from the table', () => {
  const game = playToLoot('win-seed');
  const run = game.getRun();
  assert.equal(run.phase, 'loot');
  assert.ok(run.pendingLoot);
  assert.ok(M1_DROP_TABLE.includes(run.pendingLoot.id));
  assert.ok(run.bag.some((i) => i.id === run.pendingLoot.id));
});

test('the swarm is winnable by competent play across several seeds', () => {
  for (const seed of ['s1', 's2', 's3', 's4', 's5']) {
    const game = createGame(seed);
    const combat = game.startFight();
    playout(combat);
    assert.equal(combat.getState().result, 'win', `seed ${seed} should be winnable`);
  }
});

// --- a competent auto-player: block when low, AoE the swarm, else biggest hit
function frontIdx(s) { const m = s.lane.find((x) => x.hp > 0); return m ? m.index : 0; }

function playTurn(combat) {
  let acted = true;
  while (acted) {
    acted = false;
    const s = combat.getState();
    if (s.over) return;
    const affordable = s.hand.map((c, i) => ({ c, i })).filter((o) => o.c.cost <= s.hero.mana);
    if (!affordable.length) return;
    const living = s.lane.filter((m) => m.hp > 0).length;
    let pick = null;
    if (s.hero.life < s.hero.maxLife * 0.35) pick = affordable.find((o) => o.c.block);
    if (!pick && living >= 3) pick = affordable.find((o) => o.c.target === 'aoe');
    if (!pick) pick = affordable.slice().sort((a, b) => (b.c.damage || 0) - (a.c.damage || 0))[0];
    if (!pick) pick = affordable[0];
    combat.playCard(pick.i, pick.c.target === 'single' ? frontIdx(s) : undefined);
    acted = true;
  }
}

function playout(combat) {
  let guard = 0;
  while (!combat.getState().over && guard++ < 800) {
    playTurn(combat);
    if (combat.getState().over) break;
    combat.endTurn();
  }
}

function playToLoot(seed) {
  const game = createGame(seed);
  const combat = game.startFight();
  playout(combat);
  assert.equal(combat.getState().result, 'win', `expected a winnable fight (seed ${seed})`);
  game.resolveCombat();
  return game;
}
