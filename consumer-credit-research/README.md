# consumer-credit-research/

Primary-source research and analysis feeding the **consumer credit-risk-review
process** — the fact base (delinquency, charge-offs, flow/roll rates, lending
standards) used to adjust how the consumer portfolio is assessed.

This is a **research workspace**, not an app: each file is a cited Markdown
analysis that traces every number to a Fed / FDIC / NY Fed / CFPB primary release,
so a claim can be re-verified and the whole doc re-pulled on the source's cadence.

## Contents

| File | What it is |
|---|---|
| `consumer-credit-deterioration-2026.md` | Current-state read: delinquency & charge-offs by product, the delinquency→charge-off lag, leading-vs-lagging structure, the bank-vs-whole-market divergence, the metrics to weight, and what public data can/can't show at segment level. |

## Method (repeat this for each new pass)

1. **Go to the primary release**, never a secondary summary — Fed Charge-Off &
   Delinquency release + FRED, NY Fed HHDC, FDIC QBP, Fed SLOOS, Fed G.19, CFPB.
2. **Cite every number** to its source URL + release quarter; mark anything you
   couldn't confirm to the digit with `⚑ CONFIRM`.
3. **Close with a confidence / open-questions note.**
4. Refresh on the release cadence in the doc's §7 (quarterly for most; monthly G.19).

> **Note on this repo's data sources.** These same feeds already back the suite's
> FRED and NY Fed HHDC monitors — this folder is the *analysis* layer that reasons
> across them and turns them into review-process guidance. For the heaviest
> multi-source fact-checked passes, run `/deep-research` directly.
>
> A machine with unblocked egress to the Fed/FDIC/NY Fed domains (e.g. the work
> desk, which the suite already reaches) can verify the `⚑` figures against the
> primary PDFs/FRED tables — some were snippet-sourced under a session egress block.
