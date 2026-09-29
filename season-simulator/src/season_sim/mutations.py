"""Check the checker: break the real function an invariant guards, in THIS process.

Principle 12 (`docs/DESIGN-PRINCIPLES.md:224`): a check that has never failed is
not evidence. Each mutation below replaces one real production function, in the
worker process only, with a broken version of itself. Nothing on disk changes:
the patch dies with the process, which is the "restore". The simulator is then
run and the named invariant must report it.

Each entry: name -> (the invariant that must go red, what is broken, patch).
"""

from __future__ import annotations

from datetime import timedelta


def _deadline_shift():
    import deadlines
    real = deadlines.filing_date

    def shifted(return_type, tax_year, *, extended=False):
        return real(return_type, tax_year, extended=extended) + timedelta(days=1)
    deadlines.filing_date = shifted


def _drop_chase():
    import satc.actions as actions
    actions.chase_outstanding = lambda *a, **k: None


def _unsorted_queue():
    import satc.actions as actions
    from satc.actions.propose import _URGENCY_ORDER

    # Urgency backwards: routine rows above overdue ones.
    actions.sort_key = lambda a: (-_URGENCY_ORDER.get(a.urgency, 9), a.client_id, a.kind)


def _board_drops_a_job():
    import satc.work.queue as q
    real = q._split

    def split(jobs, **kw):
        jobs = list(jobs)
        return real(jobs[1:], **kw) if len(jobs) > 1 else real(jobs, **kw)
    q._split = split


def _signing_list_drops():
    import signing
    real = signing.waiting

    def waiting(*a, **k):
        return real(*a, **k)[1:]
    signing.waiting = waiting


def _board_unsorted():
    import deadlines
    real = deadlines.board

    def board(*a, **k):
        due, unplaced = real(*a, **k)
        return list(reversed(due)), unplaced
    deadlines.board = board


MUTATIONS = {
    "deadline_shift": ("A2", "client-documents deadlines.filing_date moved one day later",
                       _deadline_shift),
    "drop_chase": ("B6", "satc_system's chase_outstanding proposer removed from build_queue",
                   _drop_chase),
    "unsorted_queue": ("B3", "build_queue sorted with urgency reversed", _unsorted_queue),
    "board_drops_job": ("C1", "the work board silently drops the first job", _board_drops_a_job),
    "signing_list_drops": ("D3", "signing.waiting drops its first engagement",
                           _signing_list_drops),
    "season_unsorted": ("E2", "deadlines.board returns its rows reversed", _board_unsorted),
}


def apply(name: str) -> tuple[str, str]:
    inv, what, patch = MUTATIONS[name]
    patch()
    return inv, what
