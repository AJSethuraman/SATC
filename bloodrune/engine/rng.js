// Seeded deterministic PRNG — the ONLY source of randomness in engine/.
// No Math.random() anywhere in engine/, so any run/fight is reproducible from
// its seed and every test can assert exact or statistical outcomes.
//
// Implementation: mulberry32. Small, fast, good enough for a game; fully
// deterministic given a seed. State lives on the returned object so it can be
// serialized (see snapshot()/restore()).

function hashString(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// Normalize any seed (string or number) to a uint32.
export function normalizeSeed(seed) {
  if (typeof seed === 'number') return seed >>> 0;
  return hashString(String(seed));
}

// A tiny stateful RNG object. `next()` returns a float in [0, 1).
export function makeRng(seed) {
  const state = { a: normalizeSeed(seed) };
  const rng = {
    next() {
      state.a |= 0;
      state.a = (state.a + 0x6d2b79f5) | 0;
      let t = Math.imul(state.a ^ (state.a >>> 15), 1 | state.a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    },
    int(n) {
      return Math.floor(rng.next() * n);
    },
    pick(arr) {
      return arr[rng.int(arr.length)];
    },
    // Fisher–Yates using this RNG; returns a new array, leaves input untouched.
    shuffle(arr) {
      const a = arr.slice();
      for (let i = a.length - 1; i > 0; i--) {
        const j = rng.int(i + 1);
        [a[i], a[j]] = [a[j], a[i]];
      }
      return a;
    },
    // For save-state: capture and restore the exact internal position.
    snapshot() {
      return state.a >>> 0;
    },
    restore(a) {
      state.a = a >>> 0;
    },
  };
  return rng;
}
