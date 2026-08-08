# Ashfall

An action-roguelite prototype: **Diablo II's itemisation inside a Hades-shaped run.**

Godot 4, GDScript, no addons, no asset dependencies. Everything you can see is
placeholder shapes; everything you can't see is tested.

---

## Running it

```bash
godot --path game            # or open game/project.godot in the editor and hit F5
```

Controls: `WASD` move · mouse aim · `LMB`/`J` attack · `Space`/`Shift` dash ·
`R` restart after death.

## Testing it

Two commands, no plugins to install, no editor required:

```bash
godot --headless --path game --import                              # once, generates .godot/
godot --headless --path game --script res://tests/run_tests.gd     # the suite
```

Filter to one file while iterating:

```bash
godot --headless --path game --script res://tests/run_tests.gd -- damage
```

Exits non-zero on failure. CI runs exactly these commands on every push that
touches `game/` — see `.github/workflows/game-tests.yml`.

## Simulating it

```bash
godot --headless --path game --script res://sim/balance_sim.gd -- 2000 0.5
```

Plays whole runs through the real core code and reports depth distribution,
clear rate, time-to-kill by floor, and which boons the winning builds actually
took. Args are `[runs] [dodge_rate]`.

The dodge rate stands in for player skill and is the model's biggest unknown —
sweeping it from `0.3` to `0.7` moves the difficulty curve far more than any
number in `data/`. That is itself a finding: the balance is more sensitive to
how well you dodge than to what you're wearing.

Read the per-floor figures with care: only runs that reached a floor contribute
a sample to it, so deep-floor numbers describe the builds that survived, not the
average build. The report prints `n` alongside each one for that reason.

### What the first run of it found

At 200 runs and `dodge=0.5`, nothing cleared floor 15 — median depth 5, best 11.
More interestingly, the four most-taken boons under a damage-greedy policy were
`ithra_rot`, `morrow_ember`, `karnak_arc` and `vess_rime` at 73–78% each: every
one of them a *flat elemental damage* boon, all four picked nearly every run.

That is the design leaking. Those boons grant `flat.<type>` and `increased.<type>`
— gear's buckets — so against a weak base weapon they beat the `more%` boons the
thesis says should own the power curve. The separation holds in the pipeline (the
tests prove that) but not in the content. Boons wanting a damage identity should
express it as `more%` plus a *behavioural* rider, not as flat damage.

Balance is not tuned and the numbers above are a starting point, not a target.

---

## The design thesis

Bolting the two games together naively fails in a specific way: D2's permanent
gear grind trivialises Hades' per-run power curve. You farm a good weapon once
and every subsequent run opens easy.

So the two systems are given **different jobs**, enforced at the damage
pipeline (`core/damage.gd`):

| | owns | bucket | effect |
|---|---|---|---|
| **Gear** | what your build *is* | flat + `increased%` (additive) | sums, so it flattens out |
| **Boons** | how strong the run *gets* | `more%` (multiplicative) | compounds within a run |

Additive modifiers suffer diminishing returns against each other; multiplicative
ones don't. So gear can be exciting to find without ever owning the power curve.

The second half of the seam is **tags**. Affixes grant tags (`ignite`, `frost`,
`chain`, `brutal`, `venom`, `swift`); boons can require them. A weapon rolling
*Blazing* doesn't mainly mean "+18 fire" — it means Morrow's fire boons are now
in your offer pool. Gear decides *what the run is allowed to become*.

`test_data.gd` enforces this: an affix that ever grants a `more` modifier fails
the build, and a boon gated on a tag no affix can grant fails as dead content.

## Layout

```
core/           pure simulation — no scene tree, fully tested
  rng.gd            seeded, derivable streams (determinism guarantee)
  damage.gd         damage types + the one resolution pipeline
  stat_block.gd     stats + the modifier grammar the JSON speaks
  affix.gd          rollable modifier templates
  item.gd           generated gear
  item_generator.gd rarity, group exclusion, ilvl gating
  boon.gd           run-scoped blessings
  boon_pool.gd      the three-way offer
  run_state.gd      base + gear + boons -> combat stats; enemy scaling
data/           content as JSON, validated by the suite
scenes/         Godot node layer — built in code, placeholder art
  feel.gd           EVERY game-feel constant, in one place (read its header)
sim/            headless balance simulator
tests/          the suite + a ~90-line assertion base class
```

The split is the point: `core/` never imports a scene node, so a run can be
played by a human or fast-forwarded ten thousand times through the *same code*.

## What's real and what isn't

**Real, and covered by ~150 assertions:** the damage pipeline and its
additive/multiplicative split, resistance caps and floors, armour, crit,
determinism from a seed, affix roll ranges, group exclusion, ilvl gating,
rarity-to-affix-count, magic find, boon offers, tag gating, prerequisite chains,
stat rebuilds on unequip, enemy depth scaling, and validation of every key in
both JSON files.

**Placeholder:** all art (circles and wedges), all audio (none), all narrative
(none), one enemy archetype, one weapon behaviour, no meta-progression, no hub,
no bosses.

**Unverified, and unverifiable without a person:** everything in
`scenes/feel.gd`. Dash length, i-frame overhang, hit-stop duration, attack
recovery, knockback, camera lag. Those numbers are genre-plausible guesses. A
test can prove a hit deals 237 damage; nothing can prove the hit feels good.
That file is where a human's work starts.
