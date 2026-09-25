"""Check the checker: put each VBA bug back and prove its test goes red.

Run from origination-cube/: python tools/mutation_check.py. Exits non-zero
if any mutation survives."""
import subprocess, shutil, sys
E="src/origination_cube/engine.py"; C="src/origination_cube/config.py"
muts = [
 ("1 blank->zero",       E, 'if p is BLANK:\n        return None, "blank"', 'if p is BLANK:\n        return 0.0, None', "test_finding_1"),
 ("2 empty->index 0",    E, 'if rate is None or base is None or base == 0:', 'if base is None or base == 0:\n        return None\n    if rate is None:\n        rate = 0.0\n    if False:', "test_finding_2"),
 ("4 text->0 on top",    E, '                if why_t or why_d:', '                if why_t and not why_d and m.mode == "sumnum":\n                    vals.append((0.0, d)); continue\n                if why_t or why_d:', "test_finding_4"),
 ("8 threshold default", C, '    absent = [k for k in BENCHMARK_KEYS if k not in node]', '    node = {"min_units": 30, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95, "power": 0.8, **node}\n    absent = [k for k in BENCHMARK_KEYS if k not in node]', "test_finding_8"),
 ("tie-out disabled",    E, '        if not _close(got, want, scale):', '        if False:', "test_the_tie_out"),
 ("unknown keys ignored",C, '        if k not in allowed:', '        if False:', "misspelled"),
 ("judgment pre-chosen", "src/origination_cube/control.py",
  'value=None if s.judgment or rec is None else rec.shown)',
  'value=(rec or s.options[0]).shown)', "waits_for_every_judgment"),
 ("outcome cut by",      E, '    tops = {m.value if m.mode == "sumnum" else m.flag for m in measures if m.is_rate}',
  '    tops = set()', "outcome"),
 ("unconfirmed columns run", C, '        if raw.get("columns_confirmed") is not True:',
  '        if False:', "confirms_it"),
 ("memory ignored", "src/origination_cube/meanings.py",
  '        if hit and hit.get("means") in cat:', '        if False:', "remembered_and_outranks"),
 ("forget forgets nothing", "src/origination_cube/memory.py",
  '        if mem["columns"].pop(n, None) is not None:', '        if mem["columns"].get(n) is None:', "forget_by_name"),
 ("key optional again",  E, '    if config.key not in have:', '    if False:', "missing_key"),
 ("reading on whole-book multiple", E, '            s.reading_topline = reading_of(s.vs_rest, s.units, bench, floor, s.p_book)',
  '            s.reading_topline = reading_of(s.vs_topline, s.units, bench, floor, s.p_book)', "big_pocket"),
]
bad = 0
for name, f, old, new, sel in muts:
    src = open(f).read(); assert old in src, name
    shutil.copy(f, f + ".bak"); open(f, "w").write(src.replace(old, new, 1))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-k", sel], capture_output=True, text=True)
    shutil.move(f + ".bak", f)
    caught = r.returncode != 0
    bad += not caught
    print(("CAUGHT " if caught else "MISSED ") + name, "|", r.stdout.strip().splitlines()[-1])
sys.exit(bad)
