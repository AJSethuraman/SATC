// Content tables. "Swarm" pass: you fight LARGE packs and are surrounded —
// everything swings each turn, so AoE and Accuracy matter. Accuracy is a
// per-attacker hit chance (attacker-driven avoidance): low-accuracy attackers
// miss, and that applies to monsters hitting you AND you hitting them. Cards
// carry an `acc` modifier — Smite-type hits are reliable, Zeal-type sweeps are
// less accurate. Non-punitive base; you stack Accuracy on gear to land heavy
// hits. Rules that consume this live in combat.js / game.js / encounters.js.

// ---- Cards ----------------------------------------------------------------
// type: 'attack' | 'skill'. target 'single' hits the focused/front monster;
// 'aoe' hits all. `acc` = accuracy modifier vs the hero's base Accuracy.
// `refund` gives Mana back. Costs scaled to a ~10+ Mana pool.
export const CARDS = {
  strike: { id: 'strike', name: 'Strike', type: 'attack', cost: 3, target: 'single', damage: 7, acc: 0,
    text: 'Deal 7 to a target.' },
  bash: { id: 'bash', name: 'Bash', type: 'attack', cost: 2, target: 'single', damage: 4, block: 3, acc: 0,
    text: 'Deal 4 to a target. Gain 3 Block.' },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 3, block: 8,
    text: 'Gain 8 Block.' },
  smite: { id: 'smite', name: 'Smite', type: 'attack', cost: 3, target: 'single', damage: 9, acc: 12,
    text: 'Deal 9 to a target. Very accurate.' },
  zeal: { id: 'zeal', name: 'Zeal', type: 'attack', cost: 4, target: 'aoe', damage: 4, acc: -12,
    text: 'Deal 4 to ALL enemies. Wild swings (less accurate).' },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', cost: 4, target: 'aoe', damage: 6, acc: -6,
    text: 'Deal 6 to ALL enemies.' },
  rend: { id: 'rend', name: 'Rend', type: 'attack', cost: 4, target: 'single', damage: 12, acc: -4,
    text: 'Deal 12 to a target.' },
  whirlwind: { id: 'whirlwind', name: 'Whirlwind', type: 'attack', cost: 6, target: 'aoe', damage: 9, acc: -16,
    text: 'Deal 9 to ALL enemies. Reckless (much less accurate).' },
  frenzy: { id: 'frenzy', name: 'Frenzy', type: 'attack', cost: 3, target: 'single', damage: 6, refund: 2, acc: 0,
    text: 'Deal 6 to a target. Refund 2 Mana.' },
  warcry: { id: 'warcry', name: 'War Cry', type: 'skill', cost: 4, block: 10, refund: 1,
    text: 'Gain 10 Block. Refund 1 Mana.' },
};

