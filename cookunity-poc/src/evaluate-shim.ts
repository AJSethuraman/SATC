import type { Page } from 'playwright';

/**
 * TypeScript runners built on esbuild (tsx, ts-node/swc) compile named function
 * expressions into `__name(fn, "fn")` calls to preserve `Function.name`. That
 * helper is defined in the Node module scope, not in the browser, so any
 * `page.evaluate` callback containing a named function throws
 * "__name is not defined" once it is serialised into the page.
 *
 * Defining a no-op `__name` in the page fixes it. The shim is passed as a
 * string so the runner cannot rewrite the shim itself.
 */
export async function installEvaluateShim(page: Page): Promise<void> {
  await page.evaluate('globalThis.__name = globalThis.__name || ((fn) => fn)');
}
