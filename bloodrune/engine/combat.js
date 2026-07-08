// Combat state machine — swarm + accuracy + elites + XP + flee. Pure engine,
// no DOM, all rolls from the injected seeded rng.
//
// Hit resolution is two-stage: attacker Accuracy (does it land?), then defender
// Evasion (dodge a landed blow; 0 for the Barbarian). Elite monsters carry
// affixes (frenzied/brutal/hardened/unerring/vampiric). Killing monsters grants
// XP. Flee ends the fight but every living monster gets a parting swing.

import { CARDS, MONSTERS, ELITE_AFFIXES } from './content.js';

const clampAcc = (a) => Math.max(5, Math.min(100, a));

function buildMonster(entry, i) {
  const id = typeof entry === 'string' ? entry : entry.id;
  const affixes = (typeof entry === 'object' && entry.affixes) ? entry.affixes : [];
  const base = MONSTERS[id];
  let hp = base.hp, attack = base.attack, accuracy = base.accuracy != null ? base.accuracy : 100;
  let extraAttack = false, leech = false;
  for (const af of affixes) {
    const mods = (ELITE_AFFIXES[af] && ELITE_AFFIXES[af].mods) || {};
    if (mods.hpMul) hp = Math.round(hp * mods.hpMul);
    if (mods.attackMul) attack = Math.round(attack * mods.attackMul);
    if (mods.accuracy != null) accuracy = mods.accuracy;
    if (mods.extraAttack) extraAttack = true;
    if (mods.leech) leech = true;
  }
  return { index: i, id, name: base.name, glyph: base.glyph, hp, maxHp: hp, attack, accuracy,
    role: base.role || 'attacker', heal: base.heal || 0, extraAttack, leech,
    affixes, elite: affixes.length > 0, intent: null };
}

