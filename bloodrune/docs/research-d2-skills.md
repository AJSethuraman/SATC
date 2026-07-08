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

## The tree STRUCTURE — how skills unlock (D2)

A skill tree is not "spend a point, take anything." Two gates:

- **Tier level-requirements.** Skills sit in rows (tiers). The top row is
  available at character level 1; each row down adds **+6** required levels —
  so tiers unlock at **clvl 1 / 6 / 12 / 18 / 24 / 30**. You cannot put a point
  in a skill until you meet its character-level requirement. [5]
- **Prerequisite arrows.** A skill that another points to is a **prerequisite**:
  you must have **≥1 point in every prerequisite** before you can allocate to the
  skill it points to. (E.g. Chilling Armor ← Shiver Armor ← Ice Blast + Frozen
  Armor.) [5]
- **Per-point level gate.** Even after a skill unlocks, "if a skill requires
  level X, to invest point Y you must be level **X + (Y−1)**" — so you can't dump
  a pile of saved points into one skill; its investment paces with your level. [5]
- You earn **1 skill point per level** (plus a few from quests). [6]

### Bloodrune translation (the tree, not just scaling)

- Each skill carries `req` (character-level requirement) and `pre` (prerequisite
  skill ids). `investSkill` refuses a point unless: you have a point to spend,
  the skill is in your class tree, **level ≥ req + currentHardPoints** (the
  per-point gate), and **every prerequisite has ≥1 point**.
- Levels are compressed for a short roguelite run (reqs like 1 / 2 / 4 / 6 / 8
  instead of 1 / 6 / 12 / 18) but the *shape* is D2's: a tier-gated, prereq-
  chained tree where your Whirlwind is a capstone you build toward — you start
  with a weapon's one skill and earn the rest, you don't open the menu with
  everything available.

## Sources
- [1] [Charged Bolt (Diablo II) — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Charged_Bolt_(Diablo_II))
- [2] [Zeal (Diablo II) — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Zeal_(Diablo_II))
- [3] [Raise Skeleton (Diablo II) — Diablo Wiki (Fandom)](https://diablo-archive.fandom.com/wiki/Raise_Skeleton_(Diablo_II))
- [4] [Synergies — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Synergies) ·
  [Synergies — diablowiki](https://diablo2.diablowiki.net/Synergies)
- [5] [Skill Trees — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Skill_Trees)
  (tier level-reqs 1/6/12/18/24/30, prerequisite arrows, per-point level gate)
- [6] [Skill points — Diablo Wiki (Fandom)](https://diablo.fandom.com/wiki/Skill_points)
