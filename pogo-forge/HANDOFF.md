# Handing this to Claude Code

## What this is

A local Pokémon GO decision tool. Two builds share one engine:

- **Python + FastAPI** (`app.py`) — roster, particle ledger, planner
- **Single HTML file** (`../pogo-forge-standalone/`) — same engine ported to JS,
  no server, runs from a phone

`gamedata.json` is extracted from Niantic's published game master by
`fetch_gamedata.py`. Nothing in it is a community estimate.

## The one rule for this codebase

**Every test must be anchored to something knowable outside this code.**

Published max-CP figures. Documented type relationships. Real screenshots whose
IVs are confirmed by a separate formula. A test asserting that the code does
what the code currently does proves nothing and will happily lock in a bug.

This is not theoretical. Building this found four real defects, every one
caught by an external check rather than by reasoning:

1. `power_up_cost` billed for the free Best Buddy level — overstating every
   max-level plan by 30,000 dust. Caught by comparing 49→50 against 49→51.
2. The type chart was indexed by the order type templates appear in the game
   master, not the canonical enum order. It produced a complete, plausible,
   entirely wrong chart. Caught by checking Normal-into-Ghost.
3. The appraisal reader required exactly three bar segments — but on a full
   bar the dividers blur away. Caught by a real screenshot, not by reasoning.
4. An empty (IV 0) bar was the largest flat grey in its row, so it voted
   itself the background and erased itself. Caught by a fixture.

Two more were caught while writing the coverage tests, both cases where the
assumption was wrong and the computation right. Those are now asserted with
comments explaining why, so nobody "fixes" them back.

## Run it

    pip install -r requirements.txt
    pytest -q                      # 120 tests, about 170 seconds

The slow ones are the image reads (~8s each). Don't speed them up by shrinking
the fixtures — resolution independence is one of the things under test.

## Layout

    fetch_gamedata.py   extracts gamedata.json from the game master
    gamedata.json       CPM curve, costs, 1024 species, moves, types, floors
    costs.py            CP/HP formulas, power-up and evolution costs
    pvp.py              stat-product rank tables (4096 spreads per species)
    appraisal.py        reads exact IVs off an Appraise screenshot
    coverage.py         type effectiveness and team-hole analysis
    dynamax.py          Max Move costs, effects, roles, tier lists
    triage.py           batch verdicts from screenshots or a recording
    app.py              FastAPI service
    static/index.html   the server build's UI
    test_pogo_forge.py  the suite
    fixtures/           four real screenshots with verified IVs

## Things that are deliberate

**Max Move costs are not in the game master — this was checked.** The mirror
at PokeMiners is current and contains no Dynamax data whatsoever. Niantic keeps
it server-side. `dynamax.py` therefore encodes community-documented figures, and
says so at the top.

It is *not*, however, the only hand-typed data here — that claim was in this
file until 13 Sep 2026 and it was false. The IV floors in `gamedata.json` were
also typed by hand; searching the game master for a minimum-IV template returns
zero results. They now live under a `community` block with a provenance line,
and `test_hand_typed_numbers_are_quarantined_and_labelled` fails if anything
hand-typed drifts back in alongside Niantic's numbers. Nothing reads them yet:
`pvp.rank()` takes a `floor_iv` but is not wired to the table.

What is certain: Max Particle costs are fixed at 400 / 600 / 800 per level for
every species and every slot. Only candy varies, by a cost group of 1-4. So
the planner can cost particles exactly and needs one piece of input per
species — which group it is in — instead of a full cost table. That is the
change to make to the roster UI.

**The appraisal reader refuses.** When it can't get a clean read it raises
rather than returning a best guess. When CP and HP don't reproduce the IVs it
read, it says the read failed. Preserve this; it is the single most valuable
property in the codebase.

**`coverage.suggest_partners` ranks typings, not Pokémon.** It will offer Onix
as an answer to a Rock weakness, because Rock genuinely resists off Ground.
That is correct for the question asked. Viability comes from `pvp.py` and the
live meta, not from here. There is a test asserting this so it doesn't get
"fixed."

**Legacy move flags matter.** `legacy_fast` and `legacy_charged` mark moves
that need an Elite TM. Getting these wrong costs a user a rare item. They are
read from the game master and asserted against known cases.

## Known gaps, in rough priority order

