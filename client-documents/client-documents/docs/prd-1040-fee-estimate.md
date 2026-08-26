# PRD: A Form 1040 fee estimate that renders for real

**Status:** Draft · **Owner:** Arjun Sethuraman · **Last updated:** 2026-08-25

Produced by `/occam` on 25 August 2026: grill → this PRD → issues. The prices it
implements were signed off across four interview rounds the same day; the
decision record is `docs/pricing-open-threads.md` and the signed sheet is the
Price Sheet artifact.

---

## 1. Problem

The firm quotes $200 to almost everyone. That number is the workbook's 1040 line
plus its state line with the locality thrown in — which means it is the price of
a return with **no schedules**, quoted to clients who have schedules. Every
Schedule C, rental and K-1 is absorbed silently.

Four rounds of sign-off in August 2026 replaced that with a real schedule: four
individual packages, a per-form rule, and named add-ons. **None of it is in the
software.** `registry/fee-schedule.yaml` still holds `[CONFIRM:` placeholders in
every amount, so `pricing.line_items()` carries the placeholder to the line and
to the total, `merge` treats a surviving `[CONFIRM:` as a hard failure, and the
fee estimate refuses to render. That refusal is correct — quoting $0 is worse
than quoting nothing — but it means the pipeline has never produced a document
the firm could actually send.

The gap is not the templates and not the engine. `SATC Fee Estimate.html`
already carries `[[EACH LineItems]]`, `[[EACH Assumptions]]` and
`<<EstimateTotal>>`; `pricing.py` already turns counts into lines. **The signed
prices do not fit the shape the registry is in**, and that mismatch is the work.

## 2. Solution

Reshape the fee schedule so it can express what was signed, fill in the numbers,
and prove a real Form 1040 estimate out the other end.

A client answers the interview once. The engine reads the facts it already
collects — which schedules, how many rentals, how many businesses, which
Schedule C tier — and **derives** which of the four packages the client is in,
picking the highest package whose gate is met. The estimate prints that package
by name with what it covers, **plus the gate that selected it**, then each
counted extra on its own line. Anything the package already covers is not
charged again: two K-1s are inside Standard, the third is billed.

The client reads one page that says what they are paying for, what is already
included, and — in words, before the work starts — what the price assumes.

## 3. Goals & Non-Goals

**Goals**

- A real (non-`--draft`) Form 1040 fee estimate renders from a real interview,
  as a PDF the firm would put in front of a client.
- Every individual price on the signed sheet is expressible in
  `registry/fee-schedule.yaml` — no price is implemented in Python.
- The package is derived from facts, never from a self-rated question, and the
  estimate shows which gate selected it.
- The interview works through **both** front doors — the CLI and the browser —
  and they agree.
- `cli.py doctor` reports zero open items among the individual-return fees.

**Non-Goals / Out of scope** — decided explicitly on 25 Aug 2026:

- **The invoice bridge.** Estimate line items → Invoicer's JSON API is phase
  two, not this. Nothing here touches `invoice-generator/`.
- **Square vs Stripe.** `delivery.payment_instruction` stays `[CONFIRM:`. It is
  on the *invoice* template, not the estimate — verified — so it blocks nothing
  here. It becomes phase two's first question.
- **The 2026 materials deadlines.** Four open settings that block the engagement
  and organizer letters. The estimate template does not reference
  `MaterialsDeadline` — verified.
- **Entity returns.** No `base.1120S/1065/1120`, no entity gates, no separate
  entity state line. The 1040 path is built correctly first and used as the
  blueprint.
- **Bookkeeping.** Parked as its own workstream (thread T-12).
- **Retiring `--draft` mode.** It stays exactly as it is.

## 4. User Stories

1. As the preparer, I want the interview to decide which package a client is in,
   so that I am not making a pricing judgement at the consultation call.
2. As the preparer, I want the estimate to print the gate that selected the
   package, so that a wrong pick is visible on the page before it reaches a
   client.
3. As the preparer, I want a client who is covered by their package not to be
   charged again for what it covers, so that the package means something.
4. As the preparer, I want a client past their allowance to be charged only for
   the excess, so that the fourth rental costs $45 and not $500.
5. As the preparer, I want one flat price for any additional form, so that I do
   not have to invent a price at the call for a form I have not seen before.
6. As the preparer, I want each form's assumption stated on the estimate in the
   client's own words, so that the boundary is agreed before the work rather
   than argued after it.
7. As the preparer, I want an assumption printed only when it could actually
   apply to this client, so that the one that matters is not buried in five that
   do not.
