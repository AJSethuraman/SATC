/* Independent readers. The point of these is that they are not our code: the
   PDF is opened with Mozilla's pdf.js — the engine Firefox itself uses — and
   the spreadsheet by a Python library that has never heard of this project. A
   document our own writer can read proves nothing. */

import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs';
import { execFileSync } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export async function readPdf(bytes) {
  const doc = await getDocument({ data: new Uint8Array(bytes), useSystemFonts: false, verbosity: 0 }).promise;
  const pages = [];
  const boxes = [];
  for (let p = 1; p <= doc.numPages; p += 1) {
    const page = await doc.getPage(p);
    const content = await page.getTextContent();
    pages.push(content.items.map((i) => i.str).join(' ').replace(/\s+/g, ' ').trim());
    boxes.push(content.items
      .filter((i) => i.str.trim())
      .map((i) => ({ str: i.str, x: i.transform[4], y: i.transform[5], w: i.width, h: i.height })));
  }
  return { numPages: doc.numPages, pages, boxes, text: pages.join(' ').replace(/\s+/g, ' ').trim() };
}

const PY = `
import json, sys, warnings
warnings.filterwarnings('ignore')
import openpyxl
path = sys.argv[1]
out = {"sheets": {}, "formulas": {}}
wb = openpyxl.load_workbook(path, data_only=False)
for ws in wb.worksheets:
    rows, formulas = [], {}
    for row in ws.iter_rows():
        cells = []
        for c in row:
            v = c.value
            if isinstance(v, str) and v.startswith("="):
                formulas[c.coordinate] = v
            cells.append(None if v is None else (v if isinstance(v, (int, float, str)) else str(v)))
        rows.append(cells)
    out["sheets"][ws.title] = rows
    out["formulas"][ws.title] = formulas
wb2 = openpyxl.load_workbook(path, data_only=True)
out["cached"] = {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in wb2.worksheets}
json.dump(out, sys.stdout, default=str)
`;

export function readXlsx(bytes) {
  const dir = mkdtempSync(join(tmpdir(), 'satc-xlsx-'));
  const file = join(dir, 'book.xlsx');
  writeFileSync(file, Buffer.from(bytes));
  const script = join(dir, 'read.py');
  writeFileSync(script, PY);
  const out = execFileSync('python3', [script, file], { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
  return JSON.parse(out);
}

/** Every string that appears anywhere in a workbook — the cheap way to ask
    "did the figure on the screen reach the file". */
export function xlsxStrings(book) {
  const seen = [];
  for (const rows of Object.values(book.sheets)) {
    for (const row of rows) for (const cell of row) if (cell !== null && cell !== undefined) seen.push(String(cell));
  }
  return seen;
}
