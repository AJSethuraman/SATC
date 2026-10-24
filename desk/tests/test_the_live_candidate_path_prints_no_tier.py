"""A candidate built by `candidates.consider` does not print a tier either.

THE FIX THAT PASSED ITS TESTS AND MISSED PRODUCTION, found by a review of the
commit that made it. `Served.classified` was added after the first live round
trip rendered `primary · not binding` above a note saying nobody had classified
the document — the desk that served it: *"Both cannot be informative ... a tired
reader keeps the word 'primary' and drops the paragraph."*

The flag was then set in `engine._serve`, on `source.id == "candidate"`. But
`candidates.consider` constructs its own `engine.Served` and never passes
through `_serve`, and it is the ONLY path that produces a candidate. So the
badge was fixed everywhere except where candidates actually come from.

The earlier test exercised the RENDERER with `classified=False` passed by hand.
Nothing exercised the CALLER. This test goes at the caller.
"""
from __future__ import annotations

import engine


def test_the_renderer_still_hides_a_tier_nobody_established():
    out = str(engine.Served(position="p", citation="c", tier="primary",
                            checked="2026-09-08", binding=False,
                            classified=False))
    assert "tier not established" in out
    assert "primary" not in out


def test_a_candidate_constructed_by_consider_is_marked_unclassified():
    """READ OFF THE CONSTRUCTION SITE, because the bug was that one call site
    disagreed with the other. `consider` needs a live fetch to run end to end,
    so this asserts the thing that was actually wrong: the keyword is passed."""
    import ast
    import inspect

    import candidates

    src = inspect.getsource(candidates)
    tree = ast.parse(src)
    served = [n for n in ast.walk(tree)
              if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute)
              and n.func.attr == "Served"]
    assert served, "candidates.py no longer constructs engine.Served — retarget this test"
    for call in served:
        names = {k.arg for k in call.keywords}
        assert "classified" in names, (
            "an engine.Served built in candidates.py does not set `classified`, "
            "so it inherits True and prints the HOST's tier as the DOCUMENT's — "
            "the defect a review caught after the first fix missed this caller")
        flag = [k.value for k in call.keywords if k.arg == "classified"][0]
        assert isinstance(flag, ast.Constant) and flag.value is False, (
            "a candidate is by definition a document nobody has read, so this "
            "is False unconditionally rather than computed")
