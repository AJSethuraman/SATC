// Bloodrune content — ABILITIES model. Combat is surrounded (inner/outer rings),
// you use always-available skills (no cards) that scale by level and roll damage
// in ranges. You start NAKED — a weapon that grants ONE skill plus a basic Guard
// — and scale via XP -> levels -> skill points (learn/level skills in the tree)
// and loot. Rules live in combat.js / game.js. Loot bases/affixes are in loot.js.

// ---- Skills (abilities) ----------------------------------------------------
// type: 'attack' | 'skill' | 'breakthrough' | 'summon'
// target: 'single' | 'aoe'   reach: 0 = inner ring only, 1 = reaches the outer ring
// scale: 'damage' (dmg:[min,max], grow) | 'hits' (dmg:[min,max], hitCap) |
//        'block' (base, grow) | 'summons' (dmg:[min,max])
// req = character-level requirement (D2 tiers, compressed for a short run).
// pre = prerequisite skill ids (need >=1 point in each before you can learn this).
// maxTargets = how many foes an AoE actually hits (you can't wipe a whole pack).
// weapon = which weapon powers the skill: 'melee' (axes), 'ranged' (bows), or
//   'spell' (weapon-independent — Necro bone magic / summons). A physical skill's
//   damage is the EQUIPPED WEAPON's damage × wpn (+ growth/level); hold the wrong
//   weapon type and you flail for a pittance. Spell skills use their own dmg.
export const SKILLS = {
  // universal
  guard: { id: 'guard', name: 'Guard', type: 'skill', weapon: 'spell', cost: 2, scale: 'block', base: 8, grow: 2, req: 1, pre: [], text: 'Brace — gain Block.' },
  // Barbarian — melee (axe-powered) + a Charge to break into the outer ring
  strike: { id: 'strike', name: 'Strike', type: 'attack', target: 'single', reach: 0, cost: 2, scale: 'damage', weapon: 'melee', wpn: 1.0, grow: 2, req: 1, pre: [] },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', target: 'aoe', reach: 0, cost: 3, scale: 'damage', weapon: 'melee', wpn: 0.85, grow: 1, maxTargets: 2, req: 1, pre: [] },
  zeal: { id: 'zeal', name: 'Zeal', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'hits', weapon: 'melee', wpn: 0.7, hitCap: 5, req: 3, pre: ['strike'] },
  smite: { id: 'smite', name: 'Smite', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'damage', weapon: 'melee', wpn: 1.6, grow: 3, req: 6, pre: ['zeal'] },
  whirlwind: { id: 'whirlwind', name: 'Whirlwind', type: 'attack', target: 'aoe', reach: 0, cost: 4, scale: 'damage', weapon: 'melee', wpn: 1.1, grow: 2, maxTargets: 4, req: 8, pre: ['cleave', 'smite'] },
  charge: { id: 'charge', name: 'Charge', type: 'breakthrough', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'melee', wpn: 1.25, grow: 2, req: 4, pre: ['cleave'] },
  warcry: { id: 'warcry', name: 'War Cry', type: 'skill', weapon: 'spell', cost: 4, scale: 'block', base: 14, grow: 3, req: 2, pre: [], text: 'A defiant roar — big Block.' },
  // Amazon — ranged (bow-powered), reaches the outer ring natively
  arrow: { id: 'arrow', name: 'Arrow', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', weapon: 'ranged', wpn: 1.0, grow: 2, req: 1, pre: [] },
  power_shot: { id: 'power_shot', name: 'Power Shot', type: 'attack', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'ranged', wpn: 1.55, grow: 3, req: 4, pre: ['arrow'] },
  strafe: { id: 'strafe', name: 'Strafe', type: 'attack', target: 'aoe', reach: 1, cost: 4, scale: 'damage', weapon: 'ranged', wpn: 0.8, grow: 2, maxTargets: 3, req: 6, pre: ['power_shot'], text: 'A volley — hits several, reaches outer.' },
  pierce: { id: 'pierce', name: 'Pierce', type: 'breakthrough', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'ranged', wpn: 1.15, grow: 2, req: 2, pre: ['arrow'], text: 'A shot through the guard (reaches, ignores guard) — you stay Exposed.' },
  // Necromancer — spell/summon skills: weapon-INDEPENDENT (the wand grants +Skills)
  raise_skeleton: { id: 'raise_skeleton', name: 'Raise Skeleton', type: 'summon', weapon: 'spell', cost: 3, scale: 'summons', dmg: [3, 5], hp: 4, hpGrow: 1, req: 1, pre: [] },
  raise_golem: { id: 'raise_golem', name: 'Raise Golem', type: 'summon', weapon: 'spell', cost: 5, scale: 'summons', dmg: [6, 10], hp: 14, hpGrow: 2, solo: true, req: 5, pre: ['raise_skeleton'] },
  bone_spear: { id: 'bone_spear', name: 'Bone Spear', type: 'attack', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'spell', dmg: [6, 10], grow: 2, req: 4, pre: ['teeth'] },
  teeth: { id: 'teeth', name: 'Teeth', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'damage', weapon: 'spell', dmg: [2, 5], grow: 1, maxTargets: 3, req: 2, pre: [], text: 'A spray of bone — hits several, reaches outer.' },
  bone_armor: { id: 'bone_armor', name: 'Bone Armor', type: 'skill', weapon: 'spell', cost: 3, scale: 'block', base: 9, grow: 2, req: 2, pre: [], text: 'Shield of bone — Block.' },
};

// ---- Classes ---------------------------------------------------------------
// You begin NAKED: `startWeapon` grants ONE skill; `tree` is what you can LEARN
// with skill points. maxLife/maxMana are low and grow with level (see game.js).
export const CLASSES = {
  barbarian: { id: 'barbarian', name: 'Barbarian', glyph: '🪓', maxLife: 56, maxMana: 10, manaRegen: 6, startBlock: 0,
    startWeapon: 'worn_axe', tree: ['strike', 'cleave', 'zeal', 'smite', 'whirlwind', 'charge', 'warcry'] },
  amazon: { id: 'amazon', name: 'Amazon', glyph: '🏹', maxLife: 47, maxMana: 9, manaRegen: 6, startBlock: 0,
    startWeapon: 'short_bow', tree: ['arrow', 'power_shot', 'strafe', 'pierce', 'guard'] },
  necromancer: { id: 'necromancer', name: 'Necromancer', glyph: '💀', maxLife: 40, maxMana: 11, manaRegen: 5, startBlock: 0,
    startWeapon: 'bone_wand', tree: ['raise_skeleton', 'raise_golem', 'bone_spear', 'teeth', 'bone_armor'] },
};

// ---- Items -----------------------------------------------------------------
// grants.skill -> ability granted while equipped. passive -> stat mods
// (maxLife, maxMana, plusSkills, startBlock). Starting weapons grant one skill.
// Weapons carry damage + a type (wtype). A weapon's damage is the BASE for the
// physical skills of its type — a better axe means a harder Cleave; a bow can't
// Cleave at all. 'focus' weapons (wands/staves) deal no weapon damage: they power
// the Necromancer, whose spells scale on +Skills, not on a swung weapon.
export const ITEMS = {
  worn_axe: { id: 'worn_axe', name: 'Worn Axe', slot: 'weapon', wtype: 'melee', dmg: [5, 8], grants: { skill: 'cleave' }, text: 'A pitted axe (5-8). Grants Cleave.' },
  short_bow: { id: 'short_bow', name: 'Short Bow', slot: 'weapon', wtype: 'ranged', dmg: [5, 8], grants: { skill: 'arrow' }, text: 'A hunting bow (5-8). Grants Arrow.' },
  bone_wand: { id: 'bone_wand', name: 'Bone Wand', slot: 'weapon', wtype: 'focus', grants: { skill: 'raise_skeleton' }, text: 'A focus for the dead. Grants Raise Skeleton.' },
  // droppable weapons — better damage/mods; type gates which skills they empower
  great_axe: { id: 'great_axe', name: 'Great Axe of Smiting', slot: 'weapon', wtype: 'melee', dmg: [8, 13], grants: { skill: 'smite' }, passive: { plusSkills: 1 }, text: 'A brutal axe (8-13). Grants Smite. +1 to Skills.' },
  war_bow: { id: 'war_bow', name: 'War Bow', slot: 'weapon', wtype: 'ranged', dmg: [8, 12], grants: { skill: 'power_shot' }, passive: { maxMana: 2 }, text: 'A heavy bow (8-12). Grants Power Shot. +2 Mana.' },
  bone_staff: { id: 'bone_staff', name: 'Bone Staff', slot: 'weapon', wtype: 'focus', grants: { skill: 'bone_spear' }, passive: { plusSkills: 1 }, text: 'A staff of bone. Grants Bone Spear. +1 to Skills.' },
};
export const WEAPON_DROPS = ['great_axe', 'war_bow', 'bone_staff'];

// ---- Enemies ---------------------------------------------------------------
// ring: 0 inner (melee reaches), 1 outer (needs reach/summons). role 'caster'
// heals + is guardable; 'guardian' protects a caster.
export const ENEMIES = {
  fallen: { id: 'fallen', name: 'Fallen', hp: 7, attack: 2, glyph: '👺', role: 'grunt', ring: 0, xp: 3 },
  zombie: { id: 'zombie', name: 'Zombie', hp: 12, attack: 4, glyph: '🧟', role: 'grunt', ring: 0, xp: 5 },
  guardian: { id: 'guardian', name: 'Fallen Champion', hp: 12, attack: 4, glyph: '🛡️', role: 'guardian', ring: 0, xp: 6 },
  goatman: { id: 'goatman', name: 'Goatman', hp: 14, attack: 6, glyph: '🐐', role: 'grunt', ring: 0, xp: 7 },
  shaman: { id: 'shaman', name: 'Fallen Shaman', hp: 16, attack: 3, glyph: '🧙', role: 'caster', heal: 4, rez: 3, ring: 1, xp: 10 },
  archer: { id: 'archer', name: 'Dark Archer', hp: 9, attack: 4, glyph: '🏹', role: 'archer', ring: 1, xp: 6 },
  the_smith: { id: 'the_smith', name: 'The Flayed Smith', hp: 70, attack: 9, glyph: '🔨', role: 'elite', ring: 0, xp: 60 },
};

// Elite affixes (rolled onto a champion for Elite nodes).
export const ELITE_AFFIXES = {
  frenzied: { id: 'frenzied', name: 'Frenzied', mods: { extraAttack: true }, text: 'Attacks twice.' },
  brutal: { id: 'brutal', name: 'Brutal', mods: { attackMul: 1.6 }, text: 'Hits much harder.' },
  hardened: { id: 'hardened', name: 'Hardened', mods: { hpMul: 1.8 }, text: 'Far tougher.' },
  vampiric: { id: 'vampiric', name: 'Vampiric', mods: { leech: true }, text: 'Heals when it hits you.' },
};

export const BOSS_PACK = [{ id: 'the_smith' }, { id: 'shaman', guards: 0 }, { id: 'guardian', guards: 0 }];

// ---- Super uniques ---------------------------------------------------------
// Named leaders (like D2's Blood Raven) that appear along the descent leading a
// pack, each with a signature trick built from the same mechanics as the mob:
// rez (raise the slain), heal, extraAttack, leech. Tougher, and richer loot.
// role/ring behave like ENEMIES; rez/heal are resolved reactively (see combat).
export const SUPERUNIQUES = {
  blood_raven: { id: 'blood_raven', name: 'Blood Raven', glyph: '🩸', role: 'archer', ring: 1,
    hp: 46, attack: 8, rez: 8, xp: 42, minions: ['zombie', 'zombie', 'fallen', 'fallen'],
    text: 'Looses burning arrows and raises your slain foes — put her down fast.' },
  rakanishu: { id: 'rakanishu', name: 'Rakanishu', glyph: '⚡', role: 'grunt', ring: 0,
    hp: 40, attack: 8, extraAttack: true, xp: 36, minions: ['goatman', 'goatman', 'fallen'],
    text: 'A shrieking champion — strikes twice each turn.' },
  corpsefire: { id: 'corpsefire', name: 'Corpsefire', glyph: '🩸', role: 'grunt', ring: 0,
    hp: 66, attack: 7, leech: true, xp: 38, minions: ['zombie', 'zombie', 'zombie'],
    text: 'A bloated horror that heals on every blow it lands.' },
  bishibosh: { id: 'bishibosh', name: 'Bishibosh', glyph: '🔥', role: 'caster', ring: 1,
    hp: 42, attack: 4, heal: 7, rez: 6, xp: 40, minions: ['fallen', 'fallen', 'goatman', 'fallen'],
    text: 'A fallen shaman of great power — mends and raises his pack without pause.' },
};
export const SUPERUNIQUE_IDS = Object.keys(SUPERUNIQUES);

// Loot slots (armor/jewelry roll random affixes via loot.js; weapon grants skills).
export const SLOTS = ['weapon', 'offhand', 'helm', 'body', 'gloves', 'boots', 'belt', 'amulet', 'ring1', 'ring2'];
export const SLOT_LABEL = { weapon: 'Weapon', offhand: 'Off-hand', helm: 'Helm', body: 'Body', gloves: 'Gloves',
  boots: 'Boots', belt: 'Belt', amulet: 'Amulet', ring1: 'Ring', ring2: 'Ring' };

// ---- Random-loot tables (armor/jewelry; weapons are separate skill-granters) --
// Consumed by loot.js. No weapon bases here — weapons come from WEAPON_DROPS.
export const BASES = {
  offhand: [{ base: 'Buckler' }, { base: 'Kite Shield' }, { base: 'Bone Charm' }],
  helm: [{ base: 'Leather Cap' }, { base: 'Iron Helm' }, { base: 'Great Helm' }],
  body: [{ base: 'Quilted Armor' }, { base: 'Chain Mail' }, { base: 'Plate' }],
  gloves: [{ base: 'Leather Gloves' }, { base: 'Gauntlets' }],
  boots: [{ base: 'Boots' }, { base: 'Greaves' }],
  belt: [{ base: 'Sash' }, { base: 'Heavy Belt' }],
  amulet: [{ base: 'Amulet' }, { base: 'Talisman' }],
  ring: [{ base: 'Ring' }, { base: 'Band' }],
};
export const PREFIXES = [
  { name: 'Sturdy', mod: { maxLife: 8 } }, { name: 'Vigorous', mod: { maxLife: 15 } },
  { name: 'Runed', mod: { maxMana: 2 } }, { name: 'Cruel', mod: { plusSkills: 1 } },
  { name: 'Warded', mod: { startBlock: 2 } }, { name: 'Savage', mod: { plusSkills: 1, maxLife: 6 } },
];
export const SUFFIXES = [
  { name: 'of the Bear', mod: { maxLife: 10 } }, { name: 'of the Magi', mod: { maxMana: 2 } },
  { name: 'of Wrath', mod: { plusSkills: 1 } }, { name: 'of the Turtle', mod: { startBlock: 2 } },
  { name: 'of Fury', mod: { plusSkills: 2 } }, { name: 'of Vigor', mod: { maxLife: 14 } },
];
export const RARITY = [
  { rarity: 'normal', weight: 40, affixes: 0, color: '#cfcfcf' },
  { rarity: 'magic', weight: 40, affixes: 2, color: '#6f8aff' },
  { rarity: 'rare', weight: 20, affixes: 4, color: '#e5d54a' },
];
