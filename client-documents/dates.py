"""The one place a date becomes a date string.

`%-d` — the day of the month with no leading zero — is a **glibc extension**.
It is not in the C standard, and it does not exist in Microsoft's CRT. On Linux
`date.today().strftime("%B %-d, %Y")` returns `September 3, 2026`; on Windows
the same call raises `ValueError: Invalid format string`.

That mattered on 3 September 2026, when this suite ran on the firm's own
Windows machine for the first time after a year of only ever running in a Linux
container. Eight call sites across seven modules used `%-d`, and every test that
dated a letter, an estimate or an invoice errored out — several hundred of them.
The software had never been portable; nothing had ever asked it to be.

The Windows spelling is `%#d`, so the obvious repair is a platform branch. This
module does not do that, because a branch is two code paths and only one of
them is ever exercised by whoever is running the tests that day. `.day` is an
`int` and formats without padding on every platform, so there is nothing to
branch on.

Every date a client reads should come from here. If a new format is needed, add
a function rather than a format string at the call site — that is the whole
point of the module, and it is the same reason `money.py` exists.
"""

from __future__ import annotations


def long_date(d) -> str:
    """`September 3, 2026` — the stamp on a letter, an estimate, an invoice."""
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def day_month(d) -> str:
    """`3 September` — the short form, for a deadline in a running sentence."""
    return f"{d.day} {d.strftime('%B')}"


def weekday_day_month(d) -> str:
    """`Thursday 3 September` — today, said the way a person says it."""
    return f"{d.strftime('%A')} {day_month(d)}"
