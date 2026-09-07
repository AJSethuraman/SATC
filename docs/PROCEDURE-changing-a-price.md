# Procedure: changing anything a client pays

**Written 7 September 2026**, from the hourly rate change done that day. Every
command below was run on this machine before it was written down.

Covers three things, which are the same procedure with a different step 2:

- **the hourly rate** — what unpriced work is billed at
- **an existing price** — a tier, a per-unit charge, a per-form charge
- **a new price** — something that has no price yet and is falling back to hourly

---

## How the dots connect

One file decides every number, and everything else is generated from it or
checks against it.

```
   client-documents/registry/fee-schedule.yaml      <-- THE SOURCE OF TRUTH
                    |                                   the only file you edit
                    |
      +-------------+--------------------+
      |                                  |
      v                                  v
   the estimate a client               build-pricing-config.py
   receives  (pricing.py)                     |
      |                                       v
      v                              website/pricing-config.js   (GENERATED)
   client-documents tests                     |
   1,513 of them                              v
                                       website/pricing.html
                                              |
                                              v
                                     merge to main -> Cloudflare
                                              |
                                              v
                                       satcllp.com  <-- CLIENTS
```

**Nothing is typed twice.** `pricing-config.js` is *generated*, never edited by
hand, and `pricing.spec.py` regenerates it and fails if the committed copy
differs. That single check means a published price cannot be stale, retyped or
invented — only correct.

**The live moment is the merge to `main`.** Cloudflare Pages builds from `main`
automatically. There is no separate "publish" step and no undo before a client
can see it.

---

## Who decides what

| | |
|---|---|
| **The number itself** | **AJ.** Delegated to this session for tax pricing on 7 September 2026 — *"you are the owner of tax pricing"* — but a number a client pays stays reversible in a word. |
| **The schedule** (`fee-schedule.yaml`, tests, estimates) | This session. |
| **The website** (`website/`) | The satcllp.com session. |
| **Wording a client reads** | **AJ.** Not either session, and one session cannot carry his approval to the other. |

---

## The procedure

### 1 · Decide the number, and write down why

Not a step to skip. The rate sat at $150 for years because nothing recorded that
it *was* a decision, so nobody revisited it.

Put the reasoning in the YAML as a comment, above the value — dated, with the
source. See `basis.rate` for the shape: what it was, what changed, what the
authority is, and the firm's own words where they exist.

### 2 · Edit the one file

```
client-documents/registry/fee-schedule.yaml
```

- **The hourly rate** is `basis.rate`.
- **A fixed price** is an `amount:` — under `base`, `per_unit`, or `per_form`.
- **A new price** for something currently hourly: give it an `amount:` and
  remove it from `hourly.situations` *and* from `DELIBERATELY_HOURLY` in
  `client-documents/tests/test_nothing_is_unpriced_by_accident.py`.

Nothing else in the file derives from `basis.rate`, so changing the rate does
**not** move any fixed price. That is asserted, not assumed.

### 3 · Prove you changed only what you meant to

Run from the repository root:

```
satc_system/.venv/Scripts/python.exe -c "import yaml,subprocess;n=yaml.safe_load(open('client-documents/registry/fee-schedule.yaml',encoding='utf-8'));o=yaml.safe_load(subprocess.run(['git','show','main:client-documents/registry/fee-schedule.yaml'],capture_output=True,text=True).stdout);f=lambda d,p='':{**({p:d['amount']} if isinstance(d,dict) and isinstance(d.get('amount'),(int,float)) else {}),**{k:v for x in ([d.items()] if isinstance(d,dict) else [enumerate(d)] if isinstance(d,list) else []) for a,b in x for k,v in f(b,f'{p}/{a}').items()}};a,b=f(o),f(n);print('changed:',{k:(a.get(k),b.get(k)) for k in set(a)|set(b) if a.get(k)!=b.get(k)} or 'NOTHING')"
```

It prints every priced amount that moved. If you changed only the hourly rate,
it must print `NOTHING`.

### 4 · Run the tests that price a client's estimate

```
satc_system/.venv/Scripts/python.exe -m pytest -q client-documents/
```

**Use that interpreter, not `python`.** `client-documents` has no virtual
environment of its own and borrows `satc_system`'s. Running plain `python` gives
52 import errors that look like a catastrophe and mean nothing.

Expect **1,513 passed, 2 skipped**. A rate change legitimately reds one test —
the one asserting a stored sample matches the schedule. That guard is correct;
regenerate the sample rather than editing the assertion.

### 5 · Regenerate the site's copy of the prices

```
cd website && ../satc_system/.venv/Scripts/python.exe build-pricing-config.py
```

Never edit `pricing-config.js` by hand.

### 6 · Prove the page matches the schedule

```
cd website && ../satc_system/.venv/Scripts/python.exe pricing.spec.py
```

Expect **66/66** and *"The published prices match the fee schedule."*

If a price also changed **wording**:

```
cd website && ../satc_system/.venv/Scripts/python.exe copy.spec.py
```

Expect **39/39**. This one enforces the copy tenets over every page *and* over
`intake-config.js`.

### 7 · Open the page

Tests prove the code agrees with itself. Only looking proves it agrees with
reality.

```
start website/pricing.html
```

### 8 · Merge — this is the live moment

Steps 2 to 7 go in **one merge**. Do not split the schedule change from the
regenerated `pricing-config.js`.

Splitting them is how `main` went red for two hours on 7 September: the schedule
said $175, the site said $150, and *published prices match the fee schedule*
failed on every branch cut afterwards, hiding everyone else's checks.

> A change that reddens `main` and its fix are one merge, or the change waits.

### 9 · Check it went live

Cloudflare rebuilds on the merge. Give it a couple of minutes, then:

```
curl -s https://satcllp.com/pricing-config.js | grep hourly
```

---

## If it is a new price

Two extra things, before step 2:

1. **Check whether it is currently falling back to hourly.** Anything in
   `hourly.situations` has no price by default, and the standing rule is that
   this is a worklist, not a resting place.
2. **Say what the price includes**, in the schedule, next to the number. A price
   with no scope beside it is renegotiated with every client.

---

## What this procedure will not let you do

- **Publish a price that was typed rather than generated.** Step 6 fails.
- **Change a client-facing sentence without the firm.** `copy.spec.py` blocks the
  wording the firm has ruled against — `engagement letter` among them.
- **Add something with no price at all.** `test_nothing_is_unpriced_by_accident`
  fails and names it. Before the hourly fallback existed, a missing price stopped
  the estimate rendering entirely; that test is what replaced the pressure.

---

## The one that is not automated

**Telling existing clients.** Nothing in this repository does that, and nothing
checks that it happened. A rate change reaches a client through the engagement
letter they sign next — which is why September is the time to make one and March
is not.
