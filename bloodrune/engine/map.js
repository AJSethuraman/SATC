// Seeded run map. At each step you're offered up to 3 forward directions and
// commit to one — no backtracking. Node types are weighted; after `length`
// non-boss steps the only way forward is the boss. Pure + deterministic.

export const NODE_TYPES = {
  combat: { id: 'combat', name: 'Prowling Pack', glyph: '⚔️', desc: 'A pack blocks the way.' },
  elite: { id: 'elite', name: 'Elite', glyph: '💀', desc: 'A cursed champion — richer loot.' },
  treasure: { id: 'treasure', name: 'Cache', glyph: '📦', desc: 'Loot, and no fight.' },
  camp: { id: 'camp', name: 'Bloodfire Camp', glyph: '🔥', desc: 'Rest: heal, and grow stronger.' },
  boss: { id: 'boss', name: 'The Flayed Smith', glyph: '🔨', desc: 'The act boss awaits.' },
};

const WEIGHTS = [['combat', 5], ['elite', 2], ['treasure', 2], ['camp', 2]];
const POOL = WEIGHTS.flatMap(([t, w]) => Array(w).fill(t));

export function makeMap({ length = 9 } = {}) {
  return { length, step: 0 };
}

// Up to 3 forward choices for the current step. At the end, only the boss.
export function nextChoices(rng, map) {
  if (map.step >= map.length) return [{ type: 'boss' }];
  return [0, 1, 2].map(() => ({ type: rng.pick(POOL) }));
}
