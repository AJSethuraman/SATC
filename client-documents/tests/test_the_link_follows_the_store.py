"""`--store` scopes the money the same way it scopes the files.

**IT DID NOT, UNTIL 4 SEPTEMBER 2026.** `--store` routed where the invoice JSON
was written; the processor and its token came from `registry/payments.yaml` and
the Windows credential store, so a run scoped entirely to a scratch directory
still reached the firm's **production** Square account.

The standing instruction on the machine this runs on is *point tests at a temp
store*. An agent obeying it believed it was isolated and was not — and that is
how this was found: an assessment agent did exactly that, and got back
`400 — This idempotency key has already been used to create a Payment Link`.

**Nothing was created, and the 400 is not the reassurance it looks like.** A 400
is what a *differing body* returns. The idempotency key is `satc-<invoice>`
while the invoice number is scanned from the local store only, so a fresh temp
store starts at `2026-0001` and collides with keys already spent on the live
account. **Had the amount matched, Square returns the existing link** — and the
fictional test client is handed a real client's payment link.

The firm, 4 September 2026, choosing between four options:
*"--no-link defaults on any non-default --store"*.

NO TEST HERE MAKES A NETWORK CALL, and the important one proves it: the
transport it installs raises if anything reaches it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import engagements
import payments


DEFAULT = engagements.STORE


# ── the decision, on its own ─────────────────────────────────────────────────

def test_the_engagement_store_still_gets_a_link():
    """The ordinary case must be untouched. A fix that makes the firm type an
    extra word to bill a real client has moved the cost rather than removed
    it."""
    assert payments.link_follows_the_store(
        store=DEFAULT, default_store=DEFAULT).wanted is True


def test_any_other_store_does_not(tmp_path):
    choice = payments.link_follows_the_store(
        store=tmp_path, default_store=DEFAULT)
    assert choice.wanted is False
    assert str(tmp_path) in choice.reason, (
        "the refusal must name the store it is talking about; a person who "
        "cannot see which directory triggered it cannot tell whether it is "
        f"right. Got: {choice.reason!r}")
    assert "--link" in choice.reason, (
        "the refusal must name the way out of it — S3, an error is the "
        f"interface. Got: {choice.reason!r}")


def test_no_link_wins_even_on_the_real_store():
    assert payments.link_follows_the_store(
        store=DEFAULT, default_store=DEFAULT, no_link=True).wanted is False


def test_link_is_the_escape_hatch_and_it_has_to_exist(tmp_path):
    """Without it, a firm that keeps its engagements anywhere but the default
    could never raise a real bill. A safety default with no override is not a
    default, it is a wall."""
    assert payments.link_follows_the_store(
        store=tmp_path, default_store=DEFAULT, link=True).wanted is True


def test_asking_for_both_is_refused_rather_than_resolved():
    """`--link --no-link` is a contradiction, not a precedence puzzle. Picking
    a winner silently would mean one of the two things the operator typed was
    ignored without being told."""
    with pytest.raises(payments.PaymentError) as exc:
        payments.link_follows_the_store(
            store=DEFAULT, default_store=DEFAULT, no_link=True, link=True)
    assert "--link" in str(exc.value) and "--no-link" in str(exc.value)


def test_the_same_directory_spelled_two_ways_is_the_same_directory():
    """`engagements/.` and `engagements` are one place. A string comparison
    says otherwise and suppresses a link the firm asked for — which is the
    failure mode of the fix, so it is asserted."""
    assert payments.link_follows_the_store(
        store=Path(str(DEFAULT) + "/."), default_store=DEFAULT).wanted is True


# ── and the one that matters: no call is made ────────────────────────────────

class Tripwire:
    """Stands in for `payments.link_for` and refuses to be reached.

    **THE FIRST VERSION OF THIS TEST WAS DECORATION, and the mutation run is
    the only reason that is known.** It put the tripwire on the HTTP
    transport and asserted the output contained the words 'no link'. Both
    halves were wrong, and the test passed against the bug it was written to
    catch:

    - `processor()` refuses before any transport is touched when no Square
      token is configured, which is the state of every test machine. The
      tripwire could not fire, so it proved 'no token here', not 'no call
      made'.
    - "No link on this bill —" is exactly what the OLD code printed when the
      processor refused. The assertion matched the bug's own output.

    Watching `link_for` tests the actual claim -- *did this run decide to
    create a live payment link* -- and the test stubs `processor` too, so the
    tripwire is genuinely reachable rather than sitting here looking like
    protection while being incapable of failing.
    """

    def __init__(self):
        self.reached = False

    def __call__(self, *a, **k):
        self.reached = True
        raise AssertionError(
            "A LIVE PAYMENT LINK WAS REQUESTED FROM A TEMP STORE. This is "
            "the exact defect this module exists to prevent: --store must "
            "scope the money seam, not only the file path.")


def test_an_invoice_raised_in_a_temp_store_contacts_nobody(tmp_path, capsys):
    """END TO END, THROUGH `cmd_invoice`, WITH A TRIPWIRE ON THE WIRE.

    The unit tests above prove the decision. This proves the decision is
    actually consulted on the path that had the bug — the two are different
    claims, and the second is the one that was false.
    """
    import cli

    store = tmp_path / "engagements"
    # The field names invoicing._sum actually reads. INVENTED VALUES: no real
    # client name, and an address that cannot resolve.
    record = {
        "ClientName": "Walkthrough Fixture", "EngagementRef": "2026-0001",
        "ClientEmail": "fixture@example.invalid",
        "LineItems": [{"Service": "Preparation", "Amount": "$500.00"}],
    }
    engagements.save(record, "2026-0001", store)

    tripwire = Tripwire()
    real_link_for, real_processor = payments.link_for, payments.processor
    payments.link_for = tripwire
    # ALSO STUB THE PROCESSOR. Without this the tripwire cannot fire on a
    # machine with no Square token: `processor()` is evaluated first, raises,
    # and `link_for` is never reached -- so the guard would sit here looking
    # like protection while being incapable of failing. Behaviour 16: a
    # check that cannot fail has not passed.
    payments.processor = lambda **k: "a processor stub"
    try:
        cli.cmd_invoice(_invoice_args(store=store, engagement="2026-0001"))
    finally:
        payments.link_for, payments.processor = real_link_for, real_processor

    assert tripwire.reached is False, "a live payment link was requested"
    out = capsys.readouterr().out
    # THE SPECIFIC REASON, not the words 'no link' -- which is also what the
    # old code printed when the processor merely refused, and is therefore
    # useless for telling the fix apart from the bug. The first version of
    # this test asserted exactly that, and the mutation run caught it.
    assert "not the engagement store" in out, (
        "the suppression has to say WHY, distinguishably from the processor "
        "simply being unconfigured. Output was:" + chr(10) + out)
    assert "--link" in out, "and it has to name the way to override it"


def _invoice_args(**over):
    """The argparse namespace `cmd_invoice` reads, with today's defaults."""
    class A:
        pass
    a = A()
    a.engagement = "2026-0001"; a.store = None; a.number = None
    a.billed = "2026 tax year"; a.credit = None; a.no_link = False
    a.link = False; a.sandbox = False; a.variance_note = None
    for k, v in over.items():
        setattr(a, k, str(v) if k == "store" else v)
    return a


