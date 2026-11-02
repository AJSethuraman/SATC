import json
import shutil
from pathlib import Path

import pytest

from workpaper_studio.pack import load
from workpaper_studio.service import Studio

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "packs"
NAMES = ["credit-file-review", "control-test", "bank-reconciliation"]


@pytest.fixture
def packs():
    return {n: load(PACKS / f"{n}.json") for n in NAMES}


def confirmed(p):
    return {k: {"limit": v["policy"], "confirmed": v["confirmed"] == "Yes", "by": v["by"], "date": v["date"]} for k, v in p.data["confirmations"].items()}


@pytest.fixture
def studio(tmp_path):
    """A fresh installation with the three demo packs published and their recommended limits confirmed."""
    packs_dir = tmp_path / "packs"
    shutil.copytree(PACKS, packs_dir)
    st = Studio(tmp_path / "studio.db", packs_dir)
    good, bad = st.pack_files()
    assert not bad
    for p in good:
        st.approve_pack("K. Owens", st.propose("M. Okafor", p.file))
        for _, b in p.calcs():
            st.confirm_limit("M. Okafor", p.name, b["id"], b["limit"])
    return st


def fill(st, cid, user, data, pack):
    """Enter a whole example through the same route a person uses: one entry at a time."""
    from workpaper_studio.engine import fmt_value
    for path, v in paths(pack, data):
        st.set(user, cid, path, "" if v is None else str(v))


def paths(pack, data):
    out = []
    for _, b in pack.blocks():
        if b["kind"] == "field" and b["id"] in data:
            out.append((f"f/{b['id']}", data[b["id"]]))
        elif b["kind"] == "grid" and b["id"] in data:
            d = data[b["id"]]
            for j, nm in enumerate(d.get("_cols") or []):
                out.append((f"g/{b['id']}/_cols/c{j}", nm))
            if "rows" in d:
                for i, r in enumerate(d["rows"]):
                    for k, v in r.items():
                        out.append((f"g/{b['id']}/{i}/{k}", v))
            for rk, r in d.items():
                if rk in ("rows", "_cols") or not isinstance(r, dict):
                    continue
                for k, v in r.items():
                    out.append((f"g/{b['id']}/{rk}/{k}", v))
    return out
