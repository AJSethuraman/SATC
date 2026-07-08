// Combat state machine (M1.5): one lane, a real Mana pool, TARGETABLE single
// attacks, telegraphed monsters, Hero Life, standing Block from armor, and a
// +to-Skills damage bonus from gear. Pure engine — NO DOM, NO Math.random (all
// randomness comes from the injected seeded rng).
//
// Turn shape (this is what makes intents "telegraphed a turn ahead"):
//   startTurn(): set Block to the hero's standing Block, refill Mana, draw to
//                hand size, then roll each living monster's intent for the
//                UPCOMING enemy phase.
//   player plays cards (killing a monster cancels its telegraphed intent)
//   endTurn(): living monsters execute their already-shown intent -> resolve
//              damage to Hero (Block absorbs first) -> check win/lose -> if the
//              fight continues, startTurn() again (new telegraphs).

import { CARDS, MONSTERS } from './content.js';

export function createCombat({ deck, hero, pack, rng }) {
  const state = {
    hero: {
      name: hero.name,
      glyph: hero.glyph,
      life: hero.maxLife,
      maxLife: hero.maxLife,
      block: 0,
      startBlock: hero.startBlock || 0,
      mana: hero.maxMana,
      maxMana: hero.maxMana,
      handSize: hero.handSize,
      plusSkills: hero.plusSkills || 0, // flat bonus to card damage (+to Skills)
    },
    lane: pack.map((id) => {
      const m = MONSTERS[id];
      return { index: 0, id: m.id, name: m.name, glyph: m.glyph, hp: m.hp, maxHp: m.hp,
        attack: m.attack, role: m.role || 'attacker', heal: m.heal || 0, intent: null };
    }),
    drawPile: rng.shuffle(deck),
    hand: [],
    discardPile: [],
    turn: 0,
    over: false,
    result: null, // 'win' | 'lose'
    log: [],
  };
  // stable lane indices for targeting
  state.lane.forEach((m, i) => { m.index = i; });

  const living = () => state.lane.filter((m) => m.hp > 0);
  const front = () => state.lane.find((m) => m.hp > 0) || null;

  function drawOne() {
    if (state.drawPile.length === 0) {
      if (state.discardPile.length === 0) return;
      state.drawPile = rng.shuffle(state.discardPile);
      state.discardPile = [];
    }
    state.hand.push(state.drawPile.pop());
  }

  function woundedAllies(self) {
    return living().filter((a) => a !== self && a.hp < a.maxHp);
  }

  function telegraph() {
    for (const m of state.lane) {
      if (m.hp <= 0) { m.intent = null; continue; }
      // Support monsters (Fallen Shaman) mend a wounded ally instead of hitting;
      // if nothing needs healing, they attack. This is why you target them first.
      if (m.role === 'healer' && woundedAllies(m).length > 0) {
        m.intent = { type: 'mend', value: m.heal };
      } else {
        m.intent = { type: 'attack', value: m.attack };
      }
    }
  }

  function startTurn() {
    state.turn += 1;
    state.hero.block = state.hero.startBlock; // standing Block from armor
    state.hero.mana = state.hero.maxMana;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) {
      drawOne();
    }
    telegraph();
    state.log.push(`— Turn ${state.turn} —`);
  }

  function hurt(m, amount) {
    m.hp = Math.max(0, m.hp - amount);
    if (m.hp === 0) { m.intent = null; state.log.push(`${m.name} dies.`); }
  }

  // targetIndex: which monster a single-target card hits. Falls back to the
  // front living monster when omitted or when the chosen target is dead.
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
      if (card.target === 'aoe') {
        for (const m of living()) hurt(m, dmg);
      } else {
        let target = null;
        if (Number.isInteger(targetIndex)) {
          const chosen = state.lane[targetIndex];
          if (chosen && chosen.hp > 0) target = chosen;
        }
        if (!target) target = front();
        if (target) hurt(target, dmg);
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
        const raw = m.intent.value;
        const absorbed = Math.min(state.hero.block, raw);
        state.hero.block -= absorbed;
        const dmg = raw - absorbed;
        state.hero.life = Math.max(0, state.hero.life - dmg);
        state.log.push(`${m.name} hits Hero for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}.`);
      } else if (m.intent.type === 'mend') {
        // heal the most-wounded living ally (never itself)
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
