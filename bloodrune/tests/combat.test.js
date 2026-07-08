// Engine tests: the surrounded ABILITIES combat — ranges, reach, guard,
// breakthrough/exposed, summons, surround, XP, flee.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeRng } from '../engine/rng.js';
import { createCombat, skillEffect, skillLevel, ENGAGE_CAP } from '../engine/combat.js';

const HERO = { name: 'Hero', glyph: '🪓', maxLife: 60, maxMana: 14, startBlock: 0, plusSkills: 0, hard: {},
  weapon: { dmg: [5, 8], wtype: 'melee' }, // an axe: powers the melee skills below
  abilities: ['strike', 'guard', 'arrow', 'charge', 'raise_skeleton', 'cleave', 'zeal'] };
function fight(pack, over = {}) { return createCombat({ hero: { ...HERO, ...over }, pack, rng: makeRng('p') }); }
const ai = (c, id) => c.getState().hero.abilities.findIndex((a) => a.id === id);

test('skills scale their own way; physical damage comes from the weapon', () => {
  const axe = { dmg: [5, 8], wtype: 'melee' };
  const h = (hard, extra) => ({ hard, plusSkills: 0, weapon: axe, ...extra });
  assert.deepEqual([skillEffect(h({}), 'strike').min, skillEffect(h({}), 'strike').max], [5, 8]); // axe 5-8 × 1.0
  assert.deepEqual([skillEffect(h({ strike: 2 }), 'strike').min, skillEffect(h({ strike: 2 }), 'strike').max], [9, 12]); // + growth 2/lvl
  assert.equal(skillEffect(h({}), 'zeal').hits, 2);
  assert.equal(skillEffect({ hard: { raise_skeleton: 4 }, plusSkills: 0 }, 'raise_skeleton').count, 3); // spell: weapon-independent
  assert.equal(skillLevel({ hard: {}, plusSkills: 3 }, 'strike'), 4);
});

test('weapon TYPE matters: a bow cannot Cleave, an axe cannot fire a Power Shot', () => {
  const axe = { dmg: [10, 10], wtype: 'melee' }; const bow = { dmg: [10, 10], wtype: 'ranged' };
  const dmg = (weapon, id) => skillEffect({ hard: {}, plusSkills: 0, weapon }, id).min;
  assert.ok(dmg(axe, 'cleave') >= 8, 'axe powers Cleave'); // 10 × 0.85 ≈ 9
  assert.ok(dmg(bow, 'cleave') <= 3, 'bow flails at Cleave'); // wrong type -> improvised 1-3
  assert.ok(dmg(bow, 'arrow') >= 9, 'bow powers Arrow');
  assert.ok(dmg(axe, 'arrow') <= 3, 'axe cannot fire Arrow');
  // a better weapon means a harder skill
  assert.ok(dmg({ dmg: [20, 20], wtype: 'melee' }, 'strike') > dmg(axe, 'strike'));
});

test('accuracy vs evade: physical attacks can miss; spells never do', () => {
  // an evasive dummy; a hero with modest accuracy misses it sometimes but not always
  const DUMMY = { id: 'goatman' }; // eva 3
  let hits = 0, n = 120;
  for (let s = 0; s < n; s++) {
    const c = createCombat({ hero: { ...HERO, accuracy: 6, hard: {}, abilities: ['strike', 'bone_spear'] }, pack: [{ id: 'zombie', eva: 6 }], rng: makeRng('acc' + s) });
    const before = c.getState().enemies[0].hp; c.useSkill(0); // strike (physical) once
    if (c.getState().enemies[0].hp < before) hits++;
  }
  assert.ok(hits > n * 0.4 && hits < n * 0.85, `strike landed ${hits}/${n} vs Evade 6 (should be partial)`);
  // a spell (bone_spear) ALWAYS lands regardless of evade
  let spellHits = 0;
  for (let s = 0; s < 40; s++) {
    const c = createCombat({ hero: { ...HERO, accuracy: 1, abilities: ['bone_spear'] }, pack: [{ id: 'zombie', eva: 20 }], rng: makeRng('sp' + s) });
    const before = c.getState().enemies[0].hp; c.useSkill(0);
    if (c.getState().enemies[0].hp < before) spellHits++;
  }
  assert.equal(spellHits, 40, 'spells ignore accuracy/evade');
});

test('Evade dodges incoming blows, scaled to the attacker’s accuracy', () => {
  // a dodgy hero (Evade 8) takes fewer hits than a clumsy one (Evade 0) from the same foe
  const dodges = (evade, n = 120) => { let taken = 0; for (let s = 0; s < n; s++) {
    const c = createCombat({ hero: { ...HERO, evade, abilities: ['guard'] }, pack: [{ id: 'fallen' }], rng: makeRng('ev' + evade + s) });
    const before = c.getState().hero.life; c.endTurn(); if (c.getState().hero.life < before) taken++; } return taken; };
  const clumsy = dodges(0), nimble = dodges(8);
  assert.equal(clumsy, 120, 'Evade 0 never dodges');
  assert.ok(nimble < 120 * 0.85, `Evade 8 dodged some (${nimble}/120 landed)`);
});

