# How Diablo II actually paced its rune economy

Research notes taken while tuning Ashfall's sigil/inscription acquisition, after
the acquisition simulator reported a median of **57 runs** for a mid-tier
inscription and **176** for the top one — numbers that felt wrong but that I had
no reference point to judge.

The headline finding inverts the assumption I was working from.

---

## 1. D2's rarest runes are rarer than mine, not less rare

> "The chance of a rune dropped by a level 81+ monster being a Zod is 1:5171."
> — [Diablo Wiki, Rune hunting](https://diablo2.diablowiki.net/Rune_hunting) (via search index)

That is **conditional on a rune dropping at all**. Per monster kill the numbers
are far bleaker:

> "Normal Cows (Hell Bovines) have a 1:730,000 chance to drop a Ber rune, and an
> abysmal 1:2,560,000 chance to drop a Zod rune."
> — [PureDiablo, Rune Farming](https://www.purediablo.com/diablo-2/diablo-2-rune-farming)

There are **33 runes**, El (#1) through Zod (#33).
— [Icy Veins, Rune Guide](https://www.icy-veins.com/d2/rune-guide-a-complete-list)

Ashfall's rarest sigil, `doom`, sits at weight 1 against a table summing to about
150 — roughly **1:150 conditional on a sigil dropping**. That is *thirty times
more generous* than Zod.

**So rarity was never the problem.** D2's top runes are far rarer than mine and
still feel attainable. What D2 has that Ashfall does not is everything that
happens *after* a miss.

## 2. Surplus converts upward — the pity mechanic I was missing

The Horadric Cube upgrades runes, and the ratio *tightens* toward the top:

| band | recipe |
|---|---|
| El → Thul | **3** of a rune → the next |
| Amn → Lo | **3** of a rune + a gem → the next |
| Lo → Sur → Ber → Jah → Cham → Zod | **2** of a rune + a gem → the next |

> "For El through Thul, you need 3 lower ranked runes of the same type… Once you
> reach Amn you'll need to start combining a gem along with the three runes… For
> the high-tier runes, you only need two copies of the same rune and a
> flawed/regular/flawless gem."
> — [Almar's Guides, High Rune Cube Recipes](https://almarsguides.com/Computer/Games/Diablo2/Crafting/HoradricCube/Runes/);
> corroborated by [PureDiablo, Horadric Cube Recipes](https://www.purediablo.com/diablo-2/horadric-cube-recipes)

This is the crucial design point. **No drop is ever wasted** — commons you will
never use are the raw material for the rune you are chasing. It converts a
lottery into a grind with a floor, and the 3:1 → 2:1 tightening means the hardest
steps are proportionally *cheaper*, not more expensive.

The end-to-end cost is still absurd, which is the joke:

> "To create your own Zod from El runes you would need 14,281,868,906,496 El
> runes and 1,088,393,215 assorted gems."
> — [Diablo Wiki, Rune hunting](https://diablo2.diablowiki.net/Rune_hunting)

But nobody converts from the bottom. They convert from the *surplus tier they are
already swimming in*, which is one or two steps below their target.

## 3. Targeted farming, with a deliberate ceiling

> "The only monster in the game with a substantially higher % chance to drop runes
> is The Countess… she can not drop the highest runes in the game."
> — [Diablo Wiki, Rune hunting](https://diablo2.diablowiki.net/Rune_hunting)

A repeatable, reliable source of *low and mid* runes, explicitly capped so it
cannot short-circuit the top of the ladder. It exists to feed the cube, not to
replace it.

## 4. Runewords require an **exact** socket count

> "Socketed items must have the exact number of sockets as the runeword formula
> requires. If the runeword is a 3 rune formula, you must use an item with
> exactly 3 sockets. A 4 socket item will not work with a 3 socket formula."
> — [d2db, Runeword Guide](https://d2db.net/runeword-guide)

And only on plain items:

> "Runewords will only work in socketed non-magical items, and the socketed item
> type must be the correct item type for the formula."
> — same source

Ashfall already had the non-magical rule. It did **not** have exact-socket
matching — a 3-socket vessel would happily form a 2-sigil word, which made
2-socket vessels nearly worthless and blunted the banking choice.

## 5. Scale

**99 runewords** across 33 runes — about three recipes per rune.
— [Wowhead, D2R Runewords](https://www.wowhead.com/diablo-2/guide/runewords-types-bonuses-sockets)

Ashfall has 9 inscriptions across 12 sigils: **0.75 per sigil**, a quarter of
D2's density. Fewer recipes per component means most drops point at nothing.

---

## What this implies for Ashfall

1. **Do not raise drop rates.** They are already far more generous than D2's.
2. **Add transmutation.** 3 sigils of a tier → 1 of the next, tightening to 2:1
   at the top. This is the single highest-value change: it makes every junk drop
   progress toward the chase and puts a ceiling on bad luck.
3. **Adopt exact-socket matching.** It costs nothing and makes socket counts
   genuinely distinct, sharpening "which vessel do I bank?".
4. **Raise recipe density** over time — more inscriptions per sigil, so a given
   drop is more often relevant to something.
5. **Consider a capped targeted source** later — a floor or encounter with
   elevated sigil odds but no top-tier sigils, feeding transmutation rather than
   bypassing it.

## Confidence and open questions

**High confidence:** rune count (33); the cube upgrade ratios and where they
change; exact-socket matching; non-magical bases only; Countess as a capped
targeted farm; Zod at 1:5171 conditional on a rune drop.

**Medium confidence:** the 99 runeword count is D2R-era and patch-dependent;
different sources count differently depending on whether ladder-only and
patch-added words are included.

**Unverified:** I could not source an exact per-rune rarity ratio — whether each
consecutive rune is a fixed fraction as common as the one below it, or whether
the curve is irregular. Several sources describe the scaling qualitatively but
none I reached gave the table. The Phrozen Keep's "Altering Rune Drop Rate"
article and the silospen drop calculator would settle it; both were unreachable
from this environment.

**Method note:** `WebFetch` was egress-blocked for every Diablo wiki domain I
tried, so these citations come from search-index summaries of those pages rather
than from pages I read directly. Quotes are reproduced as returned. Anything
load-bearing should be re-checked against the primary page before being treated
as exact.
