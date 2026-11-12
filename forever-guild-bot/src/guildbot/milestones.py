"""Guild achievements: the moments worth announcing. Pure logic, no Discord and no database."""
from __future__ import annotations

LEVEL_MARKS = (10, 20, 30, 40, 50, 60)
SKILL_MARKS = (75, 150, 225, 300)


def crossed(old: int | None, new: int | None, marks) -> int | None:
    """The highest mark passed going from `old` to `new` (old below it, new at or above it), or None.
    Several marks passed at once (a long time offline) announce only the highest."""
    if old is None or new is None or new <= old:
        return None
    hit = [m for m in marks if old < m <= new]
    return max(hit) if hit else None


def find(before_levels: dict, after_levels: dict, before_skills: dict, after_skills: dict):
    """Milestones between two snapshots. Only characters seen in the 'before' snapshot count, so a new member
    (or the very first sync) announces nothing. Returns (kind, slug, detail, value) rows:
    ('level', slug, '', 30) or ('skill', slug, 'Tailoring', 225)."""
    out = []
    for slug, new in sorted(after_levels.items()):
        if slug in before_levels:
            m = crossed(before_levels[slug], new, LEVEL_MARKS)
            if m:
                out.append(("level", slug, "", m))
    for (slug, prof), new in sorted(after_skills.items()):
        if slug in before_levels and (slug, prof) in before_skills:
            m = crossed(before_skills[(slug, prof)], new, SKILL_MARKS)
            if m:
                out.append(("skill", slug, prof, m))
    return out


def line(kind: str, name: str, class_name: str | None, detail: str, value: int) -> str:
    who = f"**{name}**" + (f" ({class_name})" if class_name else "")
    if kind == "legacy":                                   # detail is the challenge, value its id
        return f"{who} earned a Legacy point: {detail}."
    return f"{who} hit level {value}." if kind == "level" else f"{who} reached {value} in {detail}."
