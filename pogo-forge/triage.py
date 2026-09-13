"""
Batch triage.

Feed it a screen recording of you swiping through the Appraise screen, or a
pile of screenshots, and get one verdict per Pokemon.

The point is to remove the per-Pokemon decision, not to move it somewhere else.
Anything the data can't settle is marked CHECK rather than guessed at.

Species is optional. Without it the verdict comes from IV shape alone, which is
enough to clear the obvious keeps and the obvious junk. Supplying a species
upgrades that entry to an exact PvP rank.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

import appraisal
import costs
import pvp

# Frames per second to sample from a recording. Sampled finely enough that a
# brief pause on a Pokemon still produces several frames — a settled screen is
# recognised by several near-identical frames in a row, so under-sampling
# silently merges two Pokemon into one.
SAMPLE_FPS = 8
# Mean per-pixel difference above which two frames are a different Pokemon.
# Swipe animations blow far past this; a settled screen sits well under it.
FRAME_CHANGE = 6.0


@dataclass
class Entry:
    index: int
    ivs: list[int]
    iv_percent: float
    verdict: str
    reasons: list[str]
    species: str | None = None
    pvp_rank: dict | None = None
    warning: str | None = None


def frames_from_video(path: Path) -> list[Image.Image]:
    """Sample a recording, then keep one frame per settled screen."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "f_%05d.png"
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path),
             "-vf", f"fps={SAMPLE_FPS}", str(out)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise ValueError(f"could not read that video: {proc.stderr.strip()[:200]}")

        files = sorted(Path(tmp).glob("f_*.png"))
        if not files:
            raise ValueError("no frames could be extracted from that video")

        loaded = [Image.open(f).convert("RGB").copy() for f in files]

    # Group consecutive near-identical frames; each group is one Pokemon.
    arrays = [np.asarray(im, dtype=np.int16) for im in loaded]
    groups: list[list[int]] = [[0]]
    for i in range(1, len(arrays)):
        if arrays[i].shape != arrays[i - 1].shape:
            groups.append([i])
            continue
        diff = float(np.abs(arrays[i] - arrays[i - 1]).mean())
        if diff > FRAME_CHANGE:
            groups.append([i])
        else:
            groups[-1].append(i)

    # A group of one is a frame caught mid-swipe; a settled screen persists.
    return [loaded[g[len(g) // 2]] for g in groups if len(g) >= 2]


def judge(ivs: tuple[int, int, int], species: str | None,
          cap: int = 1500) -> tuple[str, list[str], dict | None]:
    """Decide what to do with one Pokemon.

    Two separate things make a Pokemon worth keeping and they pull in opposite
    directions: raids want maximum attack, PvP wants minimum attack with high
    bulk. A spread that serves neither is what you transfer.
    """
    a, d, s = ivs
    total = a + d + s
    reasons: list[str] = []
    rank_info: dict | None = None

    keep = False

    if total == 45:
        return "KEEP", ["Hundo."], None

    # PvP shape: low attack, high bulk. Only meaningful under a cap.
    pvp_shape = a <= 3 and d >= 12 and s >= 12
    if species:
        try:
            rank_info = pvp.rank(species, ivs, cap)
            if rank_info["percent"] >= 98.0:
                keep = True
                reasons.append(
                    f"PvP rank {rank_info['rank']} of {rank_info['of']} "
                    f"({rank_info['percent']}% of the best possible)."
                )
            elif pvp_shape:
                reasons.append(
                    f"PvP shape but only rank {rank_info['rank']} "
                    f"({rank_info['percent']}%)."
                )
        except costs.Unknown:
            rank_info = None
    elif pvp_shape:
        keep = True
        reasons.append("Low attack with high bulk — the PvP shape. Worth a rank check.")

    # Raid shape: attack at or near maximum, high total.
    if a >= 14 and total >= 37:
        keep = True
        reasons.append(f"Attack {a} with {total}/45 total — a raid attacker.")

    if keep:
        return "KEEP", reasons, rank_info

    if total <= 22:
        return "TRANSFER", [f"{total}/45 total. Nothing to build here."], rank_info

    if not species and total >= 37:
        return "CHECK", [
            f"{total}/45 total but no standout shape. Add the species for a "
            "PvP rank before deciding."
        ], rank_info

    return "TRANSFER", [
        f"{total}/45 total, attack {a}. Neither a raid nor a PvP build."
    ], rank_info


def triage(images: list[Image.Image], species: list[str] | None = None,
           cap: int = 1500) -> dict:
    """Read every image and return one verdict each."""
    species = species or []
    entries: list[Entry] = []
    failures: list[dict] = []

    for i, im in enumerate(images):
        sp = species[i].strip() if i < len(species) and species[i].strip() else None
        try:
            bars = appraisal.read_bars(im)
        except appraisal.ReadFailed as e:
            failures.append({"index": i + 1, "reason": str(e)})
            continue

        ivs = tuple(b.iv for b in bars)
        verdict, reasons, rank_info = judge(ivs, sp, cap)
        shaky = [n for n, b in zip(("attack", "defense", "hp"), bars)
                 if b.snap_distance > 0.25]
        entries.append(Entry(
            index=i + 1,
            ivs=list(ivs),
            iv_percent=costs.iv_percent(ivs),
            verdict=verdict,
            reasons=reasons,
            species=sp,
            pvp_rank=rank_info,
            warning=("Bars didn't land cleanly: " + ", ".join(shaky)) if shaky else None,
        ))

    counts = {v: sum(1 for e in entries if e.verdict == v)
              for v in ("KEEP", "TRANSFER", "CHECK")}
    return {
        "read": len(entries),
        "counts": counts,
        "entries": [e.__dict__ for e in entries],
        "failures": failures,
        "summary": _summary(counts, len(failures)),
    }


def _summary(counts: dict, failed: int) -> str:
    bits = [f"{counts['TRANSFER']} to transfer", f"{counts['KEEP']} to keep"]
    if counts["CHECK"]:
        bits.append(f"{counts['CHECK']} needing a species before deciding")
    if failed:
        bits.append(f"{failed} unreadable")
    return ", ".join(bits) + "."
