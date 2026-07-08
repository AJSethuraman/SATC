// Engine seam tests: gear->deck / gear->stats derivation and the seeded loot
// generator (rarity + affixes + Magic Find).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { deriveDeck, deriveStats } from '../engine/game.js';
import { rollItem } from '../engine/loot.js';
import { makeRng } from '../engine/rng.js';
import { CLASSES, ITEMS } from '../engine/content.js';

const barb = CLASSES.barbarian;

test('deriveDeck = base cards + level-up bonus cards + gear-granted cards', () => {
  const deck = deriveDeck(barb, { weapon: ITEMS.worn_axe, offhand: ITEMS.grim_fetish }, ['smite']);
  assert.equal(deck.filter((c) => c === 'strike').length, 2); // worn_axe
  assert.equal(deck.includes('warcry'), true); // grim_fetish
  assert.equal(deck.includes('smite'), true);  // level-up bonus card
});

test('deriveStats sums gear + level-up bonus stats (incl. Accuracy)', () => {
  const s = deriveStats(barb, { helm: ITEMS.horned_helm, ring1: ITEMS.hunters_band }, { accuracy: 6, plusSkills: 1 });
  assert.equal(s.maxLife, barb.maxLife + 10);
  assert.equal(s.accuracy, barb.accuracy + 8 + 6); // hunters_band +8, bonus +6
  assert.equal(s.plusSkills, 1);
});

test('rollItem is deterministic for a seed and carries a real slot', () => {
  const a = rollItem(makeRng('x'), {});
  const b = rollItem(makeRng('x'), {});
  assert.equal(a.slot, b.slot);
  assert.equal(a.name, b.name);
  assert.ok(['weapon', 'offhand', 'helm', 'body', 'gloves', 'boots', 'belt', 'amulet', 'ring'].includes(a.slot));
});

test('rarity carries the right number of affixes; magic/rare have mods', () => {
  let sawMods = false;
  for (let s = 0; s < 40; s++) {
    const it = rollItem(makeRng('r' + s), {});
    if (it.rarity === 'normal') assert.deepEqual(it.passive, {});
    if (it.rarity === 'magic' || it.rarity === 'rare') { if (Object.keys(it.passive).length) sawMods = true; }
  }
  assert.ok(sawMods, 'magic/rare items should roll stat mods');
});

test('Magic Find biases rolls toward magic/rare', () => {
  const count = (mf) => {
    let nonNormal = 0;
    for (let s = 0; s < 200; s++) if (rollItem(makeRng('mf' + s), { magicFind: mf }).rarity !== 'normal') nonNormal++;
    return nonNormal;
  };
  assert.ok(count(60) > count(0), 'more Magic Find => more magic/rare drops');
});
