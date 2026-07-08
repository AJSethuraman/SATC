// Combat state machine — "Swarm" pass. You are SURROUNDED by a large pack;
// every living monster swings each turn, so AoE and Accuracy matter. Hit
// resolution has two stages:
//   1) attacker Accuracy roll — does the blow land at all? (attacker-driven
//      avoidance: clumsy attackers miss, whether it's a monster hitting you or
//      you hitting a monster)
//   2) defender Evasion roll — a defender's chance to dodge a landed blow. This
//      is 0 for the Barbarian; it's the hook for an Amazon-style dodge class and
//      for evasive enemies (which is what makes YOUR Accuracy matter long-term).
// Pure engine — NO DOM, NO Math.random (all rolls come from the injected rng).
//
// Turn shape (telegraphed a turn ahead): startTurn sets standing Block, refills
// Mana, draws, and rolls each living monster's intent for the UPCOMING phase.

import { CARDS, MONSTERS } from './content.js';

const clampAcc = (a) => Math.max(5, Math.min(100, a));

export function createCombat({ deck, hero, pack, rng }) {
  const state = {
    hero: {
      name: hero.name, glyph: hero.glyph,
      life: hero.maxLife, maxLife: hero.maxLife,
      block: 0, startBlock: hero.startBlock || 0,
      mana: hero.maxMana, maxMana: hero.maxMana,
      handSize: hero.handSize,
      plusSkills: hero.plusSkills || 0,
      accuracy: hero.accuracy != null ? hero.accuracy : 100,
      evasion: hero.evasion || 0, // defender dodge (Amazon hook; 0 for Barbarian)
    },
    lane: pack.map((id, i) => {
      const m = MONSTERS[id];
      return { index: i, id: m.id, name: m.name, glyph: m.glyph, hp: m.hp, maxHp: m.hp,
        attack: m.attack, accuracy: m.accuracy != null ? m.accuracy : 100,
        evasion: m.evasion || 0, role: m.role || 'attacker', heal: m.heal || 0, intent: null };
    }),
    drawPile: rng.shuffle(deck),
    hand: [],
    discardPile: [],
    turn: 0,
    over: false,
    result: null,
    log: [],
  };

  const living = () => state.lane.filter((m) => m.hp > 0);
  const front = () => state.lane.find((m) => m.hp > 0) || null;

  // Two-stage hit resolution. Only consumes the evasion roll when the defender
  // actually has evasion, so rng sequences (and tests) stay stable at evasion 0.
  function lands(accuracy, defenderEvasion) {
    if (rng.next() * 100 >= clampAcc(accuracy)) return false; // missed (inaccurate)
    if (defenderEvasion > 0 && rng.next() * 100 < defenderEvasion) return false; // dodged
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
      else m.intent = { type: 'attack', value: m.attack };
    }
  }

  function startTurn() {
    state.turn += 1;
    state.hero.block = state.hero.startBlock;
    state.hero.mana = state.hero.maxMana;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) drawOne();
    telegraph();
    state.log.push(`— Turn ${state.turn} —`);
  }

  function hurt(m, amount) {
    m.hp = Math.max(0, m.hp - amount);
    if (m.hp === 0) { m.intent = null; state.log.push(`${m.name} dies.`); }
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

    if (card.damage) {
      const dmg = card.damage + state.hero.plusSkills;
      const acc = state.hero.accuracy + (card.acc || 0);
      if (card.target === 'aoe') {
        // each enemy is rolled independently — a wild sweep can miss some
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

  function endTurn() {
    if (state.over) return;
    while (state.hand.length) state.discardPile.push(state.hand.pop());
    for (const m of state.lane) {
      if (m.hp <= 0 || !m.intent) continue;
      if (m.intent.type === 'attack') {
        if (!lands(m.accuracy, state.hero.evasion)) { state.log.push(`${m.name} misses.`); continue; }
        const raw = m.intent.value;
        const absorbed = Math.min(state.hero.block, raw);
        state.hero.block -= absorbed;
        const dmg = raw - absorbed;
        state.hero.life = Math.max(0, state.hero.life - dmg);
        state.log.push(`${m.name} hits Hero for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}.`);
      } else if (m.intent.type === 'mend') {
        const allies = woundedAllies(m).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp));
        if (allies.length) {
          const t = allies[0];
          const before = t.hp;
          t.hp = Math.min(t.maxHp, t.hp + m.intent.value);
          state.log.push(`${m.name} mends ${t.name} +${t.hp - before}.`);
        }
      }
    }
    if (state.hero.life <= 0) { finish('lose'); return; }
    startTurn();
  }

  function finish(result) {
    state.over = true;
    state.result = result;
    state.log.push(result === 'win' ? 'Victory.' : 'You have died.');
  }

  function getState() {
    return {
      hero: { ...state.hero },
      lane: state.lane.map((m) => ({ ...m })),
      hand: state.hand.map((id) => ({ ...CARDS[id] })),
      drawCount: state.drawPile.length,
      discardCount: state.discardPile.length,
      turn: state.turn,
      over: state.over,
      result: state.result,
      log: state.log.slice(),
    };
  }

  startTurn();
  return { playCard, endTurn, getState };
}
