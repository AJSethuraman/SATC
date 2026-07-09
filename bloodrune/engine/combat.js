// Bloodrune combat — SURROUNDED ABILITIES engine. You stand in a ring of foes:
// an INNER ring (melee reach) and an OUTER ring (casters/archers) reachable only
// by ranged skills, a Charge/Pierce (breakthrough -> Exposed), or Summons that
// flank the guard. Skills are always available (no cards), Mana-gated, and roll
// damage in RANGES. Casters are GUARDED (reduced damage) while an escort lives.
// Every living enemy hits you each turn. Killing grants XP. Pure engine, seeded rng.

import { SKILLS, ENEMIES, ELITE_AFFIXES, SUPERUNIQUES } from './content.js';

export const GUARD_MITIGATION = 0.6;
// A surround has only so many slots — this many melee foes can reach you at once.
// The rest are in the horde but WAIT their turn; as front-liners die, they step up.
export const ENGAGE_CAP = 5;
// Summons body-block only the single heaviest blow per turn — a wall, not immunity.
export const SUMMON_BLOCK_CAP = 1;

// A skill's LEVEL = 1 + hard points + global +Skills + per-ELEMENT +Skills (from
// enabler uniques / runewords, e.g. "+2 to Fire Skills"). Level raises BASE damage
// only — never the synergy bracket (that's hard points alone). Per-element +Skills
// is how an enabler unique makes a single-element build spike.
export function skillLevel(hero, id) {
  const s = SKILLS[id]; const elem = s && s.element;
  const elemBonus = (elem && hero.plusElem && hero.plusElem[elem]) || 0;
  return 1 + ((hero.hard && hero.hard[id]) || 0) + (hero.plusSkills || 0) + elemBonus;
}

// A physical skill's base damage IS the equipped weapon's damage (× the skill's
// wpn factor); the wrong weapon type — a bow for Cleave — leaves you flailing.
// Spell skills (Necro) are weapon-independent and use their own dmg.
function weaponBase(hero, s) {
  if (!s.weapon || s.weapon === 'spell') return s.dmg || [0, 0];
  const w = hero.weapon;
  if (s.weapon === 'weapon') return (w && w.dmg) ? w.dmg : [1, 3]; // auto-attack: whatever weapon you hold
  if (w && w.wtype === s.weapon && w.dmg) return w.dmg;
  return [1, 3];
}

// SYNERGY IS THE DAMAGE. A skill's power lives in the HARD points sunk into its
// named same-tree siblings (gear +skills add ZERO synergy — they raise the skill's
// LEVEL, i.e. base damage, only). A tree's MASTERY then multiplies on top. Read
// `hero.hard` only; a fully-fed capstone lands ~3x an unsupported one, so
// committing to one tree is mathematically dominant. Cross-tree synergy = 0.
const MASTERY_OF = { fire: 'fire_mastery', cold: 'cold_mastery', light: 'light_mastery' };
const hardOf = (hero, id) => (hero.hard && hero.hard[id]) || 0;
function synergyMult(hero, s) { if (!s.syn) return 1; let m = 1; for (const sib in s.syn) m += s.syn[sib] * hardOf(hero, sib); return m; }
function masteryMult(hero, s) { const mid = s.tab && MASTERY_OF[s.tab]; if (!mid) return 1;
  const mp = (SKILLS[mid] && SKILLS[mid].masteryPct) || 0; return 1 + mp * hardOf(hero, mid); }
const synText = (mult) => (mult > 1.001 ? ` · +${Math.round((mult - 1) * 100)}% synergy` : '');

