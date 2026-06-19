import { test, chromium, Browser, BrowserContext, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BASE_URL    = 'http://localhost:5173';
const API_URL     = 'http://127.0.0.1:8000/v1';
const LOGIN_EMAIL = 'superadmin@example.com';
const LOGIN_PASS  = '123456';
const OUTPUT_DIR  = path.join(__dirname, 'output');

// All authenticated routes to screenshot
const ROUTES = [
  { name: '01_dashboard',             path: '/' },
  { name: '02_customers',             path: '/customers' },
  { name: '03_appointments',          path: '/appointments' },
  { name: '04_no_show_blocked',       path: '/no-show-blocked' },
  { name: '05_followups',             path: '/followups' },
  { name: '06_reports',              path: '/reports' },
  { name: '07_retention',            path: '/retention' },
  { name: '08_professionals',        path: '/professionals' },
  { name: '09_services',             path: '/services' },
  { name: '10_staff',                path: '/staff' },
  { name: '11_staff_new',            path: '/staff/new' },
  { name: '12_promotions',           path: '/promotions' },
  { name: '13_promotions_new',       path: '/promotions/new' },
  { name: '14_promotions_simulator', path: '/promotions/simulator' },
  { name: '15_settings',            path: '/settings' },
  { name: '16_tenants',             path: '/tenants' },
  { name: '17_store_products',      path: '/store/products' },
  { name: '18_store_categories',    path: '/store/categories' },
  { name: '19_store_offers',        path: '/store/offers' },
  { name: '20_store_catalog',       path: '/store/catalog' },
  { name: '21_store_orders',        path: '/store/orders' },
  { name: '22_store_carts',         path: '/store/carts' },
  { name: '23_whatsapp_menus',      path: '/whatsapp' },
  { name: '24_whatsapp_config',     path: '/whatsapp/config' },
  { name: '25_whatsapp_triggers',   path: '/whatsapp/triggers' },
  { name: '26_whatsapp_messages',   path: '/whatsapp/messages' },
  { name: '27_whatsapp_workflows',  path: '/whatsapp/workflows' },
  { name: '28_whatsapp_bot',        path: '/whatsapp/bot' },
  { name: '29_ai',                  path: '/ai' },
  { name: '30_ai_appointments',     path: '/ai/appointments' },
  { name: '31_ai_config',           path: '/ai/config' },
  { name: '32_admin_tenant_tracker',path: '/admin/tenant-tracker' },
  { name: '33_admin_cron_jobs',     path: '/admin/cron-jobs' },
];

/** Open a fresh browser + logged-in page; sets tenant in localStorage */
async function createSession(tenant: string): Promise<{ browser: Browser; context: BrowserContext; page: Page; token: string }> {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page    = await context.newPage();

  // Login
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await page.fill('#email', LOGIN_EMAIL);
  await page.fill('#password', LOGIN_PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20000 });
  await page.waitForLoadState('networkidle');

  const token = (await page.evaluate<string | null>(() => localStorage.getItem('auth_token'))) ?? '';

  // Inject the tenant so SelectTenantModal never appears
  await page.evaluate((t) => {
    localStorage.setItem('selected_tenant', t);
    window.dispatchEvent(new CustomEvent('tenant-change', { detail: t }));
  }, tenant);

  return { browser, context, page, token };
}

