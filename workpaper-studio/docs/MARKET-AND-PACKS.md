# Packs: how a know-how product could be sold

*1 November 2026. The owner said: this is the kind of thing they might sell, packable and marketable to a niche, and that their department depends on how they work. This is a proposal and a set of questions. It invents no prices and no market figures.*

## The idea in one paragraph

An expert's way of working (the questions they ask, the test steps, the conditions, the guidance in their words, the calculations they trust, their recommended limits) becomes a **pack**: one file. Another organization installs it, makes it theirs (words, lists, limits), and its own staff run it. The expert stops being the single point of failure, and the organization buys the know-how once instead of hiring for it. `prototype/journey.html` shows every step working.

## Adapting to a niche without building for one

A niche is a starting pack plus a few patterns. Auditors get a sample-with-attributes pattern and a control-test pack; a credit reviewer gets a question framework and line items by guarantor; a close team gets a reconciliation pack. The engine does not change between them, and a buyer can save their own patterns, so every buyer adapts the product further without a code change.

## What makes a pack sellable

- **One file.** Easy to send, version, list and install.
- **Narrow.** "Small-business credit file review for community lenders" sells; "workpaper software" does not. The same engine serves several niches, so the shelf can grow without new software (the List step shows this).
- **Honest about authority.** A pack carries the author's *recommended* limits and never claims they are the buyer's policy. The buyer must confirm every limit before anything is tested against it. This is the repository's refuse-rather-than-default rule applied to a product, and it is also what a regulated buyer will want to see.
- **Safe to update.** Locked structure plus a diff the buyer reads means updates apply cleanly and never overwrite their confirmed limits or their entries.
- **Proof built in.** The install checks the file's fingerprint, that every calculation has its inputs, and that the shipped test cases pass. Refusal names the next step.

## Ways to charge (options, not advice)

| Model | Fits when | Watch for |
|---|---|---|
| Sell packs; free or cheap runtime | The know-how is the value | Support load per buyer |
| Sell the runtime per organization; packs included | Buyers want one vendor | Needs install, licence and update machinery |
| Packs as a service: you configure the buyer's pack | Early customers; learning what buyers change | Does not scale; it is consulting |
| Annual updates | The pack tracks something that changes | You commit to maintaining it |

**Recommendation:** start with the third, because the first customers will teach you what a buyer changes, and your *locked/adjustable* settings should come from that, not from guesses. Then move to the first.

## Things to settle before selling (honest risks)

1. ~~Who owns the know-how.~~ Settled by the owner (D15): the work is original and will be recreated as such.
2. **Regulated buyers will ask for validation.** A bank or lender using a calculation tool may need documentation of how each method works and was tested. The method page with its test vectors is a start, not a substitute.
3. **Liability for methods.** A wrong method in a pack is your problem. Keep the library small and tested; label demonstration methods as such.
4. **Support.** Every buyer is a person with a question. Price for it.
5. **Do not ship thresholds as authority.** A pack's limits are recommendations. Keep it that way in the product and in the listing.

## Open questions for the owner

- ~~Which niche first~~ Auditors are a confirmed audience; the product adapts through packs and patterns rather than being built for one niche (D17).
- What would a buyer most want to change? (This decides what to lock.)
- Do you want to sell packs, a runtime, or your time?
- Whose rights apply to the existing workbook?
