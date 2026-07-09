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
  // universal — a basic weapon swing (NOT a learned skill): no Mana, uses whatever
  // weapon you hold (melee hits the inner ring, a bow the outer). Your out-of-Mana
  // fallback. Costs an action point like everything else.
  attack: { id: 'attack', name: 'Attack', type: 'attack', target: 'single', cost: 0, scale: 'damage', weapon: 'weapon', wpn: 1.0, grow: 0, req: 1, pre: [], text: 'A basic weapon swing — free, uses your weapon.' },
  guard: { id: 'guard', name: 'Guard', type: 'skill', weapon: 'spell', cost: 2, scale: 'block', base: 8, grow: 2, req: 1, pre: [], text: 'Brace — gain Block.' },
  // Barbarian — melee (axe-powered) + a Charge to break into the outer ring
  strike: { id: 'strike', name: 'Strike', type: 'attack', target: 'single', reach: 0, cost: 0, scale: 'damage', weapon: 'melee', wpn: 1.0, grow: 2, req: 1, pre: [] },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', target: 'aoe', reach: 0, cost: 3, scale: 'damage', weapon: 'melee', wpn: 0.85, grow: 1, maxTargets: 2, req: 1, pre: [] },
  zeal: { id: 'zeal', name: 'Zeal', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'hits', weapon: 'melee', wpn: 0.7, hitCap: 5, req: 3, pre: ['cleave'] },
  smite: { id: 'smite', name: 'Smite', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'damage', weapon: 'melee', wpn: 1.6, grow: 3, req: 6, pre: ['zeal'] },
  whirlwind: { id: 'whirlwind', name: 'Whirlwind', type: 'attack', target: 'aoe', reach: 0, cost: 4, scale: 'damage', weapon: 'melee', wpn: 1.1, grow: 2, maxTargets: 4, req: 8, pre: ['cleave', 'smite'] },
  charge: { id: 'charge', name: 'Charge', type: 'breakthrough', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'melee', wpn: 1.25, grow: 2, req: 4, pre: ['cleave'] },
  warcry: { id: 'warcry', name: 'War Cry', type: 'skill', weapon: 'spell', cost: 4, scale: 'block', base: 14, grow: 3, req: 2, pre: [], text: 'A defiant roar — big Block.' },
  // Amazon — ranged (bow-powered), reaches the outer ring natively
  arrow: { id: 'arrow', name: 'Arrow', type: 'attack', target: 'single', reach: 1, cost: 0, scale: 'damage', weapon: 'ranged', wpn: 1.0, grow: 2, req: 1, pre: [] },
  power_shot: { id: 'power_shot', name: 'Power Shot', type: 'attack', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'ranged', wpn: 1.55, grow: 3, req: 3, pre: [] },
  strafe: { id: 'strafe', name: 'Strafe', type: 'attack', target: 'aoe', reach: 1, cost: 4, scale: 'damage', weapon: 'ranged', wpn: 0.8, grow: 2, maxTargets: 3, req: 6, pre: ['power_shot'], text: 'A volley — hits several, reaches outer.' },
  pierce: { id: 'pierce', name: 'Pierce', type: 'breakthrough', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'ranged', wpn: 1.15, grow: 2, req: 2, pre: [], text: 'A shot through the guard (reaches, ignores guard) — you stay Exposed.' },
  // Necromancer — spell/summon skills: weapon-INDEPENDENT (the wand grants +Skills)
  raise_skeleton: { id: 'raise_skeleton', name: 'Raise Skeleton', type: 'summon', weapon: 'spell', cost: 3, scale: 'summons', dmg: [2, 4], hp: 4, hpGrow: 1, req: 1, pre: [] },
  raise_golem: { id: 'raise_golem', name: 'Raise Golem', type: 'summon', weapon: 'spell', cost: 5, scale: 'summons', dmg: [5, 8], hp: 14, hpGrow: 2, solo: true, req: 5, pre: ['raise_skeleton'] },
  bone_spear: { id: 'bone_spear', name: 'Bone Spear', type: 'attack', target: 'single', reach: 1, cost: 3, scale: 'damage', weapon: 'spell', dmg: [6, 10], grow: 2, req: 4, pre: ['teeth'] },
  teeth: { id: 'teeth', name: 'Teeth', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'damage', weapon: 'spell', dmg: [2, 5], grow: 1, maxTargets: 3, req: 2, pre: [], text: 'A spray of bone — hits several, reaches outer.' },
  bone_armor: { id: 'bone_armor', name: 'Bone Armor', type: 'skill', weapon: 'spell', cost: 3, scale: 'block', base: 9, grow: 2, req: 2, pre: [], text: 'Shield of bone — Block.' },

  // ---- Sorceress — a faithful D2 clone across THREE trees (tab: fire/cold/light) --
  // All spells are weapon-independent (the Orb just grants a skill + power). New
  // scale types: 'nova' = a burst that blasts every foe around you; 'passive' =
  // Warmth (Mana regen) and Masteries (+ spell damage), which don't auto-fire.
  // Fire
  fire_bolt: { id: 'fire_bolt', name: 'Fire Bolt', tab: 'fire', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', weapon: 'spell', dmg: [4, 7], grow: 2, req: 1, pre: [] },
  warmth: { id: 'warmth', name: 'Warmth', tab: 'fire', type: 'passive', scale: 'passive', kind: 'warmth', cost: 0, req: 2, pre: [], text: '+1 Mana regen per level.' },
  inferno: { id: 'inferno', name: 'Inferno', tab: 'fire', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'nova', weapon: 'spell', dmg: [3, 6], grow: 1, radius: 120, maxTargets: 6, req: 3, pre: ['fire_bolt'], text: 'A gout of flame — burns foes around you.' },
  fire_ball: { id: 'fire_ball', name: 'Fire Ball', tab: 'fire', type: 'attack', target: 'single', reach: 1, cost: 4, scale: 'damage', weapon: 'spell', dmg: [9, 14], grow: 3, req: 5, pre: ['fire_bolt'] },
  fire_mastery: { id: 'fire_mastery', name: 'Fire Mastery', tab: 'fire', type: 'passive', scale: 'passive', kind: 'mastery', cost: 0, req: 6, pre: ['warmth'], text: '+2 spell damage per level.' },
  meteor: { id: 'meteor', name: 'Meteor', tab: 'fire', type: 'attack', target: 'aoe', reach: 1, cost: 6, scale: 'nova', weapon: 'spell', dmg: [14, 22], grow: 3, radius: 150, maxTargets: 8, req: 9, pre: ['fire_ball'], text: 'Call down a meteor — heavy blast.' },
  // Cold
  ice_bolt: { id: 'ice_bolt', name: 'Ice Bolt', tab: 'cold', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', weapon: 'spell', dmg: [3, 6], grow: 2, req: 1, pre: [] },
  frozen_armor: { id: 'frozen_armor', name: 'Frozen Armor', tab: 'cold', type: 'skill', weapon: 'spell', cost: 3, scale: 'block', base: 8, grow: 2, req: 2, pre: [], text: 'A shell of ice — Block.' },
  frost_nova: { id: 'frost_nova', name: 'Frost Nova', tab: 'cold', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'nova', weapon: 'spell', dmg: [2, 5], grow: 1, radius: 130, maxTargets: 8, req: 3, pre: ['ice_bolt'], text: 'A ring of frost — hits all around you.' },
  ice_blast: { id: 'ice_blast', name: 'Ice Blast', tab: 'cold', type: 'attack', target: 'single', reach: 1, cost: 4, scale: 'damage', weapon: 'spell', dmg: [7, 11], grow: 3, req: 5, pre: ['ice_bolt'] },
  cold_mastery: { id: 'cold_mastery', name: 'Cold Mastery', tab: 'cold', type: 'passive', scale: 'passive', kind: 'mastery', cost: 0, req: 6, pre: ['frozen_armor'], text: '+2 spell damage per level.' },
  glacial_spike: { id: 'glacial_spike', name: 'Glacial Spike', tab: 'cold', type: 'attack', target: 'aoe', reach: 1, cost: 5, scale: 'nova', weapon: 'spell', dmg: [10, 16], grow: 3, radius: 140, maxTargets: 6, req: 8, pre: ['ice_blast'], text: 'A burst of ice shards.' },
  // Lightning
  charged_bolt: { id: 'charged_bolt', name: 'Charged Bolt', tab: 'light', type: 'attack', target: 'aoe', reach: 1, cost: 2, scale: 'damage', weapon: 'spell', dmg: [2, 4], grow: 1, maxTargets: 4, req: 1, pre: [], text: 'A spray of bolts — hits several.' },
  static_field: { id: 'static_field', name: 'Static Field', tab: 'light', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'nova', weapon: 'spell', dmg: [3, 6], grow: 1, radius: 150, maxTargets: 10, req: 3, pre: [], text: 'Crackling static — jolts everything near.' },
  nova: { id: 'nova', name: 'Nova', tab: 'light', type: 'attack', target: 'aoe', reach: 1, cost: 4, scale: 'nova', weapon: 'spell', dmg: [5, 9], grow: 2, radius: 150, maxTargets: 12, req: 5, pre: ['charged_bolt'], text: 'A shockwave of lightning in all directions.' },
  lightning: { id: 'lightning', name: 'Lightning', tab: 'light', type: 'attack', target: 'single', reach: 1, cost: 4, scale: 'damage', weapon: 'spell', dmg: [4, 16], grow: 3, req: 6, pre: ['charged_bolt'] },
  light_mastery: { id: 'light_mastery', name: 'Lightning Mastery', tab: 'light', type: 'passive', scale: 'passive', kind: 'mastery', cost: 0, req: 6, pre: ['static_field'], text: '+2 spell damage per level.' },
  chain_lightning: { id: 'chain_lightning', name: 'Chain Lightning', tab: 'light', type: 'attack', target: 'aoe', reach: 1, cost: 5, scale: 'nova', weapon: 'spell', dmg: [8, 14], grow: 3, radius: 150, maxTargets: 8, req: 8, pre: ['lightning'], text: 'Arcs from foe to foe.' },
};

// ---- Classes ---------------------------------------------------------------
// You begin NAKED: `startWeapon` grants ONE skill; `tree` is what you can LEARN
// with skill points. maxLife/maxMana are low and grow with level (see game.js).
export const CLASSES = {
  // acc = base Accuracy (physical to-hit); eva = base Evade (dodge chance). The
  // Amazon is the nimble one (high Evade); melee wants Accuracy as it scales.
  // manaRegen is SLOW and per-turn — Mana persists across the whole run (no free
  // refill between packs); you top up with Mana potions and rest at camps. Casters
  // carry a larger pool + slightly better regen.
  barbarian: { id: 'barbarian', name: 'Barbarian', glyph: '🪓', maxLife: 56, maxMana: 12, manaRegen: 2, startBlock: 0, acc: 7, eva: 1,
    startWeapon: 'worn_axe', tree: ['cleave', 'zeal', 'smite', 'whirlwind', 'charge', 'warcry'] },
  amazon: { id: 'amazon', name: 'Amazon', glyph: '🏹', maxLife: 47, maxMana: 12, manaRegen: 2, startBlock: 0, acc: 8, eva: 4,
    startWeapon: 'short_bow', tree: ['power_shot', 'strafe', 'pierce', 'guard'] },
  necromancer: { id: 'necromancer', name: 'Necromancer', glyph: '💀', maxLife: 40, maxMana: 16, manaRegen: 3, startBlock: 0, acc: 6, eva: 1,
    startWeapon: 'bone_wand', tree: ['raise_skeleton', 'raise_golem', 'bone_spear', 'teeth', 'bone_armor'] },
  // A faithful D2 Sorceress — three elemental trees; spells scale on level + Masteries.
  sorceress: { id: 'sorceress', name: 'Sorceress', glyph: '🔮', maxLife: 38, maxMana: 20, manaRegen: 4, startBlock: 0, acc: 6, eva: 2,
    startWeapon: 'sorc_orb', tabs: ['fire', 'cold', 'light'],
    tree: ['fire_bolt', 'warmth', 'inferno', 'fire_ball', 'fire_mastery', 'meteor',
      'ice_bolt', 'frozen_armor', 'frost_nova', 'ice_blast', 'cold_mastery', 'glacial_spike',
      'charged_bolt', 'static_field', 'nova', 'lightning', 'light_mastery', 'chain_lightning'] },
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
  short_bow: { id: 'short_bow', name: 'Short Bow', slot: 'weapon', wtype: 'ranged', dmg: [5, 8], grants: { skill: 'power_shot' }, text: 'A hunting bow (5-8). Grants Power Shot.' },
  bone_wand: { id: 'bone_wand', name: 'Bone Wand', slot: 'weapon', wtype: 'focus', grants: { skill: 'raise_skeleton' }, text: 'A focus for the dead. Grants Raise Skeleton.' },
  sorc_orb: { id: 'sorc_orb', name: 'Sorceress Orb', slot: 'weapon', wtype: 'focus', grants: { skill: 'fire_bolt' }, text: 'A crystal orb. Grants Fire Bolt.' },
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
  // acc = to-hit vs your Evade; eva = how hard it is to hit (vs your Accuracy).
  quill_rat: { id: 'quill_rat', name: 'Quill Rat', hp: 6, attack: 3, glyph: '🦔', role: 'grunt', ring: 0, xp: 2, acc: 5, eva: 4 },
  fallen: { id: 'fallen', name: 'Fallen', hp: 9, attack: 3, glyph: '👺', role: 'grunt', ring: 0, xp: 3, acc: 4, eva: 1 },
  zombie: { id: 'zombie', name: 'Zombie', hp: 15, attack: 5, glyph: '🧟', role: 'grunt', ring: 0, xp: 5, acc: 5, eva: 0 },
  guardian: { id: 'guardian', name: 'Fallen Champion', hp: 15, attack: 5, glyph: '🛡️', role: 'guardian', ring: 0, xp: 6, acc: 6, eva: 2 },
  goatman: { id: 'goatman', name: 'Moon Clan Goatman', hp: 17, attack: 7, glyph: '🐐', role: 'grunt', ring: 0, xp: 7, acc: 6, eva: 3 },
  shaman: { id: 'shaman', name: 'Fallen Shaman', hp: 20, attack: 4, glyph: '🧙', role: 'caster', heal: 5, rez: 3, ring: 1, xp: 10, acc: 4, eva: 2 },
  archer: { id: 'archer', name: 'Dark Ranger', hp: 12, attack: 6, glyph: '🏹', role: 'archer', ring: 1, xp: 6, acc: 7, eva: 3 },
  the_smith: { id: 'the_smith', name: 'The Smith', hp: 210, attack: 14, glyph: '🔨', role: 'elite', ring: 0, xp: 60, acc: 8, eva: 3 },
  // Andariel — Act 1 boss (Maiden of Anguish). A big, ranged poison-flinger.
  andariel: { id: 'andariel', name: 'Andariel', hp: 340, attack: 17, glyph: '🕷️', role: 'archer', ring: 1, xp: 220, acc: 9, eva: 2, boss: true },
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
    hp: 46, attack: 8, acc: 8, eva: 4, rez: 8, xp: 42, minions: ['zombie', 'zombie', 'fallen', 'fallen'],
    text: 'Looses burning arrows and raises your slain foes — put her down fast.' },
  rakanishu: { id: 'rakanishu', name: 'Rakanishu', glyph: '⚡', role: 'grunt', ring: 0,
    hp: 40, attack: 8, acc: 7, eva: 5, extraAttack: true, xp: 36, minions: ['goatman', 'goatman', 'fallen'],
    text: 'A shrieking champion — strikes twice each turn.' },
  corpsefire: { id: 'corpsefire', name: 'Corpsefire', glyph: '🩸', role: 'grunt', ring: 0,
    hp: 66, attack: 7, acc: 6, eva: 1, leech: true, xp: 38, minions: ['zombie', 'zombie', 'zombie'],
    text: 'A bloated horror that heals on every blow it lands.' },
  bishibosh: { id: 'bishibosh', name: 'Bishibosh', glyph: '🔥', role: 'caster', ring: 1,
    hp: 42, attack: 4, acc: 5, eva: 3, heal: 7, rez: 6, xp: 40, minions: ['fallen', 'fallen', 'goatman', 'fallen'],
    text: 'A fallen shaman of great power — mends and raises his pack without pause.' },
  treehead_woodfist: { id: 'treehead_woodfist', name: 'Treehead Woodfist', glyph: '🪵', role: 'grunt', ring: 0,
    hp: 120, attack: 13, acc: 7, eva: 1, extraAttack: true, xp: 70, minions: ['goatman', 'goatman', 'goatman'],
    text: 'A monstrous brute of the Dark Wood — slow, but each swing lands twice.' },
  the_countess: { id: 'the_countess', name: 'The Countess', glyph: '🩸', role: 'archer', ring: 1,
    hp: 110, attack: 14, acc: 8, eva: 4, xp: 80, minions: ['archer', 'archer', 'goatman'],
    text: 'Mistress of the Forgotten Tower — she rains fire from the ramparts.' },
};
export const SUPERUNIQUE_IDS = Object.keys(SUPERUNIQUES);

