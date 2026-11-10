// Print the example HTML outputs to PDF with the pre-installed Chromium.
// Run: node workpaper-studio/examples/print_pdfs.js
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const out = path.join(__dirname, 'out');
  const files = fs.readdirSync(out).filter(f => f.endsWith('.html'));
  const b = await chromium.launch();
  const p = await b.newPage();
  for (const f of files) {
    await p.goto('file://' + path.join(out, f));
    await p.waitForTimeout(400);
    const pdf = path.join(out, f.replace(/\.html$/, '.pdf'));
    await p.pdf({ path: pdf, format: 'Letter', printBackground: true, margin: { top: '14mm', bottom: '14mm', left: '12mm', right: '12mm' } });
    console.log('printed', path.basename(pdf), fs.statSync(pdf).size, 'bytes');
  }
  await b.close();
})();