export function createCombat({ deck, hero, pack, rng }) {
  const state = {
    hero: {
      name: hero.name, glyph: hero.glyph,
      life: hero.life != null ? Math.min(hero.life, hero.maxLife) : hero.maxLife, maxLife: hero.maxLife,
      block: 0, startBlock: hero.startBlock || 0,
      mana: hero.maxMana, maxMana: hero.maxMana,
      handSize: hero.handSize,
      plusSkills: hero.plusSkills || 0,
      accuracy: hero.accuracy != null ? hero.accuracy : 100,
      evasion: hero.evasion || 0,
      tempEvasion: 0, // from the Evade card; reset each turn like Block
    },
    lane: pack.map(buildMonster),
    drawPile: rng.shuffle(deck),
    hand: [],
    discardPile: [],
    turn: 0,
    xpEarned: 0,
    over: false,
    result: null, // 'win' | 'lose' | 'fled'
    log: [],
  };

  const living = () => state.lane.filter((m) => m.hp > 0);
  const front = () => state.lane.find((m) => m.hp > 0) || null;

  function lands(accuracy, defenderEvasion) {
    if (rng.next() * 100 >= clampAcc(accuracy)) return false;
    if (defenderEvasion > 0 && rng.next() * 100 < defenderEvasion) return false;
    return true;
  }

  function drawOne() {
    if (state.drawPile.length === 0) {
      if (state.discardPile.length === 0) return;
      state.drawPile = rng.shuffle(state.discardPile);
      state.discardPile = [];
    }
    state.hand.push(state.drawPile.pop());
  }

  const woundedAllies = (self) => living().filter((a) => a !== self && a.hp < a.maxHp);

  function telegraph() {
    for (const m of state.lane) {
      if (m.hp <= 0) { m.intent = null; continue; }
      if (m.role === 'healer' && woundedAllies(m).length > 0) m.intent = { type: 'mend', value: m.heal };
      else m.intent = { type: 'attack', value: m.attack, times: m.extraAttack ? 2 : 1 };
    }
  }

  function startTurn() {
    state.turn += 1;
    state.hero.block = state.hero.startBlock;
    state.hero.tempEvasion = 0;
    state.hero.mana = state.hero.maxMana;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) drawOne();
    telegraph();
    state.log.push(`— Turn ${state.turn} —`);
  }

  function hurt(m, amount) {
    m.hp = Math.max(0, m.hp - amount);
    if (m.hp === 0) {
      m.intent = null;
      state.xpEarned += MONSTERS[m.id].xp || 0;
      state.log.push(`${m.name} dies.`);
    }
  }

  function playCard(handIndex, targetIndex) {
    if (state.over) return { ok: false, reason: 'combat is over' };
    const cardId = state.hand[handIndex];
    if (cardId == null) return { ok: false, reason: 'no such card' };
    const card = CARDS[cardId];
    if (card.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };

    state.hero.mana -= card.cost;
    if (card.refund) state.hero.mana += card.refund;
    if (card.block) state.hero.block += card.block;
    if (card.evasion) state.hero.tempEvasion += card.evasion;

    if (card.damage) {
      const dmg = card.damage + state.hero.plusSkills;
      const acc = state.hero.accuracy + (card.acc || 0);
      if (card.target === 'aoe') {
        for (const m of living()) {
          if (lands(acc, m.evasion)) hurt(m, dmg);
          else state.log.push(`${card.name} misses ${m.name}.`);
        }
      } else {
        let target = null;
        if (Number.isInteger(targetIndex)) {
          const chosen = state.lane[targetIndex];
          if (chosen && chosen.hp > 0) target = chosen;
        }
        if (!target) target = front();
        if (target) {
          if (lands(acc, target.evasion)) hurt(target, dmg);
          else state.log.push(`${card.name} misses ${target.name}.`);
        }
      }
    }
    state.log.push(`Play ${card.name}.`);
    state.hand.splice(handIndex, 1);
    state.discardPile.push(cardId);

    if (living().length === 0) finish('win');
    return { ok: true };
  }

  // One monster attack against the hero (Block absorbs, then Life). Handles
  // Vampiric leech. Returns false if the hero has died.
  function monsterHit(m, raw) {
    const evasion = state.hero.evasion + state.hero.tempEvasion;
    if (!lands(m.accuracy, evasion)) { state.log.push(`${m.name} misses.`); return true; }
    const absorbed = Math.min(state.hero.block, raw);
    state.hero.block -= absorbed;
    const dmg = raw - absorbed;
    state.hero.life = Math.max(0, state.hero.life - dmg);
    state.log.push(`${m.name} hits Hero for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}.`);
    if (m.leech && dmg > 0) { m.hp = Math.min(m.maxHp, m.hp + dmg); state.log.push(`${m.name} leeches ${dmg}.`); }
    return state.hero.life > 0;
  }

  function endTurn() {
    if (state.over) return;
    while (state.hand.length) state.discardPile.push(state.hand.pop());
    for (const m of state.lane) {
      if (m.hp <= 0 || !m.intent) continue;
      if (m.intent.type === 'attack') {
        const times = m.intent.times || 1;
        for (let t = 0; t < times; t++) {
          if (!monsterHit(m, m.intent.value)) { finish('lose'); return; }
        }
      } else if (m.intent.type === 'mend') {
        const allies = woundedAllies(m).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp));
        if (allies.length) {
          const target = allies[0];
          const before = target.hp;
          target.hp = Math.min(target.maxHp, target.hp + m.intent.value);
          state.log.push(`${m.name} mends ${target.name} +${target.hp - before}.`);
        }
      }
    }
    startTurn();
  }

  // Flee: every living monster gets ONE parting swing; if you survive you escape
  // the fight (result 'fled') — but you gain nothing from it (no loot). If the
  // parting blows kill you, it's a loss.
  function flee() {
    if (state.over) return { result: state.result };
    for (const m of living()) {
      if (!monsterHit(m, m.attack)) { finish('lose'); return { result: 'lose' }; }
    }
    finish('fled');
    return { result: 'fled' };
  }

  function finish(result) {
    state.over = true;
    state.result = result;
    state.log.push(result === 'win' ? 'Victory.' : result === 'fled' ? 'You break away.' : 'You have died.');
  }

  function getState() {
    return {
      hero: { ...state.hero },
      lane: state.lane.map((m) => ({ ...m })),
      hand: state.hand.map((id) => ({ ...CARDS[id] })),
      drawCount: state.drawPile.length,
      discardCount: state.discardPile.length,
      turn: state.turn,
      xpEarned: state.xpEarned,
      over: state.over,
      result: state.result,
      log: state.log.slice(),
    };
  }

  startTurn();
  return { playCard, endTurn, flee, getState };
}