// ---- Act 1 — the gauntlet ---------------------------------------------------
// One run walks all of Act 1 as a SEQUENCE of areas (no exploration). Each area
// spawns waves from its pool; when its timer runs out, the area's time-GATE — a
// named super-unique — appears. Kill the gate to clear the area (and its QUEST)
// and transition to the next. The final gate is Andariel; put her down to win.
// pool = enemy ids (weighted by repetition); gate = super-unique id or ENEMIES id.
export const ACT1 = [
  { name: 'Blood Moor', quest: 'Den of Evil', questText: 'Cleanse the Den — slay Corpsefire.', dur: 50, pool: ['quill_rat', 'fallen', 'fallen', 'zombie'], gate: 'corpsefire' },
  { name: 'Cold Plains', quest: null, questText: 'Cut across the plains — Bishibosh bars the way.', dur: 55, pool: ['fallen', 'goatman', 'zombie', 'quill_rat'], gate: 'bishibosh' },
  { name: "Sisters' Burial Grounds", quest: "Sisters' Burial Grounds", questText: 'Put down Blood Raven.', dur: 55, pool: ['zombie', 'zombie', 'fallen', 'archer'], gate: 'blood_raven' },
  { name: 'Stony Field', quest: null, questText: 'Shatter Rakanishu at the cairn stones.', dur: 60, pool: ['goatman', 'fallen', 'archer', 'zombie'], gate: 'rakanishu' },
  { name: 'Dark Wood', quest: 'The Tree of Inifuss', questText: 'Fell Treehead Woodfist.', dur: 60, pool: ['goatman', 'zombie', 'shaman', 'goatman'], gate: 'treehead_woodfist' },
  { name: 'Forgotten Tower', quest: 'The Forgotten Tower', questText: 'Loot the tower — end the Countess.', dur: 62, pool: ['archer', 'goatman', 'zombie', 'shaman'], gate: 'the_countess' },
  { name: 'Jail & Barracks', quest: 'Tools of the Trade', questText: 'Reclaim the Horadric Malus — kill The Smith.', dur: 66, pool: ['guardian', 'goatman', 'archer', 'zombie'], gate: 'the_smith' },
  { name: 'Catacombs', quest: 'Sisters to the Slaughter', questText: 'Slay Andariel, Maiden of Anguish.', dur: 70, pool: ['zombie', 'archer', 'shaman', 'guardian'], gate: 'andariel' },
];

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
  { name: 'Keen', mod: { accuracy: 3 } }, { name: 'Nimble', mod: { evade: 3 } },
  { name: 'Hexing', mod: { fcr: 15 } }, { name: 'Vicious', mod: { ias: 15 } }, // Faster Cast Rate / Increased Attack Speed
];
export const SUFFIXES = [
  { name: 'of the Bear', mod: { maxLife: 10 } }, { name: 'of the Magi', mod: { maxMana: 2 } },
  { name: 'of Wrath', mod: { plusSkills: 1 } }, { name: 'of the Turtle', mod: { startBlock: 2 } },
  { name: 'of Fury', mod: { plusSkills: 2 } }, { name: 'of Vigor', mod: { maxLife: 14 } },
  { name: 'of Precision', mod: { accuracy: 4 } }, { name: 'of the Cat', mod: { evade: 3 } },
  { name: 'of Sorcery', mod: { fcr: 20 } }, { name: 'of Fervor', mod: { ias: 20 } }, // the spam-your-main-skill affixes
];
export const RARITY = [
  { rarity: 'normal', weight: 18, affixes: 0, color: '#cfcfcf' }, // whites are now rare — most drops carry affixes
  { rarity: 'magic', weight: 47, affixes: 2, color: '#6f8aff' },
  { rarity: 'rare', weight: 35, affixes: 4, color: '#e5d54a' },
];
