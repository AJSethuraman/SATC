// S8 — moment-to-moment guarantees. Standing still must be LETHAL (movement is the
// game); no single skill may cover a full 360° kill zone indefinitely (omnidirectional
// nukes carry a cooldown; fillers are spammable but directional/capped). Data audits
// over SKILLS + one live sim, all deterministic at the engine seam.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createArena } from '../engine/arena.js';
import { makeRng } from '../engine/rng.js';
import { SKILLS, ACT1 } from '../engine/content.js';

// omnidirectional = the skill sprays a full ring around you (not a directed bolt/cone/line)
const OMNI = new Set(['nova', 'arc', 'spread', 'ground']);

test('movement matters — a stationary hero is swarmed and overwhelmed ORGANICALLY (no synthetic field)', () => {
  // a weak, single-target hero (can't clear the ring): rooted, the whole horde
  // converges on its spot and real contact damage piles up; moving spreads them into
  // a chasing tail. Death comes from foes hitting you, not a "you-stopped" penalty.
  const mkHero = () => ({ name: 'S', glyph: '🔮', maxLife: 60, life: 60, maxMana: 60, mana: 60, manaRegen: 8,
    accuracy: 7, evade: 1, weapon: { wtype: 'focus' }, hard: { fire_bolt: 2 }, plusSkills: 0, abilities: ['fire_bolt'] });
  const play = (pickInput) => {
    const a = createArena({ hero: mkHero(), rng: makeRng('mm-still'), survival: { areas: ACT1, tier: 'Normal', rollLoot: () => null } });
    let t = 0; while (!a.getState().over && t < 30 * 80) { a.tick(pickInput(a)); t++; }
    return a.getState();
  };
  const still = play(() => ({ x: 0, y: 0 }));
  const moving = play((a) => a.autoInput());
  const rate = (s) => s.tally.dmgTaken / Math.max(1, s.time); // damage PER SECOND — total favors whoever lives longer
  assert.equal(still.result, 'lose', 'the rooted weak hero is overwhelmed by the converging swarm');
  assert.ok(rate(still) > rate(moving) * 1.4, `standing takes damage far FASTER (still ${rate(still).toFixed(1)}/s vs moving ${rate(moving).toFixed(1)}/s)`);
  assert.ok(!moving.over || moving.time > still.time * 1.2, `a moving hero outlasts a stationary one (moving ${moving.time.toFixed(0)}s vs still ${still.time.toFixed(0)}s)`);
});

test('every NUKE carries a cooldown; every FILLER is spammable (no cooldown)', () => {
  for (const s of Object.values(SKILLS)) {
    if (s.role === 'nuke') assert.ok(s.cd > 0, `${s.id} is a nuke and must have a cooldown`);
    if (s.role === 'filler') assert.ok(!s.cd, `${s.id} is a filler and must be spammable (no cooldown)`);
  }
});

test('no skill is an indefinite 360° kill zone — omnidirectional NUKES all have a cooldown', () => {
  for (const s of Object.values(SKILLS)) {
    if (s.geo && OMNI.has(s.geo) && s.role === 'nuke') {
      assert.ok(s.cd > 0, `${s.id} sprays a full ring AND is a nuke — it must be gated by a cooldown`);
    }
  }
  // and a spammable omnidirectional skill must NOT be a heavy nuke (it's a feeder/utility)
  const spammyOmni = Object.values(SKILLS).filter((s) => s.geo && OMNI.has(s.geo) && !s.cd);
  for (const s of spammyOmni) assert.notEqual(s.role, 'nuke', `${s.id} is a no-cooldown ring — must not be a nuke`);
});

test('the kit has a real rotation — cheap spammable fillers AND expensive gated nukes', () => {
  const fillers = Object.values(SKILLS).filter((s) => s.role === 'filler');
  const nukes = Object.values(SKILLS).filter((s) => s.role === 'nuke');
  assert.ok(fillers.length >= 3, 'at least one filler per element');
  assert.ok(nukes.length >= 3, 'multiple nukes to rotate to');
  // fillers cost less than the average nuke — you spam cheap, punctuate with dear
  const avg = (arr) => arr.reduce((n, s) => n + (s.cost || 0), 0) / arr.length;
  assert.ok(avg(fillers) < avg(nukes), 'fillers are cheaper than nukes');
});
