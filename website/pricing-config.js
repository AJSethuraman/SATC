/* SATC — pricing shown on the website.
   ===========================================================================
   EVERY NUMBER HERE IS COPIED FROM client-documents/registry/fee-schedule.yaml.
   That file is the source of truth; this one is a publication of part of it.

   Do not edit a price here on its own. Change the schedule, then run:

       cd website && python3 pricing.spec.py

   which fails if any figure below has drifted from the schedule, if anything
   the schedule withholds has appeared here, or if a price has been published
   without what it covers. That is the "does the site still match?" check, and
   it answers in about a second.

   WHY THIS IS A SEPARATE FILE from site-config.js: pricing is the one part of
   the site with an external source of truth and an automated check against it.
   Keeping it apart means the check has one file to read, and site-config.js
   stays what it is — hand-edited contact details.

   WHY THE NAMES ARE DATA: all four package names are still being reworked.
   Rendering them from here makes the next rename a one-line change instead of
   a hunt through markup, headings and anchors.

   WHAT IS DELIBERATELY ABSENT, and must stay absent:
     · the farm schedule — priced, taken, never advertised. A published price
       is a solicitation and the firm does not solicit farm returns.
     · the records-sorting fee — set by the preparer once they see what
       arrived, so a number here would be a floor presented as a price.
     · every entity return figure — the page says "quoted after a
       conversation" instead, so a visitor reading four confident individual
       prices gets a sentence rather than a gap they fill in themselves.
     · the amended return and the extension-with-estimate. These appear in
       docs/pricing-for-website.md but NOT in fee-schedule.yaml, and the rule
       is that the schedule wins. They go up when they are in the schedule.
   =========================================================================== */

window.SATC_PRICING = {

  /* Load-bearing: without it every per-item price below reads as double
     charging. Printed wherever a package price is. */
  includedInEvery: 'Every package covers your federal return, plus your first state and first local return.',

  /* Cheapest to dearest — also the order the engine considers them in, and the
     order they must display in. */
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
      who: 'No schedules.',
      covers: [
        'Wages, interest and dividends',
        'The standard deduction'
      ]
    },
    {
      id: 'standard',
      name: 'Standard',
      price: 325,
      who: 'You have schedules.',
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
      name: 'Business',
      price: 500,
      who: 'You run a business.',
      covers: [
        'Everything in Standard',
        'One full Schedule C',
        'Actual expenses, a home office, depreciation, inventory or payroll'
      ]
    }
  ],

  /* NO EXPLANATORY PREAMBLE. There was a "how it works" box here — who picks
     the package, that à la carte can come in under one, the $200 minimum and
     its exception. The firm cut all of it on 26 August 2026: "just let the
     prices speak". Four prices with what each covers say it without the
     paragraph, and the paragraph was the thing that made the page read like a
     pitch. Do not reintroduce one. */

  /* Stated because a published price is read as a commitment, and this one is
     a current price rather than a permanent one. The firm's words, 26 August
     2026: "we can state that this is what we're currently charging and it's
     subject to change". Says it about us and about nobody else. */
  currentPrices: 'These represent our pricing for the upcoming tax year and are subject to change.',

  /* Charged only past what your package already covers. */
  extras: [
    { label: 'Each state return after the first',              amount: 50 },
    { label: 'Each local return after the first',              amount: 35 },
    { label: 'Rental schedule, up to three properties',        amount: 145 },
    { label: 'Each rental property after three',               amount: 45 },
    { label: 'Each K&#8209;1 after the first two',             amount: 15 },
    { label: 'Each brokerage statement after the first',       amount: 45 },
    { label: 'Each brokerage statement keyed in by hand',      amount: 95 },
    { label: 'Each additional gig Schedule C',                 amount: 65 },
    { label: 'Each additional full Schedule C',                amount: 200 },
    { label: 'Each foreign account, up to four',               amount: 50 },
    { label: 'Earned income credit, including due diligence',  amount: 65 },
    { label: 'Any of the situations below',                    amount: 50 }
  ],

  /* All six are things that HAPPENED, so you can tell in a second whether one
     applies to you. The assumption behind each is on your own estimate, not
     here — attached to a real engagement, where it means something. */
  situations: [
    'You sold a home',
    'You had a debt canceled or forgiven',
    'You sold, exchanged or spent digital assets',
    'You had health insurance through the marketplace',
    'You paid into or out of an HSA',
    'You took money out of a retirement account before 59&#189;'
  ],

  hourly: { rate: 150, billedIn: 'the quarter hour' },

  /* Hourly happens INSTEAD of the fixed price, not on top of it. */
  hourlyApplies: [
    'Records that need reconciling first',
    'Answering a notice',
    'Anything involving a foreign company'
  ]
};
