import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './screenshots',
  use: {
    viewport: { width: 1440, height: 900 },
    headless: true,
    locale: 'en-US',
    ignoreHTTPSErrors: true,
  },
  timeout: 1800000,   // 30 minutes — covers all 7 tenants × 33 routes
  workers: 1,
  reporter: [['list']],
});
