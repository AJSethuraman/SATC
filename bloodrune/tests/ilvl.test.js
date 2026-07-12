// S9 — ITEM LEVEL (ilvl). Deeper Act 1 areas carry a higher ilvl, which gates a
// BETTER drop pool: strong uniques literally can't roll until you delve deep enough,
// and affix magnitudes trend subtly upward with depth. Independent of the drop TIER.
// Asserted at the deterministic loot seam (rollItem, seeded rng) + the arena seam
// (createArena threads curArea().ilvl into surv.rollLoot).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rollItem } from '../engine/loot.js';
import { createArena } from '../engine/arena.js';
import { makeRng } from '../engine/rng.js';
import { ACT1, UNIQUES } from '../engine/content.js';

function rollUntil(seed, pred, opts) {
  const rng = makeRng(seed);
  for (let i = 0; i < 30000; i++) { const it = rollItem(rng, opts); if (pred(it)) return it; }
  return null;
}

test('the act ilvl climbs monotonically across the areas (the delve incentive)', () => {
  for (let i = 1; i < ACT1.length; i++) {
    assert.ok(Number.isInteger(ACT1[i].ilvl), 'every area carries an integer ilvl');
    assert.ok(ACT1[i].ilvl > ACT1[i - 1].ilvl, `area ${i} deeper than ${i - 1}`);
  }
});

test('a SHALLOW (low-ilvl) area cannot roll a high-ilvl unique', () => {
  // Tier is high enough (Hell) that only ilvl — not minTier — gates these. At ilvl 1
  // no offhand unique is eligible (Arc Nexus ilvl5, Death's Fathom ilvl8), so an
  // offhand drop can never come up unique here.
  const rng = makeRng('shallow');
  for (let i = 0; i < 30000; i++) {
    const it = rollItem(rng, { tier: 'Hell', slot: 'offhand', ilvl: 1, magicFind: 120 });
    assert.notEqual(it.uid, 'u_death', "Death's Fathom must not drop in a shallow area");
    assert.notEqual(it.uid, 'u_arcnexus', 'Arc Nexus must not drop in a shallow area');
    assert.notEqual(it.rarity, 'unique', 'no eligible offhand unique at ilvl 1 -> downgrades to rare');
  }
});

test('a DEEP (high-ilvl) area CAN roll the high-ilvl uniques', () => {
  // Same slot/tier as the shallow test — only the ilvl changed.
  const death = rollUntil('deep-death', (it) => it.uid === 'u_death', { tier: 'Hell', slot: 'offhand', ilvl: 8, magicFind: 120 });
  assert.ok(death && death.unique, "Death's Fathom drops once you delve deep (ilvl 8)");
  // Arc Nexus is Normal-tier but ilvl-5 gated: it appears at a deep NORMAL area, proving
  // the ilvl gate is independent of the difficulty tier.
  const arc = rollUntil('deep-arc', (it) => it.uid === 'u_arcnexus', { tier: 'Normal', slot: 'offhand', ilvl: 6, magicFind: 120 });
  assert.ok(arc && arc.unique, 'Arc Nexus (ilvl 5) surfaces in a deep Normal area but not a shallow one');
});

test('affix magnitude trends UP with ilvl (same tier + seed, deeper rolls bigger)', () => {
  // Compare ilvl 4 vs 8: at ilvl>=4 the affix POOL is identical (all minIlvl-gated
  // affixes already unlocked), so the ONLY difference is the magnitude bump. Same seed
  // => identical draws => the deeper average is strictly higher, and only modestly so.
  const avgMag = (ilvl) => {
    const rng = makeRng('mag');
    let sum = 0, n = 0;
    for (let i = 0; i < 6000; i++) {
      const it = rollItem(rng, { tier: 'Nightmare', ilvl, magicFind: 0, allowUnique: false });
      if (it.rarity === 'common') continue;
      for (const [k, v] of Object.entries(it.passive)) {
        if (k === 'plusSkills' || k === 'penetration' || k === 'plusJumps' || k === 'plusBolts' || k === 'pierce') continue;
        sum += v; n += 1;
      }
    }
    return n ? sum / n : 0;
  };
  const shallow = avgMag(4), deep = avgMag(8);
  assert.ok(deep > shallow, `deeper rolls bigger (ilvl8 ${deep.toFixed(2)} > ilvl4 ${shallow.toFixed(2)})`);
  // but the bump is MODEST — depth nudges, it does not multiply like a tier does.
  assert.ok(deep < shallow * 1.25, 'the ilvl bump stays subtle (well under a tier step)');
});

test('the arena threads the CURRENT area ilvl into the drop', () => {
  // Spy on surv.rollLoot: a strong Sorceress mows the opening waves; every drop the
  // director triggers must carry a real Act-1 ilvl, and the opening area's ilvl (1)
  // must show up (kills start in area 0 before any gate is cleared).
  const seen = [];
  const hero = { name: 'S', glyph: '🔮', maxLife: 9000, life: 9000, maxMana: 99999, mana: 99999, manaRegen: 999,
    accuracy: 9, evade: 0, weapon: { dmg: null, wtype: 'focus' }, hard: { nova: 6, charged_bolt: 3 }, plusSkills: 0, abilities: ['nova'] };
  const a = createArena({ hero, rng: makeRng('ilvl-arena'),
    survival: { areas: ACT1, tier: 'Normal', rollLoot: (q, ilvl) => { seen.push(ilvl); return null; } } });
  for (let t = 0; t < 30 * 40 && !a.getState().over; t++) a.tick({ x: Math.sin(t / 17) * 0.5, y: Math.cos(t / 13) * 0.5 });
  const valid = new Set(ACT1.map((ar) => ar.ilvl));
  assert.ok(seen.length > 0, 'the director dropped loot at least once');
  assert.ok(seen.every((i) => valid.has(i)), 'every drop carries a real area ilvl');
  assert.ok(seen.includes(ACT1[0].ilvl), 'opening-area drops carry the opening ilvl');
});
