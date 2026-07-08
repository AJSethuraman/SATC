// Content tables. Still curated, but "M1.5" deepens the tracer toward the
// Diablo fantasy: a real Mana pool, targetable attacks, the full equipment slot
// set, and items that grant passives and/or skill cards. Rules that consume this
// live in combat.js / game.js. Later slices add the rarity ladder, affixes,
// sockets/runewords, monster affixes, and the other classes.

// ---- Cards ----------------------------------------------------------------
// type: 'attack' | 'skill'. target 'front' hits ONE monster (the focused one,
// or the front if none focused); 'aoe' hits all. `refund` gives Mana back
// (pool feel). Costs are scaled to a ~10+ Mana pool so you play several a turn.
export const CARDS = {
  strike: { id: 'strike', name: 'Strike', type: 'attack', cost: 3, target: 'single', damage: 7,
    text: 'Deal 7 to a target.' },
  bash: { id: 'bash', name: 'Bash', type: 'attack', cost: 2, target: 'single', damage: 4, block: 3,
    text: 'Deal 4 to a target. Gain 3 Block.' },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 3, block: 8,
    text: 'Gain 8 Block.' },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', cost: 5, target: 'aoe', damage: 6,
    text: 'Deal 6 to ALL enemies.' },
  rend: { id: 'rend', name: 'Rend', type: 'attack', cost: 4, target: 'single', damage: 12,
    text: 'Deal 12 to a target.' },
  whirlwind: { id: 'whirlwind', name: 'Whirlwind', type: 'attack', cost: 6, target: 'aoe', damage: 8,
    text: 'Deal 8 to ALL enemies.' },
  frenzy: { id: 'frenzy', name: 'Frenzy', type: 'attack', cost: 3, target: 'single', damage: 6, refund: 2,
    text: 'Deal 6 to a target. Refund 2 Mana.' },
  warcry: { id: 'warcry', name: 'War Cry', type: 'skill', cost: 4, block: 10, refund: 1,
    text: 'Gain 10 Block. Refund 1 Mana.' },
};

// ---- Items ----------------------------------------------------------------
// slot: which equipment slot. rings use slot 'ring' (either ring finger).
// grants.cards -> cards added to the deck. passive -> stat bonuses:
//   maxLife, maxMana, startBlock (standing Block gained at the start of each turn).
export const ITEMS = {
  // weapons (define your attacks)
  worn_axe: { id: 'worn_axe', name: 'Worn Axe', slot: 'weapon',
    grants: { cards: ['strike', 'strike'] }, text: 'Grants 2× Strike.' },
  rusted_hatchet: { id: 'rusted_hatchet', name: 'Rusted Hatchet of Rending', slot: 'weapon',
    grants: { cards: ['strike', 'rend'] }, text: 'Grants Strike + Rend.' },
  bloodied_cleaver: { id: 'bloodied_cleaver', name: 'Bloodied Cleaver', slot: 'weapon',
    grants: { cards: ['strike', 'whirlwind'] }, text: 'Grants Strike + Whirlwind.' },
  skullsplitter: { id: 'skullsplitter', name: 'Skullsplitter', slot: 'weapon',
    grants: { cards: ['frenzy', 'rend'] }, passive: { maxLife: 4 }, text: 'Grants Frenzy + Rend. +4 Life.' },
  // off-hand (utility / a skill)
  cracked_buckler: { id: 'cracked_buckler', name: 'Cracked Buckler', slot: 'offhand',
    passive: { startBlock: 3, maxLife: 5 }, text: '+3 Block each turn. +5 Life.' },
  grim_fetish: { id: 'grim_fetish', name: 'Grim Fetish', slot: 'offhand',
    grants: { cards: ['warcry'] }, passive: { maxMana: 1 }, text: 'Grants War Cry. +1 Mana.' },
  // helm
  horned_helm: { id: 'horned_helm', name: 'Horned Helm', slot: 'helm',
    passive: { maxLife: 10 }, text: '+10 Life.' },
  berserker_mask: { id: 'berserker_mask', name: 'Berserker Mask', slot: 'helm',
    grants: { cards: ['frenzy'] }, passive: { maxMana: 2 }, text: 'Grants Frenzy. +2 Mana.' },
  // body
  chainmail: { id: 'chainmail', name: 'Rusted Chainmail', slot: 'body',
    passive: { maxLife: 14, startBlock: 1 }, text: '+14 Life. +1 Block each turn.' },
  // gloves / boots / belt
  reaver_gloves: { id: 'reaver_gloves', name: 'Reaver Gloves', slot: 'gloves',
    passive: { maxMana: 2 }, text: '+2 Mana.' },
  iron_greaves: { id: 'iron_greaves', name: 'Iron Greaves', slot: 'boots',
    passive: { maxLife: 6, startBlock: 1 }, text: '+6 Life. +1 Block each turn.' },
  leather_sash: { id: 'leather_sash', name: 'Leather Sash', slot: 'belt',
    passive: { maxLife: 6 }, text: '+6 Life.' },
  // jewelry
  bone_amulet: { id: 'bone_amulet', name: 'Bone Amulet', slot: 'amulet',
    passive: { maxMana: 3 }, text: '+3 Mana.' },
  sigil_of_wrath: { id: 'sigil_of_wrath', name: 'Sigil of Wrath', slot: 'amulet',
    passive: { plusSkills: 2, maxMana: 1 }, text: '+2 to Skills (card damage). +1 Mana.' },
  iron_band: { id: 'iron_band', name: 'Iron Band', slot: 'ring',
    passive: { maxLife: 5 }, text: '+5 Life.' },
  bloodstone_ring: { id: 'bloodstone_ring', name: 'Bloodstone Ring', slot: 'ring',
    passive: { maxMana: 1, startBlock: 1 }, text: '+1 Mana. +1 Block each turn.' },
};