// ---- Items ----------------------------------------------------------------
// grants.cards -> deck; passive -> stat mods (maxLife, maxMana, startBlock,
// plusSkills, accuracy). rings use slot 'ring'.
export const ITEMS = {
  worn_axe: { id: 'worn_axe', name: 'Worn Axe', slot: 'weapon',
    grants: { cards: ['strike', 'strike'] }, text: 'Grants 2× Strike.' },
  rusted_hatchet: { id: 'rusted_hatchet', name: 'Rusted Hatchet of Rending', slot: 'weapon',
    grants: { cards: ['strike', 'rend'] }, text: 'Grants Strike + Rend.' },
  bloodied_cleaver: { id: 'bloodied_cleaver', name: 'Bloodied Cleaver', slot: 'weapon',
    grants: { cards: ['cleave', 'whirlwind'] }, text: 'Grants Cleave + Whirlwind (sweeper).' },
  war_maul: { id: 'war_maul', name: 'War Maul of Smiting', slot: 'weapon',
    grants: { cards: ['smite', 'rend'] }, passive: { accuracy: 6 }, text: 'Grants Smite + Rend. +6 Accuracy.' },
  skullsplitter: { id: 'skullsplitter', name: 'Skullsplitter', slot: 'weapon',
    grants: { cards: ['frenzy', 'zeal'] }, passive: { maxLife: 4 }, text: 'Grants Frenzy + Zeal. +4 Life.' },
  cracked_buckler: { id: 'cracked_buckler', name: 'Cracked Buckler', slot: 'offhand',
    passive: { startBlock: 3, maxLife: 5 }, text: '+3 Block each turn. +5 Life.' },
  grim_fetish: { id: 'grim_fetish', name: 'Grim Fetish', slot: 'offhand',
    grants: { cards: ['warcry'] }, passive: { maxMana: 1 }, text: 'Grants War Cry. +1 Mana.' },
  horned_helm: { id: 'horned_helm', name: 'Horned Helm', slot: 'helm',
    passive: { maxLife: 10 }, text: '+10 Life.' },
  hunters_hood: { id: 'hunters_hood', name: "Hunter's Hood", slot: 'helm',
    passive: { accuracy: 10 }, text: '+10 Accuracy.' },
  berserker_mask: { id: 'berserker_mask', name: 'Berserker Mask', slot: 'helm',
    grants: { cards: ['frenzy'] }, passive: { maxMana: 2 }, text: 'Grants Frenzy. +2 Mana.' },
  chainmail: { id: 'chainmail', name: 'Rusted Chainmail', slot: 'body',
    passive: { maxLife: 14, startBlock: 1 }, text: '+14 Life. +1 Block each turn.' },
  reaver_gloves: { id: 'reaver_gloves', name: 'Reaver Gloves', slot: 'gloves',
    passive: { maxMana: 2, accuracy: 6 }, text: '+2 Mana. +6 Accuracy.' },
  iron_greaves: { id: 'iron_greaves', name: 'Iron Greaves', slot: 'boots',
    passive: { maxLife: 6, startBlock: 1 }, text: '+6 Life. +1 Block each turn.' },
  leather_sash: { id: 'leather_sash', name: 'Leather Sash', slot: 'belt',
    passive: { maxLife: 6 }, text: '+6 Life.' },
  bone_amulet: { id: 'bone_amulet', name: 'Bone Amulet', slot: 'amulet',
    passive: { maxMana: 3 }, text: '+3 Mana.' },
  sigil_of_wrath: { id: 'sigil_of_wrath', name: 'Sigil of Wrath', slot: 'amulet',
    passive: { plusSkills: 2, maxMana: 1 }, text: '+2 to Skills (card damage). +1 Mana.' },
  iron_band: { id: 'iron_band', name: 'Iron Band', slot: 'ring',
    passive: { maxLife: 5 }, text: '+5 Life.' },
  hunters_band: { id: 'hunters_band', name: "Hunter's Band", slot: 'ring',
    passive: { accuracy: 8 }, text: '+8 Accuracy.' },
  bloodstone_ring: { id: 'bloodstone_ring', name: 'Bloodstone Ring', slot: 'ring',
    passive: { maxMana: 1, startBlock: 1 }, text: '+1 Mana. +1 Block each turn.' },
};

export const SLOTS = ['weapon', 'offhand', 'helm', 'body', 'gloves', 'boots', 'belt', 'amulet', 'ring1', 'ring2'];
export const SLOT_LABEL = {
  weapon: 'Weapon', offhand: 'Off-hand', helm: 'Helm', body: 'Body', gloves: 'Gloves',
  boots: 'Boots', belt: 'Belt', amulet: 'Amulet', ring1: 'Ring', ring2: 'Ring',
};

export const M1_DROP_TABLE = [
  'rusted_hatchet', 'bloodied_cleaver', 'war_maul', 'skullsplitter', 'berserker_mask',
  'chainmail', 'cracked_buckler', 'bone_amulet', 'sigil_of_wrath', 'hunters_hood', 'hunters_band',
];

