# Pool versus word list — the last comparison, 10 September 2026

`tools/pool_vs_routing.py` ran both mechanisms over the same questions and
printed what each returned. It was the evidence `dec-order` asked for. On
10 September 2026 the firm ended the question — *"I said to delete them. I've
said to multiple times."* — and `routing.py` was deleted, so half the comparison
no longer exists and the tool went with it.

**This file is the last run, verbatim.** It is frozen rather than re-derived,
because a comparison against a mechanism that no longer exists cannot be re-run,
and a test asserting its numbers would be a test nobody could ever fail.

## What it measured

**Every question in it was actually asked.** Section 1's seven phrasings are
Forge-Occam's, verbatim from their field report of 9 September; section 2's
fifteen are the working vernacular of a close; section 3's is `dec-kill`'s own.
None was invented for the comparison — the last time a check in this repository
was built from imagined phrasings, the vocabulary was widened by nineteen words
to satisfy sentences nobody had typed, and six plain bookkeeping questions
started being answered out of tax law.

The one case with a known right answer is section 1, and the denominator is
one: Forge-Occam's `personal-or-business` desk escalated `authority_absent`
after two independent judges refused two different citations, and reported that
the authority it wanted was Pub. 583's recordkeeping guidance — which sat on
`cash-and-bank`. One case is thin, and it is stated rather than padded.

## The run, against the seven records

```
pool: 794 citations from 7 records (794 with stored text)

1 · The one case with a known right answer: Pub. 583 on records to keep
=======================================================================
   phrasing                                                   word list                    pool top 3
   what supporting documents does the client have to keep?    -- nothing --                #1
   what supporting documents must be kept?                    -- nothing --                #1
   recordkeeping for business expenses                        personal-or-business         #1
   what receipts do we need to keep?                          meals-and-entertainment      #3
   what records must be kept for a business expense?          capitalization-and-de-mini   -- not in top 3 --
   supporting documents for a bank statement charge           cash-and-bank                #1
   what kinds of records to keep for a bank account?          cash-and-bank, vehicle-exp   #1

   word list reached the holding desk: 2/7
   pool placed the authority in top 3: 6/7

2 · Does anything come back at all, on the working vernacular
=============================================================
   2 desk(s) | IRS Pub. 463 (2025), "Adequate evidence"           what records are required for a charge with 
   4 desk(s) | 26 CFR 1.274-5T(c)(2)(i)                           charge on the bank statement with no receipt
   0 desk(s) | 26 CFR 1.62-2(j) Example 3                         we do not know what was bought - can we dedu
   1 desk(s) | IRS Pub. 463 (2025), "Accounting to Your Client"   the client took cash out of the ATM and we d
   1 desk(s) | 26 CFR 1.6041-1(a)(1)(v) Example 1                 is a payment to a credit card we have no sta
   0 desk(s) | IRS Pub. 583 (12/2024), "Reconciling the checkin   unlabelled deposits into the business accoun
   1 desk(s) | 26 CFR 1.6050W-1(e) Example 12                     the owner paid the company card from a perso
   0 desk(s) | 26 CFR 1.274-5T(c)(2)(ii)                          a cheque with no payee on the feed - how do 
   2 desk(s) | 26 CFR 1.6041-1(b)(1)                              hand tools bought for the trade - deducted o
   1 desk(s) | IRS Pub. 463 (2025), "Exception to the 50% Limit   beer at a taproom with a customer - is it de
   1 desk(s) | IRS Pub. 463 (2025), "Leasing a Car"               mileage or actual expenses for the van?
   2 desk(s) | 26 CFR 1.6050W-1(e) Example 14                     cash back on the business card - income?
   0 desk(s) | IRS Pub. 583 (12/2024), "Supporting Documents"     what supporting documents does the client ha
   0 desk(s) | IRS Pub. 583 (12/2024), "Reconciling the checkin   the statement cycle closes on the 2nd, what 
   2 desk(s) | IRS Pub. 583 (12/2024), "Supporting Documents"     groceries on the business card - business or

   word list returned nothing: 5/15
   pool returned nothing:      0/15
   NOTE: returning something is not the same as returning the right thing.
         Only section 1 has a known right answer.

3 · The question that killed the word list (dec-kill)
=====================================================
   'are unidentified deposits gross receipts?'
   word list -> meals-and-entertainment, rewards-and-information-returns
   pool ->
       11.43  26 CFR 1.263(a)-3(h)(3)(iv)                              [fixed-assets]
        9.53  Rev. Rul. 2005-28, HOLDING                               [rewards-and-information-returns]
        9.46  Rev. Rul. 2005-28, ISSUE                                 [rewards-and-information-returns]
   NEITHER IS RIGHT. Nothing on file settles whether an unidentified
   deposit is revenue; that is a coverage hole, not a retrieval one.
```

## The same questions against the one corpus, the same day

The merge deduplicated 794 citations down to 785 and resolved six truncations to
the longer text, so the scores move slightly. The result does not.

```
pool: 785 citations from one corpus
   what supporting documents does the client have to keep?    #1
   what supporting documents must be kept?                    #1
   recordkeeping for business expenses                        #1
   what receipts do we need to keep?                          #2
   what records must be kept for a business expense?          -- not in top 3 --
   supporting documents for a bank statement charge           #1
   what kinds of records to keep for a bank account?          #1
   pool placed the authority in top 3: 6/7

   'are unidentified deposits gross receipts?' ->
       11.48  26 CFR 1.263(a)-3(h)(3)(iv)
        9.56  Rev. Rul. 2005-28, HOLDING
        9.49  Rev. Rul. 2005-28, ISSUE
```

## What the numbers say, and what they do not

- **The word list reached the holding desk on 2 of 7 phrasings; the pool placed
  the authority in the top three on 6 of 7.** That is the finding `dec-kill` was
  made on, re-measured.
- **The one phrasing the pool still misses is the same one:** *"what records must
  be kept for a business expense?"* — the general question, where the corpus's
  most specific texts outscore the general guidance.
- **On the working vernacular the word list returned nothing 5 times in 15 and
  the pool returned nothing 0 times in 15. THE SECOND NUMBER IS NOT A WIN.** A
  retrieval that always answers is one whose answer means nothing. It is the open
  problem, measured separately in
  `tests/test_a_score_cannot_tell_you_nothing_answers_this.py`, which establishes
  that **no score cutoff separates answerable from not-on-file**: five of six
  questions with no answer on file outscore the weakest question that has one.
- **On `dec-kill`'s own question — "are unidentified deposits gross receipts?" —
  neither mechanism is right.** The word list reached
  `meals-and-entertainment` (because `receipts` sat there meaning *the paper you
  keep*) and `rewards-and-information-returns`. The pool returns a capitalization
  rule and a rewards ruling. **Nothing on file settles it.** That is a coverage
  hole, not a retrieval one, and it is what `dec-coverage` is about.
