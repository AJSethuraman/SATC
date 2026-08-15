import { chromium, type Browser, type BrowserContext } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { PATHS } from './config.js';

export interface SessionOptions {
  /** Record a HAR of everything this context does. */
  harPath?: string;
  /** Fail instead of prompting when no saved session exists. */
  requireSavedSession?: boolean;
  headless?: boolean;
  /** Override the saved-session file (the self-test uses its own). */
  storageStatePath?: string;
}

export interface Session {
  browser: Browser;
  context: BrowserContext;
  /** True when the run started from a previously saved session. */
  reusedSession: boolean;
  /** Persist cookies/localStorage, flush the HAR, and close the browser. */
  close: () => Promise<void>;
}

export function hasSavedSession(storageStatePath = PATHS.storageState): boolean {
  return fs.existsSync(storageStatePath);
}

/**
 * Launch Chromium, honouring PLAYWRIGHT_CHROMIUM_EXECUTABLE when set. Normal
 * local runs leave it unset and use Playwright's own browser download; the
 * override exists for environments that ship a pinned Chromium instead.
 */
export function launchChromium(headless: boolean): Promise<Browser> {
  const executablePath = process.env['PLAYWRIGHT_CHROMIUM_EXECUTABLE'];
  return chromium.launch({
    headless,
    ...(executablePath ? { executablePath } : {}),
    // Chromium's setuid sandbox cannot start as root, which is the norm inside
    // containers. Opt out only when asked; a normal local run keeps it on.
    ...(process.env['PLAYWRIGHT_NO_SANDBOX'] ? { chromiumSandbox: false } : {}),
  });
}

/**
 * True when the run should attach to a browser the operator started themselves
 * rather than launching its own. Google refuses OAuth sign-in in a
 * Playwright-launched browser ("This browser or app may not be secure"), so
 * accounts behind Google SSO have to log in in a normal Chrome, which we then
 * attach to over the DevTools protocol.
 */
export function isCdpMode(): boolean {
  return Boolean(process.env['PLAYWRIGHT_CDP_URL']);
}

export async function openSession(options: SessionOptions = {}): Promise<Session> {
  const cdpUrl = process.env['PLAYWRIGHT_CDP_URL'];
  if (cdpUrl) {
    const browser = await chromium.connectOverCDP(cdpUrl);
    const context = browser.contexts()[0];
    if (!context) {
      throw new Error(`Attached to ${cdpUrl} but it has no open window. Open a tab and retry.`);
    }
    // HAR recording is a context-creation option, so it is unavailable on a
    // context we did not create. discovery.json still captures the endpoints.
    return {
      browser,
      context,
      reusedSession: true,
      close: async () => {
        const target = options.storageStatePath ?? PATHS.storageState;
        await context.storageState({ path: target }).catch(() => undefined);
        // Detaches from the operator's browser; it keeps running.
        await browser.close();
      },
    };
  }

  const storageStatePath = options.storageStatePath ?? PATHS.storageState;
  const reusedSession = fs.existsSync(storageStatePath);

  if (options.requireSavedSession && !reusedSession) {
    throw new Error(
      `No saved session at ${storageStatePath}. Run "npm run poc" first and log in when prompted.`,
    );
  }

  const browser = await launchChromium(options.headless ?? false);
  const context = await browser.newContext({
    storageState: reusedSession ? storageStatePath : undefined,
    viewport: { width: 1440, height: 900 },
    ...(options.harPath ? { recordHar: { path: options.harPath, content: 'embed' as const } } : {}),
  });

  return {
    browser,
    context,
    reusedSession,
    close: async () => {
      // storageState() must be read before the context closes; closing the
      // context is also what flushes the HAR to disk.
      try {
        await context.storageState({ path: storageStatePath });
      } catch {
        // A context torn down early has nothing to save — not fatal.
      }
      await context.close();
      await browser.close();
    },
  };
}

/**
 * Block until the operator confirms they have logged in. Credentials are never
 * read, stored, or transmitted by this tool — the human types them directly
 * into the browser window.
 */
export async function waitForManualLogin(): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log('\n  A browser window is open. Log into CookUnity by hand.');
  console.log('  Nothing here reads or stores your credentials.\n');
  await rl.question('  Press Enter once you are logged in and can see the menu... ');
  rl.close();
}

export function ensureOutputDir(): void {
  fs.mkdirSync(PATHS.output, { recursive: true });
}

export function writeJson(filePath: string, data: unknown): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}
