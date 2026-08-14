/* ============================================================================
   SATC INTAKE — QUESTIONS, CHOICES AND BRANCHING RULES
   ----------------------------------------------------------------------------
   THIS IS THE FILE TO EDIT when the intake questions change. The engine that
   renders them lives in intake.js and should rarely need touching.

   Each step looks like:

     {
       id:       'rental_count',        // key in the submitted payload
       type:     'single',              // single | multi | text | textarea | contact
       question: 'How many rental properties?',
       help:     'A rough count is fine.',   // optional sub-line
       required: true,                       // optional, default false
       options:  [ { value: '1', label: 'Just one' }, ... ],
       showIf:   a => (a.individual_complexity || []).includes('rentals'),
     }

   `showIf` receives the answers object and returns true when the step applies.
   It is the SINGLE source of truth: it decides both whether the step is shown
   and whether its answer is allowed to survive. If it returns false, any
   existing answer for that step is deleted (see prune() in intake.js), so a
   stale value can never reach the payload.

   An option marked `exclusive: true` (e.g. "None of these") clears the other
   selections when picked, and is cleared by them.

   Plain <script> with globals, deliberately — not an ES module. Modules do not
   run from file:// URLs, and README tells people to open index.html directly.
   ========================================================================== */

window.INTAKE_STEPS = [

  /* ── 1 · Primary routing question ─────────────────────────────────────── */
  {
    id: 'services',
    type: 'multi',
    question: 'What can we help you with?',
    required: true,
    options: [
      { value: 'individual_tax', label: 'Individual tax preparation' },
      { value: 'business_tax',   label: 'Business tax preparation' },
      { value: 'bookkeeping',    label: 'Bookkeeping' },
      { value: 'tax_planning',      label: 'Tax planning' },
      { value: 'business_advisory', label: 'Business advisory / fractional CFO' },
      { value: 'tax_resolution',    label: 'An IRS or state notice / tax issue' },
      { value: 'entity_setup',      label: 'New business or entity setup' },
      { value: 'unsure',            label: "I'm not sure yet", exclusive: true },
    ],
  },

  /* ── 2 · Individual complexity ────────────────────────────────────────── */
  {
    id: 'individual_complexity',
    type: 'multi',
    question: 'Which of these apply to you?',
    required: true,
    showIf: a => hasAny(a.services, ['individual_tax', 'tax_planning', 'tax_resolution', 'unsure']),
    options: [
      { value: 'w2',              label: 'W-2 employment' },
      { value: 'self_employment', label: 'Self-employment / 1099 work' },
      { value: 'business_owner',  label: 'I own a business' },
      { value: 'rentals',         label: 'Rental property' },
      { value: 'investments',     label: 'Investments / brokerage' },
      { value: 'k1',              label: 'K-1 income' },
      { value: 'retirement',      label: 'Retirement income' },
      { value: 'crypto',          label: 'Cryptocurrency' },
      { value: 'multistate',      label: 'Multiple states' },
      { value: 'foreign',         label: 'Foreign income or assets' },
      { value: 'none',            label: 'None of these', exclusive: true },
      { value: 'unsure',          label: "I'm not sure", exclusive: true },
    ],
  },


  /* ── 4 · Business profile ─────────────────────────────────────────────── */
  {
    id: 'business_structure',
    // Multi-select on purpose. "More than one business" is a COUNT, not a
    // structure, so as a competing single choice it forced someone with two
    // S corps to say either "S corporation" or "multiple entities" and lose
    // the other. Ticking both is now the normal answer, and a Schedule C
    // alongside an S corp — genuinely common — is finally expressible.
    type: 'multi',
    question: 'How is the business set up?',
    help: "More than one is fine.",
    required: true,
    // Self-employment is deliberately NOT a trigger. 1099 work is a Schedule C
    // inside the individual return; someone freelancing does not think of
    // themselves as running a business, and asking how it is "set up" reads as
    // an interrogation about something they never claimed to have.
    showIf: a => asksBusinessStructure(a),
    options: [
      { value: 'sole_prop',   label: 'Sole proprietor / Schedule C' },
      { value: 'smllc',       label: 'Single-member LLC' },
      { value: 'partnership', label: 'Partnership / multi-member LLC' },
      { value: 's_corp',      label: 'S corporation' },
      { value: 'c_corp',      label: 'C corporation' },
      { value: 'nonprofit',   label: 'Nonprofit' },
      { value: 'multiple',    label: 'More than one business or entity' },
      { value: 'not_yet',     label: 'Not set up yet' },
      { value: 'other',       label: 'Something else' },
      { value: 'unsure',      label: "I'm not sure", exclusive: true },
    ],
  },


  /* ── 6 · Business complexity basket ───────────────────────────────────── */
  {
    id: 'business_complexity',
    type: 'multi',
    question: 'Which of these does the business involve?',
    required: true,
    // Two gates, both required.
    //   1. The business must actually exist — "not_yet" means they are here to
    //      start one, so asking about its inventory is nonsense.
    //   2. They must have ASKED for business work. Someone filing an individual
    //      return who happens to own a business gets asked its structure and
    //      nothing more; scoping a business engagement we were not asked for is
    //      what makes an intake feel like an interrogation.
    showIf: a => asksBusinessComplexity(a),
    options: [
      { value: 'employees',           label: 'Employees' },
      { value: 'contractors',         label: 'Independent contractors' },
      { value: 'inventory',           label: 'Inventory' },
      { value: 'sales_tax',           label: 'Sales tax' },
      { value: 'ecommerce',           label: 'E-commerce' },
      { value: 'accounts_receivable', label: 'Customer invoicing / receivables' },
      { value: 'accounts_payable',    label: 'Vendor bills / payables' },
      { value: 'multi_location',      label: 'Multiple locations' },
      { value: 'multistate',          label: 'Operating in multiple states' },
      { value: 'none',                label: 'None of these', exclusive: true },
      { value: 'unsure',              label: "I'm not sure", exclusive: true },
    ],
  },




  /* ── 10 · Revenue band ────────────────────────────────────────────────── */
  {
    id: 'revenue_band',
    type: 'single',
    question: 'Roughly what does the business bring in a year?',
    help: 'A range is fine.',
    showIf: a => asksBusinessComplexity(a),
    options: [
      { value: 'under_100k', label: 'Under $100k' },
      { value: '100k_500k',  label: '$100k – $500k' },
      { value: '500k_2m',    label: '$500k – $2M' },
      { value: '2m_10m',     label: '$2M – $10M' },
      { value: 'over_10m',   label: 'Over $10M' },
      { value: 'prefer_not', label: 'Prefer not to say' },
    ],
  },

  /* ── 11 · Tax status ──────────────────────────────────────────────────── */
  {
    id: 'tax_status',
    type: 'single',
    question: 'Where do your tax filings stand?',
    required: true,
    showIf: a => hasAny(a.services, ['individual_tax', 'business_tax', 'tax_planning', 'tax_resolution', 'unsure']),
    options: [
      { value: 'current',           label: 'Everything is current' },
      { value: 'current_year_only', label: 'Just the current year to file' },
      { value: 'one_prior_year',    label: 'One prior year to catch up' },
      { value: 'multiple_unfiled',  label: 'Multiple years are unfiled' },
      { value: 'received_notice',   label: 'I received an IRS or state notice' },
      { value: 'unsure',            label: "I'm not sure" },
    ],
  },


  /* ── 13 · Bookkeeping status ──────────────────────────────────────────── */
  {
    id: 'bookkeeping_status',
    type: 'single',
    question: 'Where do the books stand?',
    required: true,
    showIf: a => hasAny(a.services, ['bookkeeping']),
    options: [
      { value: 'current',           label: 'Books are current' },
      { value: 'some_cleanup',      label: 'Some cleanup is needed' },
      { value: 'months_behind',     label: 'Several months behind' },
      { value: 'year_plus_behind',  label: 'About a year or more behind' },
      { value: 'from_scratch',      label: 'Starting or rebuilding from scratch' },
      { value: 'unsure',            label: "I'm not sure" },
    ],
  },


  /* ── 15 · Urgency ─────────────────────────────────────────────────────── */
  {
    id: 'urgency',
    type: 'single',
    question: 'Is this urgent?',
    // Was a ten-option "what's driving the timing?" — a menu rather than a
    // question. What we actually need to know is whether it goes to the top of
    // the pile. The reason behind it comes out in the first minute of the call,
    // and the services + status answers already imply most of it.
    required: true,
    options: [
      { value: 'deadline', label: "Yes — there's a deadline or a notice" },
      { value: 'soon',     label: 'Soon — within a few weeks' },
      { value: 'no',       label: 'No rush' },
    ],
  },

  /* ── 16 · Deadline follow-up ──────────────────────────────────────────── */
  {
    id: 'deadline',
    type: 'text',
    question: "What's the date you're working against?",
    help: "A rough date is fine.",
    placeholder: 'March 15, or in about three weeks',
    required: true,
    showIf: a => a.urgency === 'deadline',
  },

  /* ── 17 · Free text ───────────────────────────────────────────────────── */
  {
    id: 'notes',
    type: 'textarea',
    question: "Anything else we should know?",
    help: 'Optional — anything the questions missed.',
    placeholder: "A sentence or two is plenty.",
  },

  /* ── 18 · Contact — always last ───────────────────────────────────────── */
  {
    id: 'contact',
    type: 'contact',
    question: 'How do we reach you?',
    help: "We'll read it and be in touch as soon as we can.",
  },
];