// ---- Monsters -------------------------------------------------------------
// `accuracy` = this monster's chance to land its hit on you (attacker-driven
// avoidance). Relentless undead (skeleton, ghoul) rarely miss; clumsy things
// (zombie, fallen) miss more. `role: 'healer'` = supports its pack (mend).
export const MONSTERS = {
  fallen: { id: 'fallen', name: 'Fallen', hp: 8, attack: 3, accuracy: 80, xp: 4, glyph: '👺' },
  fallen_shaman: { id: 'fallen_shaman', name: 'Fallen Shaman', hp: 16, attack: 4, accuracy: 80,
    role: 'healer', heal: 4, xp: 10, glyph: '🧙' },
  zombie: { id: 'zombie', name: 'Zombie', hp: 18, attack: 4, accuracy: 65, xp: 7, glyph: '🧟' },
  skeleton: { id: 'skeleton', name: 'Skeleton', hp: 14, attack: 5, accuracy: 100, xp: 6, glyph: '💀' },
  skeleton_archer: { id: 'skeleton_archer', name: 'Skeleton Archer', hp: 11, attack: 6, accuracy: 90, xp: 6, glyph: '🏹' },
  goatman: { id: 'goatman', name: 'Goatman', hp: 18, attack: 6, accuracy: 85, xp: 9, glyph: '🐐' },
  ghoul: { id: 'ghoul', name: 'Ghoul', hp: 26, attack: 7, accuracy: 100, xp: 12, glyph: '👹' },
  // Act boss.
  the_smith: { id: 'the_smith', name: 'The Flayed Smith', hp: 120, attack: 12, accuracy: 90, xp: 60, glyph: '🔨' },
};

// Elite monster affixes (D2 boss-pack modifiers) applied by the encounter/run
// layer. Each tweaks an elite's stats/behaviour. Curated for the current combat.
export const ELITE_AFFIXES = {
  frenzied: { id: 'frenzied', name: 'Frenzied', mods: { extraAttack: true }, glyph: '💢',
    text: 'Attacks twice.' },
  brutal: { id: 'brutal', name: 'Brutal', mods: { attackMul: 1.6 }, glyph: '🩸',
    text: 'Hits much harder.' },
  hardened: { id: 'hardened', name: 'Hardened', mods: { hpMul: 1.8 }, glyph: '🛡️',
    text: 'Far tougher.' },
  unerring: { id: 'unerring', name: 'Unerring', mods: { accuracy: 100 }, glyph: '🎯',
    text: 'Never misses.' },
  vampiric: { id: 'vampiric', name: 'Vampiric', mods: { leech: true }, glyph: '🦇',
    text: 'Heals when it hits you.' },
};

// Level-up option pool. Each option either adds a card to the deck or grants a
// permanent run stat (build-crafting between fights). The run offers 3 random
// distinct options per level.
export const LEVELUP_OPTIONS = [
  { id: 'card_smite', kind: 'card', card: 'smite', name: 'Learn Smite', text: 'Add Smite (accurate single hit) to your deck.' },
  { id: 'card_rend', kind: 'card', card: 'rend', name: 'Learn Rend', text: 'Add Rend (heavy single hit) to your deck.' },
  { id: 'card_zeal', kind: 'card', card: 'zeal', name: 'Learn Zeal', text: 'Add Zeal (wide sweep) to your deck.' },
  { id: 'card_cleave', kind: 'card', card: 'cleave', name: 'Learn Cleave', text: 'Add Cleave (AoE) to your deck.' },
  { id: 'card_frenzy', kind: 'card', card: 'frenzy', name: 'Learn Frenzy', text: 'Add Frenzy (refunds Mana) to your deck.' },
  { id: 'card_warcry', kind: 'card', card: 'warcry', name: 'Learn War Cry', text: 'Add War Cry (big Block) to your deck.' },
  { id: 'stat_skills', kind: 'stat', mod: { plusSkills: 1 }, name: '+1 to Skills', text: 'All your cards deal +1.' },
  { id: 'stat_life', kind: 'stat', mod: { maxLife: 10 }, name: 'Toughness', text: '+10 max Life.' },
  { id: 'stat_mana', kind: 'stat', mod: { maxMana: 1 }, name: 'Focus', text: '+1 max Mana.' },
  { id: 'stat_block', kind: 'stat', mod: { startBlock: 2 }, name: 'Bulwark', text: '+2 Block each turn.' },
  { id: 'stat_acc', kind: 'stat', mod: { accuracy: 6 }, name: 'Precision', text: '+6 Accuracy.' },
];

