# The judge, built as an input rather than an opinion — 8 September 2026

**Every gate in `engine._check` is exact.** The citation resolves or it does
not. The submitted conclusion is the firm's ratified one or it is not. The
publisher governs the domain or it does not. Not one of them is a statement
about whether *this paragraph supports this conclusion*, and none can be.

The desk that found the sharpest defect this system has produced said why, on
8 September:

> *"What it cannot catch is a correct position applied to the wrong facts — and
> that is the more likely error in a real close, because the agent isn't
> disagreeing with the firm, it's misreading which of the firm's two positions
> is in play."*

The answer named there, and named again in each of the two rounds after it, is
a **judge**: a second model handed the paragraph and the conclusion and asked
whether one supports the other. It has been the open item since 6 September.

---

## What was built, and what deliberately was not

**The engine does not judge.** It has no model and no network — this suite
replaces the socket layer outright, and `comparing`'s docstring records what
happened the one time a module on the front door's path could reach a fetcher by
import. So a judgment arrives the way a proof does: **as an input, never as
something the engine goes and obtains.** `prove` set that shape on the fourth
docket and it is the right one here for the same reason — a boolean would mean
this function reaches a model whenever something, somewhere, is configured true.

`ask.answer(..., judged=judging.Judgment(by=…, supports=…, because=…))`.

**And it checks exactly one thing, which is decidable without reading:**

> The words the judge says carry the answer must be in the passage.

Not a word-overlap score and not a similarity threshold — `guards.py` already
refuses to block on either, because both over-refuse or under-catch. This is the
same comparison `proving` makes against a publisher, through the same
`comparing` module, with the same meaning for a marked omission: segments
matched **in order**, so a judge cannot assemble a sentence the regulation does
not contain out of words it does.

**What is still not decidable here**, stated so nobody reads this as more than
it is: whether the quoted words actually carry the conclusion. That is the
judge's call. `judging` checks the *judgment*; it is not a second opinion on the
answer.

## The run it was built for

The 7 September failure, unchanged and still pinned by a test:

```
answer: "deducted, not capitalized"
cited:  26 CFR 1.263(a)-2(d)(1)
        "a taxpayer must capitalize amounts paid to acquire or produce a
         unit of real or personal property […] include the invoice price"
->      SERVED
```

Every exact check passed and every one was right to. With a second reader:

```
->      THE DESK DID NOT ANSWER — citation_does_not_support · fixed-assets
        …a second reader (second-reader) says the paragraph does not carry
        'deducted, not capitalized': the paragraph requires capitalization
        of amounts paid to acquire a unit of personal property…
```

**`test_the_seventh_september_answer_is_still_served_unjudged` pins the first
one**, so nobody reads this file as a claim the engine got smarter. It did not.

## Three outcomes, and why two of them are not the same refusal

| the judge | what happens | why |
|---|---|---|
| says the paragraph does not carry it | `citation_does_not_support` | The reason already exists and names the same fix: cite the paragraph that answers what was asked. A new reason would have split one problem across two names. |
| quotes words that are not in the passage | **`judgment_not_in_the_passage`** (new) | The answer is **not refused on its merits — nobody has read it.** Filing this as an authority problem would put a defect in the second reader into the queue that reads out what the *record* is missing, and that queue is how the firm decides what to go and find. |
| is the party that answered | `JudgingError`, raised | C6: the preparer does not become the verifier. A caller handing the engine one model wearing both hats has broken the contract, and a refusal filed in `unsupported/` would record it as a finding about the record when it is a finding about the caller. |

Adding the one new reason forced two decisions the repository's own guards
demanded on the spot, which is what those guards are for:
`test_every_reason_is_legibly_about_authority_facts_or_a_document` made it
declare which *kind* of problem it names, and
`test_a_brain_is_offered_every_reason_it_could_observe` made it declare that a
brain can never escalate it — only `judging.read` raises it, and a brain that
could claim its judge misquoted would be marking the marking of its own work.

## What runs when

The gate, then the proof, then the judge. **Each stage may add a refusal and
none may remove one**, and the order follows from that: judging an answer whose
passage the publisher no longer carries would be a second reader confirming text
that has already been withdrawn. A test holds it — a judgment cannot rescue an
answer the gate refused.

## Six mutations, six caught

The quote check always passing; independence not checked; a `no` served anyway;
judging moved ahead of the gate; the ordered match replaced with an unordered
one; and the not-in-the-passage case reported as a bad answer. All six red.

**And one self-proving test caught by writing it**: the offline guard first
scanned the whole module for the word `fetch` and went red on `judging`'s own
docstring explaining why it does not fetch — a guard that forbids the record
from naming the defect it exists for. That is the second such guard written here
in three days. It reads the import lines now, through `ast`, and the whole list
is `__future__`, `dataclasses`, `comparing`.

---

## For the firm — and this one is deliberately not decided here

**Nothing requires a judgment.** Which desks may not serve an unjudged answer is
the firm's call, not a session's, and a gate that turned itself on across seven
desks overnight would be exactly this session making it. The default path is
unchanged and a test says so.

The question, for the docket:

> Should any desk refuse to serve an answer no second reader has looked at —
> and if so, which? Every answer judged costs a second model call on every
> served answer; no answer judged leaves the one error class every exact check
> passes exactly where it was on 7 September.

The recommendation: **turn it on for `cash-and-bank` first.** Checked rather
than assumed — it is the only desk of the seven that holds two ratified
positions on one passage, and it is the desk where the "right position, wrong
facts" error has already happened. Leave the other six until a run gives a
reason to move them; measuring the cost on one desk is what tells the firm what
seven would cost.
