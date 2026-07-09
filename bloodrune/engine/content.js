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
  // Each damage skill carries an `element` (fire/cold/lightning — for resistances)
  // and a `syn` map: each named same-tree sibling adds `pct` PER HARD POINT to this
  // skill (gear +skills do NOT count). Masteries carry `masteryPct` (×% per hard
  // point to their tree's element). role/geo drive UI + the movement-geometry audit.
  fire_bolt: { id: 'fire_bolt', name: 'Fire Bolt', tab: 'fire', element: 'fire', role: 'filler', geo: 'seeker', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', weapon: 'spell', dmg: [4, 7], grow: 2, req: 1, pre: [], syn: { fire_ball: 0.04, meteor: 0.04 } },
  warmth: { id: 'warmth', name: 'Warmth', tab: 'fire', element: 'fire', role: 'utility', type: 'passive', scale: 'passive', kind: 'warmth', cost: 0, req: 2, pre: [], text: '+1 Mana regen per point.' },
  inferno: { id: 'inferno', name: 'Inferno', tab: 'fire', element: 'fire', role: 'synergy', geo: 'cone', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'nova', weapon: 'spell', dmg: [3, 6], grow: 1, radius: 120, maxTargets: 6, req: 3, pre: ['fire_bolt'], syn: { fire_bolt: 0.05, fire_ball: 0.04 }, text: 'A gout of flame — burns foes around you.' },
  fire_ball: { id: 'fire_ball', name: 'Fire Ball', tab: 'fire', element: 'fire', role: 'nuke', geo: 'projectile', type: 'attack', target: 'aoe', reach: 1, cost: 4, scale: 'damage', weapon: 'spell', dmg: [9, 14], grow: 3, maxTargets: 3, req: 5, pre: ['fire_bolt'], cd: 0.85, syn: { fire_bolt: 0.06, meteor: 0.05, inferno: 0.04 } },
  fire_mastery: { id: 'fire_mastery', name: 'Fire Mastery', tab: 'fire', element: 'fire', role: 'mastery', type: 'passive', scale: 'passive', kind: 'mastery', masteryPct: 0.08, cost: 0, req: 6, pre: ['warmth'] },
  meteor: { id: 'meteor', name: 'Meteor', tab: 'fire', element: 'fire', role: 'nuke', geo: 'ground', type: 'attack', target: 'aoe', reach: 1, cost: 6, scale: 'nova', weapon: 'spell', dmg: [14, 22], grow: 3, radius: 150, maxTargets: 8, req: 9, pre: ['fire_ball'], cd: 1.6, syn: { fire_bolt: 0.05, fire_ball: 0.05, inferno: 0.04 }, text: 'Call down a meteor — heavy blast.' },
  // Cold
  ice_bolt: { id: 'ice_bolt', name: 'Ice Bolt', tab: 'cold', element: 'cold', role: 'filler', geo: 'seeker', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', weapon: 'spell', dmg: [3, 6], grow: 2, req: 1, pre: [], syn: { glacial_spike: 0.04, ice_blast: 0.04 } },
  frozen_armor: { id: 'frozen_armor', name: 'Frozen Armor', tab: 'cold', element: 'cold', role: 'utility', geo: 'self', type: 'skill', weapon: 'spell', cost: 3, scale: 'block', base: 8, grow: 2, req: 2, pre: [], text: 'A shell of ice — Block.' },
  frost_nova: { id: 'frost_nova', name: 'Frost Nova', tab: 'cold', element: 'cold', role: 'synergy', geo: 'nova', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'nova', weapon: 'spell', dmg: [2, 5], grow: 1, radius: 130, maxTargets: 8, req: 3, pre: ['ice_bolt'], syn: { ice_bolt: 0.05, glacial_spike: 0.04 }, text: 'A ring of frost — hits all around you.' },
  ice_blast: { id: 'ice_blast', name: 'Ice Blast', tab: 'cold', element: 'cold', role: 'synergy', geo: 'projectile', type: 'attack', target: 'single', reach: 1, cost: 4, scale: 'damage', weapon: 'spell', dmg: [7, 11], grow: 3, req: 5, pre: ['ice_bolt'], cd: 0.85, syn: { ice_bolt: 0.06, glacial_spike: 0.05 } },
  cold_mastery: { id: 'cold_mastery', name: 'Cold Mastery', tab: 'cold', element: 'cold', role: 'mastery', type: 'passive', scale: 'passive', kind: 'mastery', masteryPct: 0.08, cost: 0, req: 6, pre: ['frozen_armor'] },
  glacial_spike: { id: 'glacial_spike', name: 'Glacial Spike', tab: 'cold', element: 'cold', role: 'nuke', geo: 'ground', type: 'attack', target: 'aoe', reach: 1, cost: 5, scale: 'nova', weapon: 'spell', dmg: [10, 16], grow: 3, radius: 140, maxTargets: 6, req: 8, pre: ['ice_blast'], cd: 1.3, syn: { ice_bolt: 0.06, ice_blast: 0.05, frost_nova: 0.04 }, text: 'A burst of ice shards.' },
  // Lightning
  charged_bolt: { id: 'charged_bolt', name: 'Charged Bolt', tab: 'light', element: 'lightning', role: 'filler', geo: 'spread', type: 'attack', target: 'aoe', reach: 1, cost: 2, scale: 'damage', weapon: 'spell', dmg: [2, 4], grow: 1, maxTargets: 4, req: 1, pre: [], syn: { nova: 0.04, chain_lightning: 0.04 }, text: 'A spray of bolts — hits several.' },
  static_field: { id: 'static_field', name: 'Static Field', tab: 'light', element: 'lightning', role: 'utility', geo: 'nova', type: 'attack', target: 'aoe', reach: 1, cost: 3, scale: 'nova', weapon: 'spell', dmg: [3, 6], grow: 1, radius: 150, maxTargets: 10, req: 3, pre: [], text: 'Crackling static — jolts everything near.' },
  nova: { id: 'nova', name: 'Nova', tab: 'light', element: 'lightning', role: 'nuke', geo: 'nova', type: 'attack', target: 'aoe', reach: 1, cost: 4, scale: 'nova', weapon: 'spell', dmg: [5, 9], grow: 2, radius: 150, maxTargets: 12, req: 5, pre: ['charged_bolt'], cd: 1.0, syn: { charged_bolt: 0.06, chain_lightning: 0.05, lightning: 0.04 }, text: 'A shockwave of lightning in all directions.' },
  lightning: { id: 'lightning', name: 'Lightning', tab: 'light', element: 'lightning', role: 'nuke', geo: 'line', type: 'attack', target: 'single', reach: 1, cost: 4, scale: 'damage', weapon: 'spell', dmg: [4, 16], grow: 3, req: 6, pre: ['charged_bolt'], cd: 0.85, syn: { charged_bolt: 0.05, nova: 0.04 } },
  light_mastery: { id: 'light_mastery', name: 'Lightning Mastery', tab: 'light', element: 'lightning', role: 'mastery', type: 'passive', scale: 'passive', kind: 'mastery', masteryPct: 0.08, cost: 0, req: 6, pre: ['static_field'] },
  chain_lightning: { id: 'chain_lightning', name: 'Chain Lightning', tab: 'light', element: 'lightning', role: 'nuke', geo: 'arc', type: 'attack', target: 'aoe', reach: 1, cost: 5, scale: 'nova', weapon: 'spell', dmg: [8, 14], grow: 3, radius: 150, maxTargets: 8, req: 8, pre: ['lightning'], cd: 1.3, syn: { charged_bolt: 0.05, nova: 0.05, lightning: 0.04 }, text: 'Arcs from foe to foe.' },
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
  // attr = base Str/Dex/Vit/Energy (D2 starting stats). Str/Dex gate what gear you
  // can wear; Vit -> Life, Energy -> Mana/regen. You earn ~5 attr points per level
  // to spend, and greed (all Energy) locks you out of heavy Str/Dex gear.
  barbarian: { id: 'barbarian', name: 'Barbarian', glyph: '🪓', maxLife: 56, maxMana: 12, manaRegen: 2, startBlock: 0, acc: 7, eva: 1,
    attr: { str: 30, dex: 20, vit: 25, energy: 10 },
    startWeapon: 'worn_axe', tree: ['cleave', 'zeal', 'smite', 'whirlwind', 'charge', 'warcry'] },
  amazon: { id: 'amazon', name: 'Amazon', glyph: '🏹', maxLife: 47, maxMana: 12, manaRegen: 2, startBlock: 0, acc: 8, eva: 4,
    attr: { str: 20, dex: 25, vit: 20, energy: 15 },
    startWeapon: 'short_bow', tree: ['power_shot', 'strafe', 'pierce', 'guard'] },
  necromancer: { id: 'necromancer', name: 'Necromancer', glyph: '💀', maxLife: 40, maxMana: 16, manaRegen: 3, startBlock: 0, acc: 6, eva: 1,
    attr: { str: 15, dex: 25, vit: 15, energy: 25 },
    startWeapon: 'bone_wand', tree: ['raise_skeleton', 'raise_golem', 'bone_spear', 'teeth', 'bone_armor'] },
  // A faithful D2 Sorceress — three elemental trees; spells scale on level + Masteries.
  sorceress: { id: 'sorceress', name: 'Sorceress', glyph: '🔮', maxLife: 38, maxMana: 20, manaRegen: 4, startBlock: 0, acc: 6, eva: 2,
    attr: { str: 10, dex: 25, vit: 10, energy: 35 },
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
// `req` = equip requirements (Str/Dex/level). Starting weapons require nothing (you
// can always wield your own start); droppable weapons gate on the stat their class
// leans on (an axe wants Str, a bow Dex) so a greedy build can't just grab them.
export const ITEMS = {
  worn_axe: { id: 'worn_axe', name: 'Worn Axe', slot: 'weapon', wtype: 'melee', dmg: [5, 8], grants: { skill: 'cleave' }, req: {}, text: 'A pitted axe (5-8). Grants Cleave.' },
  short_bow: { id: 'short_bow', name: 'Short Bow', slot: 'weapon', wtype: 'ranged', dmg: [5, 8], grants: { skill: 'power_shot' }, req: {}, text: 'A hunting bow (5-8). Grants Power Shot.' },
  bone_wand: { id: 'bone_wand', name: 'Bone Wand', slot: 'weapon', wtype: 'focus', grants: { skill: 'raise_skeleton' }, req: {}, text: 'A focus for the dead. Grants Raise Skeleton.' },
  sorc_orb: { id: 'sorc_orb', name: 'Sorceress Orb', slot: 'weapon', wtype: 'focus', grants: { skill: 'fire_bolt' }, req: {}, text: 'A crystal orb. Grants Fire Bolt.' },
  // droppable weapons — better damage/mods; type gates which skills they empower
  great_axe: { id: 'great_axe', name: 'Great Axe of Smiting', slot: 'weapon', wtype: 'melee', dmg: [8, 13], grants: { skill: 'smite' }, passive: { plusSkills: 1 }, req: { str: 40, level: 6 }, text: 'A brutal axe (8-13). Grants Smite. +1 to Skills. (Req Str 40)' },
  war_bow: { id: 'war_bow', name: 'War Bow', slot: 'weapon', wtype: 'ranged', dmg: [8, 12], grants: { skill: 'power_shot' }, passive: { maxMana: 2 }, req: { dex: 36, level: 6 }, text: 'A heavy bow (8-12). Grants Power Shot. +2 Mana. (Req Dex 36)' },
  bone_staff: { id: 'bone_staff', name: 'Bone Staff', slot: 'weapon', wtype: 'focus', grants: { skill: 'bone_spear' }, passive: { plusSkills: 1 }, req: { level: 4 }, text: 'A staff of bone. Grants Bone Spear. +1 to Skills.' },
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
// Each base carries a Normal-tier Str/Dex equip requirement; heavier bases demand
// more (loot.js scales the requirement by the drop tier). Cloth/jewelry ask for
// nothing — the light-armor casters can always wear their own kit. Shields lean on
// Str; there's a Dex-gated body ('Studded') so the Dex requirement is real.
export const BASES = {
  offhand: [{ base: 'Buckler', str: 6 }, { base: 'Kite Shield', str: 20 }, { base: 'Bone Charm' }],
  helm: [{ base: 'Leather Cap' }, { base: 'Iron Helm', str: 12 }, { base: 'Great Helm', str: 22 }],
  body: [{ base: 'Quilted Armor' }, { base: 'Chain Mail', str: 22 }, { base: 'Studded Leather', dex: 20, str: 10 }, { base: 'Plate', str: 40 }],
  gloves: [{ base: 'Leather Gloves' }, { base: 'Gauntlets', str: 14 }],
  boots: [{ base: 'Boots' }, { base: 'Greaves', str: 14 }],
  belt: [{ base: 'Sash' }, { base: 'Heavy Belt', str: 10 }],
  amulet: [{ base: 'Amulet' }, { base: 'Talisman' }],
  ring: [{ base: 'Ring' }, { base: 'Band' }],
};
// Item TIER = the difficulty it dropped in; it multiplies affix magnitudes so a
// Normal item can NEVER rival Nightmare, nor Nightmare rival Hell.
export const ITEM_TIERS = ['Normal', 'Nightmare', 'Hell'];
export const TIER_MULT = { Normal: 1, Nightmare: 2.2, Hell: 4 };

// 4 honest rarities. common = no affixes (vendor trash); magic 1-2; rare 3-5;
// unique = a fixed item pulled from UNIQUES. Each up widens the roll space and a
// common can never match a unique.
export const RARITY = [
  { rarity: 'common', weight: 40, affixes: 0, affixMax: 0, color: '#cfcfcf' },
  { rarity: 'magic', weight: 40, affixes: 1, affixMax: 2, color: '#6f8aff' },
  { rarity: 'rare', weight: 17, affixes: 3, affixMax: 5, color: '#e5d54a' },
  { rarity: 'unique', weight: 3, affixes: 0, affixMax: 0, color: '#c8863a' },
];

// Affix pool. `mod` values are Normal-tier [min,max] ranges (the drop tier
// multiplies them via TIER_MULT). `tags` mark which builds actually want the
// affix — so most drops are sidegrades/junk for any ONE build (a caster does not
// want Increased Attack Speed or Accuracy). `pen` is a fraction (−enemy resist).
export const AFFIXES = [
  { id: 'sturdy', name: 'Sturdy', pos: 'prefix', mod: { maxLife: [7, 13] }, tags: ['all'] },
  { id: 'vigor', name: 'of Vigor', pos: 'suffix', mod: { maxLife: [9, 16] }, tags: ['all'] },
  { id: 'magi', name: 'of the Magi', pos: 'suffix', mod: { maxMana: [5, 10] }, tags: ['caster'] },
  { id: 'warm', name: 'Warm', pos: 'prefix', mod: { manaRegen: [1, 2] }, tags: ['caster'] },
  { id: 'sorcery', name: 'of Sorcery', pos: 'suffix', mod: { fcr: [8, 16] }, tags: ['caster'] },
  { id: 'hexing', name: 'Hexing', pos: 'prefix', mod: { fcr: [6, 12] }, tags: ['caster'] },
  { id: 'piercing', name: 'of Piercing', pos: 'suffix', mod: { penetration: [0.03, 0.07] }, tags: ['caster'] },
  { id: 'mind', name: 'of the Mind', pos: 'suffix', mod: { energy: [3, 7] }, tags: ['caster'] },
  { id: 'adept', name: 'of the Adept', pos: 'suffix', mod: { plusSkills: [1, 1] }, tags: ['all'], plusSkills: true },
  { id: 'fervor', name: 'of Fervor', pos: 'suffix', mod: { ias: [8, 16] }, tags: ['melee'] },
  { id: 'vicious', name: 'Vicious', pos: 'prefix', mod: { ias: [6, 12] }, tags: ['melee'] },
  { id: 'keen', name: 'Keen', pos: 'prefix', mod: { accuracy: [3, 6] }, tags: ['melee'] },
  { id: 'cat', name: 'of the Cat', pos: 'suffix', mod: { evade: [2, 4] }, tags: ['melee'] },
  { id: 'warded', name: 'Warded', pos: 'prefix', mod: { startBlock: [2, 4] }, tags: ['melee'] },
  { id: 'might', name: 'of Might', pos: 'suffix', mod: { str: [3, 7] }, tags: ['melee'] },
  { id: 'oflife', name: 'of Life', pos: 'suffix', mod: { vit: [3, 7] }, tags: ['all'] },
];

// Fixed UNIQUES (the treasure-hunt peaks + build enablers). minTier gates which
// difficulty they can drop in. S7 expands this into the full enabler/runeword set.
export const UNIQUES = [
  { id: 'u_tarnhelm', name: 'Tarnhelm', slot: 'helm', minTier: 'Normal', passive: { plusSkills: 1, maxMana: 8 }, text: 'Tarnhelm — +1 Skills, +Mana.' },
  { id: 'u_magefist', name: 'Magefist', slot: 'gloves', minTier: 'Normal', passive: { fcr: 20, manaRegen: 2 }, text: 'Magefist — +20% Cast Speed, +Mana regen.', enabler: true },
  { id: 'u_nagel', name: 'Nagelring', slot: 'ring', minTier: 'Normal', passive: { maxLife: 14, penetration: 0.06 }, text: 'Nagelring — +Life, pierces resist.' },
  { id: 'u_soj', name: 'Stone of Jordan', slot: 'ring', minTier: 'Nightmare', passive: { plusSkills: 1, maxMana: 24, manaRegen: 2 }, text: 'Stone of Jordan — +1 Skills, big Mana.', enabler: true },
  { id: 'u_frostburn', name: 'Frostburn', slot: 'gloves', minTier: 'Nightmare', passive: { maxMana: 30, fcr: 10 }, text: 'Frostburn — huge Mana, +Cast Speed.' },
  { id: 'u_vipermagi', name: "Skin of the Vipermagi", slot: 'body', minTier: 'Nightmare', passive: { plusSkills: 1, fcr: 30, penetration: 0.08 }, text: 'Vipermagi — +1 Skills, +30% FCR, pierce.', enabler: true },
  { id: 'u_death', name: "Death's Fathom", slot: 'offhand', minTier: 'Hell', passive: { plusSkills: 2, penetration: 0.15 }, text: "Death's Fathom — +2 Skills, deep pierce.", enabler: true },
  // Per-ELEMENT +Skills enablers — the single-element build spike. +Skills raises
  // the whole element's BASE damage (never the synergy bracket), so an already
  // committed fire/cold/light build jumps when it finds its amulet.
  { id: 'u_ember', name: 'Ember Choker', slot: 'amulet', minTier: 'Normal', passive: { plusFire: 2, maxMana: 12 }, text: 'Ember Choker — +2 Fire Skills, +Mana.', enabler: true },
  { id: 'u_rime', name: 'Rimeward Torc', slot: 'amulet', minTier: 'Normal', passive: { plusCold: 2, maxMana: 12 }, text: 'Rimeward Torc — +2 Cold Skills, +Mana.', enabler: true },
  { id: 'u_storm', name: 'Stormcaller Beads', slot: 'amulet', minTier: 'Normal', passive: { plusLight: 2, maxMana: 12 }, text: 'Stormcaller Beads — +2 Lightning Skills, +Mana.', enabler: true },
];

// ---- Sockets, runes & runewords (the aspiration ladder) --------------------
// Socketable bases roll empty sockets (loot.js). A single rune socketed grants its
// small `mod`; fill EVERY socket of a base on a runeword's list with the exact rune
// SEQUENCE and it resolves to that runeword's fixed, far stronger `mods`. Runes are
// tier-gated (high runes only drop deeper), so runewords are a real chase.
export const RUNES = [
  { id: 'el', name: 'El', num: 1, minTier: 'Normal', mod: { accuracy: 2, maxLife: 3 } },
  { id: 'eld', name: 'Eld', num: 2, minTier: 'Normal', mod: { evade: 3 } },
  { id: 'tir', name: 'Tir', num: 3, minTier: 'Normal', mod: { maxMana: 6 } },
  { id: 'nef', name: 'Nef', num: 4, minTier: 'Normal', mod: { evade: 4 } },
  { id: 'eth', name: 'Eth', num: 5, minTier: 'Normal', mod: { penetration: 0.05 } },
  { id: 'ith', name: 'Ith', num: 6, minTier: 'Normal', mod: { maxLife: 9 } },
  { id: 'tal', name: 'Tal', num: 7, minTier: 'Normal', mod: { manaRegen: 2, maxMana: 4 } },
  { id: 'ral', name: 'Ral', num: 8, minTier: 'Nightmare', mod: { fcr: 6 } },
  { id: 'ort', name: 'Ort', num: 9, minTier: 'Nightmare', mod: { maxMana: 12 } },
  { id: 'thul', name: 'Thul', num: 10, minTier: 'Nightmare', mod: { maxLife: 16 } },
  { id: 'amn', name: 'Amn', num: 11, minTier: 'Nightmare', mod: { maxLife: 20 } },
  { id: 'sol', name: 'Sol', num: 12, minTier: 'Hell', mod: { maxLife: 26 } },
  { id: 'shael', name: 'Shael', num: 13, minTier: 'Hell', mod: { fcr: 13 } },
  { id: 'um', name: 'Um', num: 14, minTier: 'Hell', mod: { penetration: 0.12 } },
];
export const RUNE_BY_ID = Object.fromEntries(RUNES.map((r) => [r.id, r]));

// A runeword = an ordered rune sequence filling EVERY socket of a base on `slots`.
// `runes.length` is the exact socket count required. Mods override the raw runes.
export const RUNEWORDS = [
  { id: 'stealth', name: 'Stealth', runes: ['tal', 'eth'], slots: ['body'], mods: { fcr: 25, evade: 8, maxMana: 15 }, text: 'Stealth — swift and slippery (+25% FCR, evade, Mana).' },
  { id: 'lore', name: 'Lore', runes: ['ort', 'sol'], slots: ['helm'], mods: { plusSkills: 1, maxMana: 16 }, text: 'Lore — +1 to Skills, +Mana.' },
  { id: 'ancients', name: "Ancient's Pledge", runes: ['ral', 'ort', 'tal'], slots: ['offhand'], mods: { penetration: 0.13, maxLife: 12 }, text: "Ancient's Pledge — pierces resist, +Life." },
  { id: 'spirit', name: 'Spirit', runes: ['tal', 'thul', 'ort', 'amn'], slots: ['offhand'], mods: { plusSkills: 2, fcr: 30, maxMana: 40, penetration: 0.08 }, text: 'Spirit — the caster crown: +2 Skills, +30% FCR, big Mana, pierce.' },
];

// Per-class loot value weights — what an affix is WORTH to a build, for "is this an
// upgrade?" (off-build affixes score ~0, so most drops aren't upgrades for you).
export const CLASS_PROFILE = {
  sorceress: { plusSkills: 14, plusFire: 10, plusCold: 10, plusLight: 10, fcr: 2.5, penetration: 80, maxMana: 1.4, manaRegen: 4, energy: 1.4, maxLife: 1, vit: 1.2, ias: 0, accuracy: 0, evade: 0.2, startBlock: 0.2, str: 0.2, dex: 0.2 },
  barbarian: { plusSkills: 14, ias: 2.5, accuracy: 1.5, startBlock: 2, maxLife: 1.6, str: 1, dex: 0.8, vit: 1.2, evade: 0.5, fcr: 0, maxMana: 0.3, manaRegen: 0.3, penetration: 0, energy: 0.2 },
  amazon: { plusSkills: 14, ias: 2.5, accuracy: 2, evade: 1.5, maxLife: 1.4, dex: 1.2, str: 0.6, vit: 1.1, startBlock: 0.8, fcr: 0, maxMana: 0.3, manaRegen: 0.3, penetration: 0, energy: 0.2 },
  necromancer: { plusSkills: 14, fcr: 2.5, maxMana: 1.4, manaRegen: 3.5, energy: 1.3, maxLife: 1.1, vit: 1.2, penetration: 40, ias: 0, accuracy: 0, evade: 0.2, startBlock: 0.3, str: 0.2, dex: 0.2 },
};
