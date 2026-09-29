"""Defects found running PocketBook on public loan data (docs/rehearsal-public-data-2026-09.md), each held here on a
tiny synthetic book: no public row is read.

1. A category limit the launcher's list doesn't offer (Choices(many_values=60): State has 51 values and a blank, one
   over the usual 50) was written into Control's pick cell, where only a listed option is read. The Run then
   refused "60 is not an option" on a row the analyst can't edit (it is the launcher's), after Set up had already
   used 60; and reading the block back (Set up again, the launcher) quietly took the usual 50 instead.
"""

from openpyxl import load_workbook

from pocketbook import book, choices as ch, control, synth
from test_book import PICK


def _limits_book(tmp_path, **limits):
    extract = synth.write_extract(tmp_path, n=2000)
    c = ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",), **limits)
    out = book.set_up(extract, choices=c)
    assert out.ok, out.lines
    return out.book


def _answer(b):
    wb = load_workbook(b)
    for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
        k = r[control.KEY_COL - 1].value
        if k in PICK:
            r[control.CHOOSE_COL - 1].value = PICK[k]
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)


def test_a_limit_off_the_launchers_list_is_read_back_as_chosen(tmp_path):
    b = _limits_book(tmp_path, few_values=3, many_values=60)
    got, _ = control.read_choices(load_workbook(b)[control.SHEET])
    assert (got.few_values, got.many_values) == (3, 60)


def test_a_limit_off_the_launchers_list_runs(tmp_path):
    b = _limits_book(tmp_path, many_values=60)
    _answer(b)
    _, problems, _ = book.read_book(b)
    assert not [p for p in problems if "not an option" in p], problems
    ran = book.run(b)
    assert ran.ok, ran.lines


def test_a_listed_limit_is_still_picked_from_the_list(tmp_path):
    b = _limits_book(tmp_path, few_values=24, many_values=100)
    ws = load_workbook(b)[control.SHEET]
    row = {k: control.row_of(ws, k) for k in ("few_values", "many_values")}
    assert ws.cell(row=row["few_values"], column=control.CHOOSE_COL).value == "24 values"
    assert ws.cell(row=row["many_values"], column=control.CHOOSE_COL).value == "100 values"
    assert ws.cell(row=row["many_values"], column=control.OWN_COL).value is None


# --------------------------------------------------------------------------
# 2. The confirmatory test's conditional likelihood took minutes per pocket at SBA scale: kgroups.pocket_terms
#    multiplied every group's polynomial in full with np.convolve, though almost every coefficient of a tilted
#    binomial is exactly 0.0 (it underflows) and only the coefficient at m is ever read. One evaluation of a
#    pocket of 217,800 loans took 191 s; the pre-registered test on the FOIA file was stopped after 10 minutes
#    inside its first fit. Now each polynomial carries only its nonzero coefficients, and a coefficient that is
#    read once is one dot product: the same sums, without the zeros.

import math
import time

import numpy as np

from pocketbook import kgroups


def _old_pocket_terms(p, b):
    """kgroups.pocket_terms as it was before 29 Sep 2026, kept here as the reference the new one must equal."""
    K = len(p.loans)
    R = p.loans.astype(int)
    m = int(round(p.m))
    lam = kgroups._tilt(p.loans, b, m)
    mul = lambda a, c: np.convolve(a, c)[: m + 1]

    def prod(ps):
        out = np.ones(1)
        for q in ps:
            out = mul(out, q)
        return out
    coef = lambda poly: float(poly[m]) if m < len(poly) else 0.0
    f, g, h = [], [], []
    for k in range(K):
        top = min(R[k], m)
        j = np.arange(top + 1, dtype=float)
        x = b[k] + lam
        log1p = math.log1p(math.exp(-abs(x))) + max(x, 0.0)
        pmf = np.exp(kgroups._log_choose(R[k], top) + j * x - R[k] * log1p)
        f.append(pmf), g.append(j * pmf), h.append(j * j * pmf)
    B = coef(prod(f))
    logD = math.log(B) + sum(float(R[k]) * (math.log1p(math.exp(-abs(b[k] + lam))) + max(b[k] + lam, 0.0))
                             for k in range(K)) - m * lam
    ll = float((p.bad * b).sum()) - logD
    others = [prod([f[l] for l in range(K) if l != k]) for k in range(K)]
    E = np.array([coef(mul(g[k], others[k])) / B for k in range(K)])
    cov = np.zeros((K, K))
    for k in range(K):
        cov[k, k] = coef(mul(h[k], others[k])) / B - E[k] ** 2
        for l in range(k + 1, K):
            rest = prod([f[q] for q in range(K) if q not in (k, l)])
            cov[k, l] = cov[l, k] = coef(mul(mul(g[k], g[l]), rest)) / B - E[k] * E[l]
    return ll, p.bad - E, -cov


def _pockets():
    yield kgroups.Pocket([4000, 4100, 3900, 4000, 3800], [800, 820, 700, 560, 460])
    yield kgroups.Pocket([12, 3000, 7, 2500], [1, 400, 7, 300])              # a group with every loan bad
    yield kgroups.Pocket([50, 60, 0, 40], [0, 10, 0, 5])                     # an empty group, one with none bad
    yield kgroups.Pocket([9000, 200], [1500, 190])


