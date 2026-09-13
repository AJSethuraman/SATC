# pogo-forge

A local Pokémon GO roster and planning tool. Runs on the Forge, reachable from
your phone over Tailscale.

**It reads nothing from your Pokémon GO account.** There is no public API, and
anything that logs in risks the account. Every number in here is one you typed.
That constraint shapes the whole design: this is a decision tool, not a mirror
of your inventory.

## Run it

```
pip install -r requirements.txt
python app.py
```

Serves on `0.0.0.0:8737`. From your phone on the tailnet:
`http://forge:8737` (or whatever the Forge's MagicDNS name is).

The SQLite file lands next to `app.py`. Override with `POGO_FORGE_DB`.
API docs at `/api/docs` if you want to poke at it directly.

### Keeping it up

Windows host, so either Task Scheduler with a "run whether user is logged on"
trigger, or NSSM if you want a real service. Nothing in the app assumes a
particular supervisor — it's a single process with a single file behind it.

## What's here

**Roster** — the Pokémon you actually plan to build, with each Max Move slot
tracked at level 0–3. Level 0 means locked. New Dynamax entries start with Max
Attack at 1 and the other two locked, which matches how the game hands them to
you.

**Plan** — a particle ledger and a ranked list of what to build next. Ranking
is priority first, then whether the slot matches the role (attackers want Max
Attack, the tank wants Guard, the healer wants Spirit), then cost.

**Filters** — saved in-game search strings. The red dot marks a string you
transfer from, so a destructive one is visually distinct from a lookup.

## About the costs

Max Move upgrade costs vary by species and aren't published anywhere I'd trust
enough to seed a table from. So the app ships with none. Enter a cost the first
time you meet it in-game and it's there forever; until then the planner shows
that step as `cost?` rather than estimating.

This is deliberate. A planner that quietly guesses is worse than one that tells
you it doesn't know.

## Phases

- **1 — Roster and particle planner.** Done.
- **2 — Filter library.** Done. Six presets, saved strings, copy to clipboard.
- **3 — Full collection tracker.** `collection_entry` exists in the schema and
  nothing writes to it yet. The open question is entry: hand-typing a hundred
  Pokémon is the kind of chore that kills a personal tool in week two.

### On phase 3 and screenshots

The obvious answer is reading stats off screenshots — you have an RTX 2070 and
Ollama on the host, so a local vision model is right there. Two things to know
before you spend a weekend on it:

Game UI shifts between updates, so any fixed crop regions will need re-tuning
periodically. Budget for that as maintenance, not a one-time cost.

And the appraisal screen shows bars, not numbers. Exact IVs need the CP/HP
combination solved against level, which is a real calculation, not an OCR
problem. Poke Genie already does this well. Worth being honest with yourself
about whether rebuilding it is the fun part or just the part that sounds fun.

If phase 3 turns out to be a chore, the roster is the thing with actual value —
it's the small set you care about, and typing twelve Pokémon once is fine.

## Cost tab

Give it a species, IVs, current level and a goal; it returns stardust, candy
and XL candy, itemised. Goals are: highest level under a CP cap (Great/Ultra
League), a specific level, or maximum.

The numbers come from `gamedata.json`, extracted by `fetch_gamedata.py` from
Niantic's published game master — the same file the client downloads. That
covers the CP multiplier curve, the power-up cost tables, base stats for 1,024
species, evolution candy costs, and second-charged-move costs.

Validation: the CP formula reproduces published max-CP figures exactly for
Mewtwo (4178), Slaking (4431) and Magikarp (274) at level 40, and the
half-level CP multiplier interpolation matches the published level 1.5 value
to nine decimal places.

Re-run `python fetch_gamedata.py` after a major update to refresh it.

### What it can't tell you

Elite TM costs, Mega energy, and Max Move upgrade costs aren't in the game
master in a form this reads, so they aren't here. The Plan tab handles Max Move
costs by asking you to record them.

## Determinism

Every figure is a pure function of `gamedata.json` plus your inputs. No
sampling, no model, no network call at query time. The same inputs give the
same output on any machine, and you can hand-check any of it.

What was verified, not assumed:

- 200 identical `plan()` calls return exactly one distinct result.
- CP is strictly non-decreasing across all 101 half-levels, so the early
  `break` in `max_level_under_cp` can't miss a valid level.
- The `floor()` in the CP formula is not knife-edge: across six species and
  every level, the closest any raw CP came to an integer boundary was 5.2e-4.
  Float rounding differences would have to be a thousand times larger to
  change an answer.
- Published max-CP figures reproduce exactly for Mewtwo, Slaking and Magikarp.

Two defects this audit found and fixed:

- `power_up_cost` was charging for the Best Buddy bonus level. It's free.
  A level 49 to 51 run was billing 60,000 dust; it should be 30,000.
- The plan ranking read rows with no `ORDER BY`, so tie order was whatever
  SQLite returned. Pinned to `id`.

Two things that remain assumptions:

- The shadow and purified multipliers are in the game master, but the rounding
  rule isn't. `math.ceil` is used, which matches the costs I could check, but
  it isn't sourced.
- `gamedata.json` is a snapshot with no version stamp. Results are
  deterministic given that file; they change when you refetch and Niantic has
  changed something. If that matters, hash it and record the hash.

## Appraisal bar reader

Upload an Appraise-screen screenshot on the Cost tab and it fills in the exact
IVs. No model, no OCR, no cloud call — the image never leaves the Forge.

The appraisal bar already encodes the IV: it runs 0 to 15 in three equal
segments split at 5 and 10. The reader finds those segments rather than
assuming where they are, so nothing depends on your screen resolution, device
or where the bars sit. Pixels on the fill/track boundary are counted
proportionally by saturation, which makes the measurement sub-pixel accurate
and stops anti-aliasing or JPEG ringing from punching a false gap through a
segment.

Every row through a bar is measured and the median is taken, so one bad
scanline can't move the answer.

### It proves itself

A read is never returned alone. Give it the CP and HP from the same screen and
it searches all 101 half-levels for one that reproduces both numbers from the
IVs it just read. If none does, it says the read failed instead of handing back
a confident wrong answer:

    Confirmed: 13/14/13 reproduces CP 296 and HP 66 at level 20.

That is a genuine independent check — the bars and the CP/HP formula are
unrelated paths to the same three numbers.

### Measured robustness

Tested against a real screenshot at every scale from 0.4x to 2.5x, JPEG quality
95 down to 35, reduced brightness, and cropped to the bars: correct and
verified in 18 of 21 cases. The three failures — brightened images, and a crop
that cut into the bar edges — all refused rather than returning a wrong answer,
which is the behaviour that matters.

Brightening pushes the empty track toward the card colour behind it, which is
the current detection limit. Send the screenshot unedited.

## Triage

The point of this tab is to remove the per-Pokemon decision, not relocate it.
Drop in screenshots, or one screen recording of you swiping through the
Appraise screen, and get back one verdict each: KEEP, TRANSFER, or CHECK.

Species is optional and comma-separated in upload order. Left blank, a verdict
comes from IV shape alone; named, that entry gets an exact PvP rank.

### You do not need a screenshot per Pokemon

The in-game search bar already tiers everything for free — `4*`, `3*`, `2*` —
with no per-Pokemon work at all. Bulk-transfer the bottom using a string from
the Filters tab and never look at a bar. Only the survivors need exact IVs,
and that is ten or fifteen, not two hundred. For those, appraise the first in
a filtered list and swipe through the rest: one recording, not N screenshots.

### How a verdict is reached

Two things make a Pokemon worth keeping and they pull in opposite directions.
Raids want maximum attack. PvP wants minimum attack with high bulk, because a
low-attack spread can be levelled higher before hitting the CP cap, buying more
defense and HP for the same CP. A spread that serves neither is what you
transfer. Anything the data can't settle is marked CHECK rather than guessed.

PvP rank comes from stat product across all 4,096 spreads. Sanity check: the
best Great League Azumarill is 0/15/15, and a hundo Azumarill lands at rank
2550 of 4096, 93.7% — which is the known result and the reason a perfect
Pokemon is often a bad PvP one.

### Validation status — read this

**Still images are well tested.** The reader is correct on the real screenshot
at every scale from 0.4x to 2.5x and every JPEG quality from 95 down to 35:
10 of 10 in the current sweep, and it refuses rather than guessing when it
can't read.

**Video is not.** It works — a synthetic recording of five Pokemon at device
resolution yields four correctly read with correct verdicts — but that fixture
is painted flat blocks, not real footage, and I stopped tuning against it
deliberately rather than fit the detector to an artifact. The one it missed was
merged with an adjacent screen by the frame grouper.

Before trusting the video path, run one real recording through it and check the
count matches what you swiped past. If frames merge, hold each Pokemon a beat
longer; if that isn't enough, `SAMPLE_FPS` and `FRAME_CHANGE` at the top of
`triage.py` are the two knobs, and both want real footage to set properly.

## Getting screenshots in

Three ways, in ascending order of how little effort they take.

**Tap the drop zone.** On the Cost and Triage tabs. On iOS this opens the
Photo Library and multi-select works. Fine, a few taps.

**Drag or paste.** Both zones accept dragged files, and pasting anywhere on
the tab picks up an image or video from the clipboard. Useful from a desktop.

**An iOS Shortcut — the one worth setting up.** This puts the app in your
share sheet, so triage is: select screenshots in Photos, Share, tap the
shortcut. No browser, no picker, no typing.

Build it once in the Shortcuts app:

1. New Shortcut, then in its settings turn on **Show in Share Sheet** and set
   the accepted input to Images and Media.
2. Add **Get Contents of URL**.
   - URL: `http://forge:8737/api/triage` (your Forge's MagicDNS name)
   - Method: `POST`
   - Request Body: `Form`
   - Add a field named `files`, type File, value **Shortcut Input**
   - Add a text field named `cap` with value `1500`
3. Add **Get Dictionary Value** for the key `summary`.
4. Add **Show Result**.

Select tonight's screenshots, share, tap it, and you get back a line like
*"14 to transfer, 3 to keep, 1 needing a species."* Add a **Show Web Page**
step pointing at `http://forge:8737/` if you want the full breakdown.

The same shape works for a single appraisal against `/api/appraise`, which
takes `image`, `species`, and optionally `cp` and `hp`.

This only works while your phone is on the tailnet, which is the point — the
Forge is not exposed to the internet and the images never leave your network.
