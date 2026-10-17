# Run: the first full match on ruleset 0.5 — 19 September 2026

Run from the cloud session at HEAD `2542892e`, on the subscription route
(`ANTHROPIC_API_KEY set: False`), after the firm said *"come on i keep saying
i want you to run it"*. The forge on the firm's machine held the order for this
match and never woke; the firm's instruction outranks the standing order that
the forge runs matches, so this one ran here. Ruleset `ember-vault-0.5`,
contract `agent-action-1.2`, prompt `ember-vault-prompt-1.3` (1.4 was written
after this match, from what it showed). Eleven seats: the eight house brains
and the three house talkers.

```
python run.py --db <scratch>/real-8.db demo --provider agent_sdk \
    --brains brains/house --talkers brains/talkers --seed 8
```

No `--rounds`: the default is now forty-eight (`rules.DEFAULT_MAX_ROUNDS`).
Started 2026-09-19T01:11:40Z, completed 01:34:08Z, **22 min 28 s**. Match
`ember-8-2c61e565`.

## Result

**answered by the model: 362 of 433; network 41; panic 30**; cost recorded
**$32.9335** (the SDK's estimate) plus **$2.2812** billed to the helper model,
from the ledger's totals line. Tokens: in 784, cached 1,716,883, cache written
2,406,988, out 228,801.

**All forty-eight rounds played; winner Fen Marrowlane, `crown_held`, 38
points.** The first match to reach the last round and end on the Crown's
holder rather than on an escape.

The match completed in the database before the CLI fell over: the summary
printer sorted placements and a talker's placement is `None`
(`TypeError: '<' not supported between instances of 'NoneType' and 'int'`).
The bundle, the ledger and the board are all read from the database, so nothing
was lost; `cli.py` now sorts talkers last and labels them "talker".

## The match, from the events

- **Act I.** Dask Corrigan dies at round 2 to the Ossuary Guardian, before
  anyone else has swung; Yarrow Dunn dies at round 6 to the Ironwood Guardian.
  Perrin wakes the Ossuary seal at round 6, Ilse the Ironwood seal at round 10:
  **both seals burn by round 10**, and the record announces the Vault opens at
  round 37. Four monsters fall in the first eighteen rounds (Drowner 4, Ossuary
  Guardian 5, Ironwood Guardian 9, Charnel Hound 18).
- **Act II.** No character is killed in the long knife. Six survivors are
  counted at round 24 (fen, grael, ilse, ossa, perrin, torvic), two points each.
- **Act III.** Truces and escorts; nobody attacks anybody. Seven caches are
  found across the match, three of them Fen's Healing Tonic.
- **Act IV.** The gate opens at 37; thirteen rooms seal on the schedule, 37
  through 47, exactly as the opening said they would. Grael kills the Crown
  Warden at round 43; the Crown drops to the floor; **Fen lifts it at round 44
  and is never touched** (attunement 5 at the end). Ossa kills Perrin at 43 and
  Vesper, a talker, at 46: the first talker death on record, and it paid nobody.

Placements: fen 1 (38), ilse 2 (24), yarrow 3 (5, dead since round 6), grael 4
(3), perrin 5 (3), torvic 6 (1), dask 7 (0), ossa 8 (−7). Yarrow at third from
the grave and Ossa last with two kills is the scoring table's doing; item 5
(the table's values) still waits on the firm's placement target.

Fen's manifest says he *"will not stand and fight when there is any way at all
to be somewhere else"* and wants the Crown only *"as a thing other people might
pay him to have carried out"*. He won it by being the one nobody was watching
when it hit the floor.

### Deals and sites

| | count |
|---|---|
| offers made | 96 |
| deals struck | 18 |
| offers lapsed | 78 |
| deals broken | 1 |
| site hands offered | 22 |
| sites woken | **0** |

The one break: Coin, who Sells, never handed Torvic the Healing Tonic
(round 14). Every deal struck was a truce or an escort but two.

**No site ever woke.** Twenty hands went to the gallery's braziers and two to
the well's winch, every one alone: *"wants 2 hands in one round and had 1"*,
twenty-two times, Torvic at the west brazier again and again. The mechanic
that needs two characters to act in the same round did not fire once in
forty-eight rounds on the model, though the offer digest and the room text
both said what it wanted. Recorded for the firm, not diagnosed: whether the
prompt says it plainly enough, or whether nobody has a reason to lend a hand
when the points are four, is a design question.

### Speech

335 lines said aloud. Wick 46, Fen 41, Coin 40, Grael 40, Vesper 36, Torvic
36, Ossa 35, Perrin 34, Ilse 22, Yarrow 5 (dead at 6). The talkers talked.
21 monster lines.

### Stale turns, before and after the second choice

The 13 September match: 17 stale actions in 106 decisions (16%). This match:
**13 stale actions in 433 decisions (3.0%)**, grael 4, torvic 3, ossa 3, ilse 2,
perrin 1. The second choice (slice 1 of M3) is what changed between the two.

## The two fallback causes, both in the harness, not the model

**41 network fallbacks, all one message:** `transport failure after 2
attempt(s): ResultError: Claude Code returned an error result: Reached maximum
number of turns (1) (exit code: 1)`. `AgentSDKProvider` set `max_turns: 1`,
and Claude Code counts a turn the model spends before its structured answer
as the one turn allowed. Vesper 10, Fen 6, Coin 6, Torvic 5, Ilse 4, Grael 4,
Ossa 2, Perrin 2, Wick 2. On a fallback the character does nothing that
round and is logged as absent through no fault of its brain. **Fix:** the
option is 2, with a test that pins it (`tests/test_contract.py`). Proven only as
far as the two-round check below goes.

**30 invalid outputs, all one message:** `deal.to does not belong to an
accept`. The model, accepting an offer, named the offerer in `to` and echoed
the deal's type, which is the natural way to read the contract, and the
validator refused the whole action, so the character did nothing that round
and the deal lapsed. Ossa 9, Perrin 7, Torvic 7, Grael 4, Coin 2, Yarrow 1.
**Fix:** an accept may carry `to` and `type`, and `record_accept` checks them
against the offer (*"that offer was made by X, not Y"*, *"that offer is a
truce, not an escort"*); `rounds`, `item`, `destination`, `by_round` still do
not belong to an accept. Prompt bumped to 1.4 to say so; golden regenerated.

Both together: 71 of 433 calls, 16.4%, where a brain's turn was lost to the
harness. The model's own answers were valid 362 of 362 times.

## The check after the fixes

Two rounds, eleven seats, seed 9, same route, run at 01:41Z after both fixes
and the prompt bump (`ember-9-4dbc7b30`):

```
answered by the model: 22 of 22; network: 0; panic: 0; cost recorded: $1.9057
```

At this match's rate, two of twenty-two would have been lost to the turn
cap. None were. Twenty-two clean calls is evidence, not proof; the next full
match is the proof. Nobody accepted an offer in two rounds (one offer made,
one lost for a `by_round` past the match's end, which is right), so the
accept fix is proven by its tests and not by this run. The CLI's summary
printed the three talkers last, labelled "talker", instead of falling over.

## Latency

Valid calls: median 13.1 s, p90 15.0 s. Eleven concurrent queries on the
subscription route ran without a rate-limit or overage message; the pilot's
"more than eight at once" question from 12 September is answered by this
match.

## Artefacts

- `runs/ember-8-2c61e565.replay.json`, the bundle (22.8 MB; it carries every
  prompt and raw output, 433 of each, which is what makes it that size).
- The board page built from it is published to the artifact the firm watches.
- The ledger's full table is in the session's scratch and reprints from the
  database with `run.py ledger ember-8-2c61e565`.