/* ---------------------------------------------------------------------------
   Small helpers used by the showIf predicates above. Kept here so the rules
   read close to plain English.
   ------------------------------------------------------------------------- */

function hasAny(selected, values) {
  if (!selected) return false;
  const list = Array.isArray(selected) ? selected : [selected];
  return values.some(v => list.indexOf(v) !== -1);
}

/** They asked us to do work ON a business — not merely that one exists. */
function wantsBusinessWork(answers) {
  // business_advisory (fractional CFO and the like) is business work in its own
  // right, separate from tax planning — it needs the structure, complexity and
  // revenue questions even when no return is being prepared.
  return hasAny(answers.services, ['business_tax', 'bookkeeping', 'business_advisory']);
}

/**
 * A business that exists today. business_structure is a multi-select, so
 * "not_yet" on its own means there is nothing yet — but "not_yet" alongside a
 * real structure means they run one already and are setting up another.
 */
function hasBusiness(answers) {
  var picked = answers.business_structure;
  if (!picked || !picked.length) return false;
  var list = Array.isArray(picked) ? picked : [picked];
  return list.some(function (v) { return v !== 'not_yet'; });
}

/* The next two exist so that every business-branch rule states its OWN full
   precondition rather than only its immediate trigger. Without them a rule like
   `a.business_structure === 'multiple'` is correct only because prune() has
   already removed an inapplicable business_structure — an ordering guarantee
   that is invisible at the point you would edit the rule. */

/** Do we ask how the business is set up at all? */
function asksBusinessStructure(answers) {
  return wantsBusinessWork(answers) ||
         hasAny(answers.services, ['entity_setup']) ||
         hasAny(answers.individual_complexity, ['business_owner']);
}

/** Do we scope the business itself? Requires one to exist AND to be in scope. */
function asksBusinessComplexity(answers) {
  return asksBusinessStructure(answers) && hasBusiness(answers) && wantsBusinessWork(answers);
}