8. As the preparer, I want the estimate to refuse to render rather than quote a
   number nobody set, so that a placeholder can never reach a client.
9. As a client, I want to see what my package already includes, so that I can
   tell what I am getting rather than only what I am paying.
10. As a client, I want each extra on its own line, so that I can see what is
    driving my fee above the package price.
11. As the preparer, I want to run the whole thing in a browser, so that I can
    take a client through it without a terminal.
12. As the preparer, I want the browser and the CLI to reach identical answers,
    so that which door I used never changes what a client is quoted.
13. As the preparer, I want `doctor` to tell me exactly which prices are still
    unset, so that I know what is blocking a real render without reading YAML.
14. As the preparer, I want a Starter client with one extra form to pay $150 and
    not $250, so that one document does not cost a student a package jump.

## 5. Requirements

**The schedule's shape**

1. [P0] `base.1040` becomes tiered, reusing the `tier_from` / `tiers` mechanism
   that `per_unit.schedule_c` already uses. Four tiers: `starter`, `essentials`,
   `standard`, `property`.
2. [P0] Each base tier carries `label`, `detail`, `amount`, plus a `covers` list
   (what prints under the package name) and an `allows` map (what it absorbs).
3. [P0] Tier selection is **derived**, not asked. `tier_from` on a base names a
   derivation rather than a question id; the gates are expressed in the registry,
   not in Python.
4. [P0] A new `per_form` block: one `amount` and a list of named forms, each with
   `label`, `assumes` and `trigger`. Counted from the interview.
5. [P0] `per_unit` gains `foreign_account`, `brokerage`, `brokerage_manual`, and
   `schedule_c` keeps its two tiers.
6. [P0] `assumed.brokerage` is **removed** — brokerage is counted now, and an
   item cannot be both priced and assumed. `assumed.cleanup` stays unchanged.
7. [P1] Amounts stay plain numbers; `money.py` remains the only formatter.

