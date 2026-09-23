"""Score a gate run: two readers' answer files against the key.

    python3 tools/score_gate.py gate/<run> reader_a.json reader_b.json

Prints the denominator for each reader and PASS only if BOTH reach the bar
(six of eight, PRD §5.44). Chance is one of eight per character.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BAR = 6


def find_key(run: Path) -> Path:
    """Beside the pack since 12 Sep 2026 (`gate/<run>.key.json`); inside it
    (`KEY.json`) for the packs written before that, which are on the branch."""
    beside = run.parent / f"{run.name}.key.json"
    if beside.exists():
        return beside
    inside = run / "KEY.json"
    if inside.exists():
        return inside
    raise SystemExit(f"no key for {run}: expected {beside} (or KEY.json inside an older pack)")


def score(run: Path, answers: Path) -> tuple[int, int, list[str]]:
    key = json.loads(find_key(run).read_text(encoding="utf-8"))["letter_to_brain_number"]
    given = json.loads(answers.read_text(encoding="utf-8"))
    right, lines = 0, []
    for letter, truth in sorted(key.items()):
        guess = given.get(letter)
        ok = guess == truth
        right += ok
        lines.append(f"  {letter}: guessed {guess}, was {truth}  {'✓' if ok else '✗'}")
    return right, len(key), lines


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    run = Path(argv[1])
    results = []
    for label, path in zip("AB", argv[2:4]):
        right, total, lines = score(run, Path(path))
        results.append((label, right, total))
        print(f"reader {label} ({path}): {right} of {total}")
        print("\n".join(lines))
    verdict = "PASS" if all(r >= BAR for _, r, _ in results) else "FAIL"
    print(", ".join(f"reader {l} {r} of {t}" for l, r, t in results) + f": {verdict} (bar {BAR} of 8 for both)")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
