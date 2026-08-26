/* SATC — pricing shown on the website.
   ===========================================================================
   GENERATED. Do not edit by hand.

       cd website && python3 build-pricing-config.py

   Every figure, label and note below is written from
   client-documents/registry/fee-schedule.yaml, which is the source of truth.
   pricing.spec.py regenerates this file and fails if the committed copy
   differs, so a price cannot be retyped, stale or invented.

   The short page copy — the line under each price and the card bullets — is
   the firm's wording and lives in SITE_COPY in the generator. It carries no
   figures.

   WITHHELD, and the schedule says why: the farm schedule (taken, never
   advertised — a published price is a solicitation) and the records-sorting
   fee (a floor a preparer sets on sight, not a price).
   =========================================================================== */

window.SATC_PRICING = {

  /* Load-bearing: without it every per-item price below reads as double
     charging. */
  includedInEvery: 'Every package covers your federal return, plus your first state and first local return.',

  /* The firm's words, 26 August 2026. */
  currentPrices: 'These represent our pricing for the upcoming tax year and are subject to change.',

  /* Cheapest to dearest, which is also the order the engine considers them in.
     Names render from here: one of the four has already been renamed once. */
  packages: [
    {
      id: 'starter',
      name: 'Simple Filer',
      price: 100,
      who: 'Just a W&#8209;2.',
      covers: [
        'One or two W&#8209;2s',
        'The standard deduction',
        'Dependents',
        'A 1098&#8209;T education credit for yourself'
      ]
    },
    {
      id: 'essentials',
      name: 'Essentials',
      price: 200,
      who: 'The everyday return.',
      covers: [
        'Wages, interest and dividends',
        'The standard deduction'
      ]
    },
    {
      id: 'standard',
      name: 'Standard',
      price: 325,
      who: 'More than you\'d file yourself.',
      covers: [
        'Everything in Essentials',
        'Itemized deductions',
        'One brokerage statement',
        'Up to two K&#8209;1s',
        'A gig Schedule C, standard mileage'
      ]
    },
    {
      id: 'business',
      name: 'Self-Employed',
      price: 500,
      who: 'You work for yourself.',
      covers: [
        'Everything in Standard',
        'One full Schedule C',
        'Actual expenses, a home office, depreciation, inventory or payroll'
      ]
    }
  ],

  /* Charged only past what the package already covers. */
  extras: [
    { label: 'State return',                      detail: 'Per state', amount: 50 },
    { label: 'Local return',                      detail: 'Municipal, RITA, CCA or school district', amount: 35 },
    { label: 'Rental schedule',                   detail: 'Covers 3, then $45 each', amount: 145 },
    { label: 'Schedule K&#8209;1 received',       detail: 'Per K&#8209;1 entered', amount: 15 },
    { label: 'Schedule K&#8209;1 issued',         detail: 'Per owner — shareholder or partner', amount: 40 },
    { label: 'Brokerage statement',               detail: 'Per 1099-B', amount: 45 },
    { label: 'Brokerage entered by hand',         detail: 'Per statement that cannot be summarized', amount: 95 },
    { label: 'Foreign account reporting',         detail: 'Capped at 4 — past that the time is billed at $150 an hour', amount: 50 },
    { label: 'Extension with a payment estimate', detail: 'Computing what to pay by the original due date, from an incomplete file', amount: 75 },
    { label: 'Gig or contract work',              detail: 'Schedule C — standard mileage, no assets, inventory or payroll', amount: 65 },
    { label: 'Sole proprietorship',               detail: 'Schedule C — actual expenses, a home office, depreciation, inventory or employees', amount: 200 }
  ],

  /* One price for any of them. All six are things that HAPPENED, so a reader
     can tell in a second whether one applies. The assumption behind each is on
     the client's own estimate, attached to a real engagement — not here. */
  situationPrice: 50,
  situations: [
    'Sale of a home',
    'Canceled debt',
    'Digital assets',
    'Marketplace health insurance',
    'Health savings account',
    'Early retirement withdrawal'
  ],

  /* What decides an amendment's price is whose work it is, so there is no
     single number to print. `reprices` means the return's own fee too. */
  amendment: [
    { label: 'Correction of our error', detail: 'Our mistake, corrected at no charge', amount: 0, reprices: false },
    { label: 'Amendment', detail: 'Amending the return we filed, from information that arrived later', amount: 50, reprices: false },
    { label: 'Amendment', detail: 'Amending a return prepared elsewhere, priced with the return itself', amount: 50, reprices: true }
  ],

  /* FROM prices, never bare numbers. The 1040 packages are gated on what is
     on the return, so the price a visitor reads is the price they get. An
     entity base is a floor — a bare $950 gets read as a total. Each number
     carries the notes that sit beside it in the schedule. */
  entities: [
    {
      label: 'Partnership — Form 1065',
      amount: 800,
      notes: [
        'A balance sheet, where one is required',
        'Inventory, where the business carries any',
        'Each partner\'s K&#8209;1 after the first two',
        'Returns in more than one state'
      ]
    },
    {
      label: 'S corporation — Form 1120-S',
      amount: 950,
      notes: [
        'A balance sheet, where one is required',
        'Inventory, where the business carries any',
        'Each shareholder\'s K&#8209;1 after the first two',
        'Returns in more than one state'
      ]
    },
    {
      label: 'C corporation — Form 1120',
      amount: 950,
      notes: [
        'A balance sheet, where one is required',
        'Inventory, where the business carries any',
        'Returns in more than one state'
      ]
    }
  ],

  /* Hourly happens INSTEAD of the fixed price, not on top of it. */
  hourly: { rate: 150, billedIn: 'the quarter hour', minimum: '0.25' },
  hourlyApplies: [
    'Brokerage keying — a statement has to be entered by hand',
    'Foreign entities — you hold an interest in a foreign corporation or partnership',
    'Notices and correspondence — a notice arrives and you ask us to deal with it',
    'Officer compensation — you ask us to determine or review it, and we agree in writing',
    'Records cleanup — the records need reconciling before the return can be prepared'
  ]
};
