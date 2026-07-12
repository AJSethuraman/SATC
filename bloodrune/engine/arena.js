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
import { skillEffect, skillManaCost, skillCostMul, castSpeedMul, castInfo } from './combat.js';

export const DT = 1 / 30;                    // fixed sim step — determinism
export const ARENA_W = 1120, ARENA_H = 630;  // camera viewport — a standard 16:9 widescreen play area
export const WORLD_W = 2600, WORLD_H = 1700; // survival: one big map you roam
const HERO_SPEED = 158, HERO_R = 13;
const INVULN = 0.34;
const MELEE_REACH = 42;
const PROJ_SPEED = 210, HOSTILE_PROJ_SPEED = 190;
const CAP_ALIVE = 82;                        // survival: max live foes (perf + fairness)
const CORPSE_TTL = 5;                         // survival: how long a corpse lingers (rez window + cleanup)
// Standing still is dangerous ORGANICALLY, not by a synthetic "you stopped -> take
// damage" field: hold position and the whole horde converges on your spot, so many
// foes reach melee at once and their real contact/attacks pile up and overwhelm you.
// Movement spreads them into a chasing tail (fewer in contact). A strong-enough AoE
// build CAN hold a spot — that's earned, and it's meant to be hard, not forbidden.

const CD = { attack: 0.55, damage: 0.95, hits: 0.9, aoe: 1.25, breakthrough: 1.6, block: 4, summon: 2.6 };
const ELEM_FX = { fire: '#ff7a3a', cold: '#8fc4ff', lightning: '#d6a6ff', poison: '#8fe07a' };
const elemColor = (el) => ELEM_FX[el] || '#c8a24a';
// Auto-fire only reaches roughly what's ON SCREEN — you engage the fight you can see,
// not snipe things off the edge of the world.
const SCREEN_RANGE = 340;
// Foes move at a real fraction of the hero's 158 — fast enough that kiting takes
// SKILL (weave, don't get boxed), not a free stroll. Combined with ranged fire that
// LEADS you and enclosure pressure, a MOVING hero must actually work to stay clean.
const ROLE_DEF = {
  grunt:    { spd: 100, r: 13, touch: 0.85 },
  guardian: { spd: 92, r: 15, touch: 0.95 },
  archer:   { spd: 96, r: 13, fire: 1.9, range: 300 },
  caster:   { spd: 82, r: 14, support: 2.1, range: 240, fire: 2.2 },
  elite:    { spd: 88, r: 23, touch: 1.0 },
};
const SPD = { quill_rat: 98, fallen: 102, zombie: 82, guardian: 90, goatman: 108, shaman: 84, archer: 96, the_smith: 76,
  rakanishu: 116, corpsefire: 92, blood_raven: 104, bishibosh: 88 };
const RAD = { the_smith: 23 };

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const len = (x, y) => Math.hypot(x, y) || 1;

// Elemental damage after resistance. Penetration (gear −enemy-resist) lowers the
// effective resist, but a true IMMUNITY (100%) yields 0 — uncrackable by ordinary
// penetration, so you must swap element. Returns 0 iff immune to that element.
export function resistedDamage(dmg, resist, immune, element, penetration) {
  if (!element || !resist) return dmg;
  if (immune === element) return 0;
  const effRes = Math.max(-0.5, Math.min(0.95, (resist[element] || 0) - (penetration || 0)));
  return Math.max(1, Math.round(dmg * (1 - effRes)));
}

const ELEMENTS = ['fire', 'cold', 'lightning'];
// Resistances make difficulty a BUILD problem, not an HP sponge. Normal = none;
// Nightmare packs resist one element (~40%); Hell resist harder (~60%) and some
// become IMMUNE (100%) to one element — you must swap element or use penetration.
function resistFor(base, tier, rng) {
  const res = { fire: base.resist && base.resist.fire || 0, cold: base.resist && base.resist.cold || 0, lightning: base.resist && base.resist.lightning || 0 };
  let immune = base.immune || null;
  if (tier === 'Nightmare' || tier === 'Hell') { const el = ELEMENTS[rng.int(3)]; const r = tier === 'Hell' ? 0.6 : 0.4;
    res[el] = Math.max(res[el], r); for (const o of ELEMENTS) if (o !== el) res[o] = Math.max(res[o], tier === 'Hell' ? 0.25 : 0.1);
    if (tier === 'Hell' && !immune && rng.next() < 0.15) { immune = el; } }
  if (immune) res[immune] = 1;
  return { res, immune };
}
function buildRtMonster(entry, uid, rng, tier) {
  const su = (typeof entry === 'object' && entry.sid) ? SUPERUNIQUES[entry.sid] : null;
  const id = su ? su.id : (typeof entry === 'string' ? entry : entry.id);
  const base = su || ENEMIES[id];
  const affixes = (!su && typeof entry === 'object' && entry.affixes) ? entry.affixes : [];
  const o = typeof entry === 'object' ? entry : {};
  const rr = resistFor(base, tier || null, rng); const res = rr.res; let immune = rr.immune;
  if (o.resist) for (const k in o.resist) res[k] = o.resist[k]; // thematic/test overrides
  if (o.immune) { immune = o.immune; res[o.immune] = 1; }
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
    resist: res, immune,
    boss: !!base.boss || id === 'the_smith', elite: su ? true : (affixes.length > 0 || role === 'elite'), unique: !!su };
}

