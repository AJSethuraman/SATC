/* The line-by-line guide — THE PROSE ONLY.
   =========================================================================
   THIS IS THE FILE TO EDIT. Every sentence a reader sees is in here, in plain
   text. Change a word, run `npm run build`, and the page changes.

   What is deliberately NOT in here: line numbers and IRS labels. Those come
   from years/*.mjs at build time, because they move. Other expenses sit on
   line 27b for 2025 and on 27a for 2023 and 2024 — the IRS swapped them — and
   a guide with the number typed into the prose would have been wrong for half
   the years it covers within a week of being written. Write `{line:27other}`
   and the builder fills in the right one.

   THE REGISTER, from CLAUDE.md. Nothing a first-time reader has to look up.
   No sentence past about 25 words. No contract-desk verbs. If a term of art is
   unavoidable — and a few are — show it and then say what it means in the same
   breath. copy.spec.py checks all of that against the built page.

   WHERE THE LINE IS. This page says what each box is for. It does not decide
   anybody's facts. Where a question turns on someone's own circumstances, it
   says so and says that is where a preparer earns their fee — which is the
   firm's position of 6 September 2026, and the reason the tool refuses to work
   out self-employment tax. Keep that line where it is when editing.        */

export const meta = {
  title: 'What goes on each line of Schedule C',
  strap: 'A plain-English walk through the form, box by box, written by a CPA — '
    + 'and the eight places sole traders most often get it wrong.',
  intro: [
    'Schedule C is where a sole trader tells the IRS what the business took and what it spent. '
    + 'The arithmetic is easy. Deciding which box a cost belongs in is not, and that is where the money goes wrong.',
    'This page goes through the form in order. It says what each box is for, and it is honest about '
    + 'the handful of questions that depend on your own circumstances rather than on a rule.',
  ],
  toolNudge: 'There is a free tool on this site that adds it all up for you and gives you a '
    + 'profit and loss statement and a worksheet, as a PDF and a spreadsheet. Nothing you type leaves your computer.',
};

/* The eight that cost real money, up front, because most readers will not
   reach the bottom of a page this long. Each names the line it lives on. */
export const traps = [
  {
    line: '9',
    title: 'Claiming the mileage rate and the running costs',
    body: 'This is the most expensive mistake on the form, and it is easy to make. '
      + 'If you claim the mileage rate for your vehicle, that rate already includes its fuel, '
      + 'insurance, servicing and repairs. You do not also put those on the insurance or repairs lines. '
      + 'Loan interest is different — the rate does not cover borrowing, so the business share of the interest still counts.',
  },
  {
    line: '26',
    title: 'Counting what you paid yourself as wages',
    body: 'Money you take out of your own business is not an expense. '
      + 'The wages line is for people you employ. What you draw is simply profit you have already been taxed on.',
  },
  {
    line: '22',
    title: 'Materials that are not stock',
    body: 'If you buy things and use them up doing the job — paint, timber, dust sheets — they are supplies. '
      + 'Stock is different: things you were holding on the last day of the year because you meant to sell them on. '
      + 'A painter has supplies. A shop has stock.',
  },
  {
    line: '24b',
    title: 'Halving the whole food bill',
    body: 'Work out which meals had a business reason first — a client, or a trip that kept you away overnight. '
      + 'Your own lunch on a local job is not one. Halve that smaller number, not everything you spent on food.',
  },
  {
    line: '13',
    title: 'Writing off a big tool in one go without checking',
    body: 'A $40 scraper is an expense. A $1,200 sprayer may have to be spread over several years, '
      + 'or may not — there are three separate rules that can let you take it all at once, and which applies depends on your year. '
      + 'This is the one line where guessing is genuinely expensive.',
  },
  {
    line: '23',
    title: 'Putting your own tax on the taxes line',
    body: 'This box is for business licences and, if you have staff, payroll taxes. '
      + 'Not your income tax. Not your self-employment tax — the Social Security and Medicare you pay on your own profit. '
      + 'Sales tax you paid on materials is just part of what the materials cost.',
  },
  {
    line: '15',
    title: 'Putting your own health cover here',
    body: 'The form calls this line insurance other than health, and the "other than health" is the part people miss. '
      + 'Your own health cover is handled elsewhere on your return, not as a business cost here.',
  },
  {
    line: '30',
    title: 'Claiming a room the family also uses',
    body: 'A home office has to be used regularly and only for the business. '
      + 'If the children do their homework at that desk in the evening, it does not qualify at all — '
      + 'and no method of working out the figure fixes that.',
  },
];

