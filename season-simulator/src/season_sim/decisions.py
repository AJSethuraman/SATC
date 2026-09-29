"""Clear bug or the firm's decision -- kept apart from the checkers so the
launcher can build a report without importing satc_system."""

# Which findings are clear bugs and which need the firm. A clear bug is the code
# contradicting a rule written in this repository, with a local fix. A firm
# decision is a gap whose fix is a choice: a door to build (D8 deferred one), a
# policy to pick, or a reading of a rule that the firm has to confirm.
DECISION = {
    "B8": "firm_decision", "B13": "firm_decision", "C9": "firm_decision",
    "E5": "firm_decision", "G1": "firm_decision", "G2": "firm_decision",
    "G4": "firm_decision", "G5": "firm_decision", "G6": "firm_decision",
    "L3": "firm_decision", "G8": "firm_decision", "E7": "known",
}


def decision_for(code: str) -> str:
    return DECISION.get(code, "clear_bug")


