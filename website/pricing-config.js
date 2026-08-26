/* SATC — pricing shown on the website.
   ===========================================================================
   GENERATED. Do not edit by hand.

       cd website && python3 build-pricing-config.py

   Every figure, label and note below is written from
   client-documents/registry/fee-schedule.yaml, which is the source of truth.
   pricing.spec.py regenerates this file and fails if the committed copy
   differs, so a price cannot be retyped, stale or invented.

   The short page copy — the line under each price, the card bullets and the
   group headings — is the firm's wording and lives in the generator. It
   carries no figures.

   NOT PUBLISHED, and each for a reason: the farm schedule (taken, never
   advertised — a published price is a solicitation), the records-sorting fee
   (a floor a preparer sets on sight, not a price), and the no-charge
   correction of our own error (a claim about ourselves nobody asked for).
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

  /* Entity returns, shown beside the packages because that is where somebody
     looks for them. Same card, deliberately not the same price: `from` is
     set beside the amount, and `notes` is what costs EXTRA rather than what
     is included — the opposite of a package's bullets, so the card labels it. */
  entityNoteLabel: 'On top of that:',
  entityLead: 'Starting prices. Each one lists what gets added on top, and you\'ll see your own number before you agree to anything.',
  entities: [
    {
      name: 'Partnership',
      who: 'Form 1065',
      amount: 800,
      notes: [
        'A balance sheet, where one is required',
        'Inventory, where the business carries any',
        'Each partner\'s K&#8209;1 after the first two',
        'Returns in more than one state'
      ]
    },
    {
      name: 'S corporation',
      who: 'Form 1120-S',
      amount: 950,
      notes: [
        'A balance sheet, where one is required',
        'Inventory, where the business carries any',
        'Each shareholder\'s K&#8209;1 after the first two',
        'Returns in more than one state'
      ]
    },
    {
      name: 'C corporation',
      who: 'Form 1120',
      amount: 950,
      notes: [
        'A balance sheet, where one is required',
        'Inventory, where the business carries any',
        'Returns in more than one state'
      ]
    }
  ],

  /* Grouped so like things read together. `reprices` means the return's own
     fee as well, which is a different price and so a different row. */
  extraGroups: [
    {
      title: 'More to file',
      rows: [
        { label: 'Another state return',                      detail: '', amount: 50 },
        { label: 'Another local return',                      detail: 'City, RITA, CCA or school district', amount: 35 },
        { label: 'Working out what to pay with an extension', detail: 'Filing the extension itself is free', amount: 75 },
        { label: 'Amending a return we filed',                detail: 'Something arrived after it went in', amount: 50 },
        { label: 'Amending a return someone else filed',      detail: 'Plus what the return itself costs', amount: 50, reprices: true }
      ]
    },
    {
      title: 'What is on the return',
      rows: [
        { label: 'Rental property',                           detail: 'Up to three, then $45 each', amount: 145 },
        { label: 'A K&#8209;1 you received',                  detail: 'Each one', amount: 15 },
        { label: 'A K&#8209;1 you send an owner',             detail: 'Each owner', amount: 40 },
        { label: 'A brokerage statement',                     detail: 'Each one after the first', amount: 45 },
        { label: 'A brokerage statement we have to type in',  detail: 'When the totals cannot be pulled in electronically', amount: 95 },
        { label: 'Gig or contract work',                      detail: 'Standard mileage, nothing owned by the business', amount: 65 },
        { label: 'A business you run yourself',               detail: 'Actual expenses, a home office, equipment, inventory or payroll', amount: 200 },
        { label: 'A foreign account',                         detail: 'Each one, up to four. Past four we bill the time instead.', amount: 50 }
      ]
    }
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

  /* Hourly happens INSTEAD of the fixed price, not on top of it. */
  hourly: { rate: 150, billedIn: 'the quarter hour' },
  hourlyApplies: [
    'A brokerage statement that has to be typed in by hand',
    'An interest in a company based abroad',
    'A letter from the IRS or the state you would like us to handle',
    'Working out what an owner of a business should be paid',
    'Records that need reconciling before the return can start'
  ]
};
