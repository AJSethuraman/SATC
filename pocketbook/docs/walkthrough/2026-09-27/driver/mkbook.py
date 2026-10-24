"""Write the synthetic book the analyst works on, from the frozen build."""
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(W / "wc/pocketbook/src"))
from pocketbook import synth  # noqa: E402

p = synth.write_extract(W / "book/tmp", n=8000)
dest = W / "book" / "Consumer book Q3.csv"
Path(p).rename(dest)
print(dest)
