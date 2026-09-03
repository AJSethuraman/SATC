"""The end-of-cycle control: what we said, against what we filed.

THE FIRM ASKED FOR THIS IN THESE WORDS:

    "we are not copying out of drake - drake is only system of record for info.
     but our interview and such is system of record until proven wrong. we
     should update the data to match what we file if required. this should be a
     control we build at the end of the cycle. i want everything inhouse as
     much as possible for this kind of stuff."

Every other check in this repo is a TEST: it asserts a property on a fixture
and runs in CI. This is a CONTROL. It runs on real work, after the work is
done, and compares two things nobody was comparing: the answers the interview
recorded in January, and what was actually on the return in April.

WHY THAT GAP IS WHERE THINGS HIDE. Between the two sits every fact that moved
after the engagement letter went out -- a state nobody knew about until the
K-1 arrived, a marriage, a rental sold, an entity that changed shape. The
letter, the estimate and the invoice were all written from the January answers.
If the return diverged and nothing said so, three documents in the client's
file are quietly wrong and next year's interview starts from the wrong place.

A DIVERGENCE IS NOT AN ERROR. It is one of three things and only a person can
tell which: the return changed and the record should follow; the interview was
wrong and the record should follow; or somebody filed the wrong thing. The
control's job is that none of the three passes unnoticed. It proposes;
`reconcile --apply` moves the record, and says what it moved.

NO FIGURES. Nothing here asks what the tax was or what the refund was. That
would make this a second set of books beside Drake, which is the one thing the
firm said not to build.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

import engagements
import tins

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry" / "closeout.yaml"


class CloseoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class Divergence:
    """One thing the return says that the interview did not."""

    question: str          # the close-out question id
    against: str           # the interview answer it disagrees with
    asked: object          # what the interview recorded
    filed: object          # what was actually filed
    why: str               # why this one is worth asking, from the registry

    def line(self) -> str:
        return (f"  {self.question:22} interview said {_show(self.asked)}, "
                f"filed as {_show(self.filed)}")


def _show(value) -> str:
    if value is None:
        return "(nothing)"
    if isinstance(value, list):
        return f"{len(value)} ({', '.join(str(v) for v in value)})" if value else "none"
    return repr(value)


def load(path: Path | str = REGISTRY) -> list[dict]:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    questions = spec.get("questions") or []
    for q in questions:
        if not q.get("why"):
            raise CloseoutError(
                f"close-out question {q.get('id')!r} has no `why`. A question "
                f"nobody can justify is one nobody will answer honestly.")
    return questions


def questions_for(return_type: str, path: Path | str = REGISTRY) -> list[dict]:
    """The close-out questions this engagement is actually asked.

    A 1040 has no Schedules K-1 to issue and a partnership has no filing
    status. Asking anyway is the filler problem in a different costume: a
    preparer who is asked four questions that cannot apply learns to answer the
    whole set without reading it.
    """
    return [q for q in load(path)
            if not q.get("applies_to") or return_type in q["applies_to"]]


def _norm(value):
    """Compare like with like.

    A count arrives from the interview as an int and from the close-out as a
    string typed at a terminal; "2" and 2 are the same answer and must not be
    reported as a divergence. Everything else compares as text, case-folded,
    because "Yes" and "yes" are not a finding either.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return text.casefold()


def compare(interview_answers: dict, filed: dict,
            return_type: str, path: Path | str = REGISTRY) -> list[Divergence]:
    """Every place the filed return and the recorded interview disagree.

    An unanswered close-out question is NOT a divergence -- it is a question
    nobody answered, which `missing` reports separately. Silently treating it
    as agreement would let a half-finished close-out read as a clean one, and
    an absent check reading like a passing one is the failure this whole
    controls layer exists to stop.
    """
    out: list[Divergence] = []
    for q in questions_for(return_type, path):
        against = q.get("against")
        if not against:
            continue                       # recorded, not compared
        if q["id"] not in filed:
            continue                       # unanswered; see `missing`
        asked = interview_answers.get(against)
        # A count question may fall back to the LIST the count came from, when
        # the interview happened to record one and not the other. The fallback
        # is DECLARED in the registry (`or_list:`) rather than guessed from the
        # value's type: a rule that fires on whatever shape the data happens to
        # be in is a coincidence, not a rule.
        if asked in (None, "") and q.get("or_list"):
            backing = interview_answers.get(q["or_list"])
            if isinstance(backing, list):
                asked = len(backing)
        if q.get("kind") == "number" and isinstance(asked, list):
            asked = len(asked)
        if _norm(asked) != _norm(filed[q["id"]]):
            out.append(Divergence(q["id"], against, asked, filed[q["id"]],
                                  " ".join((q.get("why") or "").split())))
    return out


