// Bloodrune combat — SURROUNDED ABILITIES engine. You stand in a ring of foes:
// an INNER ring (melee reach) and an OUTER ring (casters/archers) reachable only
// by ranged skills, a Charge/Pierce (breakthrough -> Exposed), or Summons that
// flank the guard. Skills are always available (no cards), Mana-gated, and roll
// damage in RANGES. Casters are GUARDED (reduced damage) while an escort lives.
// Every living enemy hits you each turn. Killing grants XP. Pure engine, seeded rng.

import { SKILLS, ENEMIES, ELITE_AFFIXES } from './content.js';

export const GUARD_MITIGATION = 0.6;

export function skillLevel(hero, id) { return 1 + ((hero.hard && hero.hard[id]) || 0) + (hero.plusSkills || 0); }

export function skillEffect(hero, id) {
  const s = SKILLS[id]; const lvl = skillLevel(hero, id); const g = s.grow || 0;
  if (s.scale === 'damage') { const min = s.dmg[0] + g * (lvl - 1), max = s.dmg[1] + g * (lvl - 1);
    return { lvl, min, max, text: `Deal ${min}-${max}${s.target === 'aoe' ? ` to up to ${s.maxTargets || 3}` : ''}${s.reach ? ' (reaches outer)' : ''}.` }; }
  if (s.scale === 'hits') { const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, min: s.dmg[0], max: s.dmg[1], text: `Strike ${hits}× for ${s.dmg[0]}-${s.dmg[1]}.` }; }
  if (s.scale === 'block') { const block = s.base + g * (lvl - 1); return { lvl, block, text: `Gain ${block} Block.` }; }
  if (s.scale === 'summons') { const count = s.solo ? 1 : 1 + Math.floor((lvl - 1) / 2); const min = s.dmg[0] + (lvl - 1), max = s.dmg[1] + (lvl - 1);
    const hp = (s.hp || 5) + (s.hpGrow || 0) * (lvl - 1);
    return { lvl, count, min, max, hp, text: `Raise ${count} ${s.solo ? 'golem' : 'skeleton' + (count > 1 ? 's' : '')} (${min}-${max}, ${hp} HP) — strikes your target each turn and body-blocks the surround.` }; }
  return { lvl, text: '' };
}

const GUARDABLE = new Set(['caster', 'elite']);

function buildMonster(entry, i) {
  const id = typeof entry === 'string' ? entry : entry.id;
  const affixes = (typeof entry === 'object' && entry.affixes) ? entry.affixes : [];
  const base = ENEMIES[id];
  let hp = base.hp, attack = base.attack, extraAttack = false, leech = false;
  for (const af of affixes) { const m = (ELITE_AFFIXES[af] && ELITE_AFFIXES[af].mods) || {};
    if (m.hpMul) hp = Math.round(hp * m.hpMul); if (m.attackMul) attack = Math.round(attack * m.attackMul);
    if (m.extraAttack) extraAttack = true; if (m.leech) leech = true; }
  return { uid: i, id, name: base.name, glyph: base.glyph, hp, maxHp: hp, attack, role: base.role,
    ring: base.ring || 0, heal: base.heal || 0, rezLeft: base.role === 'caster' ? (base.rez || 0) : 0,
    guardsUid: (typeof entry === 'object' && entry.guards != null) ? entry.guards : null,
    affixes, elite: affixes.length > 0 || base.role === 'elite', extraAttack, leech, raised: false, intent: null };
}

