"""Generate starter documents for the reading corpus.

These are SYNTHETIC and that limitation is the point of this docstring. They are
worth more than a dict fixture — a generated PDF goes through real text
extraction, real classification, real money parsing, so it exercises the actual
ladder rather than a mock of it. They are worth less than a real ADP W-2,
because a real one has a layout nobody here designed.

So: run this to have a corpus on day one, then replace it with real documents as
you get them. The scoreboard reports both together, and the number that matters
(precision at HIGH confidence) means the same thing either way.

    python scripts/make_corpus_samples.py

Writes into ``corpus/generated/``, which is git-ignored like the rest.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "corpus" / "generated"

# (filename, layout label, the values a reader should find)
SAMPLES = [
    ("w2_clean", "W-2", {
        "Employer name": "Nordwind Logistics LLC",
        "Box 1": "84500.00",
        "Box 2": "11230.00",
        "Box 3": "84500.00",
        "Box 5": "84500.00",
    }),
    ("w2_second_job", "W-2", {
        "Employer name": "Bright Harbor Coffee Co",
        "Box 1": "23150.75",
        "Box 2": "1845.20",
        "Box 3": "23150.75",
        "Box 5": "23150.75",
    }),
    ("1099int_simple", "1099-INT", {
        "Payer name": "Lakeside Savings Bank",
        "Box 1": "1284.19",
    }),
]


def _w2_page(canvas, values: dict[str, str]) -> None:
    """A W-2-shaped page. Box labels are the real ones the classifier keys on."""
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(72, 760, "Form W-2  Wage and Tax Statement")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(72, 745, "Department of the Treasury — Internal Revenue Service")

    canvas.setFont("Helvetica", 10)
    y = 700
    canvas.drawString(72, y, "c  Employer's name, address, and ZIP code")
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(80, y - 16, values["Employer name"])
    canvas.setFont("Helvetica", 10)

    rows = [
        ("1  Wages, tips, other compensation", values["Box 1"]),
        ("2  Federal income tax withheld", values["Box 2"]),
        ("3  Social security wages", values["Box 3"]),
        ("5  Medicare wages and tips", values["Box 5"]),
    ]
    y = 640
    for label, amount in rows:
        canvas.drawString(72, y, label)
        canvas.drawRightString(430, y, amount)
        canvas.line(72, y - 4, 430, y - 4)
        y -= 34

    canvas.setFont("Helvetica", 8)
    canvas.drawString(72, 120, "This is a generated sample document. Not a real W-2.")


def _1099int_page(canvas, values: dict[str, str]) -> None:
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(72, 760, "Form 1099-INT  Interest Income")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(72, 720, "PAYER'S name, street address, city")
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(80, 704, values["Payer name"])
    canvas.setFont("Helvetica", 10)
    canvas.drawString(72, 660, "1  Interest income")
    canvas.drawRightString(430, 660, values["Box 1"])
    canvas.line(72, 656, 430, 656)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(72, 120, "This is a generated sample document. Not a real 1099-INT.")


def main() -> int:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as pdfcanvas

    OUT.mkdir(parents=True, exist_ok=True)
    for name, doc_type, values in SAMPLES:
        pdf_path = OUT / f"{name}.pdf"
        c = pdfcanvas.Canvas(str(pdf_path), pagesize=letter)
        (_w2_page if doc_type == "W-2" else _1099int_page)(c, values)
        c.showPage()
        c.save()

        lines = [f"doc_type: \"{doc_type}\"", "fields:"]
        lines += [f'  "{k}": "{v}"' for k, v in values.items()]
        lines.append('note: "GENERATED sample — exercises the real ladder, but '
                     'no real-world layout. Replace with real documents."')
        (OUT / f"{name}.expected.yaml").write_text("\n".join(lines) + "\n",
                                                   encoding="utf-8")
        print(f"wrote {pdf_path.name} + expectations")

    print(f"\n{len(SAMPLES)} documents in {OUT}")
    print("Now run:  satc scoreboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
