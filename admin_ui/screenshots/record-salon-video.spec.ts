/**
 * Records a full walkthrough video of ss_business_salon through every module.
 * Output: screenshots/video/ss_business_salon_walkthrough.webm
 *         (then converted to .mp4 by the npm script using ffmpeg)
 *
 * Run:
 *   PLAYWRIGHT_BROWSERS_PATH=0 npx playwright test screenshots/record-salon-video.spec.ts --timeout=1800000
 */
import { test, chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BASE_URL    = 'http://localhost:5173';
const LOGIN_EMAIL = 'superadmin@example.com';
const LOGIN_PASS  = '123456';
const TENANT      = 'ss_business_salon';
const VIDEO_DIR   = path.join(__dirname, 'video');

// Navigation order mirrors the sidebar: logical top-down flow
const SECTIONS = [
  // ── Core ──────────────────────────────────────────────────────────────────
  {
    section: 'Core',
    pages: [
      { label: 'Dashboard',        path: '/',            dwell: 4000, scroll: true },
      { label: 'Settings',         path: '/settings',    dwell: 3500, scroll: true },
      { label: 'Customers',        path: '/customers',   dwell: 4000, scroll: true },
      { label: 'Staff',            path: '/staff',       dwell: 3500, scroll: true },
      { label: 'Promotions',       path: '/promotions',  dwell: 3500, scroll: true },
      { label: 'Follow-ups',       path: '/followups',   dwell: 3000, scroll: true },
      { label: 'Reports',          path: '/reports',     dwell: 4000, scroll: true },
      { label: 'Retention',        path: '/retention',   dwell: 3500, scroll: true },
    ],
  },
  // ── Salon ──────────────────────────────────────────────────────────────────
  {
    section: 'Salon',
    pages: [
      { label: 'Services',         path: '/services',         dwell: 3500, scroll: true },
      { label: 'Professionals',    path: '/professionals',    dwell: 3500, scroll: true },
      { label: 'Appointments',     path: '/appointments',     dwell: 4000, scroll: true },
      { label: 'No-Show Blocked',  path: '/no-show-blocked',  dwell: 3000, scroll: true },
    ],
  },
  // ── Store ──────────────────────────────────────────────────────────────────
  {
    section: 'Store',
    pages: [
      { label: 'Store — Products',   path: '/store/products',   dwell: 3500, scroll: true },
      { label: 'Store — Categories', path: '/store/categories', dwell: 3000, scroll: true },
      { label: 'Store — Offers',     path: '/store/offers',     dwell: 3000, scroll: true },
      { label: 'Store — Catalog',    path: '/store/catalog',    dwell: 3500, scroll: true },
      { label: 'Store — Orders',     path: '/store/orders',     dwell: 3500, scroll: true },
      { label: 'Store — Carts',      path: '/store/carts',      dwell: 3500, scroll: true },
    ],
  },
  // ── WhatsApp ───────────────────────────────────────────────────────────────
  {
    section: 'WhatsApp',
    pages: [
      { label: 'WhatsApp Menus',     path: '/whatsapp',             dwell: 3500, scroll: true },
      { label: 'WhatsApp Config',    path: '/whatsapp/config',      dwell: 3000, scroll: true },
      { label: 'WhatsApp Triggers',  path: '/whatsapp/triggers',    dwell: 3000, scroll: true },
      { label: 'WhatsApp Messages',  path: '/whatsapp/messages',    dwell: 3000, scroll: true },
      { label: 'WhatsApp Workflows', path: '/whatsapp/workflows',   dwell: 3500, scroll: true },
      { label: 'WhatsApp Bot',       path: '/whatsapp/bot',         dwell: 3000, scroll: true },
    ],
  },
  // ── AI ─────────────────────────────────────────────────────────────────────
  {
    section: 'AI',
    pages: [
      { label: 'AI Hub',             path: '/ai',                dwell: 3500, scroll: true },
      { label: 'AI Appointments',    path: '/ai/appointments',   dwell: 3500, scroll: true },
      { label: 'AI Config',          path: '/ai/config',         dwell: 3000, scroll: true },
    ],
  },
  // ── Super Admin ────────────────────────────────────────────────────────────
  {
    section: 'Admin',
    pages: [
      { label: 'Tenants',           path: '/tenants',                dwell: 3500, scroll: true },
      { label: 'Tenant Tracker',    path: '/admin/tenant-tracker',   dwell: 3500, scroll: true },
      { label: 'Cron Jobs',         path: '/admin/cron-jobs',        dwell: 3000, scroll: true },
    ],
  },
];

/** Smooth scroll to the bottom of the page and back to top */
async function smoothScroll(page: import('@playwright/test').Page, dwell: number) {
  const scrollTime = Math.min(dwell * 0.45, 2500);
  await page.evaluate(async (ms: number) => {
    const totalHeight = document.body.scrollHeight - window.innerHeight;
    if (totalHeight <= 0) return;
    const steps = 30;
    const delay  = ms / steps;
    for (let i = 1; i <= steps; i++) {
      window.scrollTo(0, (totalHeight * i) / steps);
      await new Promise((r) => setTimeout(r, delay));
    }
    await new Promise((r) => setTimeout(r, 400));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, scrollTime);
}

test('record ss_business_salon walkthrough video', async () => {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });

  // ── Launch with video recording enabled ──────────────────────────────────
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: VIDEO_DIR,
      size: { width: 1440, height: 900 },
    },
  });
  const page = await context.newPage();

  // ── 1. Login ─────────────────────────────────────────────────────────────
  console.log('\n🎬 Starting video recording for ss_business_salon…');
  console.log('🔐 Logging in…');
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);  // pause on login screen

  // Type credentials visibly (slower for video effect)
  await page.fill('#email', '');
  for (const char of LOGIN_EMAIL) {
    await page.type('#email', char, { delay: 40 });
  }
  await page.fill('#password', '');
  for (const char of LOGIN_PASS) {
    await page.type('#password', char, { delay: 80 });
  }
  await page.waitForTimeout(800);
  await page.click('button[type="submit"]');

  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20000 });
  await page.waitForLoadState('networkidle');
  console.log('   ✓ Logged in');

  // ── 2. Inject tenant into localStorage ───────────────────────────────────
  await page.evaluate((t) => {
    localStorage.setItem('selected_tenant', t);
    window.dispatchEvent(new CustomEvent('tenant-change', { detail: t }));
  }, TENANT);

  // Navigate to dashboard first so the tenant is picked up
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  // Safety net: dismiss tenant modal if still showing
  const continueBtn = page.locator('button:has-text("Continue")');
  if (await continueBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await page.locator('select').first().selectOption(TENANT).catch(() => {});
    await continueBtn.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
  }

  // ── 3. Walk through every section & page ─────────────────────────────────
  for (const { section, pages } of SECTIONS) {
    console.log(`\n📂 Section: ${section}`);

    for (const { label, path: route, dwell, scroll } of pages) {
      console.log(`   → ${label}`);
      try {
        // Re-inject tenant on each navigation (React re-reads localStorage on mount)
        await page.evaluate((t) => localStorage.setItem('selected_tenant', t), TENANT);

        await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 25000 });
        await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});

        // Pause to let content settle and viewer see the heading
        await page.waitForTimeout(Math.floor(dwell * 0.25));

        // Scroll through content
        if (scroll) {
          await smoothScroll(page, dwell);
        }

        // Remaining dwell time at the top
        await page.waitForTimeout(Math.floor(dwell * 0.30));
      } catch (err) {
        console.error(`   ✗ Error on ${label}: ${(err as Error).message}`);
      }
    }
  }

  // ── 4. End on dashboard ────────────────────────────────────────────────────
  await page.evaluate((t) => localStorage.setItem('selected_tenant', t), TENANT);
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // ── 5. Save video ─────────────────────────────────────────────────────────
  console.log('\n💾 Saving video…');
  await page.close();
  const videoPath = await page.video()?.path();
  await context.close();
  await browser.close();

  // Rename from Playwright's generated UUID name to our friendly name
  if (videoPath && fs.existsSync(videoPath)) {
    const dest = path.join(VIDEO_DIR, `${TENANT}_walkthrough.webm`);
    fs.renameSync(videoPath, dest);
    const sizeMb = (fs.statSync(dest).size / 1024 / 1024).toFixed(1);
    console.log(`✅ Video saved: ${dest} (${sizeMb} MB)`);
    console.log('\nTo convert to MP4, run:');
    console.log(`  ffmpeg -i "${dest}" -c:v libx264 -preset fast -crf 22 "${dest.replace('.webm', '.mp4')}"`);
  } else {
    // Video may have been saved under a generated name; list what's in the dir
    const files = fs.readdirSync(VIDEO_DIR).filter(f => f.endsWith('.webm'));
    if (files.length > 0) {
      const generated = path.join(VIDEO_DIR, files[files.length - 1]);
      const dest = path.join(VIDEO_DIR, `${TENANT}_walkthrough.webm`);
      fs.renameSync(generated, dest);
      const sizeMb = (fs.statSync(dest).size / 1024 / 1024).toFixed(1);
      console.log(`✅ Video saved: ${dest} (${sizeMb} MB)`);
      console.log('\nTo convert to MP4, run:');
      console.log(`  ffmpeg -i "${dest}" -c:v libx264 -preset fast -crf 22 "${dest.replace('.webm', '.mp4')}"`);
    } else {
      console.error('⚠️  Could not locate the recorded video file.');
    }
  }
});
