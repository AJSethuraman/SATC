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
  includedInEvery: 'Every package covers your federal return, your first state return and your first local return.',

  /* Cheapest to dearest — also the order the engine considers them in, and the
     order they must display in. */
  packages: [
    {
      id: 'starter',
      name: 'Simple Filer',
      price: 100,
      who: 'Wages only, and nothing else arrived.',
      covers: [
        'One or two W&#8209;2s',
        'The standard deduction',
        'A 1098&#8209;T education credit you claim for yourself',
        'Children — a dependent on its own doesn&#39;t move you up'
      ]
    },
    {
      id: 'essentials',
      name: 'Essentials',
      price: 200,
      who: 'A straightforward return, no schedules.',
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
        'Itemised deductions',
        'One brokerage statement',
        'Up to two K&#8209;1s',
        'A gig Schedule C on standard mileage'
      ]
    },
    {
      id: 'business',
      name: 'Business',
      price: 500,
      who: 'You run something.',
      covers: [
        'Everything in Standard',
        'One full Schedule C — actual expenses, a home office, depreciation, inventory or employees'
      ]
    }
  ],

  /* Who picks the rung, and which way the number can move. A visitor's first
     question about a four-rung ladder is which one they land on and who
     decides; the second is whether the package is a floor. It isn't — a client
     who doesn't need everything in a package can price out below it. */
  selection: 'We put you in the cheapest package that covers your return.',
  alaCarte: 'Don&#39;t need everything in it? We price it line by line and you pay whichever is lower.',

  /* The firm's minimum, and its one exception. Framed this way on purpose:
     a page that presents $100 as the starting price makes every visitor ask
     why they aren't getting it. */
  minimum: { amount: 200, exceptionId: 'starter' },

  /* Charged only past what your package already covers. */
  extras: [
    { label: 'Each state return after the first',                      amount: 50 },
    { label: 'Each local return after the first',                      amount: 35 },
    { label: 'Rental schedule, covering up to three properties',       amount: 145 },
    { label: 'Each rental property past those three',                  amount: 45 },
    { label: 'Each K&#8209;1 past the two Standard covers',            amount: 15 },
    { label: 'Each brokerage statement after the first',               amount: 45 },
    { label: 'Each brokerage statement we have to key in by hand',     amount: 95 },
    { label: 'Each additional gig Schedule C',                         amount: 65 },
    { label: 'Each additional full Schedule C',                        amount: 200 },
    { label: 'Each foreign account, capped at four',                   amount: 50 },
    { label: 'Earned income credit, with the due diligence it needs',  amount: 65 },
    { label: 'Any one of the situations below',                        amount: 50 }
  ],

  /* All six are things that HAPPENED, so you can tell in a second whether one
     applies to you. The assumption behind each is on your own estimate, not
     here — attached to a real engagement, where it means something. */
  situations: [
    'You sold a home',
    'You had a debt cancelled or forgiven',
    'You sold, exchanged or spent digital assets',
    'You had health insurance through the marketplace',
    'You paid into or out of an HSA',
    'You took money out of a retirement account before 59&#189;'
  ],

  hourly: { rate: 150, billedIn: 'the quarter hour' },

  /* Hourly happens INSTEAD of the fixed price, not on top of it. */
  hourlyApplies: [
    'Records that need reconciling before a return can be prepared',
    'Answering a notice',
    'Anything involving a foreign company'
  ]
};
