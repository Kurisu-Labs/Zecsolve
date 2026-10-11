# zecsolve web

Vue 3 + TypeScript + Tailwind v4 frontend for the merchant case workflow: a scroll-driven landing page, the merchant case list and case view, the customer receipt link, and the printable reviewer report.

## Run

Use Node.js 24 or newer. `npm test` runs the workflow-contract regressions; CI also checks the production build.

```sh
cd apps/web
npm ci
npm run dev        # http://localhost:5173, proxies /api and /health to FastAPI on :8000
npm run build      # vue-tsc + vite build → dist/
```

With no credential the app runs on **demo data**: the real historical mainnet receipt from `fixtures/manifest.json` (Orchard output #1, 100,000 zat) replayed against synthetic invoices. Demo findings come from `src/api/rules.ts`, a TypeScript port of `domain/rules.py` (rules 0.1.0). Open **Connect** in the header and paste a merchant credential from `python -m zecsolve.auth.cli issue-credential` to switch to the live API.

`npm run types:api` regenerates `src/api/openapi.d.ts` from the running API; `src/api/types.ts` is a hand-written subset until the workflow contract is frozen.

## Map

| Path | What it holds |
|---|---|
| `src/styles/main.css` | Tokens (`@theme static`): colours sampled from the logo, type scale, motion durations and easings |
| `src/api/` | Client, demo fixtures, rules port, and `store.ts`, the one interface both modes use |
| `src/lib/status.ts` | Enum → label, tone and glyph. Unavailable data is never shown as tampering |
| `src/lib/money.ts` | Integer zatoshi formatting and exact decimal parsing. No floats |
| `src/gl/pixelField.ts` | Landing WebGL scene (Three.js points, Bayer dither), lazy chunk |
| `src/motion/` | GSAP ScrollTrigger + Lenis (landing only), decrypt text, reduced-motion switch |
| `src/pages/` | Landing, How it works, Cases, Case detail, Customer submit, Report, Connect |

## Design rules

- Four layers stay separate on every screen: customer claim, receipt, chain observation, merchant decision.
- Yellow `#FEFB30` means disclosed or approved, and is the only accent. Never use it as text on light backgrounds.
- Motion is productive (≤ 240 ms) in the app and expressive only on the landing hero. `prefers-reduced-motion` or the footer switch replaces the WebGL scene with a static poster.
- Avoid TypeScript casts inside templates; keep them in `<script setup>`.

## Not done yet

- FastAPI does not serve `dist/` yet (the implementation plan calls for same-origin hosting).
- The API has no `GET /api/cases` list route, so live mode lists only cases opened in this browser.
- Live submission and report pages are merchant-only previews, not customer/reviewer grants. Do not share a merchant credential to enable those links. Scoped access remains backend work.
- Report JSON is a merchant snapshot, not the complete replayable export packet.
- Live approval submits a request for fresh server-side evaluation; offline report balances never establish approval eligibility.
