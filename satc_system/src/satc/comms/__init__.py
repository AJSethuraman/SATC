"""CLIENT COMMUNICATIONS — per-client drafts the preparer sends by hand.

The practice writes the same handful of letters over and over: invite them to an
interview, get the engagement letter signed, ask for documents, chase what's
missing, deliver the finished return, send the bill. This area renders each of
those as a DRAFT prefilled from what the practice already knows about that
client — their name, the year, the items their engagement actually asked for,
what's still outstanding in the document register, the result on their return.

Three deliberate boundaries:

* **No SMTP. Nothing is sent.** The app renders text; the preparer reads it,
  edits it, and sends it from their own mail client. Sending stays a human act.
* **Nothing is invented.** A merge field with no fact behind it renders as a
  visible ``[[ … : fill in ]]`` marker, never a guess and never a silent blank.
* **Templates are config.** Bodies and metadata live in ``configs/comms/``;
  adding or rewording a template is a config edit, not a code change.

Three pieces, each testable alone (``tests/test_comms.py``):

===================================  ======================================
:mod:`satc.comms.library`            reads ``configs/comms/`` into objects
:mod:`satc.comms.context`            practice state -> merge values
:mod:`satc.comms.render`             merge values -> a draft + what's missing
===================================  ======================================
"""

from __future__ import annotations

from satc.comms.context import build_context
from satc.comms.library import (
    CommsLibrary,
    CommsTemplate,
    Placeholder,
    library,
    load_library,
)
from satc.comms.render import (
    RenderedDraft,
    placeholder_names,
    render,
    render_key,
    unfilled_marker,
)

__all__ = [
    "CommsLibrary",
    "CommsTemplate",
    "Placeholder",
    "RenderedDraft",
    "build_context",
    "library",
    "load_library",
    "placeholder_names",
    "render",
    "render_key",
    "unfilled_marker",
]
