// Combat state machine for the M1 tracer bullet: one lane, Mana, a card hand,
// telegraphed monsters, Hero Life. Pure engine — NO DOM, NO Math.random (all
// randomness comes from the injected seeded rng). The UI reads getState() and
// calls playCard/endTurn; tests drive the same surface with a fixed seed.
//
// Turn shape (this is what makes intents "telegraphed a turn ahead"):
//   startTurn(): reset Block, refill Mana, draw to hand size, then roll each
//                living monster's intent for the UPCOMING enemy phase.
//   player plays cards (killing a monster cancels its telegraphed intent)
//   endTurn(): living monsters execute their already-shown intent -> resolve
//              damage to Hero (Block absorbs first) -> check win/lose ->
//              if the fight continues, startTurn() again (new telegraphs).

import { CARDS, MONSTERS } from './content.js';

export function createCombat({ deck, hero, pack, rng }) {
  const state = {
    hero: {
      name: hero.name,
      glyph: hero.glyph,
      life: hero.maxLife,
      maxLife: hero.maxLife,
      block: 0,
      mana: hero.maxMana,
      maxMana: hero.maxMana,
      handSize: hero.handSize,
    },
    lane: pack.map((id) => {
      const m = MONSTERS[id];
      return { id: m.id, name: m.name, glyph: m.glyph, hp: m.hp, maxHp: m.hp,
        attack: m.attack, intent: null };
    }),
    drawPile: rng.shuffle(deck),
    hand: [],
    discardPile: [],
    turn: 0,
    over: false,
    result: null, // 'win' | 'lose'
    log: [],
  };

  function livingMonsters() {
    return state.lane.filter((m) => m.hp > 0);
  }

  function frontMonster() {
    return state.lane.find((m) => m.hp > 0) || null;
  }

  function drawOne() {
    if (state.drawPile.length === 0) {
      if (state.discardPile.length === 0) return; // deck exhausted
      state.drawPile = rng.shuffle(state.discardPile);
      state.discardPile = [];
    }
    state.hand.push(state.drawPile.pop());
  }

  // Roll the intent each living monster will act on next enemy phase.
  function telegraph() {
    for (const m of state.lane) {
      if (m.hp <= 0) { m.intent = null; continue; }
      // M1 AI: commit to a straight attack for the monster's base value.
      m.intent = { type: 'attack', value: m.attack };
    }
  }

  function startTurn() {
    state.turn += 1;
    state.hero.block = 0;
    state.hero.mana = state.hero.maxMana;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) {
      drawOne();
    }
    telegraph();
    state.log.push(`— Turn ${state.turn} —`);
  }

  function dealToMonster(m, amount) {
    m.hp = Math.max(0, m.hp - amount);
    if (m.hp === 0) { m.intent = null; state.log.push(`${m.name} dies.`); }
  }

  function playCard(handIndex, _targetIndex) {
    if (state.over) return { ok: false, reason: 'combat is over' };
    const cardId = state.hand[handIndex];
    if (cardId == null) return { ok: false, reason: 'no such card' };
    const card = CARDS[cardId];
    if (card.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };

    state.hero.mana -= card.cost;
    if (card.block) state.hero.block += card.block;
    if (card.damage) {
      if (card.target === 'aoe') {
        for (const m of livingMonsters()) dealToMonster(m, card.damage);
      } else {
        const target = frontMonster();
        if (target) dealToMonster(target, card.damage);
      }
    }
    state.log.push(`Play ${card.name}.`);
    // move card to discard
    state.hand.splice(handIndex, 1);
    state.discardPile.push(cardId);

    if (livingMonsters().length === 0) finish('win');
    return { ok: true };
  }

  function endTurn() {
    if (state.over) return;
    // discard the rest of the hand (classic deckbuilder rule)
    while (state.hand.length) state.discardPile.push(state.hand.pop());
    // enemy phase: each living monster executes its telegraphed intent
    for (const m of state.lane) {
      if (m.hp <= 0 || !m.intent) continue;
      if (m.intent.type === 'attack') {
        const raw = m.intent.value;
        const absorbed = Math.min(state.hero.block, raw);
        state.hero.block -= absorbed;
        const dmg = raw - absorbed;
        state.hero.life = Math.max(0, state.hero.life - dmg);
        state.log.push(`${m.name} hits Hero for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}.`);
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
    // Return a shallow-cloned, read-only-ish view for the UI/tests.
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

  // Kick off the first turn (draws + first telegraph).
  startTurn();

  return { playCard, endTurn, getState };
}
