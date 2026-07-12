// S3 — loot rework. Rarity widens the affix space; the drop TIER multiplies
// affix magnitudes (Normal < Nightmare < Hell) so lower-tier gear can never rival
// higher; affixes carry build tags so most drops aren't upgrades for any ONE
// build; uniques are minTier-gated fixed items. All deterministic given the rng.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rollItem, itemScore, isUpgradeFor } from '../engine/loot.js';
import { makeRng } from '../engine/rng.js';
import { TIER_MULT } from '../engine/content.js';

// Force a specific slot + rarity by rolling many until we get the affix we want.
function rollUntil(seed, pred, opts) {
  const rng = makeRng(seed);
  for (let i = 0; i < 20000; i++) { const it = rollItem(rng, opts); if (pred(it)) return it; }
  return null;
}

test('drop TIER multiplies affix magnitude — Normal < Nightmare < Hell', () => {
  // Average the total non-plusSkills, non-penetration stat magnitude of magic
  // items across tiers; higher tiers must roll strictly bigger numbers.
  const avgMag = (tier) => {
    const rng = makeRng('tier-' + tier);
    let sum = 0, n = 0;
    for (let i = 0; i < 4000; i++) {
      const it = rollItem(rng, { tier, magicFind: 0, allowUnique: false });
      if (it.rarity === 'common') continue;
      for (const [k, v] of Object.entries(it.passive)) {
        if (k === 'plusSkills' || k === 'penetration') continue;
        sum += v; n += 1;
      }
    }
    return n ? sum / n : 0;
  };
  const nrm = avgMag('Normal'), nm = avgMag('Nightmare'), hell = avgMag('Hell');
  assert.ok(nm > nrm * 1.5, `Nightmare (${nm.toFixed(1)}) should dwarf Normal (${nrm.toFixed(1)})`);
  assert.ok(hell > nm * 1.4, `Hell (${hell.toFixed(1)}) should dwarf Nightmare (${nm.toFixed(1)})`);
  // and the ratios should track TIER_MULT roughly
  assert.ok(hell / nrm > 3, 'Hell magnitudes ~4x Normal');
});

test('+skills does NOT explode with tier, penetration stays a fraction', () => {
  const skillN = rollUntil('sk-n', (it) => it.passive.plusSkills, { tier: 'Normal', allowUnique: false });
  const skillH = rollUntil('sk-h', (it) => it.passive.plusSkills, { tier: 'Hell', allowUnique: false });
  assert.ok(skillN.passive.plusSkills >= 1 && skillN.passive.plusSkills <= 2, 'Normal +skills is small');
  assert.ok(skillH.passive.plusSkills <= 4, 'Hell +skills grows only by a flat step, not 4x');
  const pen = rollUntil('pen', (it) => it.passive.penetration, { tier: 'Hell', allowUnique: false });
  assert.ok(pen.passive.penetration > 0 && pen.passive.penetration < 1, 'penetration is a fraction, not an int');
  assert.equal(Number.isInteger(pen.passive.penetration), false);
});

test('rarity ladder — common through unique all appear; Magic Find lifts the floor', () => {
  const dist = (mf) => {
    const rng = makeRng('rar-' + mf);
    const c = { common: 0, magic: 0, rare: 0, unique: 0 };
    for (let i = 0; i < 6000; i++) c[rollItem(rng, { tier: 'Hell', magicFind: mf }).rarity]++;
    return c;
  };
  const low = dist(0), high = dist(40);
  for (const r of ['common', 'magic', 'rare', 'unique']) assert.ok(low[r] > 0, `${r} should appear`);
  // Magic Find pulls weight off common toward the better tiers.
  assert.ok(high.common / 6000 < low.common / 6000, 'MF reduces the common share');
  assert.ok(high.rare > low.rare, 'MF yields more rares');
});

test('uniques are fixed items, minTier-gated (no higher-tier unique drops at Normal)', () => {
  const rngN = makeRng('uniq-normal');
  for (let i = 0; i < 8000; i++) {
    const it = rollItem(rngN, { tier: 'Normal', magicFind: 60 });
    if (it.rarity !== 'unique') continue;
    assert.equal(it.unique, true);
    assert.ok(Array.isArray(it.affixes) && it.affixes.length === 0, 'uniques carry fixed passives, not rolled affixes');
    // Stone of Jordan / Frostburn / Vipermagi / Death's Fathom are NM+ or Hell — must never drop at Normal
    assert.ok(!['u_soj', 'u_frostburn', 'u_vipermagi', 'u_death'].includes(it.uid), `${it.uid} should be gated above Normal`);
  }
  // Hell CAN surface a Hell-gated unique (Death's Fathom, offhand).
  const death = rollUntil('hell-death', (it) => it.uid === 'u_death', { tier: 'Hell', slot: 'offhand', magicFind: 80 });
  assert.ok(death && death.enabler, "Death's Fathom drops at Hell and is a build enabler");
});

test('build-fit — caster stats score for a Sorceress; off-build stats score ~0', () => {
  const caster = { id: 'c', slot: 'gloves', rarity: 'rare', passive: { fcr: 20, penetration: 0.1, plusSkills: 1 } };
  const brute = { id: 'b', slot: 'gloves', rarity: 'rare', passive: { ias: 20, accuracy: 6, str: 7 } };
  assert.ok(itemScore(caster, 'sorceress') > 30, 'a caster item is worth a lot to a Sorceress');
  assert.ok(itemScore(brute, 'sorceress') < 5, 'a melee item is near-worthless to a Sorceress');
  assert.ok(itemScore(brute, 'barbarian') > itemScore(caster, 'barbarian'), 'the brute item is the Barb upgrade instead');
});

test('most random drops are NOT upgrades for one build (a slice are)', () => {
  // A decent caster baseline in every armor/jewelry slot.
  const rng = makeRng('upgrade-rate');
  const baseline = { fcr: 12, penetration: 0.05, maxMana: 10 }; // ~ a mid rare
  let total = 0, upgrades = 0;
  for (let i = 0; i < 5000; i++) {
    const it = rollItem(rng, { tier: 'Hell', magicFind: 15 });
    const ref = { passive: baseline };
    total += 1;
    if (isUpgradeFor(it, ref, 'sorceress')) upgrades += 1;
  }
  const rate = upgrades / total;
  assert.ok(rate > 0.01, `some drops upgrade the build (got ${(rate * 100).toFixed(1)}%)`);
  assert.ok(rate < 0.5, `MOST drops are not upgrades (got ${(rate * 100).toFixed(1)}%)`);
});

test('deterministic — same seed + opts yields the identical item', () => {
  const a = rollItem(makeRng('same'), { tier: 'Nightmare', magicFind: 20 });
  const b = rollItem(makeRng('same'), { tier: 'Nightmare', magicFind: 20 });
  assert.deepEqual({ ...a, id: 0 }, { ...b, id: 0 }); // ids carry a session counter; ignore them
  assert.equal(a.name, b.name);
});

test('TIER_MULT sanity — the multipliers exist and climb', () => {
  assert.ok(TIER_MULT.Normal < TIER_MULT.Nightmare);
  assert.ok(TIER_MULT.Nightmare < TIER_MULT.Hell);
});
