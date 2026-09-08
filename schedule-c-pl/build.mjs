/* Build the one file that ships.

   satcllp.com is served from ./website, so the page has to live there — but the
   source, the tests and the evidence do not belong on a public web server. So
   this folder holds the source and generates the page into website/, the same
   way pricing-config.js is generated from the fee schedule rather than retyped.

   The output is a SINGLE self-contained HTML file. That is not tidiness: the
   page's whole claim is that your figures never leave your computer, and the
   cheapest way for a person to check that claim is to read the file. One file,
   no script tags pointing anywhere, nothing fetched.

   `node build.mjs --check` rebuilds and fails if the committed page is not what
   the source produces today, so the two cannot drift apart. */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';

const HERE = dirname(fileURLToPath(import.meta.url));
export const OUT_DIR = join(HERE, '..', 'website', 'tools', 'schedule-c-profit-and-loss');
export const OUT_FILE = join(OUT_DIR, 'index.html');

/* Order matters: a module's top-level code runs where it is placed, so
   anything it reads must already be declared above it. */
const MODULES = [
  'src/money.mjs',
  'src/lines.mjs',
  'years/2023.mjs',
  'years/2024.mjs',
  'years/2025.mjs',
  'src/years.mjs',
  'src/helpers.mjs',
  'src/engine.mjs',
  'src/report.mjs',
  'src/pdf.mjs',
  'src/xlsx.mjs',
  'src/document.mjs',
  'src/ui.mjs',
];

const IMPORT = /^\s*import[\s\S]*?from\s+['"][^'"]+['"];\s*$/gm;
const EXPORT_KEYWORD = /^export\s+(?=(const|let|var|function|class|async))/gm;
const EXPORT_LIST = /^export\s*\{[^}]*\}\s*;?\s*$/gm;

/** Flatten the modules into one script. They are already plain ES modules with
    no cycles, so this is concatenation plus removing the words that only mean
    something across file boundaries. */
export function bundle() {
  const parts = [];
  for (const rel of MODULES) {
    const src = readFileSync(join(HERE, rel), 'utf8')
      .replace(IMPORT, '')
      .replace(EXPORT_LIST, '')
      .replace(EXPORT_KEYWORD, '');
    parts.push(`/* ── ${rel} ${'─'.repeat(Math.max(0, 60 - rel.length))} */\n${src.trim()}\n`);
  }
  const code = parts.join('\n');
  assertNoDuplicateNames(code);
  return code;
}

/** Two modules declaring the same top-level name would silently shadow each
    other once the file boundaries are gone. This is what stops that becoming a
    bug nobody can see. */
function assertNoDuplicateNames(code) {
  const seen = new Map();
  const clashes = [];
  for (const m of code.matchAll(/^(?:const|let|var|function|class|async function)\s+([A-Za-z_$][\w$]*)/gm)) {
    const name = m[1];
    if (seen.has(name)) clashes.push(name);
    seen.set(name, true);
  }
  if (clashes.length) {
    throw new Error(`two modules both declare: ${[...new Set(clashes)].join(', ')}. Rename one before bundling.`);
  }
}

export function render() {
  const shell = readFileSync(join(HERE, 'src', 'shell.html'), 'utf8');
  const css = readFileSync(join(HERE, 'src', 'styles.css'), 'utf8');
  const code = bundle();
  const boot = `

/* ── boot ──────────────────────────────────────────────────────────── */
const __root = document.getElementById('tool');
try {
  start(__root);
} catch (err) {
  __root.replaceChildren(Object.assign(document.createElement('p'), {
    className: 'error',
    textContent: 'This page could not start: ' + err.message,
  }));
}
`;
  const stamp = createHash('sha256').update(code).digest('hex').slice(0, 12);
  return shell
    .replace('/* STYLES */', () => `\n${css.trim()}\n`)
    .replace('/* SCRIPT */', () => `\n${code}${boot}`)
    .replace('<p class="meta" id="build-stamp"></p>',
      `<p class="meta" id="build-stamp">Built from source ${stamp}. Tax years 2023, 2024 and 2025.</p>`);
}

/** Nothing in the shipped page may reach out to another machine. This is the
    claim on the page, checked mechanically rather than believed. */
export function findNetworkCalls(html) {
  const patterns = [
    [/\bfetch\s*\(/g, 'fetch('],
    [/XMLHttpRequest/g, 'XMLHttpRequest'],
    [/\bnavigator\.sendBeacon/g, 'sendBeacon'],
    [/\bnew\s+(WebSocket|EventSource)\b/g, 'a live connection'],
    [/<script[^>]+src=/gi, 'an external script'],
    // <link rel=canonical> points at a URL but fetches nothing; the ones that
    // do fetch are named here so the check stays about behaviour, not shape.
    [/<link[^>]+rel=["'](?:stylesheet|preload|prefetch|preconnect|dns-prefetch|modulepreload)["'][^>]*>/gi, 'an external stylesheet or preload'],
    [/<img[^>]+src=["']https?:/gi, 'a remote image'],
    [/@import\s+url/gi, 'an imported stylesheet'],
    [/\bimport\s*\(/g, 'a dynamic import'],
  ];
  const found = [];
  for (const [re, what] of patterns) {
    const hits = html.match(re);
    if (hits) found.push(`${what} (${hits.length})`);
  }
  return found;
}

function main() {
  const html = render();
  const leaks = findNetworkCalls(html);
  if (leaks.length) {
    console.error(`refusing to build: the page would talk to another machine — ${leaks.join(', ')}`);
    process.exit(2);
  }
  if (process.argv.includes('--check')) {
    const existing = existsSync(OUT_FILE) ? readFileSync(OUT_FILE, 'utf8') : '';
    if (existing !== html) {
      console.error('website/tools/schedule-c-profit-and-loss/index.html is not what the source builds today. Run: npm run build');
      process.exit(1);
    }
    console.log(`up to date — ${(html.length / 1024).toFixed(0)} KB, no network calls`);
    return;
  }
  mkdirSync(OUT_DIR, { recursive: true });
  writeFileSync(OUT_FILE, html);
  console.log(`wrote ${OUT_FILE} — ${(html.length / 1024).toFixed(0)} KB, no network calls`);
}

if (process.argv[1] && process.argv[1].endsWith('build.mjs')) main();
