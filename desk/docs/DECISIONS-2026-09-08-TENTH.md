# The firm's other position, and two bugs found by reading — 8 September 2026

**The Forge ran the round trip against 0.7.3 and found three things.** Two were
mine, shipped hours earlier. One is the sharpest defect any run has produced, and
no test in this repository could have found it, because the test would have had
to know which of two correct answers the facts were about.

Everything below came back through the same channel as the last four rounds: a
question fired into a live session on the Forge, which installs the plugin,
consults the desks with its own browser, and hands back what it found. The round
trip is the test. It is now the only thing that has caught anything in two days.

---

## 1 · A ratified position applied to the wrong facts

`cash-and-bank` holds two positions on **one section of IRS Pub. 583**, with
opposite answers, because the publication states two rules there:

| citation | the firm's answer |
|---|---|
| `… — what the statement did not yet include` | a reconciling item, no entry in the books |
| `… — what the books are updated for` | an entry in the books |

The tester asked about a **deposit made on the last day of the month and not yet
on the statement**, and cited the second. The engine served it:

> **an entry in the books** · secondary · **binds**

That is wrong, and the desk's own recorded problem **CB1** — *"A deposit made on
the last day of the month"* — gives the answer as *"a reconciling item, no entry
in the books."* The engine served the opposite, in the firm's own words, flagged
binding.

### Why nothing caught it, which is the part worth keeping

`_check` refuses a conclusion that **contradicts** a ratified position — an agent
arguing with the firm. Here the agent did not argue. It quoted them exactly,
about a different rule. The tester:

> *"What it cannot catch is a correct position applied to the wrong facts — and
> that is the more likely error in a real close, because the agent isn't
> disagreeing with the firm, it's misreading which of the firm's two positions is
> in play."*

**No check in this engine is a statement about which rule the facts are in, and
none can be.** That judgement needs the facts, which the desk does not have. This
is not a gap to be closed by a better gate.

### So the alternative is shown, not the error caught

The same trade `passage` made two releases ago: the engine cannot tell right from
wrong here, but it can stop the other answer from being invisible. `Served` now
carries **`alongside`** — the firm's other ratified positions on the same passage
— and printing the answer puts both opposite conclusions on one screen:

```
an entry in the books

    IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the books are updated for
    secondary · binds · confirmed 2026-09-05

THE FIRM HOLDS ANOTHER POSITION ON THIS SAME PASSAGE, and it does not say this.
Which one is in play is a question about the facts, and nothing here has looked
at the facts:
  · a reconciling item, no entry in the books
      IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the statement did not yet include
```

**The stem is the record's own convention, not a heuristic.** That desk's
`POSITIONS.md` explains why the two entries exist: *"A position carries one
answer, and one citation admits one position [...] those have opposite answers,
so they are cited and answered apart."* The split is written into the citation as
a trailing ` — <which rule>`. Two positions sharing a stem is therefore the
firm's own mark for *this passage carries more than one answer*, and it is the
only case `alongside` returns.

**It fires on exactly one pair across all seven desks**, and a test holds that
number. Different paragraphs of one regulation — `1.263(a)-1(f)(5)` beside
`1.263(a)-1(f)(1)(ii)(B)` — are different rules, are not siblings, and a looser
rule that fired on them would teach the reader to skip the block.

---

## 2 · A version bug shipped inside the fix for a version bug

0.7.3 replaced the `KeyError`-raising first line of `ask-desk` with a snippet
that resolves the newest installed release out of the versioned plugin cache. It
read `sorted(os.listdir(ROOT))[-1]` — a **string** sort over version directory
names:

```
sorted(["0.7.3", "0.10.0"])[-1]   ->   "0.7.3"
```

Correct today. Correct through 0.9.x. Wrong forever after. The tester found it by
**reading the fix rather than running it**:

> *"an agent following the documented snippet loads a stale plugin while
> believing it is current — which is the same failure class as [the stale
> SKILL.md], shipped inside the fix for it. Nothing will announce it."*

Ordered by number now, and mechanised: `test_a_version_check_selects_by_name.py`
runs the published snippet against a cache that has already crossed `.9`, because
that is the only way to fail **today** on a bug that does not bite until then.
That file already existed for the same defect in another costume — a plugin
selected by `['plugins'][1]` instead of by name — and the rule generalises: **a
version selected by anything other than what makes it a version is right by
accident.**

---

## 3 · The stale SKILL.md, and why the warning could never have worked

It bit again, now **four releases behind**. 0.7.3's answer was to add a version
check and a `/reload-plugins` note *to that file*. The tester found the flaw in
one sentence, and it is the most useful thing in the report:

> *"the warning you added lives in the file that does not load [...] Anything
> that depends on the loaded SKILL.md being current cannot fix a stale SKILL.md.
> If it can be checked from `ask.consult`/`ask.answer` themselves — the code that
> is current — that is the only channel that reaches an agent in this state."*

So the **layout moved onto the object**. `Served.__str__` and `Refusal.__str__`
render everything a person must see, and the skill's whole instruction is now:

```python
print(out)          # not `repr`, not field by field
```

An agent following a two-release-old skill that says *"print the answer"* now
prints all of it, `alongside` included, because printing it **is** this. A skill
can go stale; what it tells you to print cannot.

**`__repr__` is untouched**, and that split answers a second finding: `showed`
and `showed_by_source` — counters that exist to falsify a model's claim that the
desk held nothing — were reaching a human reader beside a sentence written for
them. *"Pure instrumentation next to a sentence meant for a person."* They are
for the queue, and the queue reads the repr.

The harness-side resolution is still not in this repository's hands. What changed
is that being served a stale file no longer changes what a reader sees.

---

## What the Forge confirmed had landed

| | |
|---|---|
| `passage` shows source text on a ratified position | yes — real Pub. 583 text, `passage == position` now False |
| `Refusal` carries `working` back | yes, on both refusal paths. *"I wrote the accountant's paragraph straight off the returned object rather than from memory, which I could not do last run."* |
| the snippet runs without `CLAUDE_PLUGIN_ROOT` | yes, and exits cleanly with no plugin — **but see §2** |
| `unchecked` shorter | **partly.** 370 → 145 on ordinary passages; the ratified variant is unchanged at 251 |

On the last: left alone deliberately. It is the rarer case and it says the more
specific thing — *"whether their position fits these particular facts"* — which
§1 just proved is the exact warning that matters.

---

## What this did not fix, stated plainly

- **The wrong answer still serves.** A test pins that, so nobody reads this page
  as a fix. The engine cannot tell that a deposit in transit is the other rule's
  case; it never could, and nothing here gave it that ability. Only the reader's
  chance of noticing changed.
- **The operative clause is buried.** The tester on the Pub. 583 text: the
  deciding sentence sits *"~90% into a 2,400-character block of reconciliation
  procedure. At 6pm most readers skim it."* Unaddressed.
- **The judge** — a second model handed the paragraph and the conclusion and
  asked whether one supports the other — remains the general answer to all of
  this, and is not built.
- **`capitalization_rule`**, a field the firm approved and nobody built, still
  blocks two refusals.
