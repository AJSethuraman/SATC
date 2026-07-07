# Neon Breakout

A tiny, self-contained arcade game — a neon take on the classic brick-breaker.
It's a standalone demo project, deliberately kept separate from the SATC
practice-ops code (no tax logic, no client data, no PII).

## Play it

No build step, no dependencies. Just open the file:

```bash
# option A: double-click game/index.html in a file browser
# option B: serve it (nicer for audio autoplay policies)
cd game && python -m http.server 8000
# then visit http://localhost:8000
```

## Controls

| Action            | Keys                          |
|-------------------|-------------------------------|
| Move paddle       | `←` / `→` or move the mouse   |
| Launch ball       | `Space` or click              |
| Pause / resume    | `Space`                       |
| Touch devices     | drag to move, tap to launch   |

## Features

- **Combo scoring** — chain brick hits within a rally for a rising multiplier.
- **Power-ups** drop from broken bricks:
  - `W` — **W**iden paddle
  - `3` — **multi**-ball
  - `S` — **S**low the ball
  - `+` — extra life
- **Multiple levels** with more rows, tougher bricks, and a slightly smaller
  paddle each round.
- **Juice**: particle bursts, screen shake, glow, and procedural WebAudio
  blips — all generated in code, zero image or sound assets.

## Tech

Everything lives in a single `index.html`: HTML5 `<canvas>`, plain JavaScript
game loop (`requestAnimationFrame`), and the WebAudio API for sound. ~500 lines,
no framework.

## Verify a change

It's a browser game, so verification is: open it and play. A quick headless
sanity check (loads without console errors, starts, and scores) can be run with
Playwright/Chromium against `file://.../game/index.html`.
