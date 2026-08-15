# Difficulty passes, item tiers, and what you get to keep

## The shape

A run is a **full pass through the game at escalating difficulty**, the way
Diablo II is: the same acts, replayed harder, three times.

```
run = Normal(5 acts) -> Nightmare(5 acts) -> Hell(5 acts)
      5 acts x 8 areas x 3 difficulties = 120 areas
```

The areas are the *same places* each pass. The Cinderwaste in Hell is the
Cinderwaste, not a new region — which is why difficulty is a separate axis from
act rather than more acts bolted on the end. Act names and area names are
unchanged across passes; only what lives there changes.

Terms are D2's because they are instantly legible. They are not load-bearing and
can be renamed without touching anything structural.

## Why this fixes a measured problem

The acquisition simulator was asked where the chase actually stalls. Answer:

    Conflagrant  median 19 | p90 151    blocked on: both 83%  vessel 2%  sigils 15%
    Ruin         median 91 | p90 294    blocked on: both 34%  vessel 0%  sigils 66%

Vessel-only blocking is 2% and 0% — the vessel is essentially never the last
thing you wait for. It is sigils, and the reason is visible in the table:

| tier | sigils |
|---|---|
| 1 | ash, cinder, hoar, spark |
| 2 | bile, ord, vow |
| 3 | pyre, rime, storm |
| 4 | rot |
| 5 | doom |

Transmutation walks up to *the commonest sigil of the next tier*, so from tier 2
you always get `pyre`. **`rime` and `storm` cannot be reached by grinding at
all.** A recipe wanting one is pure drop luck forever and surplus never helps.

Diablo II does not have this problem because its cube recipe is a **total
order** — El → Eld → Tir → … → Zod. Every rune is reachable by grinding upward;
the only question is how much you are willing to convert.

So two fixes, and they are the same fix seen from two sides:

1. **Transmutation becomes a total order** over all twelve sigils, not a jump to
   the commonest of the next tier. Any sigil is reachable from any lower one.
2. **Depth, not luck, gates the good components.** High sigils do not drop in
   Normal at all. Getting `doom` is a question of reaching Hell, which is a
   question of being good enough — not of repeating Normal four hundred times.

## Item tiers

The same base returns at higher difficulty as a strictly better version, with
more sockets. This is D2's Normal / Exceptional / Elite ladder.

| tier | first available | sockets |
|---|---|---|
| plain | Normal | up to 2 |
| exceptional | Nightmare | up to 3 |
| elite | Hell | up to 4 |

A three-sigil inscription therefore *cannot* be made until Nightmare, and the
four-sigil ones not until Hell. That is a gate you clear by playing well rather
than by rolling dice, which is the whole point of the change.

## What you keep

The old rule was: **only raw sigils and empty vessels may be banked, never a
completed item.** It existed to stop the run collapsing into "farm one good
weapon, then every subsequent run opens easy" — a failure mode the balance
simulator identified directly.

The new rule inverts what is stored and keeps the thing that mattered:

> **You may bank a finished item. You must assemble it inside a single run.**

What counts as finished is anything that is not a roll: a completed inscription,
a unique, a set piece. A rare stays out — banking rolls would turn the one hard
choice a run makes into a ratchet, since the next rare is always a reroll of the
last one. A unique is the same item every time, so keeping one is a decision
about which item you want rather than which roll you got.

The grind moves from hoarding components across runs to getting deep enough, in
one run, to hold everything at once. And the old failure mode does not return,
because a runeword made in Normal is outscaled by Nightmare — a banked item is a
leg up for the *next run's early game*, letting you reach depth faster, so you
can farm the components that only exist deeper. That ladder is the progression.

## Three ways to be powerful

- **Runewords** — the highest average power, and the only one you assemble.
  Requires the base, the sockets, and the exact sigils, all in one run.
- **Uniques** — fixed, named, findable. No assembly.
- **Sets** — weak alone, strong assembled; the horizontal version of a runeword.

Runewords being strongest *on average* is what keeps the assembly loop the
centre of the game, while uniques and sets mean a run that never lines up its
sigils can still produce something worth banking.

## Build order

1. **Difficulty axis** — Progression grows a difficulty, acts go 4 → 5, scaling
   gains a per-difficulty step. Everything else depends on this.
2. **Transmutation total order** — small, and independently fixes the tail.
3. **Item tiers** — bases gain a tier and a minimum difficulty.
4. **Reliquary flip** — bank finished items, assembled in-run.
5. **Uniques and sets** — a new rarity axis in the generator.

## Open

- Run length. 120 areas at current pacing is roughly twenty minutes. That is
  long for a roguelite and short for Diablo. Measure before deciding.
- Whether Hell should gate on *clearing* Nightmare or merely reaching it.
- Whether a banked item should be usable immediately or cost something.
