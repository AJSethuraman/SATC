"""Fixed raw-block anchors, shared by the runner and the builder.

One block per entity slot: periods as rows (newest first), fields as columns.
The anchor of a block depends only on ``(slot, raw_slots)`` -- never on which
entity occupies the slot. That is the whole reason a peer list is a config edit
rather than a rebuild: swapping which bank sits in slot 3 moves no formula,
because every dashboard formula points at slot 3's cells, not at that bank's.

The geometry is deliberately shared with the builder rather than duplicated. Two
copies of a layout rule is exactly the "two lists that must agree" failure this
package exists to remove -- and here the disagreement would be silent, writing
one bank's figures under another bank's name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

#: Rows per block header: the identity row, then the field-name label row.
HEADER_ROWS = 2
#: Blank rows between blocks, so a block is visually separable in the sheet.
GAP_ROWS = 2
#: The first block's header row (row 1 is the tab's banner note).
FIRST_ROW = 2
#: Column A holds the period; fields start at column B.
PERIOD_COL = 1
FIRST_FIELD_COL = 2


@dataclass
class SlotBlock:
    slot: int
    header_row: int
    label_row: int
    first_data_row: int
    slots: int                 # period rows kept (raw_slots)

    @property
    def last_data_row(self) -> int:
        return self.first_data_row + self.slots - 1


def slot_label(slot: int) -> str:
    """The layout sentinel written into column A of a block's header row.

    The runner reads this back before writing and refuses a mismatch, which is
    what makes ``raw_slots`` build-bound rather than a number anyone can edit
    into a silent misalignment.
    """
    return "slot%02d" % slot


def slot_block(slot: int, raw_slots: int) -> SlotBlock:
    """Deterministic block placement from ``(slot, raw_slots)`` alone."""
    stride = HEADER_ROWS + raw_slots + GAP_ROWS
    header_row = FIRST_ROW + (slot - 1) * stride
    return SlotBlock(slot, header_row, header_row + 1,
                     header_row + HEADER_ROWS, raw_slots)


def field_col(fname: str, fields: Sequence[str]) -> int:
    """Column for a field: B onward, in the source's fixed field order."""
    return FIRST_FIELD_COL + list(fields).index(fname)


def assemble_periods(field_rows: Dict[str, List], raw_slots: int,
                     fields: Sequence[str]
                     ) -> List[Tuple[str, Dict[str, Optional[float]]]]:
    """Per-field normalized rows -> newest-first ``[(period, {field: value})]``.

    Periods are *unioned* across fields, not taken from any one field. A field
    that is missing one period then yields a blank cell in that row rather than
    shifting every later value up a row -- which would silently attribute one
    quarter's figure to another quarter.
    """
    periods = sorted({row.period for rows in field_rows.values() for row in rows},
                     reverse=True)[:raw_slots]
    per: Dict[str, Dict[str, Optional[float]]] = {p: {} for p in periods}
    for fname, rows in field_rows.items():
        for row in rows:
            if row.period in per:
                per[row.period][fname] = row.value
    return [(p, {f: per[p].get(f) for f in fields}) for p in periods]