# ── check the checker ────────────────────────────────────────────────────────

def test_the_old_behaviour_would_fail_these_tests(tmp_path):
    """MUTATION. The old rule was `if not args.no_link:` — the store never
    consulted. Reintroduce exactly that and the temp-store case must disagree
    with the new answer.

    A regression test that passes against the bug it names is decoration.
    """
    def old_rule(no_link=False, **_):
        return not no_link

    assert old_rule(no_link=False) is True, (
        "the old behaviour no longer reproduces, so the tests above are not "
        "pinning what they claim to pin")
    new = payments.link_follows_the_store(store=tmp_path, default_store=DEFAULT)
    assert new.wanted is False
    assert new.wanted != old_rule(no_link=False), (
        "old and new agree on a temp store — the fix is doing nothing")


def test_nothing_else_builds_a_link_without_asking_first():
    """The rule is only worth having while it is the only decision.

    `link_for` is the one call that creates a live payment link. Every caller
    of it in this tree must go through `link_follows_the_store` first, or the
    next command to grow a link will reintroduce the bug in a new place —
    which is exactly how `SATC_DATA_DIR` came to be honoured by two callers
    out of eight the same afternoon.
    """
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in sorted(root.glob("*.py")):
        if path.name in {"payments.py", "square_setup.py"}:
            continue                       # where the seam itself lives
        text = path.read_text(encoding="utf-8", errors="replace")
        if "link_for(" not in text:
            continue
        if "link_follows_the_store" not in text:
            offenders.append(path.name)
    assert not offenders, (
        f"{offenders} call payments.link_for() without first asking "
        f"link_follows_the_store() whether this run may touch live payments")
