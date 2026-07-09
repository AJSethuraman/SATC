// S7 — sockets, runes, runewords + per-element enabler uniques. Socketable bases
// roll empty sockets; runes drop tier-gated; filling every socket with a runeword's
// exact rune SEQUENCE resolves to fixed, far stronger mods. Enabler uniques grant
// per-ELEMENT +Skills, spiking a committed single-element build's BASE damage
// (never its synergy). All deterministic at the engine seam.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame } from '../engine/game.js';
import { rollItem, rollRune, resolveSockets } from '../engine/loot.js';
import { skillEffect } from '../engine/combat.js';
import { makeRng } from '../engine/rng.js';

const runeItem = (rid) => ({ id: `r_${rid}`, isRune: true, runeId: rid, name: `${rid} Rune`, slot: 'rune', rarity: 'rune', itemTier: 'Normal' });
const socketBase = (slot, sockets, over = {}) => ({ id: 'sockbase', slot, rarity: 'magic', itemTier: 'Normal', sockets, socketRunes: [], socketMods: {}, passive: {}, req: {}, ...over });

test('resolveSockets — a full base + exact rune sequence resolves to a runeword', () => {
  const stealth = resolveSockets('body', 2, ['tal', 'eth']);
  assert.equal(stealth.runeword, 'Stealth');
  assert.ok(stealth.mods.fcr === 25 && stealth.mods.maxMana === 15);
  // Spirit — the 4-socket caster crown
  const spirit = resolveSockets('offhand', 4, ['tal', 'thul', 'ort', 'amn']);
  assert.equal(spirit.runeword, 'Spirit');
  assert.equal(spirit.mods.plusSkills, 2);
});

test('a runeword needs the EXACT sequence, count, and slot — else it is just runes', () => {
  assert.equal(resolveSockets('body', 2, ['eth', 'tal']).runeword, null, 'wrong order — no runeword');
  assert.equal(resolveSockets('helm', 2, ['tal', 'eth']).runeword, null, 'wrong slot — Stealth is body only');
  assert.equal(resolveSockets('body', 2, ['tal']).runeword, null, 'not every socket filled');
  // a lone rune still contributes its own mod
  const lone = resolveSockets('body', 2, ['tir']);
  assert.equal(lone.runeword, null);
  assert.equal(lone.mods.maxMana, 6, 'Tir grants its socket mod');
});

test('runes drop tier-gated — Hell runes never appear at Normal', () => {
  const rng = makeRng('runedrops');
  const seen = new Set();
  for (let i = 0; i < 4000; i++) seen.add(rollRune(rng, 'Normal').runeId);
  for (const hellRune of ['sol', 'shael', 'um']) assert.ok(!seen.has(hellRune), `${hellRune} is a Hell rune`);
  assert.ok(seen.has('el') || seen.has('tir'), 'low runes drop at Normal');
  // Hell CAN surface a high rune
  const rngH = makeRng('runedrops-h'); const seenH = new Set();
  for (let i = 0; i < 4000; i++) seenH.add(rollRune(rngH, 'Hell').runeId);
  assert.ok(seenH.has('um') || seenH.has('sol'), 'high runes drop at Hell');
});

test('socketable bases roll sockets; jewelry / light slots never do', () => {
  const rng = makeRng('sockets');
  let sockable = 0, ring = 0;
  for (let i = 0; i < 3000; i++) {
    const body = rollItem(rng, { tier: 'Hell', slot: 'body', allowUnique: false });
    if (body.sockets > 0) sockable++;
    const r = rollItem(rng, { tier: 'Hell', slot: 'ring', allowUnique: false });
    assert.equal(r.sockets, 0, 'rings never socket');
    if (r.sockets) ring++;
  }
  assert.ok(sockable > 0, 'some body armor rolls sockets');
});

test('socketing runes in order completes a runeword and it powers the hero', () => {
  const base = socketBase('offhand', 3, { id: 'shield1' }); // Ancient's Pledge: ral, ort, tal
  const runes = [runeItem('ral'), runeItem('ort'), runeItem('tal')];
  const g = createGame('s7-socket', { classId: 'sorceress', bag: [base, ...runes] });
  assert.ok(g.socketRune('shield1', 'r_ral').ok);
  assert.ok(g.socketRune('shield1', 'r_ort').ok);
  const res = g.socketRune('shield1', 'r_tal');
  assert.equal(res.runeword, "Ancient's Pledge");
  const it = g.getRun().bag.find((x) => x.id === 'shield1');
  assert.ok(it.socketMods.penetration >= 0.13, 'the runeword mods are on the item');
  // equip it and the penetration flows into the hero's stats
  assert.ok(g.equipFromBag('shield1').ok);
  assert.ok(g.getRun().stats.penetration >= 0.13, 'a worn runeword powers the hero');
});

test('socketRune gating — full sockets, wrong ids, and no field access', () => {
  const base = socketBase('helm', 1, { id: 'cap' });
  const g = createGame('s7-gate', { classId: 'sorceress', bag: [base, runeItem('tir'), runeItem('ort')] });
  assert.ok(g.socketRune('cap', 'r_tir').ok);
  assert.equal(g.socketRune('cap', 'r_ort').ok, false, 'sockets are full');
  assert.equal(g.socketRune('nope', 'r_ort').ok, false, 'no such item');
  g.toTown(); // ensure town
  g.descend();
  assert.equal(g.socketRune('cap', 'r_ort').ok, false, 'no socketing in the field');
});

test('a per-element enabler raises that element BASE damage, not synergy — and only its element', () => {
  const fed = { hard: { fire_bolt: 5, fire_ball: 5, meteor: 5, inferno: 5, fire_mastery: 5 }, plusSkills: 0, weapon: { wtype: 'focus' } };
  const base = skillEffect({ ...fed, plusElem: { fire: 0 } }, 'meteor');
  const embered = skillEffect({ ...fed, plusElem: { fire: 2 } }, 'meteor');
  assert.ok(embered.min > base.min, 'the fire enabler lifts fire capstone base damage');
  assert.equal(embered.syn, base.syn, 'per-element +Skills changes base, NOT the synergy bracket');
  const cold = skillEffect({ ...fed, plusElem: { cold: 2 } }, 'meteor');
  assert.equal(cold.min, base.min, 'a cold enabler is worthless to a fire capstone');
});

test('an enabler unique equipped in the run feeds per-element +Skills into the hero', () => {
  const ember = { id: 'ember1', slot: 'amulet', rarity: 'unique', itemTier: 'Normal', enabler: true, passive: { plusFire: 2, maxMana: 12 }, req: {} };
  const g = createGame('s7-enabler', { classId: 'sorceress', stash: [ember] });
  const before = g.getRun().stats.maxMana;
  assert.ok(g.equipFromStash('ember1').ok);
  const st = g.getRun().stats;
  assert.equal(st.plusElem.fire, 2, 'the amulet grants +2 Fire Skills');
  assert.ok(st.maxMana > before, 'and its Mana rolled in');
});
