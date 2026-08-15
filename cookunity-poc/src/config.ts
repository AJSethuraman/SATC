import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(here, '..');

export const PATHS = {
  storageState: path.join(ROOT, 'storage-state.json'),
  output: path.join(ROOT, 'output'),
  meals: path.join(ROOT, 'output', 'meals.json'),
  discovery: path.join(ROOT, 'output', 'discovery.json'),
  har: path.join(ROOT, 'output', 'session.har'),
};

export const SITE = {
  baseUrl: 'https://www.cookunity.com',
  /**
   * Pages to visit while listening for meal API traffic. The first that renders
   * a menu wins; the rest are tried only if it yields nothing.
   */
  menuPaths: ['/our-menu', '/menu', '/meals', '/'],
  /**
   * Hosts whose JSON responses are worth inspecting. Third-party analytics and
   * tag managers are noise, so they are filtered out before scoring.
   */
  ignoreHostPattern:
    /(google|googletagmanager|doubleclick|facebook|segment|sentry|datadog|hotjar|optimizely|intercom|amplitude|mixpanel|cloudflareinsights|newrelic)\./i,
};

/** Milliseconds to wait for the menu to settle after navigation. */
export const SETTLE_MS = 4000;
