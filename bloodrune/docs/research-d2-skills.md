# Research: Diablo 2 skill scaling & synergies → Bloodrune design

Grounds the "skills scale uniquely" + skill-tree design. Sources at the bottom.

## What D2 actually does

- **Skills have a level (1–20 hard, higher via gear).** A skill's numbers are a
  function of its *level*, not a flat global damage bonus.
- **+Skills gear raises the level ("soft points").** So "+1 to Skills" makes each
  skill behave as if one level higher — which means it scales in **that skill's
  own way**, not "+1 damage."
- **Each skill scales differently:**
  - **Charged Bolt** — **+1 bolt per level** (more projectiles). [1]
  - **Zeal** — **+1 hit per level**, capped at 5 (more consecutive strikes). [2]
  - **Raise Skeleton** — **+1 skeleton per point** (bigger army). [3]
  - Others scale damage, radius, or duration per level.
- **Synergies** — hard points in one skill boost another by a % per level.
  Formula: `Final = [Base + (Level−1)·Growth] · (1 + Synergy)`. **Only hard
  points** (spent in the tree) grant synergy; **soft points** (+skills from gear)
  raise the level but don't add synergy. [4]

## Bloodrune translation (design)

- **A skill = a card with a level.** `effectiveLevel = hardPoints[skill] +
  plusSkills(gear)`.
- **Learn a skill from the tree → it enters your deck** (1 hard point). Spend more
  points to raise its level. `+X to Skills` gear raises every skill's level.
- **Each skill has its own scaling function** (this is the "+1 skills ≠ +1
  damage" the design wants):
  - **Zeal** → hits `min(5, 1+level)` times (single-target multi-hit).
  - **Charged Bolt** → fires `level` bolts spread across the front cluster.
  - **Cleave** → damage `base + 2·(level−1)`, and reach widens at higher levels.
  - **Fireball** → damage `base + 3·(level−1)`, splash to the next band at high level.
  - **Raise Skeleton** (Necro, later) → `1 + floor(level/2)` skeletons.
- **Synergies** — a skill lists which other skills boost it and by how much per
  **hard** point (build depth; specialization pays off). Soft points (+skills)
  don't feed synergies — same blessing/curse tradeoff as class-specific effects.

## Sources
- [1] [Charged Bolt (Diablo II) — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Charged_Bolt_(Diablo_II))
- [2] [Zeal (Diablo II) — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Zeal_(Diablo_II))
- [3] [Raise Skeleton (Diablo II) — Diablo Wiki (Fandom)](https://diablo-archive.fandom.com/wiki/Raise_Skeleton_(Diablo_II))
- [4] [Synergies — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Synergies) ·
  [Synergies — diablowiki](https://diablo2.diablowiki.net/Synergies)
