"""Check the checker: put each VBA bug back and prove its test goes red.

Run from origination-cube/: python tools/mutation_check.py. Exits non-zero
if any mutation survives."""
import subprocess, shutil, sys
E="src/origination_cube/engine.py"; C="src/origination_cube/config.py"; B="src/origination_cube/book.py"
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
 ("RANR read as a loss", E, '                s.excess = (s.num - top * s.den) if hi == "worse" else (top * s.den - s.num)',
  '                s.excess = s.num - top * s.den', "ranr_is_revenue"),
 ("loss floor ignored",  E, '    if events is not None and higher_is == "worse" and events < min_events:',
  '    if False:', "too_few_losses"),
 ("no allowance for many tests", E, '    if how == "none" or m == 0:', '    if True:', "allowance"),
 ("judged-against ignored", E, '                if bench.compare_to == "peers":', '                if False:', "judged_against"),
 ("materiality ignored", E, '                s.material = s.excess > 0 and s.excess >= mat', '                s.material = s.excess > 0',
  "materiality_as"),
 ("loan age ignored",    E, '    if not config.min_age_months:', '    if True:', "loan_age_keeps"),
 ("key optional again",  E, '    if config.key not in have:', '    if False:', "missing_key"),
 ("reading on whole-book multiple", E, '            s.reading_topline = reading_of(s.vs_rest, s.units, bench, floor, s.p_book, **kw)',
  '            s.reading_topline = reading_of(s.vs_topline, s.units, bench, floor, s.p_book, **kw)', "big_pocket"),
 # 25 Sep 2026: the third layer, losses against revenue, and the second walk's defects
 ("split not pooled",    E, '        if strata:', '        if False:', "planted_revolving"),
 ("dollar outcome pooled as loan odds", E, '            if m.mode == "flagwt" and m.per == EACH_LOAN:',
  '            if m.mode == "flagwt":', "planted_revolving"),
 ("halves at the book's median", E, '        med = {k: statistics.median(v) for k, v in groups.items()}',
  '        med = {k: statistics.median([x for g in groups.values() for x in g]) for k in groups}', "own_median"),
 ("copied book runs old extract", B, '    if extract is not None:', '    if False:', "copied_workbook"),
 ("forget re-learned",   B, '    if dropped:\n        # a Forget', '    if False:\n        # a Forget', "learned_tab_prunes"),
 ("yes kept over new columns", B, 'and not new_cols else None', ' else None', "new_column_takes"),
 ("set up deletes results", B, '            if t in INPUT_TABS or t in HELPERS:', '            if True:', "keeps_the_last_results"),
 ("open workbook not checked", B, '    if not _writable(book):', '    if False:', "open_in_excel"),
 ("edges read as one number", B, 'abs(e) >= 100000', 'abs(e) >= 1e30', "one_number"),
 ("edge range unchecked", B, '        if bad:', '        if False:', "outside_the_columns"),
 ("revenue box flipped", B, '(0 if rs.vs_topline < 1 else 1)', '(0 if rs.vs_topline > 1 else 1)', "losses_vs_revenue"),
 ("RANR gap reads or more", B, """else '0.00"x or less"')""", """else '0.00"x or more"')""", "ranr_is_marked"),
 ("start here left stale", B, 'else f"{stamp}: {lines[0]}")', 'else stamp)', "start_here"),
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