/* The form in order. `line` keys are looked up in the year data, so the number
   and the IRS wording are always the ones for the year the page is built for. */
export const sections = [
  {
    heading: 'Before any of the boxes',
    blurb: 'Two questions sit above the figures, and both are easy to answer too quickly.',
    items: [
      {
        title: 'How you count income',
        body: 'You either count money when it arrives, or when the work is done. '
          + 'Most sole traders count it when it arrives. '
          + 'The important part is to pick the same one you picked last year — '
          + 'changing it is a thing you have to ask permission for.',
        ask: 'A customer paid a deposit in December for a job you finish in February. '
          + 'If you count money when it arrives, it is this year\'s.',
      },
      {
        title: 'Did you work in the business regularly?',
        body: 'The form asks whether you took a real, continuous part in running it. '
          + 'A weekend sideline you barely touched is a different answer from a trade you worked at all year. '
          + 'It matters because it decides whether you can use a loss this year.',
        ask: 'This is the one question on the form where the friendly wording is friendlier than the rule behind it. '
          + 'If your involvement was occasional, it is worth asking someone.',
      },
    ],
  },
  {
    heading: 'Money coming in',
    blurb: null,
    items: [
      {
        line: '1',
        body: 'Everything the business was paid. All of it — the jobs that came with a 1099 form and the ones paid in cash. '
          + 'Leaving the cash work out is the commonest first-year error, and the one most likely to be noticed.',
        ask: 'Card processing fees come off as an expense rather than out of this figure. Put the full amount here.',
      },
      {
        line: '2',
        body: 'Money you gave back to customers — a refunded deposit, a credit for work redone. '
          + 'A discount you simply never charged is not this: you invoiced less, and that is all.',
      },
      {
        line: '6',
        body: 'Anything the business earned that was not a sale. '
          + 'For most sole traders this is empty. The fuel tax credit the form mentions applies to off-road fuel — '
          + 'farms and some plant, not a van.',
      },
    ],
  },
  {
    heading: 'Stock, and the fork that catches people',
    blurb: 'This is the hardest decision on the form and it hangs on one question.',
    items: [
      {
        title: 'Did you hold things to sell on the last day of the year?',
        body: 'If you had goods sitting in a lock-up on 31 December that you had bought to sell on, that is stock, '
          + 'and it goes through the cost of goods sold part of the form. '
          + 'If you buy materials and use them up on jobs, it is not stock — those are supplies.',
        ask: 'Watch the names. There is a materials and supplies box inside the stock section and a supplies box outside it. '
          + 'They are nearly the same words and, for a trade, opposite answers.',
      },
    ],
  },
  {
    heading: 'Money going out',
    blurb: 'In the order the form asks for them. The boxes people most often confuse are next to each other on purpose.',
    items: [
      { line: '8', body: 'Yard signs, a boosted post, the local paper. Lettering on the van is advertising; the van is not.' },
      {
        line: '9',
        body: 'Two ways to do this, and you pick one. Either a set rate for every business mile, '
          + 'or what the vehicle actually cost you to run, in the business share. '
          + 'Most sole traders use the mileage rate because the records are easier.',
        ask: 'If you use the mileage rate, do not also claim fuel, insurance, servicing or repairs anywhere else. '
          + 'They are already inside it. This is the costliest error on the form.',
      },
      {
        line: '11',
        body: 'People you paid to do work who are not your employees.',
        ask: 'Two things follow. Pay anyone more than $600 in the year and you owe them a 1099-NEC form. '
          + 'And if you set their hours and supply their kit, the IRS may treat them as an employee, which is a different line and different taxes.',
      },
      {
        line: '13',
        body: 'Equipment that lasts — a machine, a laptop, a trailer. '
          + 'The cost is often spread over several years rather than taken all at once, and there are three separate rules '
          + 'that can let you take more of it up front. Which one fits depends on what you bought, when, and what else you bought that year.',
        ask: 'This is where the free tool stops, and it says so. If you have never had a depreciation schedule — '
          + 'the running list of what you own and how much of it you have written off — this is the line to get help with.',
      },
      { line: '14', body: 'Benefits for people you employ. Not for you.' },
      {
        line: '15',
        body: 'Public liability, tools, the business share of van cover if you are claiming actual running costs. '
          + 'Not your own health cover — the form says other than health, and that is deliberate.',
      },
      { line: '16b', body: 'The interest on business borrowing, including a van loan. Only the interest, not the whole payment: paying back what you borrowed is not a cost.' },
      { line: '17', body: 'Your accountant, a solicitor, a bookkeeper. If a bill covered your personal return as well, only the business share belongs here.' },
      { line: '18', body: 'The paper side of running the business — printer ink, an invoice book, stationery, software you pay for monthly.' },
      { line: '19', body: 'A pension you fund for employees. Your own retirement saving goes on your personal return, not here.' },
      { line: '20a', body: 'Plant and equipment you hired rather than bought — a scaffold tower, a floor sander, a van hired for a fortnight.' },
      { line: '20b', body: 'Rent on premises: a workshop, a lock-up, a yard.' },
      {
        line: '21',
        body: 'Keeping your own equipment working — servicing a machine, new parts, a repair.',
        ask: 'Not repairs to a customer\'s property: that is the job you were paid for, and the materials are supplies. '
          + 'And not vehicle repairs if you are claiming the mileage rate.',
      },
      { line: '22', body: 'Things you buy and use up doing the work. For most trades this is the biggest line on the form.' },
      {
        line: '23',
        body: 'Business licences, permits, and payroll taxes if you have staff.',
        ask: 'Not your own income tax, and not your self-employment tax — the Social Security and Medicare you pay on your profit. '
          + 'Sales tax on materials is part of what the materials cost, not a separate expense.',
      },
      { line: '24a', body: 'Getting somewhere for work and staying there — fares, fuel on a long trip, a hotel. A night away from home, not a day on site.' },
      {
        line: '24b',
        body: 'Meals with a business reason: a client, or a trip that kept you away overnight. '
          + 'Half of what you spent on those is the usual figure.',
        ask: 'Work out which meals qualify before you halve anything. Your own lunch on a local job does not. '
          + 'Some drivers under federal hours rules take 80% instead of half.',
      },
      { line: '25', body: 'Power, water and phone for the business. If a phone is also personal, only the business share — and you should be able to say how you worked it out. Home power belongs in the home office figure instead.' },
      {
        line: '26',
        body: 'Wages you paid other people.',
        ask: 'Not money you took yourself. What a sole trader draws out is not an expense — it is profit, and you are taxed on it either way.',
      },
      {
        line: '27other',
        body: 'Anything real that has no box of its own: bank charges, trade dues, small tools, protective clothing. '
          + 'You list them and the total comes here.',
        ask: 'Protective clothing counts; ordinary work clothes do not, even if you only wear them for work. '
          + 'The test is roughly whether you could wear them down the street.',
      },
    ],
  },
  {
    heading: 'Working from home',
    blurb: null,
    items: [
      {
        line: '30',
        body: 'Two ways again. A flat $5 a square foot, up to 300 square feet, which needs almost no records. '
          + 'Or the long way, which counts a share of your rent or mortgage interest, taxes, power and insurance.',
        ask: 'Before either: the space has to be used regularly and only for the business. '
          + 'A corner of a room the family also uses does not qualify, whichever way you work out the figure.',
      },
      {
        title: 'The connection nobody points out',
        body: 'If your home office is the main place you run the business from, '
          + 'the drive to your first job of the day is business travel rather than commuting. '
          + 'That changes what you put in the mileage boxes at the end of the form.',
      },
    ],
  },
  {
    heading: 'What the form also asks',
    blurb: null,
    items: [
      {
        title: 'The vehicle questions',
        body: 'If you claim car or truck costs, the form asks when you started using the vehicle for work '
          + 'and how the year\'s miles split between business, commuting and everything else. '
          + 'Keep a note through the year; reconstructing it in April is how people get it wrong.',
      },
      {
        title: 'If the year made a loss',
        body: 'The form asks whether all the money in the business was yours to lose. '
          + 'If some of it was not — money you borrowed that you are not personally on the hook for — '
          + 'there is a limit on how much of the loss you can use, and another form goes with it.',
      },
    ],
  },
];

export const closing = {
  heading: 'Where this page stops',
  body: [
    'Everything above is about which box a figure belongs in. That is a fair thing to publish, and it is most of what people get wrong.',
    'What it does not do is decide your facts. Whether that sprayer is spread over years, whether the person who helps you '
    + 'on big jobs is a subcontractor or an employee, whether the back bedroom qualifies at all — those turn on your circumstances, '
    + 'and getting them wrong is expensive in both directions.',
    'That is the part we do, and it is the part worth paying for. If you would rather hand the year over, we take on sole traders.',
  ],
  cta: 'Tell us about your year',
};

/* The one that will silently rot if nobody says it out loud. */
export const yearNote = 'The IRS moved two boxes for 2025: what was line 27a is now 27b. '
  + 'If you are copying figures off an earlier year\'s worksheet, check the number before you trust it. '
  + 'This page is written for the year shown at the top and takes its numbers from that year\'s form.';