export function createCombat({ hero, pack, rng }) {
  const state = {
    hero: { name: hero.name, glyph: hero.glyph,
      life: hero.life != null ? Math.min(hero.life, hero.maxLife) : hero.maxLife, maxLife: hero.maxLife,
      block: 0, startBlock: hero.startBlock || 0, mana: hero.maxMana, maxMana: hero.maxMana,
      manaRegen: hero.manaRegen != null ? hero.manaRegen : 4,
      plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) }, abilities: [...hero.abilities],
      exposed: false, summons: [], focusUid: null },
    enemies: pack.map(buildMonster),
    turn: 0, xpEarned: 0, over: false, result: null, log: [],
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const byUid = (u) => state.enemies.find((e) => e.uid === u);
  const livingGuardians = (t) => alive().filter((g) => g.role === 'guardian' && g.guardsUid === t.uid);
  const isGuarded = (e) => GUARDABLE.has(e.role) && livingGuardians(e).length > 0;
  const roll = (min, max) => min + rng.int(max - min + 1);
  const woundedAllies = (self) => alive().filter((a) => a !== self && a.hp < a.maxHp);

  // Casters CHANNEL — they don't wind up a blow, they support. What they actually
  // do is decided at end of round, reacting to that round's casualties (below).
  function telegraph() { for (const e of state.enemies) { if (e.hp <= 0) { e.intent = null; continue; }
    if (e.role === 'caster') e.intent = { type: 'support', value: e.heal };
    else e.intent = { type: 'attack', value: e.attack, times: e.extraAttack ? 2 : 1 }; } }

  // Mana is a POOL, not a per-turn allowance: you open full (turn 1 min() is a
  // no-op) and only regen a few points each turn — so mashing one expensive AoE
  // drains you and forces cheaper choices. Block still resets each turn.
  function startTurn() { state.turn += 1; state.hero.block = state.hero.startBlock;
    state.hero.mana = Math.min(state.hero.maxMana, state.hero.mana + state.hero.manaRegen);
    state.hero.exposed = false; telegraph(); state.log.push(`— Turn ${state.turn} —`); }

  function hurt(e, dmg) { e.hp = Math.max(0, e.hp - dmg); if (e.hp === 0) { e.intent = null; if (!e.raised) state.xpEarned += ENEMIES[e.id].xp || 0; state.log.push(`${e.name} ${e.raised ? 'falls again.' : 'dies.'}`); } }
  function applyHit(e, dmg, pierce) { let d = dmg; if (!pierce && isGuarded(e)) { d = Math.max(1, Math.round(dmg * (1 - GUARD_MITIGATION))); state.log.push(`${e.name} is guarded — only ${d} lands.`); } hurt(e, d); }
  function setFocus(uid) { state.hero.focusUid = uid; }
  // The front rank shields the ranks behind it. Reach r strikes the nearest r+1
  // occupied rings — so melee (reach 0) can only hit the frontmost living rank,
  // but once you clear the front the outer ring STEPS IN and melee reaches it.
  function frontRing() { const a = alive(); return a.length ? Math.min(...a.map((e) => e.ring)) : 0; }
  function inReach(e, reach) { return e.ring <= frontRing() + reach; }
  function pickTarget(s) { const reach = s.reach || 0; const f = byUid(state.hero.focusUid);
    if (f && f.hp > 0 && inReach(f, reach)) return f; return alive().filter((e) => inReach(e, reach))[0] || null; }

  function useSkill(abilityIndex, focusUid) {
    if (state.over) return { ok: false };
    if (focusUid != null) state.hero.focusUid = focusUid;
    const id = state.hero.abilities[abilityIndex]; if (id == null) return { ok: false };
    const s = SKILLS[id]; const eff = skillEffect(state.hero, id);
    if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    state.hero.mana -= s.cost;
    if (s.type === 'skill') { if (eff.block != null) { // bracing doesn't STACK — you're either braced or you're not
      if (state.hero.block >= eff.block) { state.hero.mana += s.cost; return { ok: false, reason: 'already braced' }; }
      state.hero.block = eff.block; } }
    else if (s.type === 'summon') { for (let i = 0; i < eff.count; i++) state.hero.summons.push({ glyph: s.solo ? '🗿' : '💀', min: eff.min, max: eff.max, hp: eff.hp, maxHp: eff.hp }); state.log.push(`${s.name}.`); }
    else if (s.target === 'aoe') { let pool = alive().filter((x) => inReach(x, s.reach || 0));
      if (!pool.length) { state.hero.mana += s.cost; return { ok: false, reason: 'no target in reach' }; }
      const f = byUid(state.hero.focusUid); if (f && pool.includes(f)) pool = [f, ...pool.filter((e) => e !== f)]; // your focus is struck first
      for (const e of pool.slice(0, s.maxTargets || pool.length)) applyHit(e, roll(eff.min, eff.max), false); } // AoE catches only a few, never the whole ring
    else { const t = pickTarget(s); if (!t) { state.hero.mana += s.cost; return { ok: false, reason: 'no target in reach' }; }
      if (s.type === 'breakthrough') { applyHit(t, roll(eff.min, eff.max), true); state.hero.exposed = true; state.log.push('You break through — and drop your guard.'); }
      else if (s.scale === 'hits') { for (let h = 0; h < eff.hits && t.hp > 0; h++) applyHit(t, roll(eff.min, eff.max), false); }
      else applyHit(t, roll(eff.min, eff.max), false); }
    state.log.push(`Cast ${s.name}.`);
    if (!alive().length) finish('win');
    return { ok: true };
  }

  function summonsPhase() { if (!state.hero.summons.length || !alive().length) return;
    const focus = byUid(state.hero.focusUid);
    for (const sk of state.hero.summons) { if (!alive().length) break;
      const t = (focus && focus.hp > 0) ? focus : alive().find((e) => e.role === 'caster') || alive()[0];
      const d = roll(sk.min, sk.max); applyHit(t, d, true); state.log.push(`${sk.glyph === '🗿' ? 'Golem' : 'Skeleton'} strikes ${t.name} for ${d}.`); }
    if (!alive().length) finish('win'); }

  function monsterHit(e, raw) {
    const absorbed = state.hero.exposed ? 0 : Math.min(state.hero.block, raw); state.hero.block -= absorbed;
    const dmg = raw - absorbed; state.hero.life = Math.max(0, state.hero.life - dmg);
    state.log.push(`${e.name} hits you for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}${state.hero.exposed ? ' (exposed!)' : ''}.`);
    if (e.leech && dmg > 0) { e.hp = Math.min(e.maxHp, e.hp + dmg); }
    return state.hero.life > 0;
  }

  // A living summon body-blocks one incoming swing (the biggest first), taking the
  // hit itself and shattering if worn down — the Necromancer's wall of undead.
  function blockWithSummon(value) { const w = state.hero.summons[0]; if (!w) return false;
    w.hp -= value; state.log.push(`${w.glyph === '🗿' ? 'Golem' : 'Skeleton'} takes the blow (${Math.max(0, w.hp)}/${w.maxHp}).`);
    if (w.hp <= 0) { state.hero.summons.shift(); state.log.push('It shatters.'); } return true; }

  // A slain Fallen is a corpse a Shaman can raise (Fallen only — the Fallen Shaman's
  // signature). Raised Fallen give no XP when re-killed, so you can't farm them.
  const fallenCorpse = () => state.enemies.find((e) => e.hp <= 0 && e.id === 'fallen');

  // Casters react to the round that just happened: raise a slain Fallen (capped so
  // it can't rez forever), else mend the most-wounded ally. This is why you kill —
  // or reach — the Shaman first, instead of grinding a pack it keeps restoring.
  function casterSupport() {
    for (const e of state.enemies) { if (e.hp <= 0 || e.role !== 'caster' || !e.intent || e.intent.type !== 'support') continue;
      const corpse = e.rezLeft > 0 ? fallenCorpse() : null;
      if (corpse) { e.rezLeft -= 1; corpse.hp = corpse.maxHp; corpse.raised = true;
        corpse.intent = { type: 'attack', value: corpse.attack, times: 1 }; state.log.push(`${e.name} raises ${corpse.name} from the dead!`); continue; }
      const al = woundedAllies(e).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp));
      if (al.length) { const tt = al[0]; const b = tt.hp; tt.hp = Math.min(tt.maxHp, tt.hp + e.heal); state.log.push(`${e.name} mends ${tt.name} +${tt.hp - b}.`); } }
  }

  function enemyPhase() {
    casterSupport(); // the backline reacts first, then the surround swings
    const swings = [];
    for (const e of state.enemies) { if (e.hp <= 0 || !e.intent || e.intent.type !== 'attack') continue;
      for (let t = 0; t < (e.intent.times || 1); t++) swings.push({ e, value: e.intent.value }); }
    swings.sort((a, b) => b.value - a.value); // summons soak the heaviest blows
    for (const sw of swings) { if (state.hero.summons.length && blockWithSummon(sw.value)) continue;
      if (!monsterHit(sw.e, sw.value)) { finish('lose'); return false; } }
    return true;
  }

  function endTurn() { if (state.over) return; summonsPhase(); if (state.over) return; if (!enemyPhase()) return; startTurn(); }

  // Flee: every living enemy gets one parting swing; survive -> escape (no loot), die -> loss.
  function flee() { if (state.over) return { result: state.result };
    for (const e of alive()) { if (!monsterHit(e, e.attack)) { finish('lose'); return { result: 'lose' }; } }
    finish('fled'); return { result: 'fled' }; }

  function finish(r) { state.over = true; state.result = r; state.log.push(r === 'win' ? 'The ring breaks.' : r === 'fled' ? 'You break away.' : 'You have died.'); }

  function getState() {
    return {
      hero: { ...state.hero, hard: { ...state.hero.hard }, summons: state.hero.summons.map((s) => ({ ...s })),
        abilities: state.hero.abilities.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(state.hero, id) })) },
      enemies: state.enemies.map((e) => ({ ...e, guarded: isGuarded(e), guardianCount: livingGuardians(e).length })),
      turn: state.turn, xpEarned: state.xpEarned, over: state.over, result: state.result, log: state.log.slice(),
    };
  }

  startTurn();
  return { useSkill, endTurn, flee, setFocus, getState };
}
