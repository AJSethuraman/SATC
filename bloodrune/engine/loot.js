// Seeded loot generation — the S3 rework. An item is base + rarity + tier +
// affixes. Rarity (common/magic/rare/unique) widens the affix space; the drop
// TIER (Normal/Nightmare/Hell) multiplies affix magnitudes, so a Normal item can
// NEVER rival a Nightmare one, nor Nightmare a Hell one. Affixes carry build
// `tags` — most rolls are off-build sidegrades, so only a slice are real upgrades
// for any ONE build (that's what `itemScore`/`isUpgradeFor` measure against a
// class profile). Uniques are fixed items pulled from a minTier-gated table.
// Pure + deterministic given the injected rng.

import { BASES, RARITY, AFFIXES, TIER_MULT, ITEM_TIERS, UNIQUES, CLASS_PROFILE, SLOTS, RUNES, RUNEWORDS, RUNE_BY_ID } from './content.js';

// armor/jewelry slots only (weapons are separate skill-granters; ring2 shares 'ring').
const REAL_SLOTS = SLOTS.filter((s) => s !== 'ring2' && s !== 'weapon').map((s) => (s === 'ring1' ? 'ring' : s));
const TIER_INDEX = Object.fromEntries(ITEM_TIERS.map((t, i) => [t, i]));

// Equip requirements climb with the drop tier — a Hell Plate demands far more Str
// than a Normal one, so the greed-punisher (all-Energy caster locked out of heavy
// gear) bites harder deeper in. LEVEL_REQ also gates by tier + rarity.
const REQ_TIER = { Normal: 1, Nightmare: 1.6, Hell: 2.3 };
const LEVEL_REQ = { Normal: 1, Nightmare: 14, Hell: 26 };

// Build an item's { str, dex, level } requirement from its base + drop tier + rarity.
function reqFor(baseDef, tier, rarity) {
  const f = REQ_TIER[tier] || 1;
  const req = {};
  const str = Math.round((baseDef.str || 0) * f);
  const dex = Math.round((baseDef.dex || 0) * f);
  if (str) req.str = str;
  if (dex) req.dex = dex;
  const lvl = (LEVEL_REQ[tier] || 1) + (rarity === 'rare' ? 4 : rarity === 'magic' ? 2 : 0);
  if (lvl > 1) req.level = lvl;
  return req;
}

// flavor names for rares (D2-style two-word titles)
const RARE_PRE = ['Bramble', 'Gale', 'Corpse', 'Dread', 'Storm', 'Vortex', 'Doom', 'Grim', 'Hailstone', 'Ember', 'Rune', 'Venom', 'Blight', 'Soul', 'Wraith', 'Shadow'];
const RARE_SUF = ['Song', 'Bite', 'Shard', 'Coil', 'Ward', 'Whisper', 'Grasp', 'Sunder', 'Veil', 'Root', 'Fang', 'Sigil'];

function sumMods(a, b) {
  const out = { ...a };
  for (const [k, v] of Object.entries(b)) out[k] = (out[k] || 0) + v;
  return out;
}

function rollRarity(rng, magicFind) {
  // Magic Find shifts weight off 'common' toward the better tiers.
  const mf = Math.max(0, magicFind || 0);
  const weights = RARITY.map((r) => {
    if (r.rarity === 'common') return Math.max(1, r.weight - mf);
    if (r.rarity === 'magic') return r.weight + mf * 0.5;
    if (r.rarity === 'rare') return r.weight + mf * 0.4;
    return r.weight + mf * 0.15; // unique
  });
  const total = weights.reduce((a, b) => a + b, 0);
  let roll = rng.next() * total;
  for (let i = 0; i < RARITY.length; i++) {
    if ((roll -= weights[i]) < 0) return RARITY[i];
  }
  return RARITY[0];
}

// Roll ONE affix stat value at a given tier. plusSkills is the premium stat — it
// does NOT multiply by tier magnitude (that would mint +4-skill gloves); instead
// higher tiers add a flat +1 (Normal +1, NM +2, Hell +3). penetration stays a
// fraction (never rounded to an int). Everything else scales by TIER_MULT.
function rollStat(rng, key, range, tier) {
  const base = range[0] + rng.next() * (range[1] - range[0]);
  if (key === 'plusSkills') return Math.round(base) + (TIER_INDEX[tier] || 0);
  if (key === 'penetration') return Math.round(base * (TIER_MULT[tier] || 1) * 1000) / 1000;
  return Math.max(1, Math.round(base * (TIER_MULT[tier] || 1)));
}

