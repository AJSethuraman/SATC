"""ACTIONS — what the practice would do next, already prepared.

The queue that answers "what needs me today?" without the owner having to
notice anything. Every entry carries its evidence in one line and, where it is
a message, a draft that is already written.

Nothing here sends, signs, files, or writes. It reduces a decision to one click
— it does not remove the decision. That is deliberate and permanent: sending
stays a human act, so the value has to come from making the click cheap.

Almost all of it is deterministic. A document is outstanding or it is not; a
deadline is nine days away or it is not; a 1099 arrived last year and hasn't
this year. Doctrine rule 8 — take the grind away from the human before asking a
model to be clever. A local model's budget goes on the margin: phrasing, and
the judgment calls the queue surfaces but cannot settle.
"""

from __future__ import annotations

from datetime import date

from satc.actions.propose import (
    ActionKind,
    ActionQueue,
    ProposedAction,
    Urgency,
    action_id,
    ask_prior_year_questions,
    chase_outstanding,
    chase_signature,
    deadline_pressure,
    extension_candidate,
    invite_to_interview,
    sort_key,
)

__all__ = [
    "ActionKind",
    "ActionQueue",
    "ProposedAction",
    "Urgency",
    "action_id",
    "build_queue",
    "sort_key",
]


def build_queue(*, clients, documents, obligations=(), engaged_clients=(),
                tax_year: int, today: date | None = None) -> ActionQueue:
    """Run every proposer over the practice and return the ordered queue.

    Takes plain records — no Flask, no STATE — so the whole queue is a pure
    function of the practice's data and one date. That is what makes it
    testable, and what makes "why is this here?" always answerable.
    """
    today = today or date.today()
    engaged = set(engaged_clients)
    out: list[ProposedAction] = []

    for client_id in clients:
        signature = chase_signature(documents, client_id=client_id,
                                    tax_year=tax_year, today=today)
        if signature is not None:
            out.append(signature)

        chase = chase_outstanding(documents, client_id=client_id,
                                  tax_year=tax_year, today=today)
        # An 8879 chase already covers the outstanding list for this client; two
        # rows saying "chase them" is how a queue starts getting ignored.
        if chase is not None and signature is None:
            out.append(chase)

        prior = ask_prior_year_questions(documents, client_id=client_id,
                                         tax_year=tax_year, prior_year=tax_year - 1)
        if prior is not None:
            out.append(prior)

        extension = extension_candidate(documents, obligations, client_id=client_id,
                                        tax_year=tax_year, today=today)
        if extension is not None:
            out.append(extension)

        invite = invite_to_interview(documents, client_id=client_id, tax_year=tax_year,
                                     has_engagement=client_id in engaged)
        if invite is not None:
            out.append(invite)

        out.extend(deadline_pressure(obligations, client_id=client_id, today=today))

    out.sort(key=sort_key)
    return ActionQueue(actions=out, generated_for=today)
