// Bloodrune ARENA — REAL-TIME movement engine (Vampire-Survivors shape).
// You are a token in a big arena, MOVING (the only control). Your abilities
// AUTO-FIRE on cooldown when Mana allows — movement is the skill: kite the swarm,
// line up a Cleave, back off to regen. Enemies swarm (melee), kite and loose arrows
// (ranged), or hang back and mend/raise the dead (casters).
//
// Two modes share this engine:
//   • PACK mode  (createArena({hero, pack, rng}))       — a fixed surround you clear.
//   • SURVIVAL   (createArena({hero, rng, survival:{…})}) — ONE big continuous map:
//     a spawn DIRECTOR pours in ever-tougher waves over time, monsters DROP loot you
//     walk over, and a BOSS arrives at bossTime — kill it to clear the tier.
//
// The progression is unchanged and lives in game.js: same content, weapon-driven
// damage (skillEffect), to-hit/dodge math, XP on kill, item-find. setHero() lets the
// run push live stat/ability changes (level-ups, gear) into an in-flight survival.
// Pure engine: no DOM, deterministic, all randomness through the seeded rng.

import { SKILLS, ENEMIES, ELITE_AFFIXES, SUPERUNIQUES } from './content.js';
import { skillEffect } from './combat.js';

export const DT = 1 / 30;                    // fixed sim step — determinism
export const ARENA_W = 920, ARENA_H = 560;   // pack-mode arena (also the camera viewport size)
export const WORLD_W = 2600, WORLD_H = 1700; // survival: one big map you roam
const HERO_SPEED = 158, HERO_R = 13;
const INVULN = 0.34;
const MELEE_REACH = 42;
const PROJ_SPEED = 210, HOSTILE_PROJ_SPEED = 190;
const CAP_ALIVE = 68;                        // survival: max live foes (perf + fairness)
const CORPSE_TTL = 5;                         // survival: how long a corpse lingers (rez window + cleanup)

const CD = { attack: 0.55, damage: 0.95, hits: 0.9, aoe: 1.25, breakthrough: 1.6, block: 4, summon: 2.6 };
const ROLE_DEF = {
  grunt:    { spd: 70, r: 13, touch: 0.9 },
  guardian: { spd: 62, r: 15, touch: 1.0 },
  archer:   { spd: 66, r: 13, fire: 1.7, range: 250 },
  caster:   { spd: 52, r: 14, support: 2.1, range: 205 },
  elite:    { spd: 46, r: 23, touch: 1.1 },
};
const SPD = { fallen: 74, zombie: 46, guardian: 62, goatman: 84, shaman: 52, archer: 66, the_smith: 46,
  rakanishu: 84, corpsefire: 56, blood_raven: 72, bishibosh: 54 };
const RAD = { the_smith: 23 };

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const len = (x, y) => Math.hypot(x, y) || 1;

function buildRtMonster(entry, uid, rng) {
  const su = (typeof entry === 'object' && entry.sid) ? SUPERUNIQUES[entry.sid] : null;
  const id = su ? su.id : (typeof entry === 'string' ? entry : entry.id);
  const base = su || ENEMIES[id];
  const affixes = (!su && typeof entry === 'object' && entry.affixes) ? entry.affixes : [];
  const o = typeof entry === 'object' ? entry : {};
  let hp = Math.round(base.hp * (o.hpMul || 1)), attack = Math.round(base.attack * (o.atkMul || 1));
  let extraAttack = !!base.extraAttack, leech = !!base.leech;
  for (const af of affixes) { const m = (ELITE_AFFIXES[af] && ELITE_AFFIXES[af].mods) || {};
    if (m.hpMul) hp = Math.round(hp * m.hpMul); if (m.attackMul) attack = Math.round(attack * m.attackMul);
    if (m.extraAttack) extraAttack = true; if (m.leech) leech = true; }
  const role = base.role;
  const kind = role === 'caster' ? 'caster' : role === 'archer' ? 'ranged' : 'melee';
  const rd = ROLE_DEF[role] || ROLE_DEF.grunt;
  return { uid, id, name: base.name, glyph: base.glyph, hp, maxHp: hp, attack, role, kind,
    r: RAD[id] || rd.r, spd: SPD[id] || rd.spd, x: 0, y: 0,
    acc: (typeof entry === 'object' && entry.acc != null) ? entry.acc : (base.acc != null ? base.acc : 5),
    eva: (typeof entry === 'object' && entry.eva != null) ? entry.eva : (base.eva || 0),
    heal: base.heal || 0, rezLeft: base.rez || 0, xp: base.xp || 0, extraAttack, leech,
    touchCd: (rd.touch || 0.9) / (extraAttack ? 2 : 1), touchT: 0.4,
    fireCd: rd.fire || 1.7, fireT: 1.0, range: rd.range || 250,
    supportCd: rd.support || 2.1, supportT: 1.4, flash: 0, raised: false, deadAt: -1, drop: (o.drop || 0), gate: false,
    boss: !!base.boss || id === 'the_smith', elite: su ? true : (affixes.length > 0 || role === 'elite'), unique: !!su };
}