export function createArena({ hero, pack, rng, survival }) {
  const surv = survival || null;
  const world = surv ? { w: WORLD_W, h: WORLD_H } : { w: ARENA_W, h: ARENA_H };
  const ctx = { hard: hero.hard || {}, plusSkills: hero.plusSkills || 0, plusElem: hero.plusElem || {}, weapon: hero.weapon || null };
  const state = {
    hero: { name: hero.name, glyph: hero.glyph, classId: hero.classId || null, x: world.w / 2, y: world.h / 2, r: HERO_R,
      life: hero.life != null ? Math.min(hero.life, hero.maxLife) : hero.maxLife, maxLife: hero.maxLife,
      mana: hero.mana != null ? Math.min(hero.mana, hero.maxMana) : hero.maxMana, maxMana: hero.maxMana,
      manaRegen: hero.manaRegen != null ? hero.manaRegen : 4,
      accuracy: hero.accuracy, evade: hero.evade || 0, weapon: hero.weapon || null,
      plusSkills: hero.plusSkills || 0, fcr: hero.fcr || 0, ias: hero.ias || 0, penetration: hero.penetration || 0, skillMods: hero.skillMods || {}, hard: { ...(hero.hard || {}) }, abilities: [...hero.abilities],
      shield: 0, shieldT: 0, invT: 0, stillT: 0, dir: { x: 0, y: -1 }, aim: { x: 1, y: 0 }, cd: {}, disabled: new Set() },
    enemies: [], projectiles: [], minions: [], gems: [], fx: [], pickups: [], collected: [], pending: [],
    time: 0, xpEarned: 0, over: false, result: null, nextUid: 0,
    spawnTimer: surv ? 0.6 : 0,
    areaIdx: 0, areaT: 0, gate: null, gateSpawned: false, areaCleared: 0, banner: 0, // Act 1 gauntlet state
    tally: { hits: 0, misses: 0, evades: 0, kills: 0, dmgDealt: 0, dmgTaken: 0, moveDist: 0, idleT: 0, moveT: 0 }, // moveDist/idleT/moveT: is the player actually MOVING?
  };
  const areas = (surv && surv.areas) || [];

  if (!surv) { // PACK mode: a fixed ring around the hero
    state.enemies = pack.map((e) => buildRtMonster(e, state.nextUid++, rng, null));
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
      // Loot comes from NOTABLE kills (elites, super-uniques, gates/bosses) — trash barely
      // drops. At ~7 kills/s a per-trash-kill drop just spams; this makes a drop mean something.
      const chance = e.boss ? 1 : e.unique ? 1 : e.elite ? 0.3 : (0.02 + (e.drop || 0));
      // Thread the CURRENT area's ilvl into the drop so deeper areas roll a better pool.
      if (rng.next() < chance) { const it = surv.rollLoot(e.boss ? 3 : e.unique ? 2 : e.elite ? 1 : 0, curArea().ilvl);
        if (it) state.pickups.push({ x: e.x, y: e.y, r: 11, item: it }); }
    }
  }

  // `quiet` skips the floating damage number (for fast CHANNELED ticks like Inferno,
  // where 30 popups/sec per foe would be noise — the flame + enemy flash carry it).
  function hitEnemy(e, dmg, physical, element, quiet) {
    if (physical) { if (rng.next() > clamp(0.75 + (state.hero.accuracy - (e.eva || 0)) * 0.04, 0.35, 0.95)) {
      state.tally.misses++; fx({ type: 'miss', x: e.x, y: e.y - e.r - 6, life: 0.5 }); return false; } state.tally.hits++; }
    // Elemental resistance/immunity: penetration (gear −enemy-resist) lowers resist
    // but can't crack a true immunity — you must swap element for those.
    if (element && e.resist) {
      const out = resistedDamage(dmg, e.resist, e.immune, element, state.hero.penetration || 0);
      if (out === 0) { if (!quiet) fx({ type: 'immune', x: e.x, y: e.y - e.r - 6, life: 0.6 }); return false; } // immune — swap element
      dmg = out;
    }
    e.hp = Math.max(0, e.hp - dmg); e.flash = 0.15; state.tally.dmgDealt += dmg;
    if (!quiet) fx({ type: 'dmg', x: e.x, y: e.y - e.r - 4, val: dmg, life: 0.6, vy: -26 });
    if (e.hp === 0) kill(e); return true;
  }

  // Delayed ground strikes (Meteor / Glacial Spike): after the telegraph, the AoE lands.
  function processPending(dt) {
    if (!state.pending.length) return;
    for (const p of state.pending) p.t -= dt;
    const land = state.pending.filter((p) => p.t <= 0); state.pending = state.pending.filter((p) => p.t > 0);
    for (const p of land) {
      fx({ type: 'impact', x: p.x, y: p.y, r: p.r, life: p.big ? 0.5 : 0.35, color: p.color });
      const pool = alive().filter((e) => Math.hypot(e.x - p.x, e.y - p.y) <= p.r + e.r).slice(0, p.n);
      for (const e of pool) hitEnemy(e, roll(p.min, p.max), false, p.element);
    }
  }
  // A boss's signature: a telegraphed roar that flings a ring of bolts outward — you
  // must move to dodge it, so standing on the boss and face-tanking no longer works.
  function gateSlam(g) {
    fx({ type: 'telegraph', x: g.x, y: g.y, r: 130, life: 0.5, color: '#ff5a4a' });
    const n = 18, dmg = Math.max(5, Math.round(g.attack * 0.7));
    for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2 + (g.slamT || 0);
      state.projectiles.push({ x: g.x, y: g.y, vx: Math.cos(a) * HOSTILE_PROJ_SPEED * 0.85, vy: Math.sin(a) * HOSTILE_PROJ_SPEED * 0.85,
        r: 7, dmg, hostile: true, from: g, pierce: 0, life: 2.6, glyph: '✸', element: g.slamElem || 'fire' }); }
  }
  // Second signature: the boss AIMS a tight fan of bolts straight at you — dodge SIDEWAYS,
  // not away (running back-pedals into the spread). A different read from the ring-slam.
  function gateCone(g) {
    const h = state.hero; const base = Math.atan2(h.y - g.y, h.x - g.x);
    fx({ type: 'telegraph', x: g.x, y: g.y, r: 110, life: 0.55, color: '#ffd45a' });
    const n = 7, dmg = Math.max(6, Math.round(g.attack * 0.85));
    for (let i = 0; i < n; i++) { const a = base + (i - (n - 1) / 2) * 0.18;
      state.projectiles.push({ x: g.x, y: g.y, vx: Math.cos(a) * HOSTILE_PROJ_SPEED, vy: Math.sin(a) * HOSTILE_PROJ_SPEED,
        r: 7, dmg, hostile: true, from: g, pierce: 0, life: 2.4, glyph: '✦', element: g.slamElem || 'fire' }); }
  }
  // Third signature: the boss SUMMONS a knot of its minions right on top of you — you
  // can't just kite it forever, the adds cut off your escape lane and force a reposition.
  function gateSummon(g) {
    const area = curArea(); const sc = scaleFor(); const kind = (area.pool && area.pool[0]) || 'fallen';
    fx({ type: 'cast', x: g.x, y: g.y, r: 120, life: 0.7, color: '#c62828' });
    const n = 3; for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2;
      const e = spawnAtRing({ id: kind, hpMul: sc.hpMul, atkMul: sc.atkMul });
      e.x = clamp(state.hero.x + Math.cos(a) * 150, 40, world.w - 40); e.y = clamp(state.hero.y + Math.sin(a) * 150, 40, world.h - 40); }
  }
  const GATE_ABILITIES = [gateSlam, gateCone, gateSummon];

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

  // The area GATE (a super-unique / boss), if present and alive — auto-fire FOCUSES
  // it so a swarm can't shield the boss forever (mirrors how you'd play: kill the
  // named threat, don't farm trash while it enrages you to death).
  const liveGate = () => (state.gate && state.gate.hp > 0) ? state.gate : null;

  // ---- hero abilities (auto-fire on cooldown; Mana gates which ones) ----------
  function fireHeroAbilities() {
    const h = state.hero; if (!alive().length) return;
    for (const id of h.abilities) {
      if (h.disabled.has(id)) continue;                // you can toggle a skill OFF so only the ones you want auto-fire
      if ((h.cd[id] || 0) > 0) continue;
      const s = SKILLS[id]; if (!s || s.type === 'passive') continue; // passives (Warmth/Masteries) don't fire
      const physical = s.weapon !== 'spell';
      const eff = skillEffect(ctx, id);
      const cost = skillManaCost(h, id); // effective mana cost — gear +skills & −%cost make it cheaper
      // Increased Attack Speed (physical, smooth) / Faster Cast Rate (spells, D2-style
      // BREAKPOINTS per class) shrink the cooldown — cast-rate gear is a planning target.
      const cdMul = physical ? 1 / (1 + Math.min(220, h.ias || 0) / 100) : castSpeedMul(h.classId, h.fcr || 0);
      // ---- Sorceress spells: each is routed by its GEOMETRY (`geo`), not a generic
      // "hit N nearest". geometry (shape/behavior) is decoupled from `scale` (the
      // damage number), so a bolt seeks, a ball bursts, a beam is a line, a cone is a
      // cone, a nova is a ring, a spread scatters, and chain leaps. -------------------
      if (s.weapon === 'spell' && s.geo && s.type === 'attack') {
        if (cost > h.mana) continue; const col = elemColor(s.element);
        // GEAR skill-mods reshape geometry: spellPct scales damage, aoePct scales blast
        // size, +jumps/+bolts extend chain/spread, pierce lets bolts pass through foes.
        const sm = h.skillMods || {}; const sdm = 1 + (sm.spellPct || 0) / 100; const aoe = 1 + (sm.aoePct || 0) / 100;
        const dmg = () => Math.round(roll(eff.min, eff.max) * sdm); const pierce = sm.pierce || 0;
        if (s.geo === 'nova') { // FROST NOVA / NOVA / STATIC FIELD — a ring bursting from you
          const R = (s.radius || 140) * aoe; const pool = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= R + e.r);
          if (!pool.length) continue; h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
          fx({ type: 'ring', x: h.x, y: h.y, r: R, life: 0.4, color: col });
          for (const e of pool.slice(0, s.maxTargets || pool.length)) hitEnemy(e, dmg(), false, s.element);
          continue; }
        if (s.geo === 'storm') { // THUNDER STORM — lightning falls from the sky onto scattered foes around you
          const range = s.stormRange || 360; const pool = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= range);
          if (!pool.length) continue; h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
          const strikes = Math.min(pool.length, (s.strikeBase || 2) + Math.floor((eff.lvl - 1) / 2)); const avail = pool.slice();
          for (let k = 0; k < strikes && avail.length; k++) { const e = avail.splice(rng.int(avail.length), 1)[0];
            hitEnemy(e, dmg(), false, s.element);
            fx({ type: 'chain', x: e.x, y: e.y - 94, x2: e.x, y2: e.y, life: 0.22, color: col }); // a bolt from above
            fx({ type: 'impact', x: e.x, y: e.y, r: 20, life: 0.2, color: col }); }
          continue; }
        if (s.geo === 'cone') { // INFERNO — a CHANNELED cone toward the nearest foe: it stays ON, burning
          // everything in front continuously and DRAINING mana per second (a real flamethrower).
          const ft = faceTarget(); if (!ft) continue;
          const pulse = 0.12, perSec = (s.manaPerSec || 8) * skillCostMul(h, id); // channel drain, cheaper with +skills/−cost gear
          if (h.mana < perSec * pulse) continue;           // flame sputters out when you run dry
          const ang = Math.atan2(ft.e.y - h.y, ft.e.x - h.x); const range = (s.coneRange || 165) * aoe, half = s.coneArc || 0.6;
          const inCone = alive().filter((e) => { const dd = Math.hypot(e.x - h.x, e.y - h.y); if (dd > range + e.r) return false;
            let da = Math.atan2(e.y - h.y, e.x - h.x) - ang; while (da > Math.PI) da -= 2 * Math.PI; while (da < -Math.PI) da += 2 * Math.PI; return Math.abs(da) <= half; });
          if (!inCone.length) continue;                    // don't drain into empty air
          h.mana -= perSec * pulse; h.cd[id] = pulse;       // mana per SECOND, applied per pulse
          const cap = s.maxTargets || 99; let hit = 0;
          for (const e of inCone) { if (hit++ >= cap) break; hitEnemy(e, dmg(), false, s.element, true); } // quiet: no popup spam
          fx({ type: 'cone', x: h.x, y: h.y, ang, range, half, life: pulse + 0.06, color: col }); // overlap keeps the flame solid
          continue; }
        // every other geometry needs a direction/target — aim at the boss (on-screen) else nearest
        const aim = aimPoint(); if (!aim) continue;
        if (s.geo === 'arc') { // CHAIN LIGHTNING — auto-seeks, then LEAPS to a few (jumps grow with skill + gear)
          h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
          const jumps = Math.min((s.jumpMax || 8) + (sm.jumps || 0), (s.jumpBase || 3) + Math.floor((eff.lvl - 1) / 2) + (sm.jumps || 0)); const range = s.jumpRange || 215;
          const hitU = new Set(); let fx1 = h.x, fy1 = h.y, node = aim.e;
          for (let j = 0; j < jumps && node; j++) { hitU.add(node.uid);
            fx({ type: 'chain', x: fx1, y: fy1, x2: node.x, y2: node.y, life: 0.16, color: col });
            hitEnemy(node, dmg(), false, s.element); fx1 = node.x; fy1 = node.y;
            let best = null, bd = 1e9; for (const e2 of alive()) { if (hitU.has(e2.uid)) continue; const dd = Math.hypot(e2.x - fx1, e2.y - fy1); if (dd < range && dd < bd) { bd = dd; best = e2; } }
            node = best; }
          continue; }
        if (s.geo === 'beam') { // LIGHTNING — an instant line of raw current toward the nearest foe: HUGE damage, dead straight
          const ft = faceTarget() || aim; h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
          const ang = Math.atan2(ft.e.y - h.y, ft.e.x - h.x); const L = s.beamLen || 520, halfW = (s.beamW || 34) / 2;
          const ux = Math.cos(ang), uy = Math.sin(ang);
          for (const e of alive()) { const rx = e.x - h.x, ry = e.y - h.y; const along = rx * ux + ry * uy;
            if (along < 0 || along > L) continue; const perp = Math.abs(rx * -uy + ry * ux);
            if (perp <= halfW + e.r) hitEnemy(e, dmg(), false, s.element); }
          fx({ type: 'beam', x: h.x, y: h.y, x2: h.x + ux * L, y2: h.y + uy * L, life: 0.18, color: col });
          continue; }
        if (s.geo === 'ground') { // METEOR — a telegraphed blast that falls onto the pack
          h.mana -= cost; h.cd[id] = cdMul * CD.aoe; const R = (s.radius || 140) * aoe;
          fx({ type: 'telegraph', x: aim.e.x, y: aim.e.y, r: R, life: 0.6, color: col });
          state.pending.push({ x: aim.e.x, y: aim.e.y, r: R, min: Math.round(eff.min * sdm), max: Math.round(eff.max * sdm), element: s.element, n: s.maxTargets || 8, t: 0.6, big: true, color: col });
          continue; }
        if (s.geo === 'ball') { // FIRE BALL / GLACIAL SPIKE — a projectile that BURSTS in an AoE on impact
          h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
          const b = spawnBolt(h, aim.e, dmg(), false, 0, s.glyph || '☄', s.element);
          b.splash = { r: (s.splashR || 90) * aoe, min: Math.round(eff.min * sdm), max: Math.round(eff.max * sdm), element: s.element, n: s.maxTargets || 8, color: col };
          continue; }
        if (s.geo === 'spread') { // CHARGED BOLT — a fan of erratic bolts toward the nearest foe that scatter (they do NOT seek); +bolts/pierce from gear
          const ft = faceTarget() || aim; h.mana -= cost; h.cd[id] = cdMul * CD.damage;
          const ang = Math.atan2(ft.e.y - h.y, ft.e.x - h.x); const n = Math.min((s.boltMax || 9) + (sm.bolts || 0), (s.boltBase || 3) + Math.floor((eff.lvl - 1) / 2) + (sm.bolts || 0)); const arc = s.spreadArc || 0.9;
          for (let k = 0; k < n; k++) { const a = ang + (n === 1 ? 0 : (k / (n - 1) - 0.5) * arc) + (rng.next() - 0.5) * 0.18;
            const b = spawnBolt(h, { x: h.x + Math.cos(a) * 400, y: h.y + Math.sin(a) * 400 }, dmg(), false, pierce, '⚡', s.element); b.home = false; b.life = 0.85; }
          continue; }
        // geo 'seeker' (default) — FIRE BOLT / ICE BOLT / ICE BLAST: a single homing bolt (pierces with gear)
        h.mana -= cost; h.cd[id] = cdMul * CD.damage;
        spawnBolt(h, aim.e, dmg(), false, pierce, s.glyph || '•', s.element);
        continue; }
      if (s.type === 'skill') {
        if (h.shield > (eff.block || 0) * 0.5) continue;
        if (cost > h.mana) continue; const near = nearest(h.x, h.y); if (!near || near.d > 300) continue;
        h.mana -= cost; h.shield = Math.max(h.shield, eff.block || 0); h.shieldT = 6; h.cd[id] = cdMul * CD.block;
        fx({ type: 'cast', x: h.x, y: h.y, r: 46, life: 0.4, color: '#c8a24a' }); continue; }
      if (s.type === 'summon') { const cap = 3 + (eff.count || 1);
        if (state.minions.length >= cap) continue; if (cost > h.mana) continue;
        h.mana -= cost; for (let k = 0; k < (eff.count || 1); k++) {
          const a = rng.next() * Math.PI * 2; state.minions.push({ x: h.x + Math.cos(a) * 26, y: h.y + Math.sin(a) * 26,
            r: 9, hp: eff.hp, maxHp: eff.hp, min: eff.min, max: eff.max, fireCd: 1.0, fireT: 0.3, solo: !!s.solo,
            glyph: s.solo ? '🗿' : '💀' }); }
        h.cd[id] = cdMul * CD.summon; fx({ type: 'cast', x: h.x, y: h.y, r: 30, life: 0.35, color: '#8a90c8' }); continue; }
      if (cost > h.mana) continue;
      const ranged = physical ? s.weapon === 'ranged' : (s.reach || s.target === 'aoe' || s.weapon === 'spell');
      if (s.target === 'aoe' && !ranged) { // melee AoE: a wide arc around you (Cleave / Whirlwind)
        const R = MELEE_REACH + 48; const pool = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= R + e.r);
        if (!pool.length) continue; h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
        fx({ type: 'sweep', x: h.x, y: h.y, r: R, life: 0.3 });
        for (const e of pool.slice(0, s.maxTargets || pool.length)) hitEnemy(e, roll(eff.min, eff.max), physical, s.element);
        continue; }
      if (s.target === 'aoe' && ranged) { // ranged AoE volley — focus the gate, then the nearest few (Fire Ball / Strafe / Teeth)
        let targets = alive().filter((e) => Math.hypot(e.x - h.x, e.y - h.y) <= SCREEN_RANGE).sort((a, b) => Math.hypot(a.x - h.x, a.y - h.y) - Math.hypot(b.x - h.x, b.y - h.y));
        const gt = liveGate(); if (gt && Math.hypot(gt.x - h.x, gt.y - h.y) <= SCREEN_RANGE && !targets.slice(0, s.maxTargets || 3).includes(gt)) targets = [gt, ...targets.filter((e) => e !== gt)];
        targets = targets.slice(0, s.maxTargets || 3);
        if (!targets.length) continue; h.mana -= cost; h.cd[id] = cdMul * CD.aoe;
        for (const t of targets) spawnBolt(h, t, roll(eff.min, eff.max), physical, 0, s.weapon === 'spell' ? '🦴' : '➶', s.element);
        continue; }
      // single-target: a ranged skill FOCUSES the gate (you can hit it anywhere); melee takes the nearest in reach
      const gt = liveGate();
      const tgt = (ranged && gt && Math.hypot(gt.x - h.x, gt.y - h.y) <= SCREEN_RANGE) ? { e: gt, d: Math.hypot(gt.x - h.x, gt.y - h.y) } : nearest(h.x, h.y); if (!tgt) continue;
      if (!ranged && tgt.d > MELEE_REACH + tgt.e.r + h.r + 6) continue;
      if (ranged && tgt.d > SCREEN_RANGE) continue; // no more sniping foes off-screen
      h.mana -= cost;
      if (s.type === 'breakthrough') {
        const dx = (tgt.e.x - h.x) / tgt.d, dy = (tgt.e.y - h.y) / tgt.d; const step = Math.min(tgt.d - tgt.e.r, 120);
        h.x = clamp(h.x + dx * step, h.r, world.w - h.r); h.y = clamp(h.y + dy * step, h.r, world.h - h.r);
        fx({ type: 'dash', x: h.x, y: h.y, life: 0.25 });
        if (ranged) spawnBolt(h, tgt.e, roll(eff.min, eff.max), physical, 3, '➶', s.element); else hitEnemy(tgt.e, roll(eff.min, eff.max), physical, s.element);
        h.cd[id] = cdMul * CD.breakthrough; continue; }
      if (s.scale === 'hits') { for (let hh = 0; hh < eff.hits; hh++) { const t = nearest(h.x, h.y); if (!t || t.d > MELEE_REACH + t.e.r + h.r + 6) break; hitEnemy(t.e, roll(eff.min, eff.max), physical, s.element); }
        h.cd[id] = cdMul * CD.hits; fx({ type: 'sweep', x: h.x, y: h.y, r: MELEE_REACH, life: 0.2 }); continue; }
      if (ranged) spawnBolt(h, tgt.e, roll(eff.min, eff.max), physical, 0, s.weapon === 'spell' ? '🦴' : '➶', s.element);
      else { hitEnemy(tgt.e, roll(eff.min, eff.max), physical, s.element); fx({ type: 'sweep', x: h.x, y: h.y, r: MELEE_REACH, life: 0.18 }); }
      h.cd[id] = cdMul * (id === 'attack' ? CD.attack : CD.damage);
    }
  }

  // Bolts fly STRAIGHT — fired at where the target is NOW, no course-correction. Aim it
  // (the hero auto-faces the nearest foe), and it hits only if the foe is still in its
  // path when it arrives; a mover can slip it. Nothing homes by default — tracking is
  // reserved for skills where it's intrinsic (Chain Lightning leaps foe to foe). Set
  // home:true explicitly to opt a bolt into the auto-aim below.
  function spawnBolt(from, target, dmg, physical, pierce, glyph, element) {
    const d = Math.hypot(target.x - from.x, target.y - from.y) || 1;
    const p = { x: from.x, y: from.y, vx: (target.x - from.x) / d * PROJ_SPEED, vy: (target.y - from.y) / d * PROJ_SPEED,
      r: 6, dmg, physical, element, pierce: pierce || 0, hostile: false, home: false, life: 2.2, glyph: glyph || '•', hitUids: [] };
    state.projectiles.push(p); return p;
  }
  // A ball-spell BURSTS on impact: an AoE splash at the point it landed (Fire Ball / Glacial Spike).
  function burstSplash(p) { const s = p.splash;
    fx({ type: 'impact', x: p.x, y: p.y, r: s.r, life: 0.4, color: s.color });
    const pool = alive().filter((e) => Math.hypot(e.x - p.x, e.y - p.y) <= s.r + e.r).slice(0, s.n);
    for (const e of pool) hitEnemy(e, roll(s.min, s.max), false, s.element);
  }
  // Auto-aim helper: FOCUS the boss if it's on-screen, else the nearest foe within view.
  // Used by targeted/homing casts (bolts, balls, meteor, chain) that commit to a target.
  function aimPoint() {
    const h = state.hero; const gt = liveGate();
    if (gt && Math.hypot(gt.x - h.x, gt.y - h.y) <= SCREEN_RANGE) return { e: gt, d: Math.hypot(gt.x - h.x, gt.y - h.y) };
    const n = nearest(h.x, h.y); if (!n || n.d > SCREEN_RANGE) return null; return n;
  }
  // FACING target: the nearest foe, full stop (no boss-focus). This is where the hero
  // TURNS to aim — Halls-of-Torment style, decoupled from movement — so directional
  // skills (cone/beam/spread) fire at the nearest threat while you move any direction.
  function faceTarget() { const h = state.hero; const n = nearest(h.x, h.y); if (!n || n.d > SCREEN_RANGE) return null; return n; }

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
        if (Math.hypot(p.x - e.x, p.y - e.y) <= p.r + e.r) { hitEnemy(e, p.dmg, p.physical, p.element); p.hitUids.push(e.uid);
          if (p.splash) { burstSplash(p); p.life = 0; break; } // a ball detonates on the first thing it touches
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
      r: 5, dmg: roll(m.min, m.max), physical: false, pierce: 0, hostile: false, home: false, life: 1.8, glyph: '·', hitUids: [] }); }

  const raisableCorpse = () => state.enemies.find((e) => e.hp <= 0 && e.role === 'grunt');

  function stepEnemies(dt) {
    const h = state.hero;
    for (const e of state.enemies) {
      if (e.hp <= 0) continue; if (e.flash > 0) e.flash -= dt;
      const dx = h.x - e.x, dy = h.y - e.y, d = len(dx, dy); const ux = dx / d, uy = dy / d;
      if (e.kind === 'melee') { if (d > e.r + h.r + 4) { e.x += ux * e.spd * dt; e.y += uy * e.spd * dt; }
        e.touchT -= dt; if (d <= e.r + h.r + MELEE_REACH * 0.4 && e.touchT <= 0) { e.touchT = e.touchCd; if (!hitHero(e, e.attack)) return; }
      } else {
        // Ranged foes HOLD GROUND at a modest standoff (~150) instead of fleeing across
        // the map — they advance to it and shoot, so you can actually close and kill them.
        const desired = 150; const drift = d < 100 ? -0.7 : d > desired ? 0.85 : 0;
        const ox = -uy, oy = ux; const strafe = d < desired + 60 ? 0.35 : 0;
        e.x = clamp(e.x + (ux * drift + ox * strafe) * e.spd * dt, 20, world.w - 20);
        e.y = clamp(e.y + (uy * drift + oy * strafe) * e.spd * dt, 20, world.h - 20);
        if (e.kind === 'ranged') { e.fireT -= dt; if (d < e.range + 90 && e.fireT <= 0) { e.fireT = e.fireCd;
          // Fire at where you ARE right now — NO prediction. The bolt then travels, so a
          // MOVING hero simply isn't there when it arrives (you dodged), while a hero who
          // stands still is exactly where it lands. Getting hit is YOUR inaction, not a
          // penalty the game applies for standing — pure positioning.
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
  function spawnAtRing(entry) { const e = buildRtMonster(entry, state.nextUid++, rng, surv && surv.tier);
    const a = rng.next() * Math.PI * 2, rad = 520 + rng.next() * 120;
    e.x = clamp(state.hero.x + Math.cos(a) * rad, 24, world.w - 24);
    e.y = clamp(state.hero.y + Math.sin(a) * rad, 24, world.h - 24); state.enemies.push(e); return e; }
  const curArea = () => areas[state.areaIdx] || areas[areas.length - 1];
  function spawnWave() { // pour in this area's foes from its pool, scaled by overall time
    const area = curArea(); const sc = scaleFor(); const min = state.time / 60;
    const n = Math.min(14, 3 + Math.floor(min * 1.7)); // denser waves — standing still gets you surrounded
    const WAVE_HP = 1.12; // trash stays light — the CHALLENGE is the boss fight, not chip from the swarm
    const AFFIX = Object.keys(ELITE_AFFIXES);
    // CHAMPION PACK: every so often a tight cluster of same-affixed elites converges
    // together — a real threat that drops real loot (the D2 champion/minion pack).
    if (min >= 0.5 && rng.next() < 0.16) {
      const af = rng.pick(AFFIX); const packId = rng.pick(area.pool); const size = 2 + Math.floor(rng.next() * 2);
      const a = rng.next() * Math.PI * 2, rad = 540 + rng.next() * 120; // one ring anchor, so the pack arrives as a wall
      const ax = clamp(state.hero.x + Math.cos(a) * rad, 60, world.w - 60), ay = clamp(state.hero.y + Math.sin(a) * rad, 60, world.h - 60);
      for (let k = 0; k < size; k++) { const e = spawnAtRing({ id: packId, affixes: [af], hpMul: sc.hpMul, atkMul: sc.atkMul, drop: 0.28 }); e.x = clamp(ax + (rng.next() - 0.5) * 80, 40, world.w - 40); e.y = clamp(ay + (rng.next() - 0.5) * 80, 40, world.h - 40); }
    }
    // lone champions: more common and earlier now — the swarm should have teeth in it
    const eliteChance = Math.min(0.16, 0.06 + min * 0.03);
    for (let k = 0; k < n; k++) {
      const entry = { id: rng.pick(area.pool), hpMul: sc.hpMul * WAVE_HP, atkMul: sc.atkMul };
      if (min >= 1 && rng.next() < eliteChance) { entry.affixes = [rng.pick(AFFIX)]; entry.drop = 0.24; }
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
    gate.resist = { fire: 0, cold: 0, lightning: 0 }; gate.immune = null; // a gate is never immune — you can always kill your way forward
    // A gate is a real FIGHT, not a speed bump: far more HP, a bigger body, and a
    // telegraphed ring-slam so you can't just park on it and out-DPS.
    gate.hp = Math.round(gate.hp * (isBoss ? 3.4 : 6)); gate.maxHp = gate.hp;
    gate.r = Math.round(gate.r * (isBoss ? 2.2 : 1.7)); gate.slamT = 3.2;
    gate.slamElem = area.gate === 'bishibosh' ? 'fire' : area.gate === 'rakanishu' ? 'lightning' : 'fire';
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
      // the boss cycles through its signatures (ring-slam → aimed cone → summon adds) so
      // the fight keeps changing what it asks of you instead of one dodge on repeat.
      state.gate.slamT -= dt; if (state.gate.slamT <= 0) { state.gate.slamT = 3.2;
        state.gate.abilIdx = ((state.gate.abilIdx || 0) + 1) % GATE_ABILITIES.length; GATE_ABILITIES[state.gate.abilIdx](state.gate); }
      if (age > 26) { const k = 1 + (age - 26) * 0.08; state.gate.spd = state.gate.baseSpd * Math.min(3.4, k);
        state.gate.attack = Math.round(state.gate.baseAtk * Math.min(2.6, 1 + (age - 26) * 0.05));
        if (state.gate.kind !== 'melee' && age > 40) state.gate.kind = 'melee'; } } // charges you down so it can't be kited forever
    // area cleared when its gate falls: advance to the next area, or win after Andariel
    if (state.gate && state.gate.hp <= 0) {
      state.areaCleared++;
      if (state.areaIdx >= areas.length - 1) { finish('win'); return; }
      state.areaIdx++; state.areaT = 0; state.gate = null; state.gateSpawned = false; state.banner = 2.4;
      state.enemies = []; state.projectiles = state.projectiles.filter((p) => !p.hostile); state.spawnTimer = 0.8; // clean, simple transition
      fx({ type: 'cast', x: state.hero.x, y: state.hero.y, r: 100, life: 0.8, color: '#c8a24a' });
    }
    state.spawnTimer -= dt;
    // The live-foe cap RAMPS: the opening is sparse (a weak lvl-1 hero can clear it),
    // then it swells toward CAP_ALIVE as you grow — VS-style escalation, not an instant burial.
    const aliveCap = state.gateSpawned ? 22 : Math.min(CAP_ALIVE, 16 + Math.floor((state.time / 60) * 46));
    if (state.spawnTimer <= 0 && alive().length < aliveCap) {
      spawnWave(); state.spawnTimer = (state.gateSpawned ? 3.4 : 1) * Math.max(0.5, 1.6 - (state.time / 60) * 0.12);
    }
    if (state.banner > 0) state.banner -= dt;
    if (state.enemies.length > 90) state.enemies = state.enemies.filter((e) => e.hp > 0 || e.gate || (e.deadAt >= 0 && state.time - e.deadAt < CORPSE_TTL));
  }

  function stepPickups() { // loot magnets toward you (generous, survivors-style), collected on contact -> game drains it
    const h = state.hero;
    for (const p of state.pickups) { const dx = h.x - p.x, dy = h.y - p.y, d = len(dx, dy);
      // generous magnet + pull FASTER than the hero runs, so a kiting hero still
      // vacuums up the loot its kills leave behind (no backtracking to farm).
      if (d < 340) { p.x += dx / d * Math.min(d, 440 * DT); p.y += dy / d * Math.min(d, 440 * DT); }
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
    if (ml > 0.05) { const n = ml > 1 ? ml : 1; mx /= n; my /= n; h.dir = { x: mx, y: my };
      h.x = clamp(h.x + mx * HERO_SPEED * dt * Math.min(1, ml), h.r, world.w - h.r); h.y = clamp(h.y + my * HERO_SPEED * dt * Math.min(1, ml), h.r, world.h - h.r);
      state.tally.moveT += dt; state.tally.moveDist += HERO_SPEED * Math.min(1, ml) * dt; }
    else state.tally.idleT += dt; // idle time tracked for telemetry — no synthetic penalty for it
    // the hero TURNS to face the nearest foe (aim ≠ movement) — Halls-of-Torment style
    const at = nearest(h.x, h.y); if (at && at.d > 1) h.aim = { x: (at.e.x - h.x) / at.d, y: (at.e.y - h.y) / at.d };
    if (surv) director(dt);
    fireHeroAbilities();
    stepProjectiles(dt);
    stepMinions(dt);
    stepEnemies(dt);
    if (state.over) return getState();
    processPending(dt);              // delayed ground impacts (Meteor / Glacial Spike land)
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
    if (p.fcr != null) h.fcr = p.fcr; if (p.ias != null) h.ias = p.ias; if (p.penetration != null) h.penetration = p.penetration;
    if (p.plusSkills != null) { h.plusSkills = p.plusSkills; ctx.plusSkills = p.plusSkills; }
    if (p.plusElem != null) { h.plusElem = p.plusElem; ctx.plusElem = p.plusElem; }
    if (p.skillMods != null) h.skillMods = p.skillMods;
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
        accuracy: h.accuracy, evade: h.evade, fcr: h.fcr, ias: h.ias, penetration: h.penetration, cast: castInfo(h.classId, h.fcr || 0), invuln: h.invT > 0, dir: { ...h.dir }, aim: { ...h.aim }, weapon: h.weapon,
        cd: { ...h.cd }, abilities: h.abilities.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(ctx, id), manaCost: skillManaCost(h, id), cd: h.cd[id] || 0, off: h.disabled.has(id), ready: !h.disabled.has(id) && (h.cd[id] || 0) <= 0 && skillManaCost(h, id) <= h.mana })) },
      enemies: state.enemies.filter((e) => e.hp > 0).map((e) => ({ uid: e.uid, id: e.id, name: e.name, glyph: e.glyph, x: e.x, y: e.y, r: e.r,
        hp: e.hp, maxHp: e.maxHp, kind: e.kind, role: e.role, elite: e.elite, unique: e.unique, boss: e.boss, gate: e.gate, flash: e.flash, raised: e.raised, resist: e.resist, immune: e.immune })),
      projectiles: state.projectiles.map((p) => ({ x: p.x, y: p.y, r: p.r, hostile: p.hostile, glyph: p.glyph, element: p.element, vx: p.vx, vy: p.vy })),
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
