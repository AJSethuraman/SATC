"""Curated finance-domain word lists for rule-based disclosure-language metrics.

These are small, hand-curated subsets *inspired by* the categories of the
Loughran-McDonald financial sentiment dictionary (negative, uncertainty,
litigious, constraining). They are NOT the licensed full lists — coverage is
deliberately limited, which is one reason the disclosure signal reports
medium/low confidence. Swapping in the full LM dictionary later only requires
replacing these sets.
"""

NEGATIVE = {
    "adverse", "adversely", "against", "breach", "concern", "concerns", "decline",
    "declined", "declines", "default", "deficiencies", "deficiency", "deteriorate",
    "deteriorated", "deterioration", "difficult", "difficulties", "disruption",
    "disruptions", "failure", "failures", "fine", "fines", "harm", "harmed",
    "impair", "impaired", "impairment", "impairments", "inability", "insolvency",
    "litigation", "loss", "losses", "penalties", "penalty", "restructuring",
    "shortfall", "terminate", "terminated", "termination", "weak", "weakened",
    "weakness", "weaknesses", "writedown", "writeoff", "write-down", "write-off",
}

UNCERTAINTY = {
    "anticipate", "anticipates", "approximate", "approximately", "assume",
    "assumption", "assumptions", "believe", "believes", "contingencies",
    "contingency", "could", "depend", "depends", "estimate", "estimated",
    "estimates", "exposure", "exposures", "fluctuate", "fluctuations",
    "indefinite", "may", "might", "possible", "possibly", "predict",
    "unpredictable", "risk", "risks", "seldom", "sometimes", "sudden",
    "uncertain", "uncertainties", "uncertainty", "unknown", "variability",
    "volatile", "volatility",
}

LITIGIOUS = {
    "allegation", "allegations", "alleged", "attorney", "attorneys", "claim",
    "claimant", "claims", "complaint", "complaints", "court", "courts",
    "defendant", "defendants", "deposition", "indemnification", "indemnify",
    "judgment", "judgments", "jurisdiction", "jurisdictions", "lawsuit",
    "lawsuits", "legal", "legislation", "litigation", "plaintiff", "plaintiffs",
    "proceeding", "proceedings", "regulatory", "settlement", "settlements",
    "subpoena", "testimony", "tort", "verdict",
}

CONSTRAINING = {
    "commit", "commitment", "commitments", "compelled", "comply", "compliance",
    "constrain", "constrained", "constraint", "constraints", "covenant",
    "covenants", "encumbrance", "encumbrances", "forbid", "impose", "imposed",
    "imposes", "indebted", "indebtedness", "limit", "limitation", "limitations",
    "limits", "mandatory", "obligate", "obligated", "obligation", "obligations",
    "pledge", "pledged", "prevent", "prevents", "prohibit", "prohibited",
    "prohibits", "require", "required", "requirement", "requirements",
    "restrict", "restricted", "restriction", "restrictions", "restrictive",
}

CATEGORIES = {
    "negative": NEGATIVE,
    "uncertainty": UNCERTAINTY,
    "litigious": LITIGIOUS,
    "constraining": CONSTRAINING,
}
