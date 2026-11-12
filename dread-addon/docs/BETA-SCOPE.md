# Dread beta: scope

Status: **skill system built and tested; everything else below is proposed, not started.**

## Goal (the owner, 11 Nov 2026)
> end goal for this "beta" will be to have one full character from D2 in our game (i know we may need to "adjust" skills and such) and it should be like the blood moor in d2 or something equivalent basically

> do NOT skimp on how Diablo II works with its skill tree - i want it to have an approximately equal amount of skills/choices with synergies

## Rules this changes
The feasibility spec said "No D2 art, names or text." Decided 11 Nov 2026: **WoW names and WoW art are fine; D2 names and text are not.** Copying how a skill works is fine. So the class is a **Mage**, with a Lightning tree in place of Arcane, and the first zone has its own name.

## What is built
`Dread/Skills.lua` (the table) and `Dread/Tree.lua` (the rules), pure Lua, tested in `tests/test_tree.py`.

- **30 skills, three trees of 10:** Fire, Cold, Lightning.
- **Level gates** at 1, 6, 12, 18, 24, 30. **Prerequisites** always come from an earlier gate, so there are no loops. Some skills need two.
- **Synergies:** every damaging skill gets +% damage per point spent in other skills of its tree. That is the point of the design: Frostbolt gets stronger when you also spend on Ice Lance, Glacial Spike and Frozen Orb, so a build is a choice about which skill to feed.
- **One mastery per tree**, each doing something different: Master of Flame (fire damage), Piercing Cold (lowers enemy cold resist; immune monsters only lose a fifth of it), Conductor (cheaper lightning mana).
- **Point budget:** `level + quest points`. At level 30 with 12 quest points that is 42 points against 30 skills x 20, so you cannot have everything (tested).
- **Cap of 20 points per skill.**

### The tree
| Gate | Fire | Cold | Lightning |
|---|---|---|---|
| 1 | Scorch | Frostbolt, Ice Barrier | Arcing Bolts |
| 6 | Evocation, Dragon's Breath | Frost Nova, Ice Lance, Frost Armor | Static Shock, Force Pull |
| 12 | Blazing Speed | | Thunder Nova |
| 18 | Fireball | Glacial Spike | Lightning Bolt, Chain Lightning, Blink |
| 24 | Flamestrike | Blizzard, Icicle Cloak | Storm Cloud, Mana Shield |
| 30 | Combustion, Meteor, Master of Flame, Flame Spirit | Frozen Orb, Piercing Cold | Conductor |

Run `/dread skills` in game to list it with prerequisites.

## Not verified
- The D2 details above (gates, the 20-point cap, quest points, what each mastery does) are from the owner's brief and my memory of the game. **I have not checked them against a source.** They are design inputs, not claims about D2.
- **Every number in `Skills.lua` is a placeholder to tune by playing.** Damage, mana and synergy percentages are mine.
- Lightning has 5 damaging skills against 7 in Fire and Cold; its other five are utility, buffs and a mastery. Say if you want it to have more attacks.

## Proposed next (not started, needs approval)
1. **Character:** stats (life, mana, and what each stat does), levels, experience.
2. **Combat:** projectiles, area hits and status effects (chill, freeze, burn) driven by the skill table; monster resistances and immunities.
3. **The zone:** an outdoor field with its own name, 4 or 5 monster types, one rare monster, a cave below it with a boss, and a first quest that pays one skill point.
4. **Loot:** normal / magic / rare / unique with random affixes; inventory and stash.
5. **Saving:** SavedVariables for the character, points and stash.
6. **Skill screen:** the tree drawn in a window with the arrows, click to spend a point.