test('melee reaches only the inner ring; a ranged skill reaches the outer', () => {
  const c = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const gBefore = c.getState().enemies[1].hp;
  c.useSkill(ai(c, 'strike'), 0); // focus outer shaman, melee -> hits inner instead
  assert.equal(c.getState().enemies[0].hp, 16); // shaman (outer) untouched by melee
  assert.ok(c.getState().enemies[1].hp < gBefore); // inner guardian took the Strike
  const c2 = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }], { weapon: { dmg: [5, 8], wtype: 'ranged' } });
  const before = c2.getState().enemies[0].hp;
  c2.useSkill(ai(c2, 'arrow'), 0); // Arrow reaches the shaman (guard-reduced)
  const dealt = before - c2.getState().enemies[0].hp;
  assert.ok(dealt >= 1 && dealt <= 3, `guarded arrow ${dealt}`);
});

test('a big horde only reaches you ENGAGE_CAP at a time (the rest WAIT)', () => {
  const horde = Array.from({ length: 6 }, () => ({ id: 'goatman' })); // 6 goatmen, atk 6
  const c = fight(horde);
  const waiting = c.getState().enemies.filter((e) => e.intent && e.intent.type === 'wait').length;
  assert.equal(waiting, 6 - ENGAGE_CAP); // only the front rank is engaged
  const before = c.getState().hero.life;
  c.endTurn();
  assert.equal(before - c.getState().hero.life, ENGAGE_CAP * 6); // only ENGAGE_CAP swing
});

test('AoE catches only a few foes, never the whole ring', () => {
  // five Fallen inner; Cleave (maxTargets 2) can hit at most two of them
  const c = fight([{ id: 'fallen' }, { id: 'fallen' }, { id: 'fallen' }, { id: 'fallen' }, { id: 'fallen' }]);
  c.useSkill(ai(c, 'cleave'));
  const hit = c.getState().enemies.filter((e) => e.hp < e.maxHp).length;
  assert.ok(hit <= 2, `cleave hit ${hit} (cap 2)`);
});

test('when the front rank falls, the outer ring steps into melee range', () => {
  const c = fight([{ id: 'shaman' }, { id: 'fallen' }]); // shaman outer (ring1), fallen inner (ring0)
  // melee can't reach the shaman while the fallen shields the front
  c.useSkill(ai(c, 'strike'), 0); // focus outer shaman -> Strike lands on the inner fallen instead
  assert.equal(c.getState().enemies[0].hp, 16); // shaman untouched
  // clear the fallen (hp 7); Strike again if it survived the first
  if (c.getState().enemies[1].hp > 0) c.useSkill(ai(c, 'strike'), 1);
  assert.equal(c.getState().enemies[1].hp, 0);
  // now the shaman is the front rank — melee Strike reaches it
  const before = c.getState().enemies[0].hp;
  c.useSkill(ai(c, 'strike'), 0);
  assert.ok(c.getState().enemies[0].hp < before, 'melee reaches the outer caster once the front is clear');
});

test('bracing does not stack — spamming Guard cannot pile up Block', () => {
  const c = fight([{ id: 'goatman' }]);
  const gi = ai(c, 'guard');
  const first = c.useSkill(gi); assert.equal(first.ok, true);
  const block1 = c.getState().hero.block; assert.ok(block1 > 0);
  const manaAfterFirst = c.getState().hero.mana;
  const second = c.useSkill(gi); // re-bracing at or below current Block is refused (no Mana wasted)
  assert.equal(second.ok, false);
  assert.equal(c.getState().hero.block, block1); // Block did not grow
  assert.equal(c.getState().hero.mana, manaAfterFirst); // Mana refunded
});

test('Charge pierces the guard for full damage but Exposes you', () => {
  const c = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.useSkill(ai(c, 'charge'), 0);
  assert.ok(before - c.getState().enemies[0].hp >= 6);
  assert.equal(c.getState().hero.exposed, true);
});

test('while Exposed, Block does not hold', () => {
  const c = fight([{ id: 'goatman' }]); // hp18 atk6
  c.useSkill(ai(c, 'guard'));
  assert.ok(c.getState().hero.block > 0);
  c.useSkill(ai(c, 'charge'), 0);
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 6); // goatman atk 6, Block dropped while Exposed
});

