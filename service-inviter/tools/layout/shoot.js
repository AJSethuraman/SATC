// Draws each scene in Chromium, saves a picture, prints overlaps; exits 1 if there are any.
const { chromium } = require("playwright");
const fs = require("fs");
const [render, out] = process.argv.slice(2);
const scenes = JSON.parse(fs.readFileSync(`${out}/scenes.json`));
(async () => {
  const b = await chromium.launch();
  let bad = 0;
  for (const [name, sc] of Object.entries(scenes)) {
    const pg = await b.newPage({ deviceScaleFactor: 2, viewport: { width: 960, height: 1000 } });
    await pg.goto(`file://${render}`);
    const res = await pg.evaluate(([s]) => render(s, []), [sc]);
    const bb = await pg.locator("#win").boundingBox();
    await pg.screenshot({ path: `${out}/${name}.png`, clip: { x: bb.x, y: bb.y, width: bb.width, height: bb.height + 34 } });
    const real = res.overlaps.filter(o => !o[0].startsWith("CheckButton") && !o[1].startsWith("CheckButton"));
    console.log((real.length ? "OVERLAP " : "ok      ") + name + (real.length ? "  " + JSON.stringify(real) : ""));
    bad += real.length;
    await pg.close();
  }
  await b.close();
  process.exit(bad ? 1 : 0);
})();
