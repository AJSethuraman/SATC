"""Make the evidence small enough to keep, without making it worse to read.

The 132 exhibits came to 664 MB, and the first instinct was to leave them off
the machine's repository. The firm's answer was that there is space, and they
are right about the disk -- but a git repository is not a disk. Every clone
pays for a committed file forever, and this is a quarterly job, so the cost
compounds rather than lands once.

So: measure whether the pictures can be smaller, rather than argue about where
to put them.

A Call Report page is black text and hairline rules on white. It is the worst
possible case for a colour PNG and the best possible case for a palette. Over a
random 60 strips:

    as is (2.6x colour)   11.6 KB mean   100%
    greyscale              6.2 KB mean    54%
    greyscale, 16 levels   4.2 KB mean    36%
    1-bit                  1.9 KB mean    17%

All four were rendered side by side and looked at. Greyscale and 16-level
greyscale are indistinguishable from the original at reading size. 1-bit is
legible -- the digits and the MDRM code are perfectly clear -- but the table
rules go ragged, and evidence that looks cheap gets trusted less than evidence
that looks careful, whether or not that is rational.

So 16 levels of grey. Nothing is cropped, nothing is scaled down, and no
information a reader uses is removed: the same pixels, in fewer shades.
"""
import pathlib
import sys
import time

from PIL import Image

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
SRC = SB / "deepstrips"
DST = SB / "deepstrips-grey"
DST.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

files = sorted(SRC.glob("*.png"))
started = time.time()
before = after = 0
done = skipped = 0
for i, p in enumerate(files, 1):
    out = DST / p.name
    before += p.stat().st_size
    if out.exists():
        after += out.stat().st_size
        skipped += 1
        continue
    im = Image.open(p)
    im.convert("L").quantize(colors=16).save(out, "PNG", optimize=True)
    after += out.stat().st_size
    done += 1
    if i % 5000 == 0:
        print("  %6d of %d, %.0fs" % (i, len(files), time.time() - started),
              flush=True)

print("\nstrips        : %d (%d converted, %d already done)"
      % (len(files), done, skipped))
print("before        : %6.0f MB" % (before / 1e6))
print("after         : %6.0f MB   (%.0f%%)" % (after / 1e6, 100 * after / before))
print("elapsed       : %.0f s" % (time.time() - started))
print("\nThe exhibits still have to be rebuilt against these; the number that")
print("matters is the size of the PDFs, not of the PNGs inside them.")
