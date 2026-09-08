/* An .xlsx writer, also written out rather than pulled in — same three reasons
   as pdf.mjs, plus one more: the widely used spreadsheet library was pulled
   from npm, and a free tool with a CPA's name on it should not depend on a
   package whose distribution can move.

   An .xlsx file is a zip of XML. This writes the zip with no compression, so
   every byte in it is readable, and with a fixed timestamp, so building the
   same figures twice produces the same file — which is what lets a test assert
   the output is stable.

   The totals are real SUM formulas, not pasted numbers. Someone who opens this
   to change a figure gets a working spreadsheet rather than a picture of one.
   The cached value is written alongside each formula, so a reader that does not
   recalculate still shows the right answer, and a test can check the two agree. */

const enc = new TextEncoder();

// ── zip ───────────────────────────────────────────────────────────────
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function zip(files) {
  const chunks = [];
  const central = [];
  let offset = 0;
  const put = (b) => { chunks.push(b); offset += b.length; };

  for (const { name, data } of files) {
    const nameBytes = enc.encode(name);
    const crc = crc32(data);
    const local = new Uint8Array(30 + nameBytes.length);
    const dv = new DataView(local.buffer);
    dv.setUint32(0, 0x04034b50, true);
    dv.setUint16(4, 20, true);      // version needed to extract
    dv.setUint16(6, 0, true);       // flags
    dv.setUint16(8, 0, true);       // stored, not deflated
    dv.setUint16(10, 0, true);      // time 00:00
    dv.setUint16(12, 33, true);     // date 1980-01-01 — fixed, so builds repeat
    dv.setUint32(14, crc, true);
    dv.setUint32(18, data.length, true);
    dv.setUint32(22, data.length, true);
    dv.setUint16(26, nameBytes.length, true);
    local.set(nameBytes, 30);
    const headerAt = offset;
    put(local);
    put(data);

    const cd = new Uint8Array(46 + nameBytes.length);
    const cv = new DataView(cd.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(10, 0, true);
    cv.setUint16(12, 0, true);
    cv.setUint16(14, 33, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, data.length, true);
    cv.setUint32(24, data.length, true);
    cv.setUint16(28, nameBytes.length, true);
    cv.setUint32(42, headerAt, true);
    cd.set(nameBytes, 46);
    central.push(cd);
  }

  const cdStart = offset;
  for (const cd of central) put(cd);
  const eocd = new Uint8Array(22);
  const ev = new DataView(eocd.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, central.length, true);
  ev.setUint16(10, central.length, true);
  ev.setUint32(12, offset - cdStart, true);
  ev.setUint32(16, cdStart, true);
  put(eocd);

  const out = new Uint8Array(offset);
  let at = 0;
  for (const c of chunks) { out.set(c, at); at += c.length; }
  return out;
}

// ── xml ───────────────────────────────────────────────────────────────
// Control characters are not legal in XML 1.0 and Excel refuses the whole file
// if one gets in, so they are dropped rather than escaped.
const ILLEGAL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g;
const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(ILLEGAL, '');

const COLS = ['A', 'B', 'C', 'D', 'E', 'F'];

/** Cents as the exact decimal text Excel should store. No division, so no
    float ever represents the money on its way into the file. */
export function centsToDecimal(cents, wholeDollars = false) {
  if (cents === null || cents === undefined) return '';
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  if (wholeDollars) {
    const d = Math.floor(abs / 100) + (abs % 100 >= 50 ? 1 : 0);
    return `${sign}${d}`;
  }
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}

class Sheet {
  constructor(name, widths) { this.name = name; this.widths = widths; this.rows = []; }

  add(cells) { this.rows.push(cells); return this.rows.length; }

  blank() { return this.add([]); }

  xml() {
    const cols = this.widths.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join('');
    const body = this.rows.map((cells, ri) => {
      const r = ri + 1;
      if (!cells.length) return `<row r="${r}"/>`;
      const cs = cells.map((cell, ci) => {
        if (cell === null || cell === undefined || cell.v === '' || cell.v === null) return '';
        const ref = `${COLS[ci]}${r}`;
        const s = cell.s ? ` s="${cell.s}"` : '';
        if (cell.f) return `<c r="${ref}"${s}><f>${esc(cell.f)}</f><v>${esc(cell.v)}</v></c>`;
        if (cell.n) return `<c r="${ref}"${s}><v>${esc(cell.v)}</v></c>`;
        return `<c r="${ref}"${s} t="inlineStr"><is><t xml:space="preserve">${esc(cell.v)}</t></is></c>`;
      }).join('');
      return `<row r="${r}">${cs}</row>`;
    }).join('');
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
      + `<cols>${cols}</cols><sheetData>${body}</sheetData></worksheet>`;
  }
}

const STYLES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0.00;(#,##0.00)"/><numFmt numFmtId="165" formatCode="#,##0;(#,##0)"/></numFmts>
<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="15"/><name val="Calibri"/></font><font><sz val="9"/><color rgb="FF666666"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left/><right/><top style="thin"><color rgb="FF999999"/></top><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="8">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="164" fontId="1" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="1" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
</cellXfs></styleSheet>`;

export const STYLE = { plain: 0, bold: 1, money: 2, moneyTotal: 3, title: 4, muted: 5, wholeMoney: 6, wholeMoneyTotal: 7 };

function pack(sheets) {
  const files = [
    { name: '[Content_Types].xml', data: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + sheets.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('') + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>') },
    { name: '_rels/.rels', data: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>') },
    { name: 'xl/workbook.xml', data: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + sheets.map((s, i) => `<sheet name="${esc(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('') + '</sheets></workbook>') },
    { name: 'xl/_rels/workbook.xml.rels', data: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + sheets.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('') + `<Relationship Id="rId${sheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
    { name: 'xl/styles.xml', data: enc.encode(STYLES) },
  ];
  sheets.forEach((s, i) => files.push({ name: `xl/worksheets/sheet${i + 1}.xml`, data: enc.encode(s.xml()) }));
  return zip(files);
}

/** Build the workbook. Three sheets: the statement, the worksheet, and the
    detail behind them. */
export function buildXlsx({ result, stmt, sheet, answerRows, meta, rows = {}, rounding = 'cents' }) {
  const whole = rounding === 'dollars';
  const M = whole ? STYLE.wholeMoney : STYLE.money;
  const MT = whole ? STYLE.wholeMoneyTotal : STYLE.moneyTotal;
  const num = (cents, source, style) => (source === 'empty'
    ? null
    : { v: centsToDecimal(cents, whole), n: true, s: style });

  // ── sheet 1 · profit and loss ────────────────────────────────────────
  const pl = new Sheet('Profit and loss', [40, 8, 16]);
  pl.add([{ v: meta.businessName || 'Your business', s: STYLE.title }]);
  pl.add([{ v: `Profit and loss — tax year ${result.year}`, s: STYLE.bold }]);
  pl.add([{ v: `Prepared ${meta.prepared}. The figures are yours; the order follows Schedule C.`, s: STYLE.muted }]);
  pl.blank();

  for (const sec of stmt.sections) {
    pl.add([{ v: sec.heading, s: STYLE.bold }]);
    for (const r of sec.rows) {
      pl.add([{ v: `  ${r.label}` }, { v: r.id, s: STYLE.muted }, num(r.cents, r.source, M)]);
    }
    if (sec.footer) {
      pl.add([{ v: sec.footer.label, s: STYLE.bold }, { v: sec.footer.id, s: STYLE.muted },
        num(sec.footer.cents, sec.footer.source, MT)]);
    }
    pl.blank();
  }

  // ── sheet 2 · the worksheet, with live totals ────────────────────────
  const ws = new Sheet(`Schedule C ${result.year}`, [8, 62, 16]);
  ws.add([{ v: sheet.title, s: STYLE.title }]);
  ws.add([{ v: 'Blank means nothing was entered — it does not mean zero.', s: STYLE.muted }]);
  ws.blank();

  const rowOf = new Map();
  const pending = [];
  for (const part of sheet.parts) {
    ws.add([{ v: '' }, { v: part.heading, s: STYLE.bold }]);
    for (const r of part.rows) {
      const at = ws.add([{ v: r.id, s: STYLE.muted }, { v: r.label }, num(r.cents, r.source, r.computed ? MT : M)]);
      if (!rowOf.has(r.id)) rowOf.set(r.id, at);
      if (r.computed) pending.push({ id: r.id, at, cents: r.cents, source: r.source });
    }
    ws.blank();
  }

  // Now that every line has a row, give the computed ones a real formula.
  const cell = (id) => (rowOf.has(id) ? `C${rowOf.get(id)}` : null);
  const FORMULAS = {
    3: ['sub', '1', '2'], 4: ['copy', '42'], 5: ['sub', '3', '4'], 7: ['add', '5', '6'],
    28: ['range', '8', '27b'], 29: ['sub', '7', '28'], 31: ['sub', '29', '30'],
    40: ['range', '35', '39'], 42: ['sub', '40', '41'],
  };
  FORMULAS[result.otherExpensesLine] = ['copy', '48'];
  for (const p of pending) {
    const spec = FORMULAS[p.id];
    if (!spec || p.source === 'empty') continue;
    const [op, a, b] = spec;
    let f = null;
    if (op === 'sub' && cell(a) && cell(b)) f = `${cell(a)}-${cell(b)}`;
    else if (op === 'add' && cell(a) && cell(b)) f = `${cell(a)}+${cell(b)}`;
    else if (op === 'copy' && cell(a)) f = `${cell(a)}`;
    else if (op === 'range' && cell(a) && cell(b)) f = `SUM(${cell(a)}:${cell(b)})`;
    if (!f) continue;
    ws.rows[p.at - 1][2] = { v: centsToDecimal(p.cents, whole), f, s: MT };
  }

  // ── sheet 3 · detail ─────────────────────────────────────────────────
  const detail = new Sheet('Detail', [40, 60]);
  detail.add([{ v: 'Behind the figures', s: STYLE.title }]);
  detail.blank();
  detail.add([{ v: `Other expenses — carried to line ${result.otherExpensesLine}`, s: STYLE.bold }]);
  for (const r of (rows.other || [])) detail.add([{ v: r.label }, { v: centsToDecimal(r.cents, whole), n: true, s: M }]);
  detail.blank();
  detail.add([{ v: 'What the form also asks', s: STYLE.bold }]);
  for (const a of answerRows) detail.add([{ v: a.label }, { v: a.value }]);
  detail.blank();
  detail.add([{ v: 'Worth checking', s: STYLE.bold }]);
  for (const n of result.notices) detail.add([{ v: n.line ? `Line ${n.line}` : 'Note' }, { v: n.message }]);
  if (!result.notices.length) detail.add([{ v: 'Nothing flagged.', s: STYLE.muted }]);
  detail.blank();
  detail.add([{ v: 'What this tool did not work out', s: STYLE.bold }]);
  for (const r of meta.refusals) detail.add([{ v: `Line ${r.line} — ${r.subject}` }, { v: `${r.because} ${r.instead}` }]);
  detail.blank();
  detail.add([{ v: meta.disclaimer }]);
  detail.add([{ v: meta.invitation }]);

  return pack([pl, ws, detail]);
}
