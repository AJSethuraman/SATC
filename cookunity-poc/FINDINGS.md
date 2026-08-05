# CookUnity meal data — findings

**Verdict: the POC passes.** Meal data is reachable reliably, as structured
JSON, without scraping. Two material caveats are recorded below; neither blocks
the personalization phase, but one of them shapes it.

Captured 2026-08-05 against a logged-in account, Windows, Chrome attach mode.

## Which approach worked

**`api`.** The menu page fetches its own data and we read that response:

```
GET https://www.cookunity.com/api/sample-menu-by-store?storeId=1
→ 200, meals in a top-level `meals` array, 349 items
```

No `Authorization` header on the request — it rides on cookies, or is public.

The other two paths lost, and it is worth recording why:

- **`embedded`** — nothing. The menu is not serialised into the page.
- **`dom`** — found **0 cards** on the real menu page. The structural card
  finder anchors on rendered prices, and the menu grid does not present prices
  the way the fixture does. The fallback is therefore **unproven against the
  real site**, despite passing the fixture tests. If the API disappears, this
  needs work; it is not a ready safety net today.

The menu lives at `/our-menu`. The earlier guesses (`/menu`, `/meals`) are 404s
that redirect to the marketing homepage, which produced a "1 meal" result that
was actually a promo tile — a silent wrong answer, now guarded by logging the
landed URL and page title on every navigation.

## Field coverage, 349 meals

| Field | Populated | Notes |
|---|---|---|
| name, description | 349 | |
| chef | 349 | split as `chef_firstname` / `chef_lastname` |
| calories | 349 | |
| tags | 349 | ~19 per meal |
| rating | 327 (94%) | `stars`; review counts alongside |
| category | 349 | from `cuisines` (plural array) |
| image | 349 | root-relative; absolutised |
| **protein / carbs / fat** | **0** | **not served — see below** |
| price | 111 > $0, **238 = $0** | **see below** |

## Two things that are not resolved

**1. Macros beyond calories do not exist in this payload.** `nutritional_facts`
contains `calories` and nothing else. This is not a mapping bug — the field is
absent. Consequences for personalization:

- The tag list carries coarse buckets (`High Protein`, `High Fat`, `Mid
  Calorie`, `High Sodium`, `Low Sugar`). That is real ranking signal, and it is
  present on every meal.
- Gram-level macros, if needed, likely require per-meal detail requests — 349
  extra fetches. That is a phase-2 design decision, not a blocker.

**2. `price` is $0 for 238 of 349 meals, and the reason is unknown.** A sample
meal reads `price: 14.8, premium_fee: 0`, so `price` is plain dollars and
`premium_fee` is a separate surcharge (both are now captured). But two-thirds
of the catalog priced at zero has no innocent reading yet. Candidates: `price`
is an à-la-carte figure populated only for some meals; or it is a
plan-relative upcharge; or this sample payload is simply incomplete.

**Do not build cost logic on this field until it is explained.** Money
correctness is a hard constraint in this repo, and this is exactly the kind of
field that silently produces wrong totals.

## Reliability

- **Session reuse works.** Run 2 does not prompt for login.
- **Google SSO forces attach mode.** Google refuses OAuth in a
  Playwright-launched browser ("this browser or app may not be secure"), so the
  account must be logged in inside a normal Chrome that the harness attaches to
  over the DevTools protocol. This means a run is not fully unattended: a human
  must have logged into that browser at some point. Session lifetime under this
  arrangement has not been measured.
- **No HAR in attach mode**, since `recordHar` only applies to a context
  Playwright created. `discovery.json` still records every endpoint.

## What is most likely to break, and how we would notice

| Risk | Signal |
|---|---|
| Menu URL changes | `landed on ... — "<title>" (N cards)` shows the wrong page |
| API endpoint renamed or reshaped | `apiCandidates: []` in `discovery.json` |
| Field renamed | that field goes null across all meals — coverage table above is the baseline |
| Google session expires | attach-mode run returns marketing-page content |

The extraction is deliberately schema-agnostic: endpoints are found by scoring
payloads for meal-shaped arrays, and fields by pattern-matching key names. A
rename breaks one field, not the run.

## Open question: is this even your menu?

`storeId=1` is a parameter, every SKU is prefixed `NY-`, and the endpoint is
named *sample*-menu. CookUnity assigns a store from the delivery address, so
this is plausibly a default catalog rather than the account's real, available
weekly menu with true regional pricing.

**For browsing, ranking, and explanations, this data is sufficient.** For
anything that eventually selects meals to order, the authenticated
per-account menu must be confirmed first — otherwise we would be reasoning
about meals the account cannot actually get. Re-running after setting a
delivery address, and diffing `storeId` and prices, is the cheap next test.

## Go / no-go

**Go for personalization and explanations.** 349 meals with names, chefs,
cuisines, calories, ratings, review counts, and dense tags is more than enough
to rank and explain recommendations.

**Not yet for auto-selection.** Two gates first: explain the `price: 0`
population, and confirm the account's real menu rather than store 1's sample.
Auto-selection also inherits the attach-mode constraint above, which is a
poor fit for anything meant to run unattended.
