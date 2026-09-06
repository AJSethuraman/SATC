/* A PDF writer, written out rather than pulled in.

   Three reasons it is not a library. The tool's whole claim is that nothing
   leaves the browser, and that claim is only as good as the code a person can
   read — a megabyte of minified third-party script makes it unauditable. The
   output has to be checked by tests down to the figure, which is far easier
   when the bytes are ours. And a document with a CPA's name on it should not
   change shape because a dependency shipped a minor version.

   It writes PDF 1.4 with uncompressed content streams, so you can open the file
   in a text editor and read the numbers. That is a feature: the proof that the
   PDF says what the screen said is a grep away.

   Figures are set in Courier — a fixed-width face, so a column of money aligns
   exactly with no font metrics to embed and nothing to get subtly wrong. */

import { formatCents } from './money.mjs';

const PAGE_W = 612, PAGE_H = 792;
const MARGIN = 54;
const RIGHT = PAGE_W - MARGIN;
const COURIER_W = 0.6; // every Courier glyph, in em

// WinAnsiEncoding for the handful of non-ASCII characters our copy uses.
const WINANSI = new Map(Object.entries({
  '–': '\x96', '—': '\x97', '‘': '\x91', '’': '\x92',
  '“': '\x93', '”': '\x94', '…': '\x85', '·': '\xb7',
  ' ': ' ', 'é': '\xe9', '£': '\xa3', '•': '\x95',
}));

export function encodeText(s) {
  let out = '';
  for (const ch of String(s)) {
    const mapped = WINANSI.get(ch);
    if (mapped !== undefined) { out += mapped; continue; }
    const code = ch.codePointAt(0);
    out += code < 256 ? ch : '?';
  }
  return out.replace(/[\\()]/g, (c) => `\\${c}`);
}

class Doc {
  constructor() {
    this.pages = [];
    this.newPage();
  }

  newPage() {
    this.ops = [];
    this.pages.push(this.ops);
    this.y = PAGE_H - MARGIN;
    return this.y;
  }

  space(needed) {
    if (this.y - needed < MARGIN + 24) this.newPage();
  }

  text(str, x, y, { font = 'F1', size = 9, gray = 0 } = {}) {
    if (str === '' || str === null || str === undefined) return;
    this.ops.push(`q ${gray} g BT /${font} ${size} Tf 1 0 0 1 ${x.toFixed(2)} ${y.toFixed(2)} Tm (${encodeText(str)}) Tj ET Q`);
  }

  right(str, xRight, y, { size = 9, gray = 0, font = 'F3' } = {}) {
    if (!str) return;
    const width = String(str).length * COURIER_W * size;
    this.text(str, xRight - width, y, { font, size, gray });
  }

  rule(y, { from = MARGIN, to = RIGHT, gray = 0.75, width = 0.5 } = {}) {
    this.ops.push(`q ${gray} G ${width} w ${from} ${y.toFixed(2)} m ${to} ${y.toFixed(2)} l S Q`);
  }

  /** Wrap on spaces at a rough character budget. Helvetica is proportional and
      we carry no width table, so the budget is deliberately conservative —
      a short line is a cosmetic problem, an overrun is a broken document. */
  paragraph(str, x, { size = 8, gray = 0.25, width = RIGHT - MARGIN, leading = 11 } = {}) {
    const perLine = Math.floor(width / (size * 0.5));
    const words = String(str).split(/\s+/);
    let cur = '';
    const lines = [];
    for (const w of words) {
      if (cur && (cur + ' ' + w).length > perLine) { lines.push(cur); cur = w; } else cur = cur ? `${cur} ${w}` : w;
    }
    if (cur) lines.push(cur);
    for (const l of lines) {
      this.space(leading);
      this.y -= leading;
      this.text(l, x, this.y, { size, gray });
    }
  }
}

function figure(cents, source, rounding) {
  if (source === 'empty') return '';
  return formatCents(rounding === 'dollars' ? Math.round(cents / 100) * 100 : cents, { dollars: rounding === 'dollars' });
}