0. ~~**The species-to-cost-group mapping is missing.**~~ **The mechanism is
   built; the mapping is still user-supplied, by design.** `species_cost_group`
   stores one group per species, `/api/cost-groups` reads and writes it, and
   the Plan tab asks for it with the four groups' candy figures shown. Nothing
   is pre-selected and nothing is guessed: no group means candy is reported as
   unknown while particles stay exact, because particles do not vary by species.
   A cost observed in-game overrides the group tables and is labelled as having
   done so. There is still no published mapping to seed from, and there may
   never be — that is the correct end state, not a gap.

   The wiring was the real gap: `dynamax.py` was 187 lines with 14 passing
   tests and **no caller**. Nothing in `app.py` imported it. Meanwhile the
   planner asked the user to enter nine numbers per species, six of which were
   the constants this module already held.

1. **The standalone HTML has no coverage, moveset or Dynamax data yet.** The Python
   side gained `coverage.py`, the type chart, movesets, legacy flags, buddy
   distances and IV floors. The JS engine has not been updated. Port them and
   mirror the tests with Playwright, which is how the existing browser build
   was verified.

2. **Video triage is under-tested.** It works — a five-Pokémon recording read
   correctly — but the fixture is synthetic, painted flat blocks rather than
   real footage. Do not tune `SAMPLE_FPS` or `FRAME_CHANGE` against it; that
   is fitting to an artifact. Get a real screen recording first.

3. ~~**`gamedata.json` has no version stamp.**~~ **Done.** It now carries
   `version` (sha256 of the game master) and `fetched`. `costs.plan()` returns
   `gamedata_version`; the UI still doesn't show it. The 13 Sep refetch was
   diffed field-by-field against the previous snapshot before being adopted:
   zero differences in CPM, the type chart, the upgrade tables or any of the
   1,024 species' stats, moves, legacy flags, buddy distances or third-move
   costs. Everything new is additive.

4. **The PvP rank tables are slow to build** (~1s per species/cap, then
   cached). Fine interactively, noticeable in the suite.

5. **Tier lists in `dynamax.py` carry a date and will go stale.** They are
   deliberately not fetched at runtime. Surface `SOURCE_DATE` in any UI that
   displays them so nobody trusts a six-month-old ranking. *Partly done:*
   `/api/cost-groups` returns `SOURCE_DATE` in its provenance line and the Plan
   tab shows it. `BEST_ATTACKERS`, `BEST_DEFENDERS` and `BEST_HEALERS` are
   still displayed nowhere at all.

6. ~~**Regional and alternate forms are absent.**~~ **Done.** The extractor now
   keeps a variant as its own species wherever its stats or typing differ from
   the base — 158 of them, out of 1,446 variant templates; the other 1,288 are
   costumes and `_NORMAL` duplicates that match their base exactly and would
   only bloat the file. `NINETALES_ALOLA` is Ice/Fairy with its own moveset,
   where it used to answer as Kanto Ninetales, Fire.

   Lookup takes an alias table generated from the data rather than hand-listed,
   so `alolan ninetales`, `ninetales alola` and `galarian darmanitan` all
   resolve and a new region needs no code change. A name that is already a
   species key always wins, so nothing is shadowed.

   Two things this turned up. Nidoran female and male have no template whose
   suffix equals their id, so the first cut of this work dropped both — the
   field-by-field no-regression check against the previous snapshot is what
   caught it, and one is now promoted deliberately with an assertion that its
   variants agree. And **Niantic's file disagrees with itself about Dugtrio**:
   134 defence on `V0051_POKEMON_DUGTRIO`, 136 on `..._DUGTRIO_NORMAL`,
   everything else identical. Community databases are split the same way
   because they read one template or the other. Nothing in the file says which
   is current, so both are stored and neither is chosen.

7. **`coverage.py` is still unreachable from the product.** 89 lines, 6
   passing tests, imported by nothing but the suite — the same shape of gap
   `dynamax.py` had. There is no endpoint and no UI for team weaknesses or
   partner suggestions, so `shared_weaknesses` and `suggest_partners` cannot
   be used from the app at all. `pvp.py` is nearly as buried: it is reachable
   only as a side effect of uploading a screenshot to `/api/triage`, so there
   is no way to ask "where does this spread rank" directly.

8. **Mega energy is in the game master after all.** 129 `temporaryEvolution`
   branches carry `temporaryEvolutionEnergyCost` and a subsequent-evolution
   cost. The README said it wasn't; that has been corrected. Nothing extracts
   it yet.

## What not to do

- Don't rewrite `appraisal.py` thresholds without a fixture demonstrating the
  problem. Those numbers came from measured failures, not taste.
- Don't add a build system to the standalone HTML. One file, no npm, is the
  entire point of that build.
- Don't fetch live meta or spawn data. That is deliberately manual — it
  changes weekly and the user is fine looking it up.
- Don't make the reader return a guess when uncertain.
