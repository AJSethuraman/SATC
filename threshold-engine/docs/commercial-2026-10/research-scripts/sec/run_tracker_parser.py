import sys, os, glob, json, importlib.util
from collections import defaultdict
TR="/home/user/SATC/edgar-crit-class-tracker"
spec=importlib.util.spec_from_file_location("runner", TR+"/runner.py"); R=importlib.util.module_from_spec(spec); sys.modules["runner"]=R; spec.loader.exec_module(R)
sys.path.insert(0,TR); import member_seed as MS; sys.path.pop(0)
D=sys.argv[1]; subs=json.load(open(os.path.join(D,"subs.json")))
mm=defaultdict(dict)
for cik,fam,q,g in MS.member_map_rows(): mm[str(cik)][q]=g
cm={q:k for c,q,k in MS.CLASS_MAP_SEEDS}
for t,s in sorted(subs.items()):
    inst=glob.glob(os.path.join(D,t,"*_htm.xml"))[0]
    facts=R.EdgarProvider.parse_instance(open(inst,"rb").read(), str(s["cik"]), "2026-06-30", s["recent"][0][3], "", "10-Q")
    seeded=str(s["cik"]) in MS.SEED_FAMILY
    grades=sorted({f.grade_qname for f in facts})
    classes=sorted({f.class_qname for f in facts})
    unm_g=[g for g in grades if g not in mm.get(str(s["cik"]),{})] if seeded else "n/a (not in seed)"
    unm_c=[c for c in classes if c not in cm]
    print("%-6s facts=%-3d seeded=%s fam=%s\n   grades=%s\n   unmapped grades=%s\n   classes(seed-mapped)=%s\n   unmapped classes=%s"%(t,len(facts),seeded,MS.SEED_FAMILY.get(str(s["cik"])),grades,unm_g,{c:cm[c] for c in classes if c in cm},unm_c))
