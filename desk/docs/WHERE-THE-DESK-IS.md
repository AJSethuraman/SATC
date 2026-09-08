# Where the desk is

**The desk is a session, not a library.** `THE-DESK-IS-A-SESSION.md` argues why.
This file answers the one question that argument leaves open: *which session?*

---

## The desk session

| | |
|---|---|
| **Forge-Desk** | `session_016cgnNu73t4Y3pGyMYTNExh` |
| Last confirmed | **8 September 2026, 16:27 UTC** — request `904c3671edd9` fired to it |
| Where it runs | the firm's machine, which is the point — it has a browser |

Every desk round trip on record has gone to this session: `413dc229b76c` (the
lease hole, on 0.10.2), the `#344` live browser run, and the 0.11.x / 0.12.x
rounds.

**The asking session sets it as an environment variable before consulting:**

```
SATC_DESK_SESSION=session_016cgnNu73t4Y3pGyMYTNExh
```

---

## Why this is written down but NOT used as a default

**Both halves are deliberate, and they answer two different failures.**

**Recorded, because not recording it cost a false blocker.** On 8 September a
session with the variable unset told the firm the round trip *"cannot be done
from this container"* — and then found the id in ninety seconds by reading
`list_triggers`, where every previous round trip had left one. The firm:

> *"How in the world will the skill ever work if you can't even keep it
> straight. Does it need built into the plugin itself?"*

Nothing in the repository said where the desk was. Finding it required knowing
to grep the trigger list, which is archaeology, and a step that needs
archaeology is a step that will be skipped.

**Not a default, because a stale id fails SILENTLY and that is worse.**
`relay.desk_session()` refuses when the variable is unset, and keeps refusing —
it reads this file's name into its error, never this file's contents. The
reasoning is in that function and it stands:

> *A wrong one fails silently — the question goes somewhere, the asker waits,
> and nothing says the desk never saw it.*

A session id changes when a container is replaced. If the code trusted this
page, the day Forge-Desk is recreated every question would fire into a dead
session and every asker would wait forever, with a green test suite. Refusing
is loud; a stale default is not. `DESIGN-PRINCIPLES.md`: **refuse rather than
default.**

So: **a human or a session reads this page and exports the value.** That one
step is the check that the id is still the right one.

---

## If it looks wrong

**Do not guess, and do not resend into the void.** In order:

1. **Check the trigger record.** `list_triggers` shows every trigger bound to a
   session; the ones named `Desk request …` and `Desk answer …` name the two
   ends of past round trips. The most recent `persistent_session_id` that is not
   this session is the desk.
2. **Ask the firm.** Forge-Desk runs on their machine and only they know whether
   it is up.
3. **Update this page** with the new id and the date it was confirmed, in the
   same commit as whatever needed it.

**A fire returning 200 is not delivery, and an absent `last_fired_at` is not
evidence of non-delivery** — both measured 8 September 2026. Only the recipient
knows. If no answer comes back, say so; do not resend on the strength of the
record, and do not substitute a test this container *can* run and call it
verification.