export function createArena({ hero, pack, rng, survival }) {
  const surv = survival || null;
  const world = surv ? { w: WORLD_W, h: WORLD_H } : { w: ARENA_W, h: ARENA_H };
  const ctx = { hard: hero.hard || {}, plusSkills: hero.plusSkills || 0, weapon: hero.weapon || null };
  const state = {
    hero: { name: hero.name, glyph: hero.glyph, x: world.w / 2, y: world.h / 2, r: HERO_R,
      life: hero.life != null ? Math.min(hero.life, hero.maxLife) : hero.maxLife, maxLife: hero.maxLife,
      mana: hero.mana != null ? Math.min(hero.mana, hero.maxMana) : hero.maxMana, maxMana: hero.maxMana,
      manaRegen: hero.manaRegen != null ? hero.manaRegen : 4,
      accuracy: hero.accuracy, evade: hero.evade || 0, weapon: hero.weapon || null,
      plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) }, abilities: [...hero.abilities],
      shield: 0, shieldT: 0, invT: 0, dir: { x: 0, y: -1 }, cd: {}, disabled: new Set() },
    enemies: [], projectiles: [], minions: [], gems: [], fx: [], pickups: [], collected: [],
    time: 0, xpEarned: 0, over: false, result: null, nextUid: 0,
    spawnTimer: surv ? 0.6 : 0,
    areaIdx: 0, areaT: 0, gate: null, gateSpawned: false, areaCleared: 0, banner: 0, // Act 1 gauntlet state
    tally: { hits: 0, misses: 0, evades: 0, kills: 0, dmgDealt: 0, dmgTaken: 0 },
  };
  const areas = (surv && surv.areas) || [];

  if (!surv) { // PACK mode: a fixed ring around the hero
    state.enemies = pack.map((e) => buildRtMonster(e, state.nextUid++, rng));
    const N = state.enemies.length;
    state.enemies.forEach((e, i) => {
      const a = (i / N) * Math.PI * 2 + rng.next() * 0.4;
      const rad = (e.kind === 'melee' ? 205 : 285) + rng.next() * 40;
      e.x = clamp(world.w / 2 + Math.cos(a) * rad, 30, world.w - 30);
      e.y = clamp(world.h / 2 + Math.sin(a) * rad, 30, world.h - 30);
    });
  }

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const roll = (min, max) => min + rng.int(max - min + 1);
  const nearest = (x, y, pred) => { let best = null, bd = Infinity;
    for (const e of state.enemies) { if (e.hp <= 0 || (pred && !pred(e))) continue;
      const d = Math.hypot(e.x - x, e.y - y); if (d < bd) { bd = d; best = e; } } return best ? { e: best, d: bd } : null; };
  function fx(o) { state.fx.push({ life: o.life || 0.3, maxLife: o.life || 0.3, ...o }); }

  function kill(e) { e.hp = 0; e.flash = 0.2; e.deadAt = state.time; state.tally.kills++;
    if (!e.raised) { state.xpEarned += e.xp || 0; state.gems.push({ x: e.x, y: e.y, xp: e.xp || 0, life: 8, t: 0.15 }); }
    // Monsters drop random loot for the hero to grab off the ground (survival only).
    if (surv && surv.rollLoot && !e.raised) {
      const chance = e.boss ? 1 : e.unique ? 1 : e.elite ? 0.6 : (0.10 + (e.drop || 0));
      if (rng.next() < chance) { const it = surv.rollLoot(e.boss ? 3 : e.unique ? 2 : e.elite ? 1 : 0);
        if (it) state.pickups.push({ x: e.x, y: e.y, r: 11, item: it }); }
    }
  }

  function hitEnemy(e, dmg, physical) {
    if (physical) { if (rng.next() > clamp(0.75 + (state.hero.accuracy - (e.eva || 0)) * 0.04, 0.35, 0.95)) {
      state.tally.misses++; fx({ type: 'miss', x: e.x, y: e.y - e.r - 6, life: 0.5 }); return false; } state.tally.hits++; }
    e.hp = Math.max(0, e.hp - dmg); e.flash = 0.15; state.tally.dmgDealt += dmg;
    fx({ type: 'dmg', x: e.x, y: e.y - e.r - 4, val: dmg, life: 0.6, vy: -26 });
    if (e.hp === 0) kill(e); return true;
  }

  function hitHero(e, raw) {
    const h = state.hero; if (h.invT > 0) return true;
    if (h.evade > 0 && rng.next() > clamp(0.80 + ((e.acc != null ? e.acc : 5) - h.evade) * 0.04, 0.30, 0.95)) {
      state.tally.evades++; fx({ type: 'evade', x: h.x, y: h.y - h.r - 6, life: 0.5 }); return true; }
    const absorbed = Math.min(h.shield, raw); h.shield -= absorbed; const dmg = raw - absorbed;
    h.life = Math.max(0, h.life - dmg); h.invT = INVULN; state.tally.dmgTaken += dmg;
    if (dmg > 0) fx({ type: 'hurt', x: h.x, y: h.y, life: 0.3 });
    if (e && e.leech && dmg > 0) e.hp = Math.min(e.maxHp, e.hp + dmg);
    if (h.life <= 0) { finish('lose'); return false; } return true;
  }

  // ---- hero abilities (auto-fire on cooldown; Mana gates which ones) ----------
  function fireHeroAbilities() {
    const h = state.hero; if (!alive().length) return;
    for (const id of h.abilities) {
      if (h.disabled.has(id)) continue;                // you can toggle a skill OFF so only the ones you want auto-fire
      if ((h.cd[id] || 0) > 0) continue;
      const s = SKILLS[id]; if (!s || s.type === 'passive') continue; // passives (Warmth/Masteries) don't fire
      const physical = s.weapon !== 'spell';
      const eff = skillEffect(ctx, id);
      if (s.scale === 'nova') { // a burst around you that hits every foe in radius (Nova / Frost Nova / Meteor…)
        const R = s.radius || 140; const pool = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= R + e.r);
        if (!pool.length) continue; if (s.cost > h.mana) continue; h.mana -= s.cost; h.cd[id] = CD.aoe;
        fx({ type: 'cast', x: h.x, y: h.y, r: R, life: 0.35, color: '#8a90c8' });
        for (const e of pool.slice(0, s.maxTargets || pool.length)) hitEnemy(e, roll(eff.min, eff.max), false);
        continue; }
      if (s.type === 'skill') {
        if (h.shield > (eff.block || 0) * 0.5) continue;
        if (s.cost > h.mana) continue; const near = nearest(h.x, h.y); if (!near || near.d > 300) continue;
        h.mana -= s.cost; h.shield = Math.max(h.shield, eff.block || 0); h.shieldT = 6; h.cd[id] = CD.block;
        fx({ type: 'cast', x: h.x, y: h.y, r: 46, life: 0.4, color: '#c8a24a' }); continue; }
      if (s.type === 'summon') { const cap = 3 + (eff.count || 1);
        if (state.minions.length >= cap) continue; if (s.cost > h.mana) continue;
        h.mana -= s.cost; for (let k = 0; k < (eff.count || 1); k++) {
          const a = rng.next() * Math.PI * 2; state.minions.push({ x: h.x + Math.cos(a) * 26, y: h.y + Math.sin(a) * 26,
            r: 9, hp: eff.hp, maxHp: eff.hp, min: eff.min, max: eff.max, fireCd: 1.0, fireT: 0.3, solo: !!s.solo,
            glyph: s.solo ? '🗿' : '💀' }); }
        h.cd[id] = CD.summon; fx({ type: 'cast', x: h.x, y: h.y, r: 30, life: 0.35, color: '#8a90c8' }); continue; }
      if (s.cost > h.mana) continue;
      const ranged = physical ? s.weapon === 'ranged' : (s.reach || s.target === 'aoe' || s.weapon === 'spell');
      if (s.target === 'aoe' && !ranged) { // melee AoE: a wide arc around you (Cleave / Whirlwind)
        const R = MELEE_REACH + 48; const pool = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= R + e.r);
        if (!pool.length) continue; h.mana -= s.cost; h.cd[id] = CD.aoe;
        fx({ type: 'sweep', x: h.x, y: h.y, r: R, life: 0.3 });
        for (const e of pool.slice(0, s.maxTargets || pool.length)) hitEnemy(e, roll(eff.min, eff.max), physical);
        continue; }
      if (s.target === 'aoe' && ranged) { // ranged AoE volley at the nearest few (Strafe / Teeth)
        const targets = alive().sort((a, b) => Math.hypot(a.x - h.x, a.y - h.y) - Math.hypot(b.x - h.x, b.y - h.y)).slice(0, s.maxTargets || 3);
        if (!targets.length) continue; h.mana -= s.cost; h.cd[id] = CD.aoe;
        for (const t of targets) spawnBolt(h, t, roll(eff.min, eff.max), physical, 0, s.weapon === 'spell' ? '🦴' : '➶');
        continue; }
      const tgt = nearest(h.x, h.y); if (!tgt) continue;
      if (!ranged && tgt.d > MELEE_REACH + tgt.e.r + h.r + 6) continue;
      h.mana -= s.cost;
      if (s.type === 'breakthrough') {
        const dx = (tgt.e.x - h.x) / tgt.d, dy = (tgt.e.y - h.y) / tgt.d; const step = Math.min(tgt.d - tgt.e.r, 120);
        h.x = clamp(h.x + dx * step, h.r, world.w - h.r); h.y = clamp(h.y + dy * step, h.r, world.h - h.r);
        fx({ type: 'dash', x: h.x, y: h.y, life: 0.25 });
        if (ranged) spawnBolt(h, tgt.e, roll(eff.min, eff.max), physical, 3, '➶'); else hitEnemy(tgt.e, roll(eff.min, eff.max), physical);
        h.cd[id] = CD.breakthrough; continue; }
      if (s.scale === 'hits') { for (let hh = 0; hh < eff.hits; hh++) { const t = nearest(h.x, h.y); if (!t || t.d > MELEE_REACH + t.e.r + h.r + 6) break; hitEnemy(t.e, roll(eff.min, eff.max), physical); }
        h.cd[id] = CD.hits; fx({ type: 'sweep', x: h.x, y: h.y, r: MELEE_REACH, life: 0.2 }); continue; }
      if (ranged) spawnBolt(h, tgt.e, roll(eff.min, eff.max), physical, 0, s.weapon === 'spell' ? '🦴' : '➶');
      else { hitEnemy(tgt.e, roll(eff.min, eff.max), physical); fx({ type: 'sweep', x: h.x, y: h.y, r: MELEE_REACH, life: 0.18 }); }
      h.cd[id] = id === 'attack' ? CD.attack : CD.damage;
    }
  }

  function spawnBolt(from, target, dmg, physical, pierce, glyph) {
    const d = Math.hypot(target.x - from.x, target.y - from.y) || 1;
    state.projectiles.push({ x: from.x, y: from.y, vx: (target.x - from.x) / d * PROJ_SPEED, vy: (target.y - from.y) / d * PROJ_SPEED,
      r: 6, dmg, physical, pierce: pierce || 0, hostile: false, home: true, life: 2.2, glyph: glyph || '•', hitUids: [] });
  }

  function homeBolt(p, dt) { // VS-style auto-aim so ranged reliably connects
    const t = nearest(p.x, p.y, (e) => !p.hitUids.includes(e.uid)); if (!t) return;
    const sp = Math.hypot(p.vx, p.vy) || PROJ_SPEED; const cur = Math.atan2(p.vy, p.vx);
    const want = Math.atan2(t.e.y - p.y, t.e.x - p.x); let dA = want - cur;
    while (dA > Math.PI) dA -= 2 * Math.PI; while (dA < -Math.PI) dA += 2 * Math.PI;
    const na = cur + clamp(dA, -7 * dt, 7 * dt); p.vx = Math.cos(na) * sp; p.vy = Math.sin(na) * sp;
  }

  function stepProjectiles(dt) {
    for (const p of state.projectiles) {
      if (p.home && !p.hostile) homeBolt(p, dt);
      p.x += p.vx * dt; p.y += p.vy * dt; p.life -= dt;
      if (p.x < -20 || p.x > world.w + 20 || p.y < -20 || p.y > world.h + 20) p.life = 0;
      if (p.hostile) { const h = state.hero; if (Math.hypot(p.x - h.x, p.y - h.y) <= p.r + h.r) { hitHero(p.from, p.dmg); p.life = 0; } continue; }
      for (const e of state.enemies) { if (e.hp <= 0 || p.hitUids.includes(e.uid)) continue;
        if (Math.hypot(p.x - e.x, p.y - e.y) <= p.r + e.r) { hitEnemy(e, p.dmg, p.physical); p.hitUids.push(e.uid);
          if (p.pierce > 0) p.pierce -= 1; else { p.life = 0; break; } } }
    }
    state.projectiles = state.projectiles.filter((p) => p.life > 0);
  }

  function stepMinions(dt) {
    const h = state.hero;
    for (const m of state.minions) {
      const tgt = nearest(m.x, m.y);
      const anchor = tgt && tgt.d < 220 ? tgt.e : h; const dx = anchor.x - m.x, dy = anchor.y - m.y; const d = len(dx, dy);
      const want = tgt && tgt.d < 220 ? Math.max(0, Math.min(90, d - 40)) : Math.max(0, d - 30);
      const sp = 120; if (d > 4) { m.x += dx / d * Math.min(sp * dt, want * 0.5 + sp * dt * 0.2); m.y += dy / d * Math.min(sp * dt, want * 0.5 + sp * dt * 0.2); }
      m.fireT -= dt; if (tgt && tgt.d < 210 && m.fireT <= 0) { m.fireT = m.fireCd; spawnMinionBolt(m, tgt.e); }
    }
  }
  function spawnMinionBolt(m, target) { const d = Math.hypot(target.x - m.x, target.y - m.y) || 1;
    state.projectiles.push({ x: m.x, y: m.y, vx: (target.x - m.x) / d * PROJ_SPEED, vy: (target.y - m.y) / d * PROJ_SPEED,
      r: 5, dmg: roll(m.min, m.max), physical: false, pierce: 0, hostile: false, home: true, life: 1.8, glyph: '·', hitUids: [] }); }

  const raisableCorpse = () => state.enemies.find((e) => e.hp <= 0 && e.role === 'grunt');

  function stepEnemies(dt) {
    const h = state.hero;
    for (const e of state.enemies) {
      if (e.hp <= 0) continue; if (e.flash > 0) e.flash -= dt;
      const dx = h.x - e.x, dy = h.y - e.y, d = len(dx, dy); const ux = dx / d, uy = dy / d;
      if (e.kind === 'melee') { if (d > e.r + h.r + 4) { e.x += ux * e.spd * dt; e.y += uy * e.spd * dt; }
        e.touchT -= dt; if (d <= e.r + h.r + MELEE_REACH * 0.4 && e.touchT <= 0) { e.touchT = e.touchCd; if (!hitHero(e, e.attack)) return; }
      } else {
        const desired = e.range; const drift = d < desired ? -1 : d > desired + 40 ? 1 : 0;
        const ox = -uy, oy = ux;
        e.x = clamp(e.x + (ux * drift + ox * 0.5) * e.spd * dt, 20, world.w - 20);
        e.y = clamp(e.y + (uy * drift + oy * 0.5) * e.spd * dt, 20, world.h - 20);
        if (e.kind === 'ranged') { e.fireT -= dt; if (d < e.range + 90 && e.fireT <= 0) { e.fireT = e.fireCd;
          state.projectiles.push({ x: e.x, y: e.y, vx: ux * HOSTILE_PROJ_SPEED, vy: uy * HOSTILE_PROJ_SPEED, r: 6,
            dmg: e.attack, hostile: true, from: e, pierce: 0, life: 3, glyph: '➹' }); } }
        e.supportT -= dt; if ((e.rezLeft > 0 || e.heal) && e.supportT <= 0) { e.supportT = e.supportCd;
          const corpse = e.rezLeft > 0 ? raisableCorpse() : null;
          if (corpse) { e.rezLeft -= 1; corpse.hp = corpse.maxHp; corpse.raised = true; corpse.deadAt = -1;
            const a = rng.next() * Math.PI * 2; corpse.x = clamp(e.x + Math.cos(a) * 40, 20, world.w - 20); corpse.y = clamp(e.y + Math.sin(a) * 40, 20, world.h - 20);
            fx({ type: 'cast', x: e.x, y: e.y, r: 34, life: 0.5, color: '#6fd08a' }); }
          else if (e.heal) { const wounded = alive().filter((a) => a !== e && a.hp < a.maxHp).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp))[0];
            if (wounded) { wounded.hp = Math.min(wounded.maxHp, wounded.hp + e.heal); fx({ type: 'cast', x: wounded.x, y: wounded.y, r: 22, life: 0.4, color: '#6fd08a' }); } } }
      }
    }
  }

  // ---- survival director: pour in ramping waves, drop loot, land the boss --------
  // Enemy toughness scales with elapsed MINUTES (steeper on higher tiers) — the
  // "area level" of a survivors run. Spawn just outside the camera so foes converge.
  function scaleFor() {
    const min = state.time / 60; const t = surv.tier;
    const hs = { Nightmare: 0.55, Hell: 0.85 }[t] || 0.34;
    const as = { Nightmare: 0.20, Hell: 0.30 }[t] || 0.13;
    return { hpMul: 1 + min * hs, atkMul: 1 + min * as };
  }
  function spawnAtRing(entry) { const e = buildRtMonster(entry, state.nextUid++, rng);
    const a = rng.next() * Math.PI * 2, rad = 520 + rng.next() * 120;
    e.x = clamp(state.hero.x + Math.cos(a) * rad, 24, world.w - 24);
    e.y = clamp(state.hero.y + Math.sin(a) * rad, 24, world.h - 24); state.enemies.push(e); return e; }
  const curArea = () => areas[state.areaIdx] || areas[areas.length - 1];
  function spawnWave() { // pour in this area's foes from its pool, scaled by overall time
    const area = curArea(); const sc = scaleFor(); const min = state.time / 60;
    const n = Math.min(11, 2 + Math.floor(min * 1.4));
    for (let k = 0; k < n; k++) {
      const entry = { id: rng.pick(area.pool), hpMul: sc.hpMul, atkMul: sc.atkMul };
      if (min >= 2 && rng.next() < 0.10) { entry.affixes = [rng.pick(Object.keys(ELITE_AFFIXES))]; entry.drop = 0.3; }
      spawnAtRing(entry);
    }
  }
  // The area's time-GATE: a named super-unique (or boss). Killing it clears the area.
  function spawnGate(area) {
    const sc = scaleFor(); const bt = surv.tier; const min = state.time / 60;
    const isBoss = !SUPERUNIQUES[area.gate]; // the_smith / andariel are ENEMIES bosses (huge base) — scale them MILDLY
    const bossHP = { Nightmare: 1.5, Hell: 2.0 }[bt] || 1, bossATK = { Nightmare: 1.3, Hell: 1.6 }[bt] || 1;
    const hpMul = isBoss ? (1 + min * 0.09) * bossHP : sc.hpMul, atkMul = isBoss ? (1 + min * 0.05) * bossATK : sc.atkMul;
    const entry = SUPERUNIQUES[area.gate] ? { sid: area.gate, hpMul, atkMul } : { id: area.gate, hpMul, atkMul };
    const gate = spawnAtRing(entry); gate.gate = true; gate.boss = isBoss; gate.spawnT = state.time; gate.baseSpd = gate.spd; gate.baseAtk = gate.attack;
    state.gate = gate; state.gateSpawned = true;
    const su = SUPERUNIQUES[area.gate]; const mins = su ? su.minions : [area.pool[0], area.pool[0]];
    for (const m of mins) spawnAtRing({ id: m, hpMul: sc.hpMul, atkMul: sc.atkMul });
    fx({ type: 'cast', x: state.hero.x, y: state.hero.y, r: 140, life: 1.0, color: '#c62828' });
  }
  function director(dt) {
    const area = curArea();
    if (!state.gateSpawned) { state.areaT += dt; if (state.areaT >= area.dur) spawnGate(area); }
    // ENRAGE: a gate that's dragged on too long grows faster and hits harder, so a
    // kiting stalemate always resolves (you kill it, or it runs you down). No infinite runs.
    if (state.gate && state.gate.hp > 0) { const age = state.time - state.gate.spawnT;
      if (age > 18) { const k = 1 + (age - 18) * 0.09; state.gate.spd = state.gate.baseSpd * Math.min(3.6, k);
        state.gate.attack = Math.round(state.gate.baseAtk * Math.min(3, 1 + (age - 18) * 0.06));
        if (state.gate.kind !== 'melee' && age > 28) state.gate.kind = 'melee'; } } // charges you down so it can't be kited forever
    // area cleared when its gate falls: advance to the next area, or win after Andariel
    if (state.gate && state.gate.hp <= 0) {
      state.areaCleared++;
      if (state.areaIdx >= areas.length - 1) { finish('win'); return; }
      state.areaIdx++; state.areaT = 0; state.gate = null; state.gateSpawned = false; state.banner = 2.4;
      state.enemies = []; state.projectiles = state.projectiles.filter((p) => !p.hostile); state.spawnTimer = 0.8; // clean, simple transition
      fx({ type: 'cast', x: state.hero.x, y: state.hero.y, r: 100, life: 0.8, color: '#c8a24a' });
    }
    state.spawnTimer -= dt;
    if (state.spawnTimer <= 0 && alive().length < (state.gateSpawned ? 20 : CAP_ALIVE)) { // once the gate is up, waves thin so you can focus it
      spawnWave(); state.spawnTimer = (state.gateSpawned ? 3.4 : 1) * Math.max(0.55, 1.9 - (state.time / 60) * 0.13);
    }
    if (state.banner > 0) state.banner -= dt;
    if (state.enemies.length > 90) state.enemies = state.enemies.filter((e) => e.hp > 0 || e.gate || (e.deadAt >= 0 && state.time - e.deadAt < CORPSE_TTL));
  }

  function stepPickups() { // loot magnets toward you, collected on contact -> game drains it
    const h = state.hero;
    for (const p of state.pickups) { const dx = h.x - p.x, dy = h.y - p.y, d = len(dx, dy);
      if (d < 96) { p.x += dx / d * Math.min(d, 220 * DT); p.y += dy / d * Math.min(d, 220 * DT); }
      if (d <= h.r + p.r + 4) { p.got = true; state.collected.push(p.item); fx({ type: 'cast', x: h.x, y: h.y, r: 18, life: 0.3, color: p.item.color || '#c8a24a' }); } }
    state.pickups = state.pickups.filter((p) => !p.got);
  }

  function tick(input) {
    if (state.over) return getState();
    const h = state.hero, dt = DT;
    state.time += dt;
    if (h.invT > 0) h.invT -= dt;
    if (h.shieldT > 0) { h.shieldT -= dt; if (h.shieldT <= 0) h.shield = 0; }
    h.mana = Math.min(h.maxMana, h.mana + h.manaRegen * dt);
    for (const id of h.abilities) if (h.cd[id] > 0) h.cd[id] -= dt;
    let mx = input && input.x || 0, my = input && input.y || 0; const ml = Math.hypot(mx, my);
    if (ml > 0.01) { mx /= ml > 1 ? ml : 1; my /= ml > 1 ? ml : 1; h.dir = { x: mx, y: my };
      h.x = clamp(h.x + mx * HERO_SPEED * dt, h.r, world.w - h.r); h.y = clamp(h.y + my * HERO_SPEED * dt, h.r, world.h - h.r); }
    if (surv) director(dt);
    fireHeroAbilities();
    stepProjectiles(dt);
    stepMinions(dt);
    stepEnemies(dt);
    if (state.over) return getState();
    if (surv) stepPickups();
    for (const f of state.fx) { f.life -= dt; if (f.vy) f.y += f.vy * dt; }
    state.fx = state.fx.filter((f) => f.life > 0);
    for (const g of state.gems) { g.life -= dt; if (g.t > 0) g.t -= dt; }
    state.gems = state.gems.filter((g) => g.life > 0);
    if (!surv && !alive().length) finish('win'); // pack mode: clear the ring to win (survival wins on the boss)
    return getState();
  }

  // Headless movement autopilot (balance bot + tests): range-aware kite/close.
  const heroKites = (() => { const w = state.hero.weapon;
    if (w && w.wtype === 'ranged') return true;
    return state.hero.abilities.some((id) => { const s = SKILLS[id]; return s && (s.type === 'summon' || (s.type === 'attack' && s.weapon === 'spell')); }); })();
  function autoInput() {
    const h = state.hero; const t = nearest(h.x, h.y); let x = 0, y = 0, avoidWall = true;
    if (!t) return { x: 0, y: 0 };
    const desired = heroKites ? 190 : 66;
    const near = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) < (heroKites ? desired : 120));
    const to = (t.e.x - h.x) / t.d, ty = (t.e.y - h.y) / t.d;
    if (t.d > desired + 18) { x = to; y = ty; avoidWall = false; }
    else if (heroKites && t.d < desired - 34) { x = -to; y = -ty; }
    else { x = -ty; y = to; }
    if (heroKites && avoidWall) for (const e of near) { const dx = h.x - e.x, dy = h.y - e.y, d = len(dx, dy); x += dx / d * 0.6; y += dy / d * 0.6; }
    if (surv) for (const e of near) { const dx = h.x - e.x, dy = h.y - e.y, d = len(dx, dy); x += dx / d * 0.35; y += dy / d * 0.35; } // survival: bleed off pressure from every side
    if (avoidWall) { const edge = 90; if (h.x < edge) x += 1; if (h.x > world.w - edge) x -= 1; if (h.y < edge) y += 1; if (h.y > world.h - edge) y -= 1; }
    const l = Math.hypot(x, y); return l > 0.01 ? { x: x / l, y: y / l } : { x: 0, y: 0 };
  }

  function quaff(kind, amount) {
    if (state.over) return { ok: false }; const h = state.hero;
    if (kind === 'life') { if (h.life >= h.maxLife) return { ok: false, reason: 'full' }; h.life = Math.min(h.maxLife, h.life + amount); }
    else { if (h.mana >= h.maxMana) return { ok: false, reason: 'full' }; h.mana = Math.min(h.maxMana, h.mana + amount); }
    fx({ type: 'cast', x: h.x, y: h.y, r: 24, life: 0.3, color: kind === 'life' ? '#c62828' : '#4a7bff' });
    return { ok: true };
  }

  // Push live run changes (level-ups, gear) into the in-flight survival. maxLife/
  // maxMana gains are ADDED to current pools (a level-up bump you feel).
  function setHero(p) { const h = state.hero;
    if (p.maxLife != null) { const inc = Math.max(0, p.maxLife - h.maxLife); h.maxLife = p.maxLife; h.life = Math.min(h.maxLife, h.life + inc); }
    if (p.maxMana != null) { const inc = Math.max(0, p.maxMana - h.maxMana); h.maxMana = p.maxMana; h.mana = Math.min(h.maxMana, h.mana + inc); }
    if (p.accuracy != null) h.accuracy = p.accuracy;
    if (p.evade != null) h.evade = p.evade;
    if (p.manaRegen != null) h.manaRegen = p.manaRegen;
    if (p.plusSkills != null) { h.plusSkills = p.plusSkills; ctx.plusSkills = p.plusSkills; }
    if (p.hard) { h.hard = { ...p.hard }; ctx.hard = h.hard; }
    if (p.weapon !== undefined) { h.weapon = p.weapon; ctx.weapon = p.weapon; }
    if (p.abilities) h.abilities = [...p.abilities];
  }
  function heal(amount) { const h = state.hero; h.life = Math.min(h.maxLife, h.life + amount); }
  function takeCollected() { const c = state.collected; state.collected = []; return c; } // game drains dropped loot
  function setDisabled(ids) { state.hero.disabled = new Set(ids || []); } // curate which skills auto-fire
  function toggleAbility(id) { if (state.hero.disabled.has(id)) state.hero.disabled.delete(id); else state.hero.disabled.add(id); return !state.hero.disabled.has(id); }

  function flee() { if (state.over) return { result: state.result };
    for (const e of alive()) { if (Math.hypot(e.x - state.hero.x, e.y - state.hero.y) < 220) { state.hero.invT = 0; if (!hitHero(e, e.attack)) return { result: 'lose' }; } }
    finish('fled'); return { result: 'fled' }; }
  function finish(r) { if (state.over) return; state.over = true; state.result = r; }

  function getState() {
    const h = state.hero;
    return {
      hero: { name: h.name, glyph: h.glyph, x: h.x, y: h.y, r: h.r, life: h.life, maxLife: h.maxLife,
        mana: Math.floor(h.mana), maxMana: h.maxMana, manaRegen: h.manaRegen, shield: Math.round(h.shield),
        accuracy: h.accuracy, evade: h.evade, invuln: h.invT > 0, dir: { ...h.dir }, weapon: h.weapon,
        cd: { ...h.cd }, abilities: h.abilities.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(ctx, id), cd: h.cd[id] || 0, off: h.disabled.has(id), ready: !h.disabled.has(id) && (h.cd[id] || 0) <= 0 && SKILLS[id].cost <= h.mana })) },
      enemies: state.enemies.filter((e) => e.hp > 0).map((e) => ({ uid: e.uid, id: e.id, name: e.name, glyph: e.glyph, x: e.x, y: e.y, r: e.r,
        hp: e.hp, maxHp: e.maxHp, kind: e.kind, role: e.role, elite: e.elite, unique: e.unique, boss: e.boss, gate: e.gate, flash: e.flash, raised: e.raised })),
      projectiles: state.projectiles.map((p) => ({ x: p.x, y: p.y, r: p.r, hostile: p.hostile, glyph: p.glyph })),
      minions: state.minions.map((m) => ({ x: m.x, y: m.y, r: m.r, glyph: m.glyph, hp: m.hp, maxHp: m.maxHp })),
      gems: state.gems.map((g) => ({ x: g.x, y: g.y })),
      pickups: state.pickups.map((p) => ({ x: p.x, y: p.y, r: p.r, color: p.item.color || '#c8a24a', slot: p.item.slot })),
      fx: state.fx.map((f) => ({ ...f })),
      time: state.time, turn: Math.round(state.time), xpEarned: state.xpEarned,
      over: state.over, result: state.result, tally: { ...state.tally },
      survival: !!surv,
      area: surv ? { idx: state.areaIdx, total: areas.length, name: curArea().name, quest: curArea().quest, questText: curArea().questText,
        timeLeft: Math.max(0, curArea().dur - state.areaT), gateSpawned: state.gateSpawned, gateName: state.gate ? state.gate.name : null } : null,
      areaCleared: state.areaCleared, banner: state.banner,
      boss: state.gate && state.gate.hp > 0 ? { hp: Math.max(0, state.gate.hp), maxHp: state.gate.maxHp, name: state.gate.name } : null,
      aliveCount: state.enemies.reduce((n, e) => n + (e.hp > 0 ? 1 : 0), 0),
      world: { w: world.w, h: world.h }, arena: { w: ARENA_W, h: ARENA_H },
    };
  }

  return { tick, autoInput, quaff, flee, setHero, heal, takeCollected, setDisabled, toggleAbility, getState, DT };
}