// Equipment slot layout (the paper-doll). Two ring fingers.
export const SLOTS = ['weapon', 'offhand', 'helm', 'body', 'gloves', 'boots', 'belt', 'amulet', 'ring1', 'ring2'];
export const SLOT_LABEL = {
  weapon: 'Weapon', offhand: 'Off-hand', helm: 'Helm', body: 'Body', gloves: 'Gloves',
  boots: 'Boots', belt: 'Belt', amulet: 'Amulet', ring1: 'Ring', ring2: 'Ring',
};

// Loot table the M1 fight rolls from on victory (into the bag, not auto-equipped).
export const M1_DROP_TABLE = [
  'rusted_hatchet', 'bloodied_cleaver', 'skullsplitter', 'berserker_mask',
  'chainmail', 'cracked_buckler', 'bone_amulet', 'bloodstone_ring', 'sigil_of_wrath',
];

// ---- Monsters -------------------------------------------------------------
// A curated but varied bestiary. `role: 'healer'` monsters (the Fallen Shaman)
// support their pack instead of only attacking — kill them first. Packs are
// built by the seeded encounter generator (encounters.js).
export const MONSTERS = {
  fallen: { id: 'fallen', name: 'Fallen', hp: 8, attack: 3, glyph: '👺' },
  fallen_shaman: { id: 'fallen_shaman', name: 'Fallen Shaman', hp: 16, attack: 3, glyph: '🧙',
    role: 'healer', heal: 4 },
  zombie: { id: 'zombie', name: 'Zombie', hp: 16, attack: 4, glyph: '🧟' },
  skeleton: { id: 'skeleton', name: 'Skeleton', hp: 14, attack: 5, glyph: '💀' },
  skeleton_archer: { id: 'skeleton_archer', name: 'Skeleton Archer', hp: 11, attack: 6, glyph: '🏹' },
  goatman: { id: 'goatman', name: 'Goatman', hp: 18, attack: 6, glyph: '🐐' },
  ghoul: { id: 'ghoul', name: 'Ghoul', hp: 24, attack: 7, glyph: '👹' },
};

// ---- Packs ----------------------------------------------------------------
// D2-style: a pack is mostly homogeneous, sometimes with a leader/support at
// the back. filler = [[monsterId, minCount, maxCount], ...] rolled per fight;
// the encounter generator (encounters.js) may also drag in a second pack.
export const PACKS = {
  fallen_camp: { name: 'Fallen Camp', leader: 'fallen_shaman', filler: [['fallen', 2, 3]] },
  bone_host: { name: 'Bone Host', filler: [['skeleton', 1, 2], ['skeleton_archer', 1, 2]] },
  rotting_pit: { name: 'Rotting Pit', filler: [['zombie', 1, 2], ['ghoul', 0, 1]] },
  goat_warren: { name: 'Goat Warren', filler: [['goatman', 1, 2]] },
};

// ---- Classes --------------------------------------------------------------
export const CLASSES = {
  barbarian: {
    id: 'barbarian',
    name: 'Barbarian',
    glyph: '🪓',
    maxLife: 64,
    maxMana: 10, // a real pool; gear pushes it higher
    handSize: 5,
    startBlock: 0,
    startingWeapon: 'worn_axe',
    baseCards: ['bash', 'guard', 'guard', 'cleave'],
    // A little starter loot in the bag so opening the inventory is rewarding.
    startingBag: ['rusted_hatchet', 'horned_helm', 'reaver_gloves', 'grim_fetish', 'iron_band'],
  },
};