// ---- Packs (LARGE, D2-style) ----------------------------------------------
// filler = [[monsterId, minCount, maxCount], ...] rolled per fight; a leader
// (support) sits at the back. The encounter generator may drag in a 2nd pack.
export const PACKS = {
  fallen_camp: { name: 'Fallen Camp', leader: 'fallen_shaman', filler: [['fallen', 4, 6]] },
  bone_host: { name: 'Bone Host', filler: [['skeleton', 2, 3], ['skeleton_archer', 2, 3]] },
  rotting_pit: { name: 'Rotting Pit', filler: [['zombie', 3, 5], ['ghoul', 1, 2]] },
  goat_warren: { name: 'Goat Warren', filler: [['goatman', 3, 5]] },
};

// The act boss encounter.
export const BOSS_PACK = ['the_smith'];

// ---- Loot generation tables (random rarity + affixes) ---------------------
// Item bases per slot. Weapon bases grant a starting card; everything else is
// a pure affix carrier. The loot generator (loot.js) rolls rarity + affixes.
export const BASES = {
  weapon: [
    { base: 'Hand Axe', card: 'strike' }, { base: 'Short Sword', card: 'strike' },
    { base: 'War Maul', card: 'smite' }, { base: 'Battle Cleaver', card: 'cleave' },
    { base: 'Halberd', card: 'rend' },
  ],
  offhand: [{ base: 'Buckler' }, { base: 'Kite Shield' }, { base: 'Bone Charm' }],
  helm: [{ base: 'Leather Cap' }, { base: 'Iron Helm' }, { base: 'Great Helm' }],
  body: [{ base: 'Quilted Armor' }, { base: 'Chain Mail' }, { base: 'Plate' }],
  gloves: [{ base: 'Leather Gloves' }, { base: 'Gauntlets' }],
  boots: [{ base: 'Boots' }, { base: 'Greaves' }],
  belt: [{ base: 'Sash' }, { base: 'Heavy Belt' }],
  amulet: [{ base: 'Amulet' }, { base: 'Talisman' }],
  ring: [{ base: 'Ring' }, { base: 'Band' }],
};

// Rollable affixes. `mods` use the same additive stat keys as gear passives.
export const PREFIXES = [
  { name: 'Sturdy', mod: { maxLife: 8 } },
  { name: 'Vigorous', mod: { maxLife: 15 } },
  { name: 'Keen', mod: { accuracy: 8 } },
  { name: 'Deadeye', mod: { accuracy: 15 } },
  { name: 'Runed', mod: { maxMana: 2 } },
  { name: 'Cruel', mod: { plusSkills: 2 } },
  { name: 'Warded', mod: { startBlock: 2 } },
  { name: 'Savage', mod: { plusSkills: 1, accuracy: 6 } },
];
export const SUFFIXES = [
  { name: 'of the Bear', mod: { maxLife: 10 } },
  { name: 'of Precision', mod: { accuracy: 10 } },
  { name: 'of the Magi', mod: { maxMana: 2 } },
  { name: 'of Wrath', mod: { plusSkills: 1 } },
  { name: 'of the Turtle', mod: { startBlock: 2 } },
  { name: 'of Fury', mod: { plusSkills: 2 } },
  { name: 'of Warding', mod: { startBlock: 3 } },
];

// Rarity weights (before Magic Find). MF shifts weight toward magic/rare.
export const RARITY = [
  { rarity: 'normal', weight: 40, affixes: 0, color: '#cfcfcf' },
  { rarity: 'magic', weight: 40, affixes: 2, color: '#6f8aff' },
  { rarity: 'rare', weight: 20, affixes: 4, color: '#e5d54a' },
];

// ---- Classes --------------------------------------------------------------
export const CLASSES = {
  barbarian: {
    id: 'barbarian',
    name: 'Barbarian',
    glyph: '🪓',
    maxLife: 82,
    maxMana: 10,
    accuracy: 85, // base hit chance; gear pushes it up (matters for heavy hits)
    handSize: 5,
    startBlock: 0,
    startingWeapon: 'worn_axe',
    // AoE-capable base deck so you can survive being swarmed from turn one.
    baseCards: ['cleave', 'zeal', 'guard', 'guard', 'bash'],
    startingBag: ['bloodied_cleaver', 'war_maul', 'horned_helm', 'reaver_gloves', 'grim_fetish', 'hunters_band'],
  },
};