test('summons strike your focus each turn, flanking the guard', () => {
  const c = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  c.useSkill(ai(c, 'raise_skeleton'));
  c.setFocus(0);
  const before = c.getState().enemies[0].hp;
  c.endTurn();
  const dealt = before - c.getState().enemies[0].hp;
  assert.ok(dealt >= 3 && dealt <= 5, `skeleton flanked ${dealt}`);
});

test('every living enemy hits you each turn (the surround) and kills grant XP', () => {
  const c = fight([{ id: 'fallen' }, { id: 'fallen' }, { id: 'goatman' }]);
  c.endTurn(); assert.equal(c.getState().hero.life, 60 - (2 + 2 + 6)); // fallen 2 + fallen 2 + goatman 6
  const c2 = fight([{ id: 'fallen' }]);
  c2.useSkill(ai(c2, 'strike'), 0); // kill it (strike 5-8 >= 8? maybe; use zeal? fallen hp8)
  // strike may not one-shot; cast again
  if (c2.getState().enemies[0].hp > 0) c2.useSkill(ai(c2, 'strike'), 0);
  assert.equal(c2.getState().enemies[0].hp, 0);
  assert.ok(c2.getState().xpEarned >= 3);
});

test('summons body-block the surround (the skeleton wall) and can shatter', () => {
  // one goatman (atk 6); a lone skeleton (4 HP) soaks the blow so the hero is untouched.
  const c = fight([{ id: 'goatman' }]);
  c.useSkill(ai(c, 'raise_skeleton'));
  const lifeBefore = c.getState().hero.life;
  c.endTurn();
  assert.equal(c.getState().hero.life, lifeBefore); // the wall took the hit, not you
  assert.equal(c.getState().hero.summons.length, 0); // 4-HP skeleton shattered on a 6 hit
});

test('a super unique leads a pack (Blood Raven: named, ranged, raises the slain)', () => {
  const c = fight([{ sid: 'blood_raven' }, { id: 'fallen' }]);
  const raven = c.getState().enemies[0];
  assert.equal(raven.name, 'Blood Raven');
  assert.equal(raven.unique, true);
  assert.equal(raven.ring, 1); // a ranged leader — behind her pack
  c.useSkill(ai(c, 'strike'), 1); if (c.getState().enemies[1].hp > 0) c.useSkill(ai(c, 'strike'), 1);
  assert.equal(c.getState().enemies[1].hp, 0); // slew the fallen
  c.endTurn();
  assert.ok(c.getState().enemies[1].hp > 0, 'Blood Raven raised the fallen — kill HER first');
});

test('a caster CHANNELS support (it does not wind up an attack)', () => {
  const c = fight([{ id: 'shaman' }, { id: 'fallen' }]);
  assert.equal(c.getState().enemies[0].intent.type, 'support');
});

test('the Shaman reacts at end of round: mends the most-wounded ally', () => {
  const c = fight([{ id: 'shaman' }, { id: 'goatman' }]); // goatman hp16
  c.useSkill(ai(c, 'strike'), 1); // wound the goatman
  const wounded = c.getState().enemies[1].hp; assert.ok(wounded < 16);
  c.endTurn(); // shaman reacts to the damage you just did
  assert.ok(c.getState().enemies[1].hp > wounded, 'shaman mended the goatman');
});

test('the Shaman raises a slain Fallen — kill the Shaman or they come back (no XP farm)', () => {
  const c = fight([{ id: 'shaman' }, { id: 'fallen' }]);
  c.useSkill(ai(c, 'strike'), 1); if (c.getState().enemies[1].hp > 0) c.useSkill(ai(c, 'strike'), 1);
  assert.equal(c.getState().enemies[1].hp, 0); // Fallen slain
  const xpAfterKill = c.getState().xpEarned;
  c.endTurn(); // shaman raises it
  assert.ok(c.getState().enemies[1].hp > 0, 'the Fallen was raised');
  // re-killing a raised Fallen grants no XP
  c.useSkill(ai(c, 'strike'), 1); if (c.getState().enemies[1].hp > 0) c.useSkill(ai(c, 'strike'), 1);
  assert.equal(c.getState().enemies[1].hp, 0);
  assert.equal(c.getState().xpEarned, xpAfterKill, 'raised Fallen give no XP when re-killed');
});

test('flee ends the fight without a win; parting blows can kill', () => {
  const c = fight([{ id: 'fallen' }, { id: 'goatman' }]);
  const r = c.flee();
  assert.ok(['fled', 'lose'].includes(r.result));
  assert.equal(c.getState().over, true);
});

test('same seed + actions => identical state (determinism)', () => {
  const p = [{ id: 'shaman' }, { id: 'guardian', guards: 0 }, { id: 'fallen' }];
  const a = fight(p); const b = fight(p);
  a.useSkill(ai(a, 'raise_skeleton')); b.useSkill(ai(b, 'raise_skeleton'));
  a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