**The prices** (all signed 25 Aug 2026; `[F]` = the firm's own figure)

8. [P0] Packages: Starter 100, Essentials 200 `[F]`, Standard 325, Property &
   Business 500.
9. [P0] Per form: 50 `[F]` — set against a recommendation of 75.
10. [P0] Per unit: state 50 `[F]`, local 35, rental 45 (past the allowance),
    K-1 15 `[F]` (past the allowance), Schedule C gig 65 / full 200 `[F]`,
    brokerage 45 (past the allowance), brokerage entered lot by lot 95, foreign
    account 50 `[F]`.
11. [P0] Named exceptions to the per-form rule, priced separately: earned income
    credit with due diligence 150, amended return 250, extension with a payment
    estimate 75.
12. [P0] Allowances — Standard absorbs one brokerage statement, two K-1s and one
    gig Schedule C; Property & Business additionally absorbs **either** up to
    three rentals **or** one full Schedule C, not both.

**Derivation and pricing**

13. [P0] The engine picks the **highest** package whose gate is met.
14. [P0] A form on top never changes the package. A Starter client with one
    additional form is 100 + 50 = 150.
15. [P0] Counted units are reduced by the selected package's allowance before
    pricing; the reduction is never negative.
16. [P0] The `Property & Business` either/or allowance resolves in the client's
    favour — whichever branch absorbs more.
17. [P0] An unset amount still carries its `[CONFIRM:` to the line and the total.
    This behaviour must not regress.
18. [P1] The base line's `Service` is the package name; its `Detail` names the
    gate that selected it.

**The estimate**

19. [P0] `[[EACH LineItems]]` renders package first, then extras in schedule
    order. The template itself needs **no changes** — verified.
20. [P0] Per-form assumptions print only when that form is on the return.
    `assumed.cleanup` prints always.
21. [P0] Real mode still writes **nothing at all** if any document in the set
    would be holed.

**Both front doors**

22. [P0] Every gate and derivation lives behind `intake.finish` / `pricing`;
    neither `cli.py` nor `web.py` gains a decision.
23. [P0] `additional_forms` changes from a free-text `list` to a `multi` over the
    six named forms, plus a free-text "anything else" that prices nothing.
24. [P1] `doctor` separates individual-return fees from entity fees so the 1040
    path can reach zero open items while entities stay open.

## 6. Implementation Decisions

**Where the gates live.** In `registry/fee-schedule.yaml`, not in Python. The
repo's convention is that Drake-adjacent and fee behaviour is config-driven, and
`per_unit.schedule_c` already proves the pattern. A gate is a list of conditions
over interview answers:

```yaml
base:
  "1040":
    tier_from: derived          # not a question id — the engine evaluates
    tiers:
      standard:
        label: "Standard"
        detail: "Schedules, but nothing that scales"
        amount: 325
        covers: ["Itemized deductions", "One brokerage statement",
                 "Up to two K-1s", "A gig Schedule C on standard mileage"]
        allows: {count_brokerages: 1, count_k1s: 2, schedule_c_gig: 1}
        gate:                    # ALL must hold; highest matching tier wins
          - any_of: {federal_schedules: [A, D, E2, C]}
```

Order in the file is the ladder order; the engine walks it top-down and takes
the last tier whose gate holds. That keeps "highest package whose gate is met"
readable as data rather than as a chain of `if`s.

**Allowances.** `allows` maps a `count_from` key to how many units the package
absorbs. `line_items` subtracts it before the existing `count <= 0: continue`
guard, using the same `max(0, …)` shape already used for `base_covers:
one_included`. The Property & Business either/or is the one special case: compute
both branches and keep the cheaper total for the client.

**Per-form.** A new block parallel to `per_unit`, because a form is not a unit —
it has one price for all of them and its own assumption text:

```yaml
per_form:
  amount: 50
  count_from: additional_forms       # a multi; length is the count
  forms:
    hsa:
      label: "Health savings account"
      detail: "Form 8889"
      assumes: "you have the 1099-SA and the 5498-SA"
      trigger: "contributions exceeded the limit and have to be unwound"
```

`assumptions()` grows a notion of relevance: an `assumed:` item still prints
unconditionally, but a `per_form` item prints only when its key is in
`additional_forms`. This is a deliberate narrowing of the module's documented
"always print" rule, and the docstring must say why: an assumption that cannot
apply to this client is not a boundary, it is noise, and six irrelevant
sentences bury the one that matters.

**Interfaces that do not change.** `pricing.line_items(answers, schedule)` and
`pricing.assumptions(answers, schedule)` keep their signatures. `is_open()`,
`_line()`, `money.money()` and `estimate_total()` are untouched. `merge` is
untouched. The Fee Estimate template is untouched.

**Silent mismatch to fix, not footnote.** `assumed.brokerage` currently declares
`inside_base: true` while the signed sheet prices brokerage at $45 and $95. Left
in place, the estimate would both charge for a second brokerage statement and
print a sentence saying brokerage is included. It must be removed in the same
change that adds the counted lines.

## 7. Testing Decisions

Four seams, all of which already exist. No new ones.

- **Seam 1 — `tests/test_pricing.py`** (answers → line items → total). Package
  derivation, every allowance, the per-form rule, the Starter-plus-a-form case,
  and the `[CONFIRM:` carry-through.
- **Seam 2 — `tests/test_pipeline.py`** (a record goes in, documents come out —
  or nothing does). A complete 1040 record renders a real estimate; an incomplete
  one writes nothing at all.
- **Seam 3 — `tests/test_web.py`** (the browser and the core agree; `web.py`
  decides nothing of its own). The interview runs to a priced estimate over HTTP
  and reaches the same numbers as the CLI.
- **Seam 4 — `tests/test_registry.py`** (template, registry and interview stay in
  step). Every base tier's gate names questions that exist; every `per_form` key
  is an option of `additional_forms` — the same class of check that caught the
  orphaned Schedule C tier.

**What a good test proves.** Not that a function returns a number, but that a
client with a given set of facts is quoted a given price *and shown why*. The
allowance tests are the ones that matter most: charging for a K-1 that was
included is the failure a client notices and the firm does not.

**Client PII.** The estimate is a client-facing document and legitimately carries
`ClientFullName` and address — that is the document's job. The constraint is
everywhere else: no real name, SSN or EIN in fixtures, sample records, test
output or committed artifacts. Fixtures use invented names, and the existing
`test_pipeline` rule that metadata cannot reach a document stands unchanged. No
tax identifiers appear anywhere in this feature.

## 8. Success Metrics

- `cd client-documents && PYTHONPATH=. pytest -q` green, including new tests at
  all four seams.
- `make demo` completes and writes a **real** (non-draft) fee estimate PDF.
- `cli.py doctor` reports zero open items among individual-return fees.
- The firm renders one real client's estimate and confirms it is a document they
  would send — the only check that catches wording rather than arithmetic.

## 9. Open Questions

Only items genuinely owed to the firm.

1. Rendering a real client's estimate requires the firm's own machine and their
   own client data. Nobody else can perform the acceptance check in §8.

Two decisions were made on the firm's behalf during grilling and are recorded
here so they can be overruled cheaply rather than discovered later: a form never
changes the package (§5.14), and per-form assumptions print conditionally
(§6). Both were stated to the firm at the time.
