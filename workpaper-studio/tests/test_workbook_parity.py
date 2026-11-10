"""The application's engine and the exported workbook's formulas agree, case for case.

The workbook carries live formulas so that someone who stays in Excel still has a working tool. That makes it a second
implementation of the same rules, which is only acceptable if it is proven to agree (TENETS S3). Every case here is
written to a workbook, recalculated by LibreOffice, and every status, result, verdict and part is read back by defined
name and compared with engine.evaluate(). The cases are each pack's example, its blank tool, and randomly part-filled
copies of the example, so an empty cell, a missing row and a waiting condition are all exercised.
"""
import copy
import json
import os
import random
import shutil
import subprocess

import pytest

from conftest import NAMES, confirmed
from workpaper_studio import engine
from workpaper_studio.workbook import build_workbook

SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")
if not SOFFICE:
    if os.environ.get("CI"):
        raise RuntimeError("LibreOffice is required in CI: a skipped parity check is not a passed one.")
    pytest.skip("LibreOffice is not installed here; the parity check needs it to recalculate", allow_module_level=True)

openpyxl = pytest.importorskip("openpyxl")


def thin_out(data, rng):
    d = copy.deepcopy(data)
    for k in list(d):
        v = d[k]
        if isinstance(v, dict):
            if "rows" in v:
                for r in v["rows"]:
                    for c in list(r):
                        if rng.random() < .15:
                            del r[c]
            for rk, r in list(v.items()):
                if isinstance(r, dict):
                    for c in list(r):
                        if rng.random() < .2:
                            del r[c]
        elif rng.random() < .25:
            del d[k]
    return d


def cases(packs):
    out = []
    for n in NAMES:
        p = packs[n]
        ex = p.data["example"]
        conf = confirmed(p)
        out.append((n, "example", ex, conf))
        out.append((n, "blank", {}, {}))
        out.append((n, "example, limit not confirmed", ex, {k: dict(v, confirmed=False) for k, v in conf.items()}))
        for g, v in ex.items():          # a table with exactly its minimum number of rows: the boundary of "at least one"
            if isinstance(v, dict) and len(v.get("rows") or []) > 1:
                one = copy.deepcopy(ex); one[g]["rows"] = one[g]["rows"][:1]
                out.append((n, f"one row in {g}", one, conf))
                break
        rng = random.Random(n)
        for i in range(6):
            out.append((n, f"part-filled {i}", thin_out(ex, rng), conf))
    return out


def read(wb_f, wb_v, name):
    sheet, coord = next(iter(wb_f.defined_names[name].destinations))
    return wb_v[sheet][coord.replace("$", "")].value


def test_engine_and_workbook_agree(packs, tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    src.mkdir(), out.mkdir()
    todo = []
    for i, (n, label, data, pol) in enumerate(cases(packs)):
        p = packs[n]
        conf = {k: {"policy": v["limit"], "confirmed": "Yes" if v["confirmed"] else "No", "by": v.get("by"), "date": v.get("date")} for k, v in pol.items()}
        path = src / f"c{i:02d}.xlsx"
        build_workbook(p.data, data, conf, path, "parity test")
        todo.append((path, n, label, data, pol))
    subprocess.run([SOFFICE, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out), *[str(t[0]) for t in todo]],
                   check=True, capture_output=True, timeout=600)
    diffs, compared = [], 0
    for path, n, label, data, pol in todo:
        p = packs[n]
        ev = engine.evaluate(p, data, {}, pol)
        wf, wv = openpyxl.load_workbook(path), openpyxl.load_workbook(out / path.name, data_only=True)

        def same(what, got, want):
            nonlocal compared
            compared += 1
            ok = (abs(got - want) < 1e-6) if isinstance(want, float) and isinstance(got, (int, float)) else got == want
            if not ok:
                diffs.append(f"{n} / {label} / {what}: workbook {got!r}, engine {want!r}")
        for s in ev["sections"]:
            same(f"status {s['id']}", read(wf, wv, f"Status_{s['id']}"), s["status"])
        for cid, k in ev["calcs"].items():
            want = k["value"] if k["status"] == "calculated" else k["display"]
            same(f"result {cid}", read(wf, wv, f"Result_{cid}"), want)
            same(f"verdict {cid}", read(wf, wv, f"Verdict_{cid}"), k["verdict"])
            for lab, v in k["parts"].items():
                nm = f"Calc_{cid}_" + "".join(ch if ch.isalnum() else "_" for ch in lab)
                same(f"{cid} {lab}", read(wf, wv, nm), "Not calculated" if v is None else (float(v) if not isinstance(v, int) or lab != "Inputs still missing" else v))
        for gid, t in ev["tables"].items():
            for ck, v in t["totals"].items():
                same(f"total {gid}.{ck}", read(wf, wv, f"Total_{gid}_{ck}"), "Not calculated" if v is None else float(v))
        same("ready", read(wf, wv, "Ready"), "Yes" if ev["ready"] else "No")
        same("missing", read(wf, wv, "Missing"), ev["missing"])
    assert compared > 300
    assert not diffs, "\n".join(diffs[:40])