// Pick `count` DISTINCT affixes. `prefer` (a build tag like 'caster'/'melee')
// biases ~75% of rolls toward on-build affixes so your drops are actually FOR your
// build — you find gear you can use, not a stream of wrong-class junk.
function pickAffixes(rng, count, prefer) {
  const pool = AFFIXES.slice();
  const out = [];
  for (let i = 0; i < count && pool.length; i++) {
    let idx;
    const pref = prefer ? pool.filter((a) => (a.tags || []).includes(prefer) || (a.tags || []).includes('all')) : [];
    if (pref.length && rng.next() < 0.75) { idx = pool.indexOf(pref[Math.floor(rng.next() * pref.length)]); }
    else idx = Math.floor(rng.next() * pool.length);
    out.push(pool.splice(idx, 1)[0]);
  }
  return out;
}

const KEY_TEXT = {
  maxLife: (v) => `+${v} Life`, maxMana: (v) => `+${v} Mana`, manaRegen: (v) => `+${v} Mana Regen`,
  plusSkills: (v) => `+${v} to Skills`, fcr: (v) => `+${v}% Faster Cast Rate`, ias: (v) => `+${v}% Attack Speed`,
  penetration: (v) => `-${Math.round(v * 100)}% to Enemy Resist`, accuracy: (v) => `+${v} Accuracy`,
  evade: (v) => `+${v} Evade`, startBlock: (v) => `+${v} Block`, energy: (v) => `+${v} Energy`,
  str: (v) => `+${v} Strength`, dex: (v) => `+${v} Dexterity`, vit: (v) => `+${v} Vitality`,
};
function modText(mods) {
  const parts = [];
  for (const [k, v] of Object.entries(mods)) { if (KEY_TEXT[k] && v) parts.push(KEY_TEXT[k](v)); }
  return parts.join(', ');
}

let counter = 0; // uniquifies generated item ids within a session

// Pull a fixed unique for a slot at a tier (minTier-gated). Returns null if none
// eligible (caller downgrades to rare).
function pickUnique(rng, slot, tier) {
  const ti = TIER_INDEX[tier] || 0;
  const pool = UNIQUES.filter((u) => (!slot || u.slot === slot) && ti >= (TIER_INDEX[u.minTier] || 0));
  if (!pool.length) return null;
  return pool[Math.floor(rng.next() * pool.length)];
}

// Generate one random item. `tier` gates affix magnitude (and which uniques can
// appear); `magicFind` biases rarity upward; `slot` forces a slot; `allowUnique`
// lets callers suppress uniques (e.g. guaranteed non-unique drops).
export function rollItem(rng, { tier = 'Normal', magicFind = 0, slot = null, allowUnique = true, prefer = null } = {}) {
  const useTier = TIER_MULT[tier] ? tier : 'Normal';
  const useSlot = slot || rng.pick(REAL_SLOTS);
  let rarity = rollRarity(rng, magicFind);

  // ---- unique: a fixed item from the table ----
  if (rarity.rarity === 'unique' && allowUnique) {
    const u = pickUnique(rng, useSlot, useTier);
    if (u) {
      return {
        id: `${u.id}_${counter++}`, uid: u.id, name: u.name, slot: u.slot, rarity: 'unique',
        itemTier: useTier, color: rarity.color, unique: true, enabler: !!u.enabler,
        passive: { ...u.passive }, affixes: [], tags: ['unique'],
        req: { level: LEVEL_REQ[useTier] || 1 }, text: u.text,
      };
    }
    rarity = RARITY.find((r) => r.rarity === 'rare'); // no eligible unique -> rare
  }

  // ---- common/magic/rare: rolled affixes ----
  const baseDef = rng.pick(BASES[useSlot]);
  const affixCount = rarity.affixes === 0 ? 0
    : rarity.affixes + Math.floor(rng.next() * (rarity.affixMax - rarity.affixes + 1));
  const chosen = pickAffixes(rng, affixCount, prefer);

  let mods = {};
  const affixNames = [];
  const tagSet = new Set();
  for (const af of chosen) {
    let rolled = {};
    for (const [key, range] of Object.entries(af.mod)) rolled[key] = rollStat(rng, key, range, useTier);
    mods = sumMods(mods, rolled);
    affixNames.push({ name: af.name, pos: af.pos });
    (af.tags || []).forEach((t) => tagSet.add(t));
  }

  // name: magic uses prefix/suffix; rare gets a flavor title; common is plain.
  let name;
  if (rarity.rarity === 'common' || affixNames.length === 0) {
    name = baseDef.base;
  } else if (rarity.rarity === 'magic') {
    const pre = affixNames.find((a) => a.pos === 'prefix');
    const suf = affixNames.find((a) => a.pos === 'suffix');
    name = [pre && pre.name, baseDef.base, suf && suf.name].filter(Boolean).join(' ');
  } else {
    name = `${rng.pick(RARE_PRE)} ${rng.pick(RARE_SUF)} ${baseDef.base}`;
  }

  return {
    id: `gen_${useSlot}_${counter++}`, name, slot: useSlot, rarity: rarity.rarity,
    itemTier: useTier, color: rarity.color, passive: mods,
    affixes: affixNames.map((a) => a.name), tags: [...tagSet],
    req: reqFor(baseDef, useTier, rarity.rarity),
    sockets: rollSockets(rng, useSlot, useTier), socketRunes: [], socketMods: {},
    text: affixNames.length ? (modText(mods) || '(plain)') : '(plain)',
  };
}

