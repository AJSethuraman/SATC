// Gear as the ENABLER — the balance pass that makes items matter. Three seams:
// (1) FCR works on D2-style breakpoints with per-class tables (the Sorceress is the
// premier caster); (2) gear makes a skill's mana cost cheaper (+skills level + a
// −%cost affix); (3) uniques roll within ranges so a HIGH roll is a real find.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { castInfo, castSpeedMul, skillManaCost } from '../engine/combat.js';
import { rollItem } from '../engine/loot.js';
import { makeRng } from '../engine/rng.js';

test('FCR is on BREAKPOINTS — flat within a tier, a discrete step across one', () => {
  assert.equal(castSpeedMul('sorceress', 0), 1, 'no FCR = base cast speed');
  assert.equal(castSpeedMul('sorceress', 10), castSpeedMul('sorceress', 19), 'more FCR does nothing until the next breakpoint');
  assert.ok(castSpeedMul('sorceress', 20) < castSpeedMul('sorceress', 19), 'crossing a breakpoint speeds you up');
  const info = castInfo('sorceress', 10);
  assert.equal(info.hitBp, 9, 'reports the breakpoint you are standing on');
  assert.ok(info.next && info.next.fcr === 20, 'and the next one to aim for');
});

test('classes have different cast tables — the Sorceress out-casts a Barbarian at the same FCR', () => {
  assert.ok(castSpeedMul('sorceress', 20) < castSpeedMul('barbarian', 20), 'the premier caster reaches faster tiers cheaper');
  assert.ok(castSpeedMul('sorceress', 200) <= castSpeedMul('sorceress', 105), 'stacking to the top tier is fastest');
});

test('gear makes a skill cheaper — +element skills AND a −%cost affix both shave mana cost', () => {
  const bare = { hard: { meteor: 3 }, plusSkills: 0, plusElem: {}, skillMods: {} };
  const base = skillManaCost(bare, 'meteor');
  const plusSkilled = skillManaCost({ ...bare, plusElem: { fire: 6 } }, 'meteor');
  assert.ok(plusSkilled < base, '+Fire skills raise the effective level and shave the cost');
  const reduced = skillManaCost({ ...bare, skillMods: { costReduce: 30 } }, 'meteor');
  assert.ok(reduced < base, 'a −% Skill Mana Cost affix shaves the cost');
  assert.ok(skillManaCost({ hard: {}, skillMods: {} }, 'warmth') === 0, 'a cost-less skill stays free');
});

test('uniques roll within a RANGE across drops — a high roll is a real find', () => {
  const rng = makeRng('uniq'); const seen = new Set(); let n = 0;
  for (let i = 0; i < 8000 && n < 30; i++) {
    const it = rollItem(rng, { tier: 'Normal', slot: 'gloves', magicFind: 60, prefer: 'caster' });
    if (it.uid === 'u_cinderbrand') { n++; const v = it.passive.aoePct;
      assert.ok(v >= 25 && v <= 45, `Cinderbrand +Blast rolled in range (got ${v})`); seen.add(v); }
  }
  assert.ok(n > 0, 'found some Cinderbrands');
  assert.ok(seen.size > 1, 'and they did NOT all roll the same value — the roll varies');
});
