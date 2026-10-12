import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/browser',
  timeout: 60_000,
  workers: 1,
  fullyParallel: false,
  reporter: 'list',
  outputDir: './artifacts/browser',
  use: {
    baseURL: process.env.ZECSOLVE_BROWSER_URL ?? 'https://localhost:8443',
    ignoreHTTPSErrors: true,
    channel: process.env.ZECSOLVE_BROWSER_CHANNEL ?? 'chrome',
    // Traces can retain access codes and original evidence; keep them disabled.
    trace: 'off',
    screenshot: 'off',
    viewport: { width: 1280, height: 900 },
  },
})
