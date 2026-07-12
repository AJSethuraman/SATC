// Process the painted PNGs into game-ready sprites: key out the (often baked
// checkerboard / opaque) background to real transparency via a border flood-fill
// — connectivity protects the character even where it's light/grey — then trim to
// content, downscale, and emit a { id: dataURI } map embedded for the artifact.
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright/index.js');
const DIR = '/tmp/claude-0/-home-user-SATC/17c5a522-3b84-5bf0-a40c-3acac7fbdbaa/scratchpad/art_in';

// filename -> engine sprite id
const MAP = {
  'z1/Sorceress.png': 'sorceress', 'z1/Barbarian.png': 'barbarian', 'z1/Amazon.png': 'amazon', 'z1/Necromancer.png': 'necromancer',
  'z1/Fallen.png': 'fallen', 'z1/Guardian.png': 'guardian', 'z1/Dark Archer.png': 'archer', 'z1/Quill Rat.png': 'quill_rat', 'z1/Shaman.png': 'shaman',
  'z2/goatman.png': 'goatman', 'z2/Bishibosh.png': 'bishibosh', 'z2/Blood Raven.png': 'blood_raven', 'z2/Rakanishu.png': 'rakanishu',
  'z2/The Countess.png': 'the_countess', 'z2/Treehead Woodfist.png': 'treehead_woodfist', 'z2/andrial.png': 'andariel', 'z2/the smith.png': 'the_smith',
};
const dataUri = (p) => 'data:image/png;base64,' + fs.readFileSync(DIR + '/' + p).toString('base64');

const b = await chromium.launch();
const page = await b.newPage();
const out = {};
for (const [file, id] of Object.entries(MAP)) {
  const src = dataUri(file);
  const res = await page.evaluate(async ({ src, id }) => {
    const img = new Image(); img.src = src; await img.decode();
    // draw at <=512 for a quick, clean key
    const scale = Math.min(1, 512 / Math.max(img.width, img.height));
    const W = Math.round(img.width * scale), H = Math.round(img.height * scale);
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const c = cv.getContext('2d');
    c.drawImage(img, 0, 0, W, H);
    const im = c.getImageData(0, 0, W, H); const d = im.data;
    const isBg = (i) => { const a = d[i + 3]; if (a < 40) return true; const r = d[i], g = d[i + 1], bl = d[i + 2];
      const mx = Math.max(r, g, bl), mn = Math.min(r, g, bl); return mn > 150 && mx - mn < 32; }; // transparent, or light + desaturated (checkerboard/white)
    // flood-fill from every border pixel; only edge-connected background is cleared
    const stack = []; const seen = new Uint8Array(W * H);
    for (let x = 0; x < W; x++) { stack.push(x, x + (H - 1) * W); } for (let y = 0; y < H; y++) { stack.push(y * W, W - 1 + y * W); }
    while (stack.length) { const p = stack.pop(); if (seen[p]) continue; seen[p] = 1; const i = p * 4; if (!isBg(i)) continue;
      d[i + 3] = 0; const px = p % W, py = (p / W) | 0;
      if (px > 0) stack.push(p - 1); if (px < W - 1) stack.push(p + 1); if (py > 0) stack.push(p - W); if (py < H - 1) stack.push(p + W); }
    // soften stray semi-bg at the halo: any near-bg pixel adjacent to cleared -> knock down alpha
    c.putImageData(im, 0, 0);
    // content bbox
    let minX = W, minY = H, maxX = 0, maxY = 0;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { if (d[(y * W + x) * 4 + 3] > 24) { if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y; } }
    if (maxX < minX) { minX = 0; minY = 0; maxX = W - 1; maxY = H - 1; }
    const cw = maxX - minX + 1, ch = maxY - minY + 1;
    // fit into a square target, feet near the bottom, horizontally centered
    const T = 256, pad = 8; const avail = T - pad * 2;
    const k = Math.min(avail / cw, (T - pad) / ch);
    const dw = cw * k, dh = ch * k;
    const fin = document.createElement('canvas'); fin.width = T; fin.height = T; const fc = fin.getContext('2d');
    fc.imageSmoothingQuality = 'high';
    fc.drawImage(cv, minX, minY, cw, ch, (T - dw) / 2, T - dh - 3, dw, dh); // feet ~3px off the bottom
    return { uri: fin.toDataURL('image/png'), w: cw, h: ch };
  }, { src, id });
  out[id] = res.uri;
  console.log(id.padEnd(18), 'content', res.w + 'x' + res.h, '->', Math.round(res.uri.length / 1024) + 'KB');
}
await b.close();

const js = '// AUTO-GENERATED painted sprites (background-keyed, trimmed, 256px). See docs/ART_BRIEF.md.\n'
  + 'export const RASTER_SPRITES = {\n'
  + Object.entries(out).map(([k, v]) => `  ${k}: '${v}',`).join('\n') + '\n};\n';
fs.writeFileSync('/home/user/SATC/bloodrune/ui/sprites.js', js);
console.log('\nwrote ui/sprites.js', Math.round(js.length / 1024) + 'KB total, ' + Object.keys(out).length + ' sprites');
