// Seeded encounter generation (M1.6). Diablo-style packs: pick a primary pack
// archetype and roll its (mostly homogeneous) members, place any leader/support
// at the BACK so single-target attacks hit the filler first — you must aim to
// reach the shaman. Sometimes a second pack is "dragged in" for a mixed fight.
// Pure + deterministic given the injected rng.

import { PACKS } from './content.js';

function rint(rng, lo, hi) { return lo + rng.int(hi - lo + 1); }

// Append a pack's filler (front) and, unless fillerOnly, its leader (back).
function addPack(out, pack, rng, cap, fillerOnly) {
  const filler = [];
  for (const [type, lo, hi] of pack.filler) {
    const n = rint(rng, lo, hi);
    for (let i = 0; i < n; i++) filler.push(type);
  }
  for (const t of filler) if (out.length < cap) out.push(t);
  if (!fillerOnly && pack.leader && out.length < cap) out.push(pack.leader);
}

// Returns an ordered array of monster ids (index 0 = front of the lane).
export function generateEncounter(rng, { maxMonsters = 8, mixChance = 0.4 } = {}) {
  const ids = Object.keys(PACKS);
  const out = [];
  const primaryId = rng.pick(ids);
  addPack(out, PACKS[primaryId], rng, maxMonsters, false);

  // chance to drag in a different pack's filler (a mixed encounter)
  if (rng.next() < mixChance && out.length < maxMonsters) {
    const others = ids.filter((id) => id !== primaryId);
    const secId = rng.pick(others.length ? others : ids);
    addPack(out, PACKS[secId], rng, maxMonsters, true);
  }

  // guarantee at least one monster (defensive; filler minimums make this rare)
  if (out.length === 0) out.push(PACKS[primaryId].filler[0][0]);
  return out.slice(0, maxMonsters);
}