function drawStatement(doc, stmt, result) {
  const { rounding } = stmt;
  doc.y -= 6;
  doc.space(20); doc.y -= 14;
  doc.text('Profit and loss', MARGIN, doc.y, { font: 'F2', size: 13 });

  for (const sec of stmt.sections) {
    doc.space(30);
    doc.y -= 18;
    doc.text(sec.heading, MARGIN, doc.y, { font: 'F2', size: 9.5 });
    doc.y -= 4;
    doc.rule(doc.y);
    for (const r of sec.rows) {
      doc.space(14);
      doc.y -= 12;
      doc.text(r.label, MARGIN + 10, doc.y);
      doc.right(`(${r.id})`, MARGIN + 220, doc.y, { size: 7.5, gray: 0.5 });
      const shown = figure(r.cents, r.source, rounding);
      doc.right(r.negate && r.cents > 0 ? `(${shown})` : shown, RIGHT, doc.y);
    }
    if (sec.footer) {
      doc.space(18);
      doc.y -= 5;
      doc.rule(doc.y, { from: RIGHT - 96 });
      doc.y -= 11;
      doc.text(sec.footer.label, MARGIN + (sec.rows.length ? 10 : 10), doc.y, { font: 'F2', size: 9 });
      doc.right(`(${sec.footer.id})`, MARGIN + 220, doc.y, { size: 7.5, gray: 0.5 });
      doc.right(figure(sec.footer.cents, sec.footer.source, rounding), RIGHT, doc.y, { size: 9.5 });
      if (sec.final) { doc.y -= 3; doc.rule(doc.y, { from: RIGHT - 96, gray: 0.2 }); doc.y -= 2; doc.rule(doc.y, { from: RIGHT - 96, gray: 0.2 }); }
    }
  }
  void result;
}


/** Break a label on spaces so nothing is ever lost. A cut label makes the
    worksheet disagree with the spreadsheet about the form's own wording. */
function wrapLabel(label, budget) {
  const words = String(label).split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    if (cur && (`${cur} ${w}`).length > budget) { lines.push(cur); cur = w; } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [''];
}

function drawWorksheet(doc, sheet) {
  const { rounding } = sheet;
  doc.space(40);
  doc.y -= 26;
  doc.text(sheet.title, MARGIN, doc.y, { font: 'F2', size: 13 });
  doc.y -= 4;
  doc.paragraph('Every line, in the order Schedule C asks for them. Blank means nothing was entered, not zero.', MARGIN, { size: 7.5 });

  for (const part of sheet.parts) {
    doc.space(28);
    doc.y -= 16;
    doc.text(part.heading, MARGIN, doc.y, { font: 'F2', size: 9.5 });
    doc.y -= 4;
    doc.rule(doc.y);
    for (const r of part.rows) {
      doc.space(13);
      doc.y -= 11;
      doc.text(r.id, MARGIN, doc.y, { font: 'F3', size: 8, gray: 0.45 });
      // WRAP, NEVER CUT. This truncated at 78 characters, which clipped five of
      // the 55 IRS labels -- line 6 lost one character. lines.test.mjs verifies
      // 52 of them word-for-word against the official PDF going IN, and nothing
      // looked at what came OUT, so the worksheet quietly disagreed with the
      // spreadsheet about what the form says. The whole point of the worksheet
      // is the form's own wording.
      const [head, ...restWords] = wrapLabel(r.label, 78);
      doc.text(head, MARGIN + 26, doc.y, { size: 8.5, gray: r.computed ? 0.35 : 0 });
      doc.right(figure(r.cents, r.source, rounding), RIGHT, doc.y, { size: 8.5 });
      for (const line of restWords) {
        doc.space(11);
        doc.y -= 9.5;
        doc.text(line, MARGIN + 26, doc.y, { size: 8.5, gray: r.computed ? 0.35 : 0 });
      }
    }
  }
}

function drawAnswers(doc, rows) {
  doc.space(40);
  doc.y -= 22;
  doc.text('What the form also asks', MARGIN, doc.y, { font: 'F2', size: 11 });
  doc.y -= 4;
  doc.rule(doc.y);
  for (const r of rows) {
    doc.space(13);
    doc.y -= 11;
    doc.text(r.label, MARGIN + 10, doc.y, { size: 8.5 });
    doc.text(r.value, MARGIN + 320, doc.y, { size: 8.5, gray: r.value === 'Not answered' ? 0.55 : 0 });
  }
}

