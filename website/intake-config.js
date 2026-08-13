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
    help: 'Choose everything that applies — you can change this later.',
    required: true,
    options: [
      { value: 'individual_tax', label: 'Individual tax preparation' },
      { value: 'business_tax',   label: 'Business tax preparation' },
      { value: 'bookkeeping',    label: 'Bookkeeping' },
      { value: 'payroll',        label: 'Payroll' },
      { value: 'tax_planning',   label: 'Tax planning & advisory' },
      { value: 'tax_resolution', label: 'An IRS or state notice / tax issue' },
      { value: 'entity_setup',   label: 'New business or entity setup' },
      { value: 'unsure',         label: "I'm not sure yet", exclusive: true },
    ],
  },

  /* ── 2 · Individual complexity ────────────────────────────────────────── */
  {
    id: 'individual_complexity',
    type: 'multi',
    question: 'Which of these apply to you?',
    help: 'Select all that apply. This tells us what your return actually involves.',
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

  /* ── 3 · Rental follow-up ─────────────────────────────────────────────── */
  {
    id: 'rental_count',
    type: 'single',
    question: 'How many rental properties?',
    help: 'A rough count is fine.',
    required: true,
    showIf: a => hasAny(a.individual_complexity, ['rentals']),
    options: [
      { value: '1',    label: 'Just one' },
      { value: '2_3',  label: '2–3' },
      { value: '4_9',  label: '4–9' },
      { value: '10up', label: '10 or more' },
    ],
  },

  /* ── 4 · Business profile ─────────────────────────────────────────────── */
  {
    id: 'business_structure',
    type: 'single',
    question: 'How is the business set up?',
    help: "If you're not certain, say so — we'll confirm it from your filings.",
    required: true,
    showIf: a =>
      hasAny(a.services, ['business_tax', 'bookkeeping', 'payroll', 'entity_setup']) ||
      hasAny(a.individual_complexity, ['business_owner', 'self_employment']),
    options: [
      { value: 'sole_prop',   label: 'Sole proprietor / Schedule C' },
      { value: 'smllc',       label: 'Single-member LLC' },
      { value: 'partnership', label: 'Partnership / multi-member LLC' },
      { value: 's_corp',      label: 'S corporation' },
      { value: 'c_corp',      label: 'C corporation' },
      { value: 'nonprofit',   label: 'Nonprofit' },
      { value: 'multiple',    label: 'Multiple businesses or entities' },
      { value: 'not_yet',     label: "Not set up yet — that's why I'm here" },
      { value: 'other',       label: 'Something else' },
      { value: 'unsure',      label: "I'm not sure" },
    ],
  },

  /* ── 5 · Entity count follow-up ───────────────────────────────────────── */
  {
    id: 'entity_count',
    type: 'single',
    question: 'How many entities?',
    required: true,
    showIf: a => a.business_structure === 'multiple',
    options: [
      { value: '2',   label: 'Two' },
      { value: '3_5', label: '3–5' },
      { value: '6up', label: '6 or more' },
    ],
  },

  /* ── 6 · Business complexity basket ───────────────────────────────────── */
  {
    id: 'business_complexity',
    type: 'multi',
    question: 'Which of these does the business involve?',
    help: 'Select all that apply.',
    required: true,
    showIf: a => !!a.business_structure && !onlyService(a, 'entity_setup'),
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

  /* ── 7 · Employee count ───────────────────────────────────────────────── */
  {
    id: 'headcount',
    type: 'single',
    question: 'Roughly how many employees?',
    required: true,
    showIf: a => hasAny(a.business_complexity, ['employees']) || hasAny(a.services, ['payroll']),
    options: [
      { value: 'none',  label: 'None right now' },
      { value: '1_5',   label: '1–5' },
      { value: '6_20',  label: '6–20' },
      { value: '21_50', label: '21–50' },
      { value: '50up',  label: 'More than 50' },
    ],
  },

  /* ── 8 · Contractor count ─────────────────────────────────────────────── */
  {
    id: 'contractor_count',
    type: 'single',
    question: 'Roughly how many contractors do you pay?',
    help: 'People you issue 1099s to.',
    required: true,
    showIf: a => hasAny(a.business_complexity, ['contractors']),
    options: [
      { value: '1_5',  label: '1–5' },
      { value: '6_20', label: '6–20' },
      { value: '20up', label: 'More than 20' },
    ],
  },

  /* ── 9 · Which states ─────────────────────────────────────────────────── */
  {
    id: 'states_detail',
    type: 'text',
    question: 'Which states are involved?',
    help: 'Just list them — we\'ll work out the filing requirements.',
    placeholder: 'e.g. FL, GA, NY',
    required: true,
    showIf: a =>
      hasAny(a.individual_complexity, ['multistate']) ||
      hasAny(a.business_complexity, ['multistate']),
  },

  /* ── 10 · Revenue band ────────────────────────────────────────────────── */
  {
    id: 'revenue_band',
    type: 'single',
    question: 'Roughly what does the business bring in a year?',
    help: 'A range is fine — it helps us scope the work.',
    showIf: a => !!a.business_structure && a.business_structure !== 'not_yet',
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
      { value: 'one_prior_year',    label: 'One prior year also needs attention' },
      { value: 'multiple_unfiled',  label: 'Multiple years are unfiled' },
      { value: 'received_notice',   label: 'I received an IRS or state notice' },
      { value: 'unsure',            label: "I'm not sure" },
    ],
  },

  /* ── 12 · Unfiled years follow-up ─────────────────────────────────────── */
  {
    id: 'unfiled_years',
    type: 'single',
    question: 'How many years are unfiled?',
    help: "An estimate is fine. This is common and fixable.",
    required: true,
    showIf: a => a.tax_status === 'multiple_unfiled',
    options: [
      { value: '2_3',    label: '2–3 years' },
      { value: '4_5',    label: '4–5 years' },
      { value: '6up',    label: '6 or more' },
      { value: 'unsure', label: "I'm not sure" },
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

  /* ── 14 · Transaction volume ──────────────────────────────────────────── */
  {
    id: 'transaction_volume',
    type: 'single',
    question: 'Roughly how many transactions a month?',
    help: 'Bank and card transactions across all accounts. A guess is fine.',
    showIf: a => hasAny(a.services, ['bookkeeping']),
    options: [
      { value: 'under_50',  label: 'Under 50' },
      { value: '50_200',    label: '50 – 200' },
      { value: '200_500',   label: '200 – 500' },
      { value: '500_2000',  label: '500 – 2,000' },
      { value: 'over_2000', label: 'More than 2,000' },
      { value: 'unsure',    label: "I'm not sure" },
    ],
  },

  /* ── 15 · Urgency ─────────────────────────────────────────────────────── */
  {
    id: 'urgency',
    type: 'single',
    question: "What's driving the timing?",
    required: true,
    options: [
      { value: 'normal',           label: 'Normal upcoming tax or accounting work' },
      { value: 'filing_deadline',  label: 'A filing deadline is coming up' },
      { value: 'notice',           label: 'An IRS or state notice' },
      { value: 'unfiled',          label: 'Unfiled returns to catch up on' },
      { value: 'books_cleanup',    label: 'Books need cleaning up quickly' },
      { value: 'transaction',      label: 'A business sale, purchase or financing' },
      { value: 'new_business',     label: 'Starting a new business' },
      { value: 'life_event',       label: 'A major financial or life event' },
      { value: 'nothing_urgent',   label: 'Nothing urgent — planning ahead' },
      { value: 'other',            label: 'Something else' },
    ],
  },

  /* ── 16 · Deadline follow-up ──────────────────────────────────────────── */
  {
    id: 'deadline',
    type: 'text',
    question: "What's the date you're working against?",
    help: "A date, or a rough sense of it — 'end of the month' is fine.",
    placeholder: 'e.g. March 15, or in about three weeks',
    required: true,
    showIf: a => ['filing_deadline', 'notice', 'unfiled'].indexOf(a.urgency) !== -1,
  },

  /* ── 17 · Free text ───────────────────────────────────────────────────── */
  {
    id: 'notes',
    type: 'textarea',
    question: "Anything else we should know?",
    help: 'Optional. Good place for anything unusual that the questions missed.',
    placeholder: "A sentence or two is plenty.",
  },

  /* ── 18 · Contact — always last ───────────────────────────────────────── */
  {
    id: 'contact',
    type: 'contact',
    question: 'How do we reach you?',
    help: "Arjun will read this personally and reply within one business day.",
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

/** True when `service` is the ONLY thing they picked. */
function onlyService(answers, service) {
  const s = answers.services || [];
  return s.length === 1 && s[0] === service;
}