def test_the_conditional_likelihood_is_unchanged(tmp_path):
    for p in _pockets():
        for b in (np.zeros(len(p.loans)), np.linspace(-0.4, 0.5, len(p.loans))):
            new, old = kgroups.pocket_terms(p, b), _old_pocket_terms(p, b)
            assert math.isclose(new[0], old[0], rel_tol=1e-12, abs_tol=1e-9), (new[0], old[0])
            assert np.allclose(new[1], old[1], rtol=1e-10, atol=1e-8), (new[1], old[1])
            assert np.allclose(new[2], old[2], rtol=1e-9, atol=1e-7), (new[2], old[2])


def test_a_pocket_the_size_of_an_sba_stratum_takes_seconds_not_minutes():
    loans = np.array([44000, 44000, 44000, 44000, 41800])
    p = kgroups.Pocket(loans, np.round(loans * np.array([.2, .2, .18, .14, .12])))
    t = time.perf_counter()
    kgroups.pocket_terms(p, np.zeros(5))
    took = time.perf_counter() - t
    assert took < 20, f"{took:.1f} s for one evaluation (it was 191 s)"


# --------------------------------------------------------------------------
# 3. scikit-learn installed but refused by the machine. On the rehearsal machine, Windows Application Control blocked
#    scikit-learn 1.9.1's compiled files ("DLL load failed while importing _loss: An Application Control policy has
#    blocked this file."). PocketBook looks for scikit-learn without loading it, so it counted as there, and the
#    Run crashed on the import inside the forest instead of saying so; a bank machine is the likeliest place for
#    such a policy. Now the Run says it in words, and confirming a saved shortlist still works.

import os
import subprocess
import sys
from pathlib import Path

BLOCKED = "DLL load failed while importing _loss: An Application Control policy has blocked this file."


def test_scikit_learn_that_wont_load_is_said_in_words_and_a_saved_shortlist_still_confirms(tmp_path):
    fake = tmp_path / "blocked"
    (fake / "sklearn" / "ensemble").mkdir(parents=True)
    (fake / "sklearn" / "__init__.py").write_text("")
    (fake / "sklearn" / "ensemble" / "__init__.py").write_text(f"raise ImportError({BLOCKED!r})\n")
    (fake / "sklearn" / "metrics.py").write_text(f"raise ImportError({BLOCKED!r})\n")
    work = tmp_path / "work"
    work.mkdir()
    code = f"""
from pathlib import Path
import yaml
from pocketbook import book, deps, scout
import test_scout
from test_book_dates import _choose
assert scout.missing() is None              # it is there, as far as looking can tell
x, b = test_scout._book(Path({str(work)!r}), 3000, test=('UTIL', 'TENURE'))
ran = book.run(b)
print('SCOUT', ran.ok, '|'.join(ran.problems))
spec = {{'prespec': 1, 'written': '2026-09-29', 'outcome': 'BAD_FLAG',
        'inputs': [{{'column': 'UTIL', 'bins': [0.9], 'reference': 0}}], 'strata': ['FICO', 'CHANNEL'],
        'confidence': 0.95, 'holdout': {{'from': '2024-11-02', 'to': '2026-12-31'}},
        'development': {{'from': '2020-01-01', 'to': '2024-11-01'}}}}
(b.parent / 'saved.yaml').write_text(yaml.safe_dump(spec, sort_keys=False))
_choose(b, shortlist='saved.yaml', run_kind='new_variable')
print('SAVED', book.run(b).ok)
"""
    here = Path(__file__).parent
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(fake), str(here.parent / "src"), str(here)]),
               GIT_CEILING_DIRECTORIES=str(tmp_path), POCKETBOOK_MEMORY=str(tmp_path / "memory.yaml"))
    got = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=here.parent)
    assert got.returncode == 0, got.stderr[-3000:]
    out = {line.split(" ", 1)[0]: line.split(" ", 1)[1] for line in got.stdout.splitlines() if " " in line}
    ok, problems = out["SCOUT"].split(" ", 1)
    assert ok == "False"
    assert "scikit-learn is installed but won't load on this machine" in problems and BLOCKED in problems, problems
    assert out["SAVED"] == "True"


# --------------------------------------------------------------------------
# 4. The checker of the checker on Windows. tools/mutation_check.py opened each file in the platform's encoding:
#    cp1252 on Windows, where the bank's machine and this one run, UTF-8 on CI's Linux. Four planted bugs whose line
#    holds a character outside cp1252 (a multiplication sign, an arrow) were never found there, and a Windows run
#    died on the first of them; tests/test_mutation_tool.py read the same way and failed on this machine only.
#    Held on any platform by reading the checker itself: every text file it opens names its encoding.

import ast

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"


def _unnamed_encodings(path: Path) -> list[str]:
    bad = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
        if name not in ("open", "read_text", "write_text"):
            continue
        mode = next((a.value for a in node.args[1:2] if isinstance(a, ast.Constant)), None) if name == "open" else None
        mode = next((k.value.value for k in node.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)),
                    mode)
        if isinstance(mode, str) and "b" in mode:
            continue
        if not any(k.arg == "encoding" for k in node.keywords):
            bad.append(f"{path.name}:{node.lineno}")
    return sorted(bad, key=lambda x: int(x.rsplit(":", 1)[1]))


def test_the_mutation_checker_reads_and_writes_utf8_whatever_the_platform():
    here = Path(__file__).resolve().parent
    assert _unnamed_encodings(TOOLS_DIR / "mutation_check.py") == []
    assert _unnamed_encodings(here / "test_mutation_tool.py") == []


def test_the_encoding_check_can_fail(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("open('a').read()\nPath('b').read_text()\nopen('c', 'rb')\nopen('d', encoding='utf-8')\n",
                 encoding="utf-8")
    assert _unnamed_encodings(f) == ["x.py:1", "x.py:2"]