function drawNotes(doc, heading, items) {
  if (!items.length) return;
  doc.space(36);
  doc.y -= 22;
  doc.text(heading, MARGIN, doc.y, { font: 'F2', size: 11 });
  doc.y -= 4;
  doc.rule(doc.y);
  for (const it of items) {
    doc.space(16);
    doc.y -= 12;
    doc.text(it.line ? `Line ${it.line}` : 'Note', MARGIN, doc.y, { font: 'F2', size: 8 });
    doc.paragraph(it.message, MARGIN + 52, { size: 8, gray: 0.2, width: RIGHT - MARGIN - 52, leading: 10 });
    doc.y -= 1;
  }
}

function serialise(doc, meta) {
  const objects = [];
  const add = (body) => { objects.push(body); return objects.length; };

  const fontIds = {
    F1: add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'),
    F2: add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>'),
    F3: add('<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>'),
  };
  const resources = `<< /Font << /F1 ${fontIds.F1} 0 R /F2 ${fontIds.F2} 0 R /F3 ${fontIds.F3} 0 R >> >>`;

  const pagesId = objects.length + 1 + doc.pages.length * 2;
  const pageIds = [];
  for (const ops of doc.pages) {
    const stream = ops.join('\n');
    const contentId = add(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
    pageIds.push(add(`<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 ${PAGE_W} ${PAGE_H}] /Resources ${resources} /Contents ${contentId} 0 R >>`));
  }
  const realPagesId = add(`<< /Type /Pages /Count ${pageIds.length} /Kids [${pageIds.map((i) => `${i} 0 R`).join(' ')}] >>`);
  const infoId = add(`<< /Title (${encodeText(meta.title)}) /Producer (SATC Schedule C profit and loss tool) /Creator (satcllp.com) /CreationDate (D:${meta.stamp}) >>`);
  const catalogId = add(`<< /Type /Catalog /Pages ${realPagesId} 0 R >>`);

  let out = '%PDF-1.4\n%\xe2\xe3\xcf\xd3\n';
  const offsets = [0];
  objects.forEach((body, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xrefAt = out.length;
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i <= objects.length; i += 1) {
    out += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  out += `trailer\n<< /Size ${objects.length + 1} /Root ${catalogId} 0 R /Info ${infoId} 0 R >>\nstartxref\n${xrefAt}\n%%EOF\n`;

  const bytes = new Uint8Array(out.length);
  for (let i = 0; i < out.length; i += 1) bytes[i] = out.charCodeAt(i) & 0xff;
  if (realPagesId !== pagesId) throw new Error('page tree id drifted — the /Parent references would dangle');
  return bytes;
}

/** Build the PDF. `include` picks which of the two documents go in it. */
export function buildPdf({ result, input, stmt, sheet, answerRows, meta, include = ['statement', 'worksheet'], footingNote = null }) {
  const doc = new Doc();

  doc.text(meta.firm, MARGIN, doc.y, { font: 'F2', size: 10 });
  doc.right(meta.site, RIGHT, doc.y, { font: 'F1', size: 8.5, gray: 0.4 });
  doc.y -= 6;
  doc.rule(doc.y, { gray: 0.35, width: 1 });
  doc.y -= 16;
  doc.text(meta.businessName || 'Your business', MARGIN, doc.y, { font: 'F2', size: 15 });
  doc.y -= 13;
  doc.text(`Tax year ${result.year}${meta.activity ? ` · ${meta.activity}` : ''}`, MARGIN, doc.y, { size: 9, gray: 0.3 });
  doc.y -= 11;
  doc.text(`Prepared ${meta.prepared}`, MARGIN, doc.y, { size: 9, gray: 0.3 });

  if (include.includes('statement')) drawStatement(doc, stmt, result);
  if (include.includes('worksheet')) {
    drawWorksheet(doc, sheet);
    drawAnswers(doc, answerRows);
  }

  if (footingNote) drawNotes(doc, 'About the rounding', [{ line: null, message: footingNote }]);
  drawNotes(doc, 'Worth checking', result.notices.map((n) => ({ line: n.line, message: n.message })));
  drawNotes(doc, 'What this tool did not work out', meta.refusals.map((r) => ({
    line: r.line, message: `${r.subject}. ${r.because} ${r.instead}`,
  })));

  doc.space(60);
  doc.y -= 26;
  doc.rule(doc.y, { gray: 0.6 });
  doc.paragraph(meta.disclaimer, MARGIN, { size: 8, gray: 0.3 });
  doc.paragraph(meta.invitation, MARGIN, { size: 8, gray: 0.3 });

  void input;
  return serialise(doc, meta);
}
