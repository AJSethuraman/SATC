# Bloodrune — Design Doc

The reference we build from, so genre-obvious requirements are on the table
*before* they show up as bugs in playtesting. Grounded in Diablo 2 (see
`research-d2-skills.md` and the research notes folded in below). Living doc.

> **Status legend:** ✅ built · 🟡 partial · ⬜ not yet · ❓ open decision

---

## 1. Pillars (the fantasy)

1. **Diablo 2, turned tactical.** The D2 fantasy — a dark gothic crawl, a
   character *body* you gear, skills you spec into, loot that defines you —
   expressed as **turn-based tactical combat** instead of real-time clicking.
   Explicitly D2, not the sanitized feel of D3/D4.
2. **Surrounded and outnumbered.** You are one hero ringed by a horde.
   Positioning is abstracted to **rings + an engagement cap**; the tension is
   *who can reach whom* and *who do I kill first* (the healer, the rezzer, the
   elite).
3. **Start naked, become a god — or die.** Begin with one weapon-granted skill;
   scale through XP, the skill tree, and loot. Some runs you fix your build's
   weakness; some you die to it. Permadeath roguelite.
4. **Your build is your character.** Class + skill tree + **weapon type** + gear
   = a distinct way to fight. Items must matter (weapon damage feeds skills;
   affixes should change how you *play*, not just raise a number). Specialization
   pays off.
5. **Readable depth.** Every mechanic is telegraphed and legible — enemy intents,
   reach, "out of reach", waiting foes, damage ranges. Complexity comes from
   systems interacting, not hidden math or twitch.

---

## 2. What's built today

### Combat — the surrounded arena ✅
- **Rings:** inner (melee-reachable) / outer (casters & archers). Melee reaches
  only the frontmost living rank; clear the front and the back is **pinned**.
  Reach skills (Charge / ranged / summons) strike past a living screen.
- **Engagement cap:** only ~4 melee foes reach you per turn; the rest **wait**
  and step up as front-liners fall. Decouples horde *size* from incoming *damage*.
- **Abilities, not cards:** always available, **Mana-gated**, roll damage in
  **ranges**. Mana is a **regenerating pool** (open full, regen a few/turn) — no
  free per-turn refill, so spamming one skill drains you.
- **Guarded casters / breakthrough / Exposed:** a guarded caster takes reduced
  damage; Charge/Pierce pierce the guard but leave you Exposed next enemy phase.
- **Reactive casters:** the Shaman (and rezzer super uniques) **channel** and, at
  end of round, react to the casualties you just caused — raise a slain grunt
  (capped) or mend the most-wounded. "Kill the rezzer first."
- **Summons:** the Necromancer's skeletons **body-block** the surround and strike
  your focus; they shatter and must be re-raised (Mana tradeoff).

### Characters 🟡
- 3 classes: **Barbarian** (melee + Charge to reach), **Amazon** (ranged reach),
  **Necromancer** (summons + spell damage, weapon-independent).
- **Skill tree** ✅ — D2-style **level-req tiers + prerequisite arrows +
  per-point level gate**; capstones (Whirlwind req 8) you build toward. `+Skills`
  gear raises every skill's level.
- Each skill **scales its own way** (Zeal +1 hit/level, Raise Skeleton +1
  skeleton/2 levels, damage skills grow per level).
- **No attributes** (Str/Dex/Vit/Energy) ⬜ · **no synergies** ⬜ · **no respec** ⬜.

### Items 🟡
- **Weapons** ✅ carry damage + a **type** (melee/ranged/focus). A physical
  skill's base damage **is** the equipped weapon's damage × the skill's factor —
  a better axe = a harder Cleave; wrong type = you flail. Focus weapons power the
  Necro's spells (which scale on +Skills).
- **Armor/jewelry** ✅ roll prefix/suffix affixes at rarities normal/magic/rare.
- **No sockets/runes/runewords** ⬜ · **no set/unique items** ⬜ · **no item-level
  affix gating** ⬜ · **no gold/vendors/gambling** ⬜.

