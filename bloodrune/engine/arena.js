// Bloodrune ARENA — REAL-TIME movement engine (the Vampire-Survivors-style pivot).
// You are a token in an arena, MOVING (the only control). Your abilities AUTO-FIRE
// on cooldown when Mana allows — movement is the skill: kite the swarm, line up a
// Cleave, back off to regen. Enemies swarm toward you (melee), kite and loose
// arrows (ranged), or hang back and mend/raise the dead (casters).
//
// It keeps the SAME progression as the turn-based build: the same content
// (classes, skills, enemies, super uniques), the same weapon-driven damage
// (skillEffect), the same to-hit / dodge math, XP on kill, and the same win/lose
// contract game.js expects (getState() -> { over, result, xpEarned, hero, tally }).
// Pure engine: no DOM, deterministic, all randomness through the seeded rng.

import { SKILLS, ENEMIES, ELITE_AFFIXES, SUPERUNIQUES } from './content.js';
import { skillEffect } from './combat.js';

// Fixed simulation step. The UI accumulates real time and calls tick() this often;
// tests call tick() in a loop. A fixed dt keeps the sim fully deterministic.
export const DT = 1 / 30;
export const ARENA_W = 920, ARENA_H = 560;
const HERO_SPEED = 158, HERO_R = 13;
const INVULN = 0.34;          // brief i-frames after a hit so a surround can't melt you in one frame
const MELEE_REACH = 42;       // how far past your token a swing/contact lands
const PROJ_SPEED = 210, HOSTILE_PROJ_SPEED = 190;

// Real-time tuning per weapon of a skill's shape. Cooldowns gate spam; Mana still
// gates WHICH skills fire (an empty pool drops you to the free auto-attack).
const CD = { attack: 0.55, damage: 0.95, hits: 0.9, aoe: 1.25, breakthrough: 1.6, block: 4, summon: 2.6 };

// Enemy movement/timing. speed < hero speed so kiting works (the VS core); casters
// and archers keep their distance. Values fall back by role, override by id.
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

function buildRtMonster(entry, i, rng) {
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
  // Movement archetype: casters kite + support only; archers loose arrows (Blood
  // Raven also raises the dead between shots); everything else closes to melee.
  const role = base.role;
  const kind = role === 'caster' ? 'caster' : role === 'archer' ? 'ranged' : 'melee';
  const rd = ROLE_DEF[role] || ROLE_DEF.grunt;
  return { uid: i, id, name: base.name, glyph: base.glyph, hp, maxHp: hp, attack, role, kind,
    r: RAD[id] || rd.r, spd: SPD[id] || rd.spd, x: 0, y: 0, vx: 0, vy: 0,
    acc: (typeof entry === 'object' && entry.acc != null) ? entry.acc : (base.acc != null ? base.acc : 5),
    eva: (typeof entry === 'object' && entry.eva != null) ? entry.eva : (base.eva || 0),
    heal: base.heal || 0, rezLeft: base.rez || 0, xp: base.xp || 0, extraAttack, leech,
    touchCd: (rd.touch || 0.9) / (extraAttack ? 2 : 1), touchT: 0.4,
    fireCd: rd.fire || 1.7, fireT: 1.0, range: rd.range || 250,
    supportCd: rd.support || 2.1, supportT: 1.4, flash: 0, raised: false,
    elite: su ? true : (affixes.length > 0 || role === 'elite'), unique: !!su };
}