/** Fetch all tenants from backend */
async function fetchTenants(token: string): Promise<Array<{ tenant: string; category: string }>> {
  const res = await fetch(`${API_URL}/tenants`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to fetch tenants: ${res.status}`);
  return res.json();
}

test('capture screenshots for every tenant', async () => {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  // ── Login page (no tenant needed) ─────────────────────────────────────────
  {
    const loginBrowser = await chromium.launch({ headless: true });
    const loginCtx     = await loginBrowser.newContext({ viewport: { width: 1440, height: 900 } });
    const loginPage    = await loginCtx.newPage();
    const loginDir     = path.join(OUTPUT_DIR, '00_login');
    fs.mkdirSync(loginDir, { recursive: true });
    console.log('\n📸 Capturing login page…');
    await loginPage.goto(`${BASE_URL}/login`);
    await loginPage.waitForLoadState('networkidle');
    await loginPage.screenshot({ path: path.join(loginDir, '00_login.png'), fullPage: true });
    console.log('   saved: 00_login/00_login.png');
    await loginBrowser.close();
  }

  // ── Get tenant list ────────────────────────────────────────────────────────
  // Use a temporary session just to get the token
  const tmpBrowser = await chromium.launch({ headless: true });
  const tmpCtx     = await tmpBrowser.newContext({ viewport: { width: 1440, height: 900 } });
  const tmpPage    = await tmpCtx.newPage();
  await tmpPage.goto(`${BASE_URL}/login`);
  await tmpPage.waitForLoadState('networkidle');
  await tmpPage.fill('#email', LOGIN_EMAIL);
  await tmpPage.fill('#password', LOGIN_PASS);
  await tmpPage.click('button[type="submit"]');
  await tmpPage.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20000 });
  const token = (await tmpPage.evaluate<string | null>(() => localStorage.getItem('auth_token'))) ?? '';
  await tmpBrowser.close();

  const tenants = await fetchTenants(token);
  console.log(`\n📋 Found ${tenants.length} tenants: ${tenants.map(t => t.tenant).join(', ')}`);

  // ── Per-tenant screenshots ─────────────────────────────────────────────────
  for (const { tenant, category } of tenants) {
    const tenantDir = path.join(OUTPUT_DIR, tenant);
    fs.mkdirSync(tenantDir, { recursive: true });
    console.log(`\n🏢 Tenant: ${tenant} (${category})`);

    // Fresh browser session per tenant — avoids accumulated memory/crash issues
    let browser!: Browser;
    let page!: Page;

    try {
      ({ browser, page } = await createSession(tenant));
    } catch (err) {
      console.error(`   ✗ Could not create session for ${tenant}: ${(err as Error).message}`);
      continue;
    }

    for (const route of ROUTES) {
      const filePath = path.join(tenantDir, `${route.name}.png`);

      // Skip if already captured (useful when re-running after a crash)
      if (fs.existsSync(filePath)) {
        console.log(`   ⏭  ${route.name}.png (already exists, skipping)`);
        continue;
      }

      try {
        // Re-inject tenant before each navigation (React re-reads localStorage on mount)
        await page.evaluate((t) => {
          localStorage.setItem('selected_tenant', t);
        }, tenant);

        await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 25000 });

        // Safety net: dismiss tenant modal if it's still showing
        const continueBtn = page.locator('button:has-text("Continue")');
        if (await continueBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
          const sel = page.locator('select').first();
          await sel.selectOption(tenant).catch(() => {});
          await continueBtn.click().catch(() => {});
          await page.waitForTimeout(600);
        }

        await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
        await page.waitForTimeout(1000);

        await page.screenshot({ path: filePath, fullPage: true });
        console.log(`   ✓ ${route.name}.png`);
      } catch (err) {
        const msg = (err as Error).message;
        console.error(`   ✗ ERROR ${route.name}: ${msg}`);

        // If the page/browser crashed, restart the session and continue
        if (msg.includes('closed') || msg.includes('crash') || msg.includes('disconnect')) {
          console.log('   🔄 Browser crashed — restarting session…');
          try { await browser.close(); } catch { /* ignore */ }
          try {
            ({ browser, page } = await createSession(tenant));
            console.log('   ✓ Session restarted');
          } catch (restartErr) {
            console.error(`   ✗ Could not restart session: ${(restartErr as Error).message}`);
            break;
          }
        }
      }
    }

    try { await browser.close(); } catch { /* ignore */ }
    console.log(`   📁 Folder: screenshots/output/${tenant}/`);
  }

  // ── Summary ────────────────────────────────────────────────────────────────
  console.log(`\n✅ Done! Screenshots saved to: ${OUTPUT_DIR}`);
  let total = 0;
  for (const { tenant } of tenants) {
    const dir = path.join(OUTPUT_DIR, tenant);
    const count = fs.existsSync(dir) ? fs.readdirSync(dir).filter(f => f.endsWith('.png')).length : 0;
    console.log(`   ${tenant}: ${count} screenshots`);
    total += count;
  }
  const loginCount = fs.readdirSync(path.join(OUTPUT_DIR, '00_login')).filter(f => f.endsWith('.png')).length;
  console.log(`   00_login: ${loginCount} screenshot`);
  console.log(`   Total: ${total + loginCount} screenshots`);
});