### Monsters 🟡
- Roster: fallen, zombie, goatman, guardian, shaman (heal+rez), archer.
- **Elite affixes** (frenzied/brutal/hardened/vampiric) 🟡 — only 4 of D2's ~20.
- **Super uniques** ✅ — named leaders + minions + a signature (Blood Raven rez,
  Rakanishu double-strike, Corpsefire leech, Bishibosh heal+rez), gated to mid-run.
- **One act boss** (the Flayed Smith). One difficulty. ⬜ no NM/Hell, no 2nd act.

### The run / loop 🟡
- Descend a **9-step branching blind map** (Combat / Elite / Super-unique /
  Treasure / Camp / Boss). XP→levels→skill points + loot. Permadeath.
- Minimal meta (localStorage). ⬜ no gold, vendors, gambling, town, waypoints,
  potions/consumables, or real meta-progression.

---

## 3. Fantasy Gaps — the backlog (my first cut; research is enriching this)

Ranked roughly by **impact-to-effort**. These are the "obvious in terms of
design and fantasy" items — the things a D2 grounding demands that we don't have.

| # | Gap | Why it matters | Sketch |
|---|-----|----------------|--------|
| 1 | **Accuracy & Dodge/Evade** ⬜ | Everything auto-hits; the Amazon has no signature avoidance. You explicitly want accuracy to matter and evade to be "not punitive but real." | A hit-chance roll (attacker accuracy vs target evade), telegraphed as a %; Amazon gets an innate Dodge% avoid roll. |
| 2 | **Resistances & elemental damage** ⬜ | Everything is physical → no build adaptation, no "this pack resists fire, swap." The spine of D2 build variety and difficulty. | Add fire/cold/lightning/poison to some skills & enemies; enemies carry resists/immunities; gear grants res. Cold = slow, poison = DoT, etc. |
| 3 | **Sockets + runes + runewords** ⬜ | The signature D2 hook, promised in the PRD. The best "loot excitement" per unit effort. | Items roll sockets; runes drop; ordered rune recipes = runewords granting skills/mods. |
| 4 | **Set & unique items** ⬜ | Chase loot that *defines* a build; the dopamine of a gold/green drop. | A small table of named uniques with build-warping mods; a 2–3 piece set. |
| 5 | **Attributes (Str/Dex/Vit/Energy)** ❓ | D2's per-level stat choice; gear requirements; ties Dex→accuracy/block, Vit→life. | Stat points per level; or fold into a lighter roguelite model. Decision: full attributes vs streamlined. |
| 6 | **More monster affixes / curses** ⬜ | D2's ~20 boss mods (Extra Fast, Cursed, Aura Enchanted, Mana Burn, Cold/Fire Enchanted…) are what create "oh no" packs. | Add a handful with the most tactical texture; some debuff the player. |
| 7 | **Skill synergies** ⬜ | Hard points in one skill boosting another = specialization depth, the reason to go deep not wide. | Each skill lists synergy skills; hard points add %. |
| 8 | **Economy: gold / vendors / gambling / potions** ⬜ | The town rhythm and the "spend to gear/heal" loop; potions are core ARPG safety. | Gold drops; a between-node vendor/gamble; healing/mana potions with a belt limit. |
| 9 | **Depth beyond one act** ❓ | One act, one difficulty caps the run. Roguelite answer may be escalating descent rather than NM/Hell. | Longer/looping descent with rising area level, or Normal→Nightmare tiers. |
| 10 | **Mercenary / hireling** ⬜ | An ally that adds a tactical body & an aura; classic D2 flavor. | A hireable unit that acts each turn; auras buff you. |

---

## 4. Open decisions to talk through
- **Attributes:** full Str/Dex/Vit/Energy with level-up allocation, or a leaner
  roguelite stat model? (Affects accuracy, block, life, gear reqs.)
- **Damage types:** how far into elemental/resist land do we go for a turn-based
  roguelite — full 4 elements + immunities, or a lighter 2–3?
- **Run shape:** deepen one escalating descent, or add Nightmare/Hell tiers?
- **Economy weight:** how much town/vendor/gold, vs. keeping the run lean and
  combat-forward?

---

*Next: fold in the five research streams (itemization, character systems, combat
math, monsters/difficulty, core-loop/feel) with citations, then sequence the
backlog with you.*