export function createArena({ hero, pack, rng }) {
  const ctx = { hard: hero.hard || {}, plusSkills: hero.plusSkills || 0, weapon: hero.weapon || null };
  const state = {
    hero: { name: hero.name, glyph: hero.glyph, x: ARENA_W / 2, y: ARENA_H / 2, r: HERO_R,
      life: hero.life != null ? Math.min(hero.life, hero.maxLife) : hero.maxLife, maxLife: hero.maxLife,
      mana: hero.mana != null ? Math.min(hero.mana, hero.maxMana) : hero.maxMana, maxMana: hero.maxMana,
      manaRegen: hero.manaRegen != null ? hero.manaRegen : 4, // now PER SECOND (pool still persists across the run)
      accuracy: hero.accuracy, evade: hero.evade || 0, weapon: hero.weapon || null,
      plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) }, abilities: [...hero.abilities],
      shield: 0, shieldT: 0, invT: 0, dir: { x: 0, y: -1 }, cd: {} },
    enemies: [], projectiles: [], minions: [], gems: [], fx: [],
    time: 0, xpEarned: 0, over: false, result: null,
    tally: { hits: 0, misses: 0, evades: 0, kills: 0, dmgDealt: 0, dmgTaken: 0 },
  };

  // Spawn the pack in a ring around the hero — melee close in front, ranged/casters
  // farther back — so you open surrounded and must carve a way out by moving.
  state.enemies = pack.map((e, i) => buildRtMonster(e, i, rng));
  const N = state.enemies.length;
  state.enemies.forEach((e, i) => {
    const a = (i / N) * Math.PI * 2 + rng.next() * 0.4;
    const far = e.kind === 'melee' ? 205 : 285;
    const rad = far + rng.next() * 40;
    e.x = clamp(ARENA_W / 2 + Math.cos(a) * rad, 30, ARENA_W - 30);
    e.y = clamp(ARENA_H / 2 + Math.sin(a) * rad, 30, ARENA_H - 30);
  });

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const roll = (min, max) => min + rng.int(max - min + 1);
  const nearest = (x, y, pred) => { let best = null, bd = Infinity;
    for (const e of state.enemies) { if (e.hp <= 0 || (pred && !pred(e))) continue;
      const d = Math.hypot(e.x - x, e.y - y); if (d < bd) { bd = d; best = e; } } return best ? { e: best, d: bd } : null; };

  function fx(o) { state.fx.push({ life: o.life || 0.3, maxLife: o.life || 0.3, ...o }); }

  function kill(e) { e.hp = 0; e.flash = 0.2; state.tally.kills++;
    if (!e.raised) { state.xpEarned += e.xp || 0; state.gems.push({ x: e.x, y: e.y, xp: e.xp || 0, life: 8, t: 0.15 }); } }

  // Land a blow. Physical (weapon != spell) rolls to-hit vs the target's Evade;
  // spells and summons auto-hit. Guarding didn't survive the movement port — a hit
  // is a hit — so damage lands whole.
  function hitEnemy(e, dmg, physical) {
    if (physical) { if (rng.next() > clamp(0.75 + (state.hero.accuracy - (e.eva || 0)) * 0.04, 0.35, 0.95)) {
      state.tally.misses++; fx({ type: 'miss', x: e.x, y: e.y - e.r - 6, life: 0.5 }); return false; } state.tally.hits++; }
    e.hp = Math.max(0, e.hp - dmg); e.flash = 0.15; state.tally.dmgDealt += dmg;
    fx({ type: 'dmg', x: e.x, y: e.y - e.r - 4, val: dmg, life: 0.6, vy: -26 });
    if (e.hp === 0) kill(e); return true;
  }

  // A blow lands on the hero: Evade dodges it whole (scaled vs the attacker's
  // accuracy — the Amazon's edge); a Block shield soaks the rest; i-frames follow.
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
      if ((h.cd[id] || 0) > 0) continue;
      const s = SKILLS[id]; if (!s) continue;
      const physical = s.weapon !== 'spell';
      const eff = skillEffect(ctx, id);
      if (s.type === 'skill') { // a brace: cast when the shield is spent and danger is near
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
      // damage skills need a target and Mana
      if (s.cost > h.mana) continue;
      const ranged = physical ? s.weapon === 'ranged' : (s.reach || s.target === 'aoe' || s.weapon === 'spell');
      if (s.target === 'aoe' && !ranged) { // melee AoE: sweep everything around you (Cleave / Whirlwind) — a wide arc so you can hit from the pack's edge, not its center
        const R = MELEE_REACH + 48; const pool = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= R + e.r);
        if (!pool.length) continue; h.mana -= s.cost; h.cd[id] = CD.aoe;
        fx({ type: 'sweep', x: h.x, y: h.y, r: R, life: 0.3 });
        for (const e of pool.slice(0, s.maxTargets || pool.length)) hitEnemy(e, roll(eff.min, eff.max), physical);
        continue; }
      if (s.target === 'aoe' && ranged) { // ranged AoE: a volley at the nearest few (Strafe / Teeth)
        const targets = alive().sort((a, b) => Math.hypot(a.x - h.x, a.y - h.y) - Math.hypot(b.x - h.x, b.y - h.y)).slice(0, s.maxTargets || 3);
        if (!targets.length) continue; h.mana -= s.cost; h.cd[id] = CD.aoe;
        for (const t of targets) spawnBolt(h, t, roll(eff.min, eff.max), physical, 0, s.weapon === 'spell' ? '🦴' : '➶');
        continue; }
      // single target
      const tgt = nearest(h.x, h.y); if (!tgt) continue;
      if (!ranged && tgt.d > MELEE_REACH + tgt.e.r + h.r + 6) continue; // must be in swing range for a melee skill
      h.mana -= s.cost;
      if (s.type === 'breakthrough') { // a lunge: dash toward the foe, then strike (Charge / Pierce)
        const dx = (tgt.e.x - h.x) / tgt.d, dy = (tgt.e.y - h.y) / tgt.d; const step = Math.min(tgt.d - tgt.e.r, 120);
        h.x = clamp(h.x + dx * step, h.r, ARENA_W - h.r); h.y = clamp(h.y + dy * step, h.r, ARENA_H - h.r);
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

  // Your bolts seek (VS-style auto-aim): they curve toward the nearest foe so ranged
  // classes reliably connect even against a circling kiter. Capped turn rate so a
  // dodging target can still slip a shot.
  function homeBolt(p, dt) {
    const t = nearest(p.x, p.y, (e) => !p.hitUids.includes(e.uid)); if (!t) return;
    const sp = Math.hypot(p.vx, p.vy) || PROJ_SPEED; const cur = Math.atan2(p.vy, p.vx);
    let want = Math.atan2(t.e.y - p.y, t.e.x - p.x); let dA = want - cur;
    while (dA > Math.PI) dA -= 2 * Math.PI; while (dA < -Math.PI) dA += 2 * Math.PI;
    const turn = clamp(dA, -7 * dt, 7 * dt); const na = cur + turn;
    p.vx = Math.cos(na) * sp; p.vy = Math.sin(na) * sp;
  }

  function stepProjectiles(dt) {
    for (const p of state.projectiles) {
      if (p.home && !p.hostile) homeBolt(p, dt);
      p.x += p.vx * dt; p.y += p.vy * dt; p.life -= dt;
      if (p.x < -20 || p.x > ARENA_W + 20 || p.y < -20 || p.y > ARENA_H + 20) p.life = 0;
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
      const tgt = nearest(m.x, m.y); // trail the hero; peel off to strike the nearest foe
      const anchor = tgt && tgt.d < 220 ? tgt.e : h; const dx = anchor.x - m.x, dy = anchor.y - m.y; const d = len(dx, dy);
      const want = tgt && tgt.d < 220 ? Math.max(0, Math.min(90, d - 40)) : Math.max(0, d - 30);
      const sp = 120; if (d > 4) { m.x += dx / d * Math.min(sp * dt, want * 0.5 + sp * dt * 0.2); m.y += dy / d * Math.min(sp * dt, want * 0.5 + sp * dt * 0.2); }
      m.fireT -= dt; if (tgt && tgt.d < 210 && m.fireT <= 0) { m.fireT = m.fireCd;
        spawnMinionBolt(m, tgt.e); }
    }
  }
  function spawnMinionBolt(m, target) { const d = Math.hypot(target.x - m.x, target.y - m.y) || 1;
    state.projectiles.push({ x: m.x, y: m.y, vx: (target.x - m.x) / d * PROJ_SPEED, vy: (target.y - m.y) / d * PROJ_SPEED,
      r: 5, dmg: roll(m.min, m.max), physical: false, pierce: 0, hostile: false, home: true, life: 1.8, glyph: '·', hitUids: [] }); }

  // A slain grunt is a corpse a rezzer can raise (capped by rezLeft; raised foes
  // give no XP, so you can't farm them). This is why you cut down the shaman first.
  const raisableCorpse = () => state.enemies.find((e) => e.hp <= 0 && e.role === 'grunt');

  function stepEnemies(dt) {
    const h = state.hero;
    for (const e of state.enemies) {
      if (e.hp <= 0) continue; if (e.flash > 0) e.flash -= dt;
      const dx = h.x - e.x, dy = h.y - e.y, d = len(dx, dy); const ux = dx / d, uy = dy / d;
      if (e.kind === 'melee') { if (d > e.r + h.r + 4) { e.x += ux * e.spd * dt; e.y += uy * e.spd * dt; }
        e.touchT -= dt; if (d <= e.r + h.r + MELEE_REACH * 0.4 && e.touchT <= 0) { e.touchT = e.touchCd; if (!hitHero(e, e.attack)) return; }
      } else { // ranged / caster: hold at their range and orbit, loose bolts / channel support
        const desired = e.range; const drift = d < desired ? -1 : d > desired + 40 ? 1 : 0;
        const ox = -uy, oy = ux; // strafe perpendicular so they don't sit still
        e.x = clamp(e.x + (ux * drift + ox * 0.5) * e.spd * dt, 20, ARENA_W - 20);
        e.y = clamp(e.y + (uy * drift + oy * 0.5) * e.spd * dt, 20, ARENA_H - 20);
        if (e.kind === 'ranged') { e.fireT -= dt; if (d < e.range + 90 && e.fireT <= 0) { e.fireT = e.fireCd;
          state.projectiles.push({ x: e.x, y: e.y, vx: ux * HOSTILE_PROJ_SPEED, vy: uy * HOSTILE_PROJ_SPEED, r: 6,
            dmg: e.attack, hostile: true, from: e, pierce: 0, life: 3, glyph: '➹' }); } }
        e.supportT -= dt; if ((e.rezLeft > 0 || e.heal) && e.supportT <= 0) { e.supportT = e.supportCd;
          const corpse = e.rezLeft > 0 ? raisableCorpse() : null;
          if (corpse) { e.rezLeft -= 1; corpse.hp = corpse.maxHp; corpse.raised = true;
            const a = rng.next() * Math.PI * 2; corpse.x = clamp(e.x + Math.cos(a) * 40, 20, ARENA_W - 20); corpse.y = clamp(e.y + Math.sin(a) * 40, 20, ARENA_H - 20);
            fx({ type: 'cast', x: e.x, y: e.y, r: 34, life: 0.5, color: '#6fd08a' }); }
          else if (e.heal) { const wounded = alive().filter((a) => a !== e && a.hp < a.maxHp).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp))[0];
            if (wounded) { wounded.hp = Math.min(wounded.maxHp, wounded.hp + e.heal); fx({ type: 'cast', x: wounded.x, y: wounded.y, r: 22, life: 0.4, color: '#6fd08a' }); } } }
      }
    }
  }

  function tick(input) {
    if (state.over) return getState();
    const h = state.hero, dt = DT;
    state.time += dt;
    if (h.invT > 0) h.invT -= dt;
    if (h.shieldT > 0) { h.shieldT -= dt; if (h.shieldT <= 0) h.shield = 0; }
    h.mana = Math.min(h.maxMana, h.mana + h.manaRegen * dt);
    for (const id of h.abilities) if (h.cd[id] > 0) h.cd[id] -= dt;
    // movement (the only control)
    let mx = input && input.x || 0, my = input && input.y || 0; const ml = Math.hypot(mx, my);
    if (ml > 0.01) { mx /= ml > 1 ? ml : 1; my /= ml > 1 ? ml : 1; h.dir = { x: mx, y: my };
      h.x = clamp(h.x + mx * HERO_SPEED * dt, h.r, ARENA_W - h.r); h.y = clamp(h.y + my * HERO_SPEED * dt, h.r, ARENA_H - h.r); }
    fireHeroAbilities();
    stepProjectiles(dt);
    stepMinions(dt);
    stepEnemies(dt);
    if (state.over) return getState();
    // fx / gems ageing
    for (const f of state.fx) { f.life -= dt; if (f.vy) f.y += f.vy * dt; }
    state.fx = state.fx.filter((f) => f.life > 0);
    for (const g of state.gems) { g.life -= dt; if (g.t > 0) g.t -= dt; }
    state.gems = state.gems.filter((g) => g.life > 0);
    if (!alive().length) finish('win');
    return getState();
  }

  // Headless autopilot (for the balance bot + tests): movement-only, range-aware.
  // A ranged/summoner hero kites at bow range; a melee hero closes to swing range
  // and chases down kiting casters (so a fight can't stalemate). Flee hard when low.
  const heroKites = (() => { const w = state.hero.weapon;
    if (w && w.wtype === 'ranged') return true;
    return state.hero.abilities.some((id) => { const s = SKILLS[id]; return s && (s.type === 'summon' || (s.type === 'attack' && s.weapon === 'spell')); }); })();
  function autoInput() {
    const h = state.hero; const t = nearest(h.x, h.y); let x = 0, y = 0, avoidWall = true;
    if (!t) return { x: 0, y: 0 };
    const desired = heroKites ? 190 : 66; // melee holds at the edge of its swing arc — in reach, out of contact
    const near = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) < (heroKites ? desired : 120));
    const to = (t.e.x - h.x) / t.d, ty = (t.e.y - h.y) / t.d;
    if (t.d > desired + 18) { x = to; y = ty; avoidWall = false; }   // approach straight — chase into corners, don't let the wall repel us off the target
    else if (heroKites && t.d < desired - 34) { x = -to; y = -ty; }  // too close (kiter) — back off
    else { x = -ty; y = to; }                                        // in the band — strafe, keep moving
    if (heroKites && avoidWall) for (const e of near) { const dx = h.x - e.x, dy = h.y - e.y, d = len(dx, dy); x += dx / d * 0.6; y += dy / d * 0.6; } // spread from the swarm while kiting
    if (avoidWall) { const edge = 70; if (h.x < edge) x += 1; if (h.x > ARENA_W - edge) x -= 1; if (h.y < edge) y += 1; if (h.y > ARENA_H - edge) y -= 1; }
    const l = Math.hypot(x, y); return l > 0.01 ? { x: x / l, y: y / l } : { x: 0, y: 0 };
  }

  function quaff(kind, amount) {
    if (state.over) return { ok: false }; const h = state.hero;
    if (kind === 'life') { if (h.life >= h.maxLife) return { ok: false, reason: 'full' }; h.life = Math.min(h.maxLife, h.life + amount); }
    else { if (h.mana >= h.maxMana) return { ok: false, reason: 'full' }; h.mana = Math.min(h.maxMana, h.mana + amount); }
    fx({ type: 'cast', x: h.x, y: h.y, r: 24, life: 0.3, color: kind === 'life' ? '#c62828' : '#4a7bff' });
    return { ok: true };
  }

  // Flee: a parting swing from every foe still close enough to reach you, then you break away.
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
        cd: { ...h.cd }, abilities: h.abilities.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(ctx, id), cd: h.cd[id] || 0, ready: (h.cd[id] || 0) <= 0 && SKILLS[id].cost <= h.mana })) },
      enemies: state.enemies.map((e) => ({ uid: e.uid, id: e.id, name: e.name, glyph: e.glyph, x: e.x, y: e.y, r: e.r,
        hp: e.hp, maxHp: e.maxHp, kind: e.kind, role: e.role, elite: e.elite, unique: e.unique, flash: e.flash, raised: e.raised })),
      projectiles: state.projectiles.map((p) => ({ x: p.x, y: p.y, r: p.r, hostile: p.hostile, glyph: p.glyph })),
      minions: state.minions.map((m) => ({ x: m.x, y: m.y, r: m.r, glyph: m.glyph, hp: m.hp, maxHp: m.maxHp })),
      gems: state.gems.map((g) => ({ x: g.x, y: g.y })),
      fx: state.fx.map((f) => ({ ...f })),
      time: state.time, turn: Math.round(state.time), xpEarned: state.xpEarned,
      over: state.over, result: state.result, tally: { ...state.tally },
      arena: { w: ARENA_W, h: ARENA_H },
    };
  }

  return { tick, autoInput, quaff, flee, getState, DT };
}
