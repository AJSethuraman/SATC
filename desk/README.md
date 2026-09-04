# desk — expert desks

A **desk** is an expert an agent consults so a question does not reach the firm.
It answers only from authority it can cite, states how binding that authority is,
and **escalates rather than guesses**.

Installing `desk` brings `canon` with it: this plugin declares it as a dependency
because it uses canon's selector for routing and inherits Bassy's challenge duty.
Canon uses nothing from here, and must not — it has to lift out whole.

## The one rule

**An answer with no resolvable citation never counts as correct**, and that is
enforced in `engine.py` rather than asked for in a prompt. The difference was
measured: the same policy written as skill prose was obeyed *"100%, 4%, 0% of
runs"*; at the API choke point it *"is obeyed always, from every path"*
(`docs/LOCAL-LLM-PATTERN.md`, rule 6).

## Four outcomes, and the order they are reported in

```
wrongly absorbed   wrong, uncatchable, would have shipped   ← first. always.
correct
wrong (caught)     wrong, and the engine stopped it
escalated          the desk knew it did not know — a SUCCESS
```

`wrongly_absorbed` is the only one that costs anything: every other outcome costs
a little time, that one costs the reason to trust the rest. **Never summed into a
single figure** — a percentage hides exactly the number worth reading.

## What is in a desk

```
desks/<name>/
  SOURCES.md    what it may rely on: tier, access, may_store, checked
  PROBLEMS.md   the denominator — worked examples whose answers are not ours
  extracted/    public-domain authority text — the RULES, never the examples.
                an agent may write this.
  positions/    what the firm decided. an agent only PROPOSES here.
```

The two stores have different gates on purpose. Every line in `extracted/` is
checkable against a public source, so a large diff can be skimmed. `positions/`
holds judgement, so its diffs are read. **The pull request is the firm's yes.**

## Why Markdown and not YAML

This plugin installs with `pip install pytest` and nothing else, because a plugin
that lifts out whole is worth more than one with conveniences. Python has no YAML
in its standard library. Canon already parses this shape, so the choice was
between reusing a format that works and adding a parser beside it — and a record
ratified by reading a diff should read like prose in that diff.

## Running it

```
cd desk && pytest -q
```

The suite is offline by construction: `conftest.py` replaces the socket layer, and
a test proves that guard itself can fail. Verification reads stored text; freshness
is a separate job, so a government website being down never turns CI red.