export function skillEffect(hero, id) {
  const s = SKILLS[id]; const lvl = skillLevel(hero, id); const g = s.grow || 0;
  if (s.scale === 'passive') { const mp = s.masteryPct ? Math.round(s.masteryPct * 100 * hardOf(hero, id)) : 0;
    return { lvl, text: s.kind === 'mastery' ? `+${mp || Math.round((s.masteryPct || 0) * 100)}% ${s.tab} damage${s.masteryPct && hardOf(hero, id) ? ` (now +${mp}%)` : ' per point'}.` : (s.text || '') }; }
  if (s.scale === 'nova') { const syn = synergyMult(hero, s), mas = masteryMult(hero, s), scale = syn * mas;
    const min = Math.round((s.dmg[0] + g * (lvl - 1)) * scale), max = Math.round((s.dmg[1] + g * (lvl - 1)) * scale);
    return { lvl, min, max, syn, mas, element: s.element, text: `Blast ${min}-${max} to up to ${s.maxTargets || 6} around you${synText(scale)}.` }; }
  if (s.scale === 'damage') { const [wmin, wmax] = weaponBase(hero, s); const m = s.wpn || 1;
    const syn = synergyMult(hero, s), mas = masteryMult(hero, s), scale = syn * mas;
    const min = Math.round((Math.round(wmin * m) + g * (lvl - 1)) * scale), max = Math.round((Math.round(wmax * m) + g * (lvl - 1)) * scale);
    return { lvl, min, max, syn, mas, element: s.element, text: `Deal ${min}-${max}${s.target === 'aoe' ? ` to up to ${s.maxTargets || 3}` : ''}${s.reach ? ' (reaches)' : ''}${synText(scale)}.` }; }
  if (s.scale === 'hits') { const [wmin, wmax] = weaponBase(hero, s); const m = s.wpn || 0.7;
    const min = Math.max(1, Math.round(wmin * m)), max = Math.max(1, Math.round(wmax * m));
    const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, min, max, text: `Strike ${hits}× for ${min}-${max}.` }; }
  if (s.scale === 'block') { const block = s.base + g * (lvl - 1); return { lvl, block, text: `Gain ${block} Block.` }; }
  if (s.scale === 'summons') { const count = s.solo ? 1 : 1 + Math.floor((lvl - 1) / 2); const min = s.dmg[0] + (lvl - 1), max = s.dmg[1] + (lvl - 1);
    const hp = (s.hp || 5) + (s.hpGrow || 0) * (lvl - 1);
    return { lvl, count, min, max, hp, text: `Raise ${count} ${s.solo ? 'golem' : 'skeleton' + (count > 1 ? 's' : '')} (${min}-${max}, ${hp} HP) — strikes your target each turn and body-blocks the surround.` }; }
  return { lvl, text: '' };
}

const GUARDABLE = new Set(['caster', 'elite']);

function buildMonster(entry, i) {
  const su = (typeof entry === 'object' && entry.sid) ? SUPERUNIQUES[entry.sid] : null;
  const id = su ? su.id : (typeof entry === 'string' ? entry : entry.id);
  const base = su || ENEMIES[id];
  const affixes = (!su && typeof entry === 'object' && entry.affixes) ? entry.affixes : [];
  const o = typeof entry === 'object' ? entry : {};
  let hp = Math.round(base.hp * (o.hpMul || 1)), attack = Math.round(base.attack * (o.atkMul || 1)), extraAttack = !!base.extraAttack, leech = !!base.leech;
  for (const af of affixes) { const m = (ELITE_AFFIXES[af] && ELITE_AFFIXES[af].mods) || {};
    if (m.hpMul) hp = Math.round(hp * m.hpMul); if (m.attackMul) attack = Math.round(attack * m.attackMul);
    if (m.extraAttack) extraAttack = true; if (m.leech) leech = true; }
  return { uid: i, id, name: base.name, glyph: base.glyph, hp, maxHp: hp, attack, role: base.role,
    ring: base.ring || 0, heal: base.heal || 0, rezLeft: base.rez || 0, xp: base.xp || 0,
    acc: (typeof entry === 'object' && entry.acc != null) ? entry.acc : (base.acc != null ? base.acc : 5),
    eva: (typeof entry === 'object' && entry.eva != null) ? entry.eva : (base.eva || 0),
    guardsUid: (!su && typeof entry === 'object' && entry.guards != null) ? entry.guards : null,
    affixes, elite: su ? true : (affixes.length > 0 || base.role === 'elite'), unique: !!su, extraAttack, leech, raised: false, intent: null };
}

