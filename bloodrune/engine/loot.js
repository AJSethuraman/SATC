// Seeded loot generation: roll a random item (base + rarity + affixes). Rarity
// is weighted, biased upward by Magic Find. Affixes roll from the prefix/suffix
// pools and stack additively into the item's `passive` mods — the same stat keys
// gear already uses, so generated items drop straight into the equip system.
// Pure + deterministic given the injected rng.

import { BASES, PREFIXES, SUFFIXES, RARITY, SLOTS } from './content.js';

// weapons are skill-granters (not random-rolled); exclude them + the 2nd ring.
const REAL_SLOTS = SLOTS.filter((s) => s !== 'ring2' && s !== 'weapon').map((s) => (s === 'ring1' ? 'ring' : s));

function sumMods(a, b) {
  const out = { ...a };
  for (const [k, v] of Object.entries(b)) out[k] = (out[k] || 0) + v;
  return out;
}

function rollRarity(rng, magicFind) {
  // Magic Find shifts weight off 'normal' toward 'magic'/'rare'.
  const mf = Math.max(0, magicFind || 0);
  const weights = RARITY.map((r) => {
    if (r.rarity === 'normal') return Math.max(1, r.weight - mf);
    if (r.rarity === 'magic') return r.weight + mf * 0.6;
    return r.weight + mf * 0.4; // rare
  });
  const total = weights.reduce((a, b) => a + b, 0);
  let roll = rng.next() * total;
  for (let i = 0; i < RARITY.length; i++) {
    if ((roll -= weights[i]) < 0) return RARITY[i];
  }
  return RARITY[0];
}

function modText(mod) {
  const parts = [];
  if (mod.maxLife) parts.push(`+${mod.maxLife} Life`);
  if (mod.maxMana) parts.push(`+${mod.maxMana} Mana`);
  if (mod.accuracy) parts.push(`+${mod.accuracy} Accuracy`);
  if (mod.plusSkills) parts.push(`+${mod.plusSkills} to Skills`);
  if (mod.startBlock) parts.push(`+${mod.startBlock} Block/turn`);
  return parts.join(', ');
}

let counter = 0; // uniquifies generated item ids within a session

// Generate one random item. itemLevel gently scales nothing yet (hook for later
// gating); magicFind biases rarity.
export function rollItem(rng, { magicFind = 0, slot = null } = {}) {
  const useSlot = slot || rng.pick(REAL_SLOTS);
  const baseDef = rng.pick(BASES[useSlot]);
  const rarity = rollRarity(rng, magicFind);

  let mods = {};
  const affixNames = { prefix: null, suffix: null };
  if (rarity.affixes >= 1) {
    const p = rng.pick(PREFIXES); mods = sumMods(mods, p.mod); affixNames.prefix = p.name;
  }
  if (rarity.affixes >= 2) {
    const s = rng.pick(SUFFIXES); mods = sumMods(mods, s.mod); affixNames.suffix = s.name;
  }
  // rare items roll extra affixes (stack more of the same pools)
  for (let i = 2; i < rarity.affixes; i++) {
    const pool = rng.next() < 0.5 ? PREFIXES : SUFFIXES;
    mods = sumMods(mods, rng.pick(pool).mod);
  }

  const name = [affixNames.prefix, baseDef.base, affixNames.suffix].filter(Boolean).join(' ');
  const item = {
    id: `gen_${useSlot}_${counter++}`,
    name,
    slot: useSlot,
    rarity: rarity.rarity,
    color: rarity.color,
    passive: mods,
    text: rarity.affixes === 0 ? '(plain)' : modText(mods) || '(plain)',
  };
  if (baseDef.card) item.grants = { cards: [baseDef.card] };
  return item;
}
