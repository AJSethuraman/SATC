"""A longer independent shuffle test for one band: tieout.py's own shuffle_test, nothing from PocketBook.

    python tieout_band.py LOANS_CSV BAND SHUFFLES SEED OUT_JSON
    python tieout_band.py loans.csv "653 - 685" 100000 777 deep.json

Used in TIEOUT.html section 7.2 to settle the two pockets whose 10,000-shuffle p-values sat furthest apart.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tieout  # noqa: E402

src, band, n, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
_, loans, _ = tieout.load(src)
segs = {x["seg"] for x in loans if x["band"] == band}
got = tieout.shuffle_test(loans, {(band, s) for s in segs}, n, seed)
Path(out).write_text(json.dumps({f"{k[0]}|{k[1]}": v for k, v in got.items()}))
print({f"{k[0]}|{k[1]}": (v["hits"], round(v["p"], 5)) for k, v in got.items()})