def missing(filed: dict, return_type: str,
            path: Path | str = REGISTRY) -> list[str]:
    """Close-out questions this engagement was asked and did not answer."""
    return [q["id"] for q in questions_for(return_type, path)
            if q["id"] not in filed]


# ── the store ─────────────────────────────────────────────────────────────

def save(ref: str, filed: dict, store: Path = engagements.STORE) -> Path:
    """What was filed, beside the record and the interview.

    THE MOMENT OF MAXIMUM EXPOSURE. This is filled in with the filed return
    open on the other screen, and `closeout_note` invites free text -- so it is
    the one place in the cycle where a preparer is reading a document that
    carries every SSN on the return while typing into one that must carry none.
    The header of `registry/closeout.yaml` says "Nothing is read out of Drake";
    that was a comment, and this is the gate.
    """
    tins.refuse(filed, "the close-out record")
    path = engagements._dir(store, ref) / "closeout.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(filed, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def load_filed(ref: str, store: Path = engagements.STORE) -> dict | None:
    path = engagements._dir(store, ref) / "closeout.json"
    if not path.exists():
        return None
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return got if isinstance(got, dict) else None


def apply_to_answers(ref: str, divergences: list[Divergence],
                     store: Path = engagements.STORE) -> list[dict]:
    """Move the interview's answers to match what was filed, and say so.

    "our interview and such is system of record UNTIL PROVEN WRONG." This is
    the proving. Every move is appended to the engagement's own reconciliation
    log -- append-only, never pruned, for the same reason the override log is:
    a record you can edit is not evidence, and next year's interview is seeded
    from these answers.
    """
    if not divergences:
        return []
    answers = json.loads(
        (engagements._dir(store, ref) / "interview.json").read_text(
            encoding="utf-8"))

    moved = []
    for d in divergences:
        moved.append({"answer": d.against, "was": answers.get(d.against),
                      "now": d.filed, "because": d.question})
        answers[d.against] = d.filed

    engagements.save_answers(answers, ref, store)

    log = engagements._dir(store, ref) / "reconciled.json"
    history = []
    if log.exists():
        try:
            existing = json.loads(log.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                history = existing
        except json.JSONDecodeError:
            pass
    history.append({
        "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "moved": moved,
    })
    log.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return moved


# ── the sweep ─────────────────────────────────────────────────────────────

@dataclass
class Reviewed:
    ref: str
    client: str
    return_type: str
    closed: bool
    divergences: list
    unanswered: list


def sweep(store: Path = engagements.STORE) -> list[Reviewed]:
    """Every engagement in the store, closed or not.

    An engagement with no close-out is reported as NOT CLOSED rather than
    skipped. A control that only examines the work somebody remembered to
    close is a control over the diligent, which is not where the problem is.
    """
    out: list[Reviewed] = []
    for entry in engagements.listing(store):
        ref = entry.get("ref") or entry.get("EngagementRef") or ""
        if not ref:
            continue
        answers_path = engagements._dir(store, ref) / "interview.json"
        if not answers_path.exists():
            continue
        answers = json.loads(answers_path.read_text(encoding="utf-8"))
        record = engagements.load(ref, store)
        return_type = record.get("_return_type", "individual")
        filed = load_filed(ref, store)
        out.append(Reviewed(
            ref=ref,
            client=record.get("ClientFullName", ""),
            return_type=return_type,
            closed=filed is not None,
            divergences=compare(answers, filed or {}, return_type),
            unanswered=missing(filed or {}, return_type) if filed else [],
        ))
    return out