export function createCombat({ hero, pack, rng }) {
  const state = {
    hero: { name: hero.name, glyph: hero.glyph,
      life: hero.life != null ? Math.min(hero.life, hero.maxLife) : hero.maxLife, maxLife: hero.maxLife,
      block: 0, startBlock: hero.startBlock || 0,
      mana: hero.mana != null ? Math.min(hero.mana, hero.maxMana) : hero.maxMana, maxMana: hero.maxMana,
      manaRegen: hero.manaRegen != null ? hero.manaRegen : 4, weapon: hero.weapon || null,
      accuracy: hero.accuracy, evade: hero.evade || 0, actions: 0, maxActions: hero.actions || 3,
      plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) }, abilities: [...hero.abilities],
      exposed: false, summons: [], focusUid: null },
    enemies: pack.map(buildMonster),
    turn: 0, xpEarned: 0, over: false, result: null, log: [],
    tally: { hits: 0, misses: 0, evades: 0, kills: 0, dmgDealt: 0, dmgTaken: 0 }, // unbiased combat telemetry
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const byUid = (u) => state.enemies.find((e) => e.uid === u);
  const livingGuardians = (t) => alive().filter((g) => g.role === 'guardian' && g.guardsUid === t.uid);
  const isGuarded = (e) => GUARDABLE.has(e.role) && livingGuardians(e).length > 0;
  const roll = (min, max) => min + rng.int(max - min + 1);
  const woundedAllies = (self) => alive().filter((a) => a !== self && a.hp < a.maxHp);

  // Casters CHANNEL support (resolved reactively at end of round). Melee foes can
  // only reach you ENGAGE_CAP at a time — the front rank swings, the rest WAIT.
  // Ranged foes (outer ring) always act; they don't need a melee slot.
  function telegraph() {
    const frontMelee = new Set(alive().filter((e) => (e.ring || 0) === 0).slice(0, ENGAGE_CAP).map((e) => e.uid));
    for (const e of state.enemies) { if (e.hp <= 0) { e.intent = null; continue; }
      if (e.role === 'caster') e.intent = { type: 'support', value: e.heal };
      else if ((e.ring || 0) === 0 && !frontMelee.has(e.uid)) e.intent = { type: 'wait' };
      else e.intent = { type: 'attack', value: e.attack, times: e.extraAttack ? 2 : 1 }; } }

  // Mana is a POOL, not a per-turn allowance: you open full (turn 1 min() is a
  // no-op) and only regen a few points each turn — so mashing one expensive AoE
  // drains you and forces cheaper choices. Block still resets each turn.
  function startTurn() { state.turn += 1; state.hero.block = state.hero.startBlock;
    state.hero.mana = Math.min(state.hero.maxMana, state.hero.mana + state.hero.manaRegen);
    state.hero.actions = state.hero.maxActions; // action points bound how MANY things you do; Mana gates WHICH
    state.hero.exposed = false; telegraph(); state.log.push(`— Turn ${state.turn} —`); }

  function hurt(e, dmg) { e.hp = Math.max(0, e.hp - dmg); if (e.hp === 0) { e.intent = null; state.tally.kills++; if (!e.raised) state.xpEarned += e.xp || 0; state.log.push(`${e.name} ${e.raised ? 'falls again.' : 'dies.'}`); } }
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  // Physical attacks roll to-hit (Accuracy vs the target's Evade); a wide floor/
  // cap so accuracy MATTERS without being punitive. `acc == null` => auto-hit
  // (spells and summons never miss — the caster's edge).
  function applyHit(e, dmg, pierce, acc) {
    if (acc != null) { if (rng.next() > clamp(0.75 + (acc - (e.eva || 0)) * 0.04, 0.35, 0.95)) { state.tally.misses++; state.log.push(`You miss ${e.name}.`); return false; } state.tally.hits++; }
    let d = dmg; if (!pierce && isGuarded(e)) { d = Math.max(1, Math.round(dmg * (1 - GUARD_MITIGATION))); state.log.push(`${e.name} is guarded — only ${d} lands.`); } hurt(e, d); state.tally.dmgDealt += d; return true; }
  function setFocus(uid) { state.hero.focusUid = uid; }
  // The front rank shields the ranks behind it. Reach r strikes the nearest r+1
  // occupied rings — so melee (reach 0) can only hit the frontmost living rank,
  // but once you clear the front the outer ring STEPS IN and melee reaches it.
  function frontRing() { const a = alive(); return a.length ? Math.min(...a.map((e) => e.ring)) : 0; }
  function inReach(e, reach) { return e.ring <= frontRing() + reach; }
  // the auto-attack's reach follows the weapon (a bow reaches the outer ring, an axe doesn't)
  function reachOf(s) { return s.weapon === 'weapon' ? ((state.hero.weapon && state.hero.weapon.wtype === 'ranged') ? 1 : 0) : (s.reach || 0); }
  function pickTarget(s) { const reach = reachOf(s); const f = byUid(state.hero.focusUid);
    if (f && f.hp > 0 && inReach(f, reach)) return f; return alive().filter((e) => inReach(e, reach))[0] || null; }

  function useSkill(abilityIndex, focusUid) {
    if (state.over) return { ok: false };
    if (focusUid != null) state.hero.focusUid = focusUid;
    const id = state.hero.abilities[abilityIndex]; if (id == null) return { ok: false };
    const s = SKILLS[id]; const eff = skillEffect(state.hero, id);
    if (state.hero.actions <= 0) return { ok: false, reason: 'no actions left this turn' };
    if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    state.hero.mana -= s.cost;
    const acc = s.weapon === 'spell' ? null : state.hero.accuracy; // physical skills roll to-hit; spells auto-hit
    if (s.type === 'skill') { if (eff.block != null) { // bracing doesn't STACK — you're either braced or you're not
      if (state.hero.block >= eff.block) { state.hero.mana += s.cost; return { ok: false, reason: 'already braced' }; }
      state.hero.block = eff.block; } }
    else if (s.type === 'summon') { for (let i = 0; i < eff.count; i++) state.hero.summons.push({ glyph: s.solo ? '🗿' : '💀', min: eff.min, max: eff.max, hp: eff.hp, maxHp: eff.hp }); state.log.push(`${s.name}.`); }
    else if (s.target === 'aoe') { let pool = alive().filter((x) => inReach(x, s.reach || 0));
      if (!pool.length) { state.hero.mana += s.cost; return { ok: false, reason: 'no target in reach' }; }
      const f = byUid(state.hero.focusUid); if (f && pool.includes(f)) pool = [f, ...pool.filter((e) => e !== f)]; // your focus is struck first
      for (const e of pool.slice(0, s.maxTargets || pool.length)) applyHit(e, roll(eff.min, eff.max), false, acc); } // AoE catches only a few, never the whole ring
    else { const t = pickTarget(s); if (!t) { state.hero.mana += s.cost; return { ok: false, reason: 'no target in reach' }; }
      if (s.type === 'breakthrough') { applyHit(t, roll(eff.min, eff.max), true, acc); state.hero.exposed = true; state.log.push('You break through — and drop your guard.'); }
      else if (s.scale === 'hits') { for (let h = 0; h < eff.hits && t.hp > 0; h++) applyHit(t, roll(eff.min, eff.max), false, acc); }
      else applyHit(t, roll(eff.min, eff.max), false, acc); }
    state.hero.actions -= 1; // a successful action spends one action point
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
    // Evade: dodge the blow entirely, scaled against the ATTACKER's accuracy (a
    // sloppy foe is easy to juke, a precise one punches through). The Amazon's edge.
    if (state.hero.evade > 0 && rng.next() > clamp(0.80 + ((e.acc != null ? e.acc : 5) - state.hero.evade) * 0.04, 0.30, 0.95)) {
      state.tally.evades++; state.log.push(`You evade ${e.name}.`); return true; }
    const absorbed = state.hero.exposed ? 0 : Math.min(state.hero.block, raw); state.hero.block -= absorbed;
    const dmg = raw - absorbed; state.hero.life = Math.max(0, state.hero.life - dmg); state.tally.dmgTaken += dmg;
    state.log.push(`${e.name} hits you for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}${state.hero.exposed ? ' (exposed!)' : ''}.`);
    if (e.leech && dmg > 0) { e.hp = Math.min(e.maxHp, e.hp + dmg); }
    return state.hero.life > 0;
  }

  // A living summon body-blocks one incoming swing (the biggest first), taking the
  // hit itself and shattering if worn down — the Necromancer's wall of undead.
  function blockWithSummon(value) { const w = state.hero.summons[0]; if (!w) return false;
    w.hp -= value; state.log.push(`${w.glyph === '🗿' ? 'Golem' : 'Skeleton'} takes the blow (${Math.max(0, w.hp)}/${w.maxHp}).`);
    if (w.hp <= 0) { state.hero.summons.shift(); state.log.push('It shatters.'); } return true; }

  // A slain grunt is a corpse a rezzer can raise. Raised foes give no XP when
  // re-killed, so you can't farm them.
  const raisableCorpse = () => state.enemies.find((e) => e.hp <= 0 && e.role === 'grunt');

  // Any rezzer/healer (the Shaman, Blood Raven, Bishibosh...) reacts to the round
  // that just happened: raise a slain grunt (capped so it can't rez forever), else
  // mend the most-wounded ally. This is why you kill — or reach — them FIRST,
  // instead of grinding a pack they keep restoring. Pure casters do only this;
  // hybrids (Blood Raven) also swing via their own attack intent.
  function casterSupport() {
    for (const e of state.enemies) { if (e.hp <= 0 || (e.rezLeft <= 0 && !e.heal)) continue;
      // A rezzer can only raise a body while it still has a SCREEN (a living inner-
      // ring ally). Once you've cleared the front and pinned it, it can't wall
      // itself back up — you earned the turn to strike it. (Fairness fix.)
      const screened = alive().some((a) => a !== e && (a.ring || 0) === 0);
      const corpse = (e.rezLeft > 0 && screened) ? raisableCorpse() : null;
      if (corpse) { e.rezLeft -= 1; corpse.hp = corpse.maxHp; corpse.raised = true;
        corpse.intent = { type: 'attack', value: corpse.attack, times: 1 }; state.log.push(`${e.name} raises ${corpse.name} from the dead!`); continue; }
      if (!e.heal) continue;
      const al = woundedAllies(e).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp));
      if (al.length) { const tt = al[0]; const b = tt.hp; tt.hp = Math.min(tt.maxHp, tt.hp + e.heal); state.log.push(`${e.name} mends ${tt.name} +${tt.hp - b}.`); } }
  }

  function enemyPhase() {
    casterSupport(); // the backline reacts first, then the surround swings
    const swings = [];
    for (const e of state.enemies) { if (e.hp <= 0 || !e.intent || e.intent.type !== 'attack') continue;
      for (let t = 0; t < (e.intent.times || 1); t++) swings.push({ e, value: e.intent.value }); }
    swings.sort((a, b) => b.value - a.value); // summons soak the heaviest blows
    let blocked = 0;
    for (const sw of swings) { if (blocked < SUMMON_BLOCK_CAP && state.hero.summons.length && blockWithSummon(sw.value)) { blocked++; continue; }
      if (!monsterHit(sw.e, sw.value)) { finish('lose'); return false; } }
    return true;
  }

  function endTurn() { if (state.over) return; summonsPhase(); if (state.over) return; if (!enemyPhase()) return; startTurn(); }

  // Quaff a belt potion — a free action (doesn't end your turn); scarcity is the
  // limiter. Returns whether it was consumed so the run can decrement the belt.
  function quaff(kind, amount) {
    if (state.over) return { ok: false };
    if (state.hero.actions <= 0) return { ok: false, reason: 'no actions left this turn' }; // a sip costs an action, like a swing
    const h = state.hero;
    if (kind === 'life') { if (h.life >= h.maxLife) return { ok: false, reason: 'full' }; h.life = Math.min(h.maxLife, h.life + amount); state.log.push(`You quaff a Life potion (+${amount}).`); }
    else { if (h.mana >= h.maxMana) return { ok: false, reason: 'full' }; h.mana = Math.min(h.maxMana, h.mana + amount); state.log.push(`You quaff a Mana potion (+${amount}).`); }
    state.hero.actions -= 1;
    return { ok: true };
  }

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
      turn: state.turn, xpEarned: state.xpEarned, over: state.over, result: state.result, log: state.log.slice(), tally: { ...state.tally },
    };
  }

  startTurn();
  return { useSkill, endTurn, flee, setFocus, quaff, getState };
}
