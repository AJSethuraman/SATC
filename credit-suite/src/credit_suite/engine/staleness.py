"""The staleness guard: fetch success is not data currency.

Carried from the FDIC monitor's trap F2, and the reason it exists is worth
keeping attached: a bank that merged away keeps returning its final reporting
date, with a perfectly successful HTTP 200 and no error anywhere. Without this
guard the workbook shows that bank's last-ever figures under today's timestamp,
which reads as current.

The test is *relative to the peer set*, not absolute. An absolute age test would
flag every entity at once whenever a regulator's release slipped, which trains
the analyst to ignore the flag; a relative test flags the one entity that
stopped reporting while its peers carried on.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def is_stale(last_period: Optional[str], set_max_period: Optional[str],
             stale_multiplier: float, period_days: int) -> bool:
    """True when this entity's latest period lags the set's by too much.

    An entity with no period at all is stale -- nothing landed, so nothing is
    current. When *nothing* landed anywhere there is no baseline to judge
    against, and claiming staleness would be inventing a finding, so that case
    is not stale.

    An unparseable period is stale: a date this cannot read is a date it cannot
    vouch for.
    """
    if last_period is None:
        return True
    if set_max_period is None:
        return False                      # nothing landed anywhere: no baseline
    try:
        last = date.fromisoformat(str(last_period)[:10])
        newest = date.fromisoformat(str(set_max_period)[:10])
    except ValueError:
        return True
    return (newest - last).days > stale_multiplier * period_days
