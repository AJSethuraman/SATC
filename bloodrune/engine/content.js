// Content tables for the M1 tracer bullet — deliberately tiny and curated.
// Everything here is plain data; the rules that consume it live in combat.js /
// game.js. Later slices grow these tables (more classes, the full rarity
// ladder, sockets/runewords, monster affixes) without changing the engine shape.

// ---- Cards ----------------------------------------------------------------
// A card is data; combat.js interprets `effect`. Types: 'attack' | 'skill'.
// `target: 'front'` hits the front (index 0) living monster; 'aoe' hits all.
export const CARDS = {
  strike: { id: 'strike', name: 'Strike', type: 'attack', cost: 1, target: 'front', damage: 6,
    text: 'Deal 6 damage.' },
  bash: { id: 'bash', name: 'Bash', type: 'attack', cost: 1, target: 'front', damage: 4, block: 3,
    text: 'Deal 4 damage. Gain 3 Block.' },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 1, block: 6,
    text: 'Gain 6 Block.' },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', cost: 2, target: 'aoe', damage: 5,
    text: 'Deal 5 damage to ALL enemies.' },
  // Weapon-granted cards (proof of the gear->deck seam):
  rend: { id: 'rend', name: 'Rend', type: 'attack', cost: 1, target: 'front', damage: 10,
    text: 'Deal 10 damage.' },
  whirlwind: { id: 'whirlwind', name: 'Whirlwind', type: 'attack', cost: 2, target: 'aoe', damage: 7,
    text: 'Deal 7 damage to ALL enemies.' },
};

// ---- Items ----------------------------------------------------------------
// M1 items only carry `grants.cards`. Slice 4 adds rarity/affixes/passives.
// Equipping a weapon rebuilds the deck (see game.deriveDeck).
export const ITEMS = {
  worn_axe: { id: 'worn_axe', name: 'Worn Axe', slot: 'weapon',
    grants: { cards: ['strike', 'strike'] }, text: 'Grants 2x Strike.' },
  rusted_hatchet: { id: 'rusted_hatchet', name: 'Rusted Hatchet of Rending', slot: 'weapon',
    grants: { cards: ['strike', 'rend'] }, text: 'Grants Strike + Rend.' },
  bloodied_cleaver: { id: 'bloodied_cleaver', name: 'Bloodied Cleaver', slot: 'weapon',
    grants: { cards: ['strike', 'whirlwind'] }, text: 'Grants Strike + Whirlwind.' },
};

// The loot table the M1 fight rolls from on victory (seeded).
export const M1_DROP_TABLE = ['rusted_hatchet', 'bloodied_cleaver'];

// ---- Monsters -------------------------------------------------------------
// AI for M1 is simple + telegraphed: each monster commits an intent a turn
// ahead. `attack` is its base hit. Kept deterministic; variety comes later.
export const MONSTERS = {
  fallen: { id: 'fallen', name: 'Fallen', hp: 10, attack: 4, glyph: '👺' },
  skeleton: { id: 'skeleton', name: 'Skeleton Archer', hp: 14, attack: 6, glyph: '💀' },
  ghoul: { id: 'ghoul', name: 'Ghoul', hp: 22, attack: 8, glyph: '🧟' },
};

// The single-lane pack for the M1 fight.
export const M1_PACK = ['fallen', 'skeleton', 'ghoul'];

// ---- Classes --------------------------------------------------------------
// M1 ships the Barbarian only. `baseCards` are the class's innate skills; the
// equipped weapon adds the rest. Barbarian is the "focus" pole (see PRD).
export const CLASSES = {
  barbarian: {
    id: 'barbarian',
    name: 'Barbarian',
    glyph: '🪓',
    maxLife: 60,
    maxMana: 3,
    handSize: 5,
    startingWeapon: 'worn_axe',
    baseCards: ['bash', 'guard', 'guard', 'cleave'],
  },
};