// Socketable bases (armor/jewelry loot.js produces): how many sockets they CAN
// hold. The drop tier caps how many actually roll — deeper drops carry more, and a
// 4-socket offhand (for Spirit) only shows up at Hell.
const SOCKETABLE = { body: 3, helm: 2, offhand: 4 };
function rollSockets(rng, slot, tier) {
  const cap = SOCKETABLE[slot]; if (!cap) return 0;
  if (rng.next() >= 0.5) return 0; // ~half of socketable bases roll clean
  const max = Math.min(cap, 2 + (TIER_INDEX[tier] || 0));
  return 1 + Math.floor(rng.next() * max);
}

// Resolve an item's socket contribution — PURE. If every socket is filled with a
// runeword's exact rune SEQUENCE (on a base in its slot list), it returns that
// runeword's fixed mods; otherwise the socketed runes each add their small mod.
export function resolveSockets(slot, sockets, runeIds) {
  const runes = runeIds || [];
  const rw = RUNEWORDS.find((w) => w.slots.includes(slot) && w.runes.length === sockets
    && runes.length === sockets && w.runes.every((r, i) => r === runes[i]));
  if (rw) return { runeword: rw.name, mods: { ...rw.mods } };
  const mods = {};
  for (const rid of runes) { const r = RUNE_BY_ID[rid]; if (r) for (const [k, v] of Object.entries(r.mod)) mods[k] = (mods[k] || 0) + v; }
  return { runeword: null, mods };
}

// Roll a RUNE drop, tier-gated (high runes only appear deeper). Returns a rune
// "item" that lives in the bag/stash like loot and is consumed by socketing.
export function rollRune(rng, tier = 'Normal') {
  const ti = TIER_INDEX[tier] || 0;
  const pool = RUNES.filter((r) => ti >= (TIER_INDEX[r.minTier] || 0));
  const r = pool[Math.floor(rng.next() * pool.length)] || RUNES[0];
  return { id: `rune_${r.id}_${counter++}`, isRune: true, runeId: r.id, name: `${r.name} Rune`, slot: 'rune',
    rarity: 'rune', color: '#d98b3a', itemTier: tier, mod: { ...r.mod }, text: `${r.name} — socket it (${modText(r.mod)}).` };
}

// ---- build-fit scoring -----------------------------------------------------
// How much an item is WORTH to a build: sum of its stat mods weighted by the
// class profile. Off-build stats (ias/accuracy for a caster) weigh ~0, so most
// random drops score low for any one build. `profile` is a CLASS_PROFILE entry
// or a class id string.
export function itemScore(item, profile) {
  if (!item) return 0;
  const w = typeof profile === 'string' ? CLASS_PROFILE[profile] : profile;
  if (!w) return 0;
  let score = 0;
  const mods = item.passive || {};
  for (const [k, v] of Object.entries(mods)) score += (w[k] || 0) * v;
  return Math.round(score * 100) / 100;
}

// Is `item` a strict build-upgrade over what's `equipped` in its slot for this
// profile? An empty slot scores 0, so any positive-value item fills it.
export function isUpgradeFor(item, equipped, profile) {
  if (!item) return false;
  return itemScore(item, profile) > itemScore(equipped, profile);
}
