import json, sys, re
from pathlib import Path
d = json.load(open(Path(sys.argv[1]) / "fico.json"))
MAP = [("Card", r"(ConsumerCreditCard|CreditCardReceivables)$"),
       ("Residential (mortgage + home equity before 2020)", r"ResidentialPrimeFinancingReceivables$"),
       ("Mortgage", r"RealEstateResidentialMortgage$"), ("Home equity", r"HomeEquityLoan$"),
       ("Other consumer (direct + indirect)", r"(ConsumerDirectLoans|ConsumerIndirectLoans|OtherConsumerLoans)$")]
def band(b):
    b = b.lower()
    return "u660" if "lessthan660" in b else "660_749" if "660to749" in b else "750" if ("750" in b) else "none" if "noscore" in b else b
rows = {}
for date, classes in sorted(d.items()):
    for name, pat in MAP:
        acc = {}
        for cls, bands in classes.items():
            last = cls.split(" / ")[-1]
            if " / " not in cls or not re.search(pat, last):
                continue
            for b, (v, how) in bands.items():
                if v is not None:
                    acc[band(b)] = acc.get(band(b), 0) + v
        if acc:
            rows.setdefault(name, []).append((date, acc))
json.dump(rows, open(Path(sys.argv[1]) / "series.json", "w"), indent=1)
for name, rs in rows.items():
    print("==", name)
    for date, a in rs:
        scored = sum(v for k, v in a.items() if k != "none")
        print("   %s scored $%6.0fm  under660 %5.1f%%  660-749 %5.1f%%  750+ %5.1f%%  noscore $%4.0fm" % (
            date, scored / 1e6, 100 * a.get("u660", 0) / scored, 100 * a.get("660_749", 0) / scored,
            100 * a.get("750", 0) / scored, a.get("none", 0) / 1e6))
