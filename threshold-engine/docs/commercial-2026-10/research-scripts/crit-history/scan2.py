import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from sec import get; import analyze2
D = sys.argv[1]; DL = sys.argv[2]; sel = sys.argv[3]; rev = len(sys.argv) > 4
plan = json.load(open(os.path.join(D, "plan.json")))
os.makedirs(os.path.join(D, "sum2"), exist_ok=True); os.makedirs(DL, exist_ok=True)
want = []
for t, cik, per, forms, ch in plan:
    if not ch: continue
    if eval(sel, {"t": t, "per": per}): want.append((t, cik, per, ch))
if rev: want = want[::-1]
print("n", len(want), flush=True)
def one(w):
    t, cik, per, (acc, form, name) = w
    out = os.path.join(D, "sum2", acc + ".json")
    if os.path.exists(out): return
    url = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s" % (cik, acc.replace("-", ""), name)
    tmp = os.path.join(DL, acc + ".xml")
    try:
        open(tmp, "wb").write(get(url))
        r = analyze2.run(tmp); r.update(url=url, bank=t, period=per, form=form, acc=acc)
        json.dump(r, open(out + ".part", "w")); os.rename(out + ".part", out)
        print("ok", t, per, len(r["facts"]), flush=True)
    except Exception as e:
        print("ERR", t, per, url, repr(e), flush=True)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
with ThreadPoolExecutor(3) as ex: list(ex.map(one, want))
print("done", flush=True)
