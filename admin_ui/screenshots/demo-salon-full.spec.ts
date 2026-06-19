/**
 * FULL FUNCTIONALITY DEMO — ss_business_salon
 * Covers: Login → Dashboard → Customers (CRUD) → Services (CRUD) →
 * Professionals (Add+Required Fields/Schedule) → Appointments (Create/Filter/Cancel) →
 * Staff (Add) → Promotions (Create with Discount) → Store (Categories/Products/Discount/
 * Offers/Orders/Carts/Catalog) → Reports → Retention → Settings →
 * WhatsApp (Config/Triggers/Menus/Workflows/Bot Simulator with full booking flow) → AI
 *
 * Run:
 *   PLAYWRIGHT_BROWSERS_PATH=0 npx playwright test screenshots/demo-salon-full.spec.ts --timeout=3600000
 */
import { test, chromium, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE_URL    = 'http://localhost:5173';
const LOGIN_EMAIL = 'superadmin@example.com';
const LOGIN_PASS  = '123456';
const TENANT      = 'ss_business_salon';
const VIDEO_DIR   = path.join(__dirname, 'video');
const ACTION_TO   = 8000;   // default action timeout for interactions

// ─── Helpers ─────────────────────────────────────────────────────────────────
async function p(page: Page, ms = 1500) { await page.waitForTimeout(ms); }

async function go(page: Page, route: string, waitMs = 2000) {
  await page.evaluate((t) => localStorage.setItem('selected_tenant', t), TENANT);
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(waitMs);
}

async function scroll(page: Page, ms = 2500) {
  await page.evaluate(async (dur: number) => {
    const h = document.body.scrollHeight - window.innerHeight;
    if (h <= 0) return;
    const steps = 25;
    for (let i = 1; i <= steps; i++) {
      window.scrollTo(0, (h * i) / steps);
      await new Promise(r => setTimeout(r, dur / steps));
    }
    await new Promise(r => setTimeout(r, 300));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, ms);
  await page.waitForTimeout(400);
}

async function clickBtn(page: Page, name: string | RegExp, timeout = ACTION_TO) {
  await page.getByRole('button', { name }).first().click({ timeout }).catch(async () => {
    // Fallback: search by text content
    await page.locator(`button:has-text("${name}")`).first().click({ timeout: 3000 }).catch(() => {});
  });
  await page.waitForTimeout(400);
}

/** Fill a labeled TextField. Falls back to placeholder/name searches. */
async function fill(page: Page, label: string, value: string, timeout = ACTION_TO) {
  const el = page.getByLabel(label).first();
  try {
    await el.waitFor({ timeout });
    await el.fill(value);
  } catch {
    await page.locator(`input[placeholder*="${label}" i], textarea[placeholder*="${label}" i]`)
      .first().fill(value).catch(() => {});
  }
  await page.waitForTimeout(200);
}

/** Wait for MUI Dialog to appear */
async function openDialog(page: Page) {
  await page.waitForSelector('.MuiDialog-root', { timeout: 8000 });
  await page.waitForTimeout(600);
  return page.locator('.MuiDialog-root').first();
}

/** Wait for dialog to close */
async function closeDialog(page: Page) {
  await page.waitForSelector('.MuiDialog-root', { state: 'detached', timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(400);
}

/** Click button inside a dialog safely */
async function dlgBtn(page: Page, name: string | RegExp) {
  await page.locator('.MuiDialog-root').getByRole('button', { name }).first()
    .click({ timeout: ACTION_TO }).catch(() => {});
  await page.waitForTimeout(400);
}

async function botSend(page: Page, msg: string, waitMs = 3200) {
  const input = page.locator('input[placeholder*="Type your message"]').first();
  await input.fill(msg).catch(() => {});
  await page.waitForTimeout(300);
  const sendBtn = page.locator('button').filter({ has: page.locator('[data-testid="SendIcon"]') }).first();
  if (await sendBtn.isVisible({ timeout: 1000 }).catch(() => false)) await sendBtn.click().catch(() => {});
  else await page.keyboard.press('Enter').catch(() => {});
  await page.waitForTimeout(waitMs);
}

async function botChip(page: Page, label: string) {
  await page.locator(`.MuiChip-root:has-text("${label}")`).first().click({ timeout: 3000 }).catch(() => {});
  await page.waitForTimeout(3000);
}

function log(msg: string) { console.log(`\n▶  ${msg}`); }

// ─────────────────────────────────────────────────────────────────────────────
test('ss_business_salon — FULL FUNCTIONALITY DEMO', async () => {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  // Set action timeout globally
  page.setDefaultTimeout(ACTION_TO);

  // ══════════════════════════════════════════════════════════════════════════
  // 1. LOGIN
  // ══════════════════════════════════════════════════════════════════════════
  log('LOGIN');
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await p(page, 2000);
  await page.fill('#email', '');
  await page.type('#email', LOGIN_EMAIL, { delay: 40 });
  await p(page, 400);
  await page.fill('#password', '');
  await page.type('#password', LOGIN_PASS, { delay: 100 });
  await p(page, 700);
  await page.click('button[type="submit"]');
  await page.waitForURL(url => !url.pathname.startsWith('/login'), { timeout: 20000 });
  await page.waitForLoadState('networkidle');
  await page.evaluate((t) => {
    localStorage.setItem('selected_tenant', t);
    window.dispatchEvent(new CustomEvent('tenant-change', { detail: t }));
  }, TENANT);
  await go(page, '/', 2000);
  // Dismiss modal
  if (await page.locator('button:has-text("Continue")').isVisible({ timeout: 1500 }).catch(() => false)) {
    await page.locator('select').first().selectOption(TENANT).catch(() => {});
    await page.locator('button:has-text("Continue")').click();
    await page.waitForLoadState('networkidle');
    await p(page, 800);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 2. DASHBOARD
  // ══════════════════════════════════════════════════════════════════════════
  log('DASHBOARD');
  await go(page, '/', 2500);
  await scroll(page, 2500);
  await p(page, 1500);

  // ══════════════════════════════════════════════════════════════════════════
  // 3. CUSTOMERS — Search + Add + Edit + Deactivate
  // ══════════════════════════════════════════════════════════════════════════
  log('CUSTOMERS');
  await go(page, '/customers', 2000);
  await scroll(page, 2000);

  // Search
  const cs = page.locator('input[placeholder*="Search"]').first();
  await cs.fill('Anita').catch(() => {});
  await p(page, 2000);
  await cs.fill('').catch(() => {});
  await p(page, 600);

  // Add customer
  await clickBtn(page, 'Add');
  await openDialog(page).catch(() => {});
  await fill(page, 'Name', 'Priya Demo');
  await fill(page, 'Phone', '9876543210');
  await fill(page, 'Email', 'priya.demo@glamour.com');
  await fill(page, 'Tags (comma separated)', 'vip,new');
  await p(page, 1200);
  await dlgBtn(page, 'Save');
  await closeDialog(page);
  await p(page, 1000);
  log('  ✓ customer added');

  // Edit
  await cs.fill('Priya Demo').catch(() => {});
  await p(page, 1500);
  const editCustBtn = page.getByRole('button', { name: 'Edit' }).first();
  if (await editCustBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await editCustBtn.click();
    await openDialog(page).catch(() => {});
    await fill(page, 'Email', 'priya.updated@glamour.com');
    await fill(page, 'Tags (comma separated)', 'vip,loyal');
    await p(page, 800);
    await dlgBtn(page, 'Save');
    await closeDialog(page);
    log('  ✓ customer edited');
  }

  // Deactivate
  const deactBtn = page.getByRole('button', { name: 'Deactivate' }).first();
  if (await deactBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await deactBtn.click();
    await p(page, 1500);
    await page.getByRole('button', { name: 'Activate' }).first().click({ timeout: 3000 }).catch(() => {});
    await p(page, 1000);
    log('  ✓ customer deactivated & re-activated');
  }
  await cs.fill('').catch(() => {});
  await p(page, 500);

  // ══════════════════════════════════════════════════════════════════════════
  // 4. SERVICES — Add + Edit + Delete
  // ══════════════════════════════════════════════════════════════════════════
  log('SERVICES — Add / Edit / Delete');
  await go(page, '/services', 2000);
  await scroll(page, 2000);

  await clickBtn(page, 'New Service');
  await openDialog(page).catch(() => {});
  await fill(page, 'Service Name', 'Demo Keratin Treatment');
  await fill(page, 'Description', 'Smoothing treatment for frizzy hair');
  await fill(page, 'Base Price', '2500');
  await fill(page, 'Duration (min)', '90');
  await p(page, 1000);
  await dlgBtn(page, 'Save');
  await closeDialog(page);
  await p(page, 1000);
  log('  ✓ service added');

  // Edit last row (first icon button = edit)
  const svcRow = page.locator('tbody tr').last();
  await svcRow.locator('button').first().click({ timeout: 3000 }).catch(() => {});
  if (await page.locator('.MuiDialog-root').isVisible({ timeout: 2000 }).catch(() => false)) {
    await fill(page, 'Base Price', '3000');
    await fill(page, 'Duration (min)', '120');
    await p(page, 800);
    await dlgBtn(page, 'Save');
    await closeDialog(page);
    log('  ✓ service edited');
  }

  // Delete (second icon button = delete)
  await page.locator('tbody tr').last().locator('button').nth(1).click({ timeout: 3000 }).catch(() => {});
  await p(page, 800);
  const confirmBtn = page.getByRole('button', { name: /confirm|ok|yes|delete/i }).first();
  if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await confirmBtn.click();
    await p(page, 1200);
    log('  ✓ service deleted');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 5. PROFESSIONALS — Browse + Add (all required fields) + View Schedule
  // ══════════════════════════════════════════════════════════════════════════
  log('PROFESSIONALS — Browse / Add / Schedule');
  await go(page, '/professionals', 2000);

  // Click first professional
  await page.locator('.MuiListItemButton-root').first().click({ timeout: 3000 }).catch(() => {});
  await p(page, 2000);
  await scroll(page, 2000);
  log('  ✓ professional schedule viewed');

  // Add professional — fill ALL required fields
  await clickBtn(page, 'Add');
  await openDialog(page).catch(() => {});
  await fill(page, 'Name', 'Lalitha Devi');
  await fill(page, 'Employee ID', 'EMP-DEMO-001');   // ← required
  await fill(page, 'Price', '800');
  await fill(page, 'Phone', '9876012345');
  await fill(page, 'Degree / Qualification', 'Diploma in Cosmetology');
  await fill(page, 'Bio / Description', 'Expert in keratin treatments and hair coloring');
  await p(page, 1000);
  await dlgBtn(page, 'Create');
  await closeDialog(page);
  await p(page, 1500);
  log('  ✓ professional added');

  // ══════════════════════════════════════════════════════════════════════════
  // 6. APPOINTMENTS — Browse + Filter + Search + Create form + Cancel
  // ══════════════════════════════════════════════════════════════════════════
  log('APPOINTMENTS — Browse / Filter / Create / Cancel');
  await go(page, '/appointments', 2000);
  await scroll(page, 2000);

  // Search
  const apptSearch = page.locator('input[placeholder*="Search"], input[placeholder*="name" i]').first();
  if (await apptSearch.isVisible({ timeout: 2000 }).catch(() => false)) {
    await apptSearch.fill('Anita');
    await p(page, 1500);
    await apptSearch.fill('');
    await p(page, 500);
  }

  // Create appointment (dialog is informational — shows fields then we close)
  await clickBtn(page, 'New');
  await openDialog(page).catch(() => {});
  await fill(page, 'Customer Name', 'Priya Demo');
  await fill(page, 'Customer Phone', '9876543210');
  // Select date (today)
  const today = new Date().toISOString().split('T')[0];
  await page.locator('.MuiDialog-root').getByLabel('Date').fill(today).catch(() => {});
  await p(page, 800);
  // Select professional from dropdown
  const profDD = page.locator('.MuiDialog-root').getByLabel('Professional').first();
  await profDD.click({ timeout: 4000 }).catch(() => {});
  await p(page, 600);
  const profOpt = page.locator('[role="option"]').first();
  if (await profOpt.isVisible({ timeout: 2000 }).catch(() => false)) {
    await profOpt.click();
    await p(page, 1500);
    // Show available slots
    await scroll(page, 1000);
    await p(page, 1000);
  } else await page.keyboard.press('Escape').catch(() => {});
  // Close dialog without submitting (to keep data clean)
  await dlgBtn(page, 'Close');
  await closeDialog(page);
  log('  ✓ appointment create dialog demonstrated');

  // Cancel appointment via action menu
  await go(page, '/appointments', 1500);
  const moreIcon = page.locator('[data-testid="MoreVertIcon"]').first();
  if (await moreIcon.isVisible({ timeout: 3000 }).catch(() => false)) {
    await moreIcon.click();
    await p(page, 800);
    const cancelOpt = page.locator('[role="menuitem"]:has-text("Cancel")').first();
    if (await cancelOpt.isVisible({ timeout: 2000 }).catch(() => false)) {
      await cancelOpt.click();
      await p(page, 1000);
      const confirmOk = page.getByRole('button', { name: /yes|confirm|ok/i }).first();
      if (await confirmOk.isVisible({ timeout: 2000 }).catch(() => false)) {
        await confirmOk.click();
        await p(page, 1500);
        log('  ✓ appointment cancelled');
      } else await page.keyboard.press('Escape').catch(() => {});
    } else await page.keyboard.press('Escape').catch(() => {});
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 7. NO-SHOW + FOLLOW-UPS
  // ══════════════════════════════════════════════════════════════════════════
  log('NO-SHOW BLOCKED + FOLLOW-UPS');
  await go(page, '/no-show-blocked', 2000);
  await scroll(page, 2000);
  await go(page, '/followups', 2000);
  await scroll(page, 2000);

  // ══════════════════════════════════════════════════════════════════════════
  // 8. STAFF — Browse + Add
  // ══════════════════════════════════════════════════════════════════════════
  log('STAFF — Browse / Add');
  await go(page, '/staff', 2000);
  await scroll(page, 2000);
  await go(page, '/staff/new', 1500);
  await p(page, 600);
  await fill(page, 'Name', 'Demo Stylist');
  await fill(page, 'Role', 'Stylist');
  await fill(page, 'Phone', '9988776600');
  await fill(page, 'Email', 'demo.stylist@glamour.com');
  const skillInput = page.getByLabel(/skill/i).first();
  if (await skillInput.isVisible({ timeout: 1000 }).catch(() => false)) {
    await skillInput.fill('Keratin,Colour');
    await page.getByRole('button', { name: 'Add' }).first().click({ timeout: 3000 }).catch(() => {});
  }
  await p(page, 1200);
  await page.getByRole('button', { name: /create|save/i }).first().click({ timeout: 5000 });
  await page.waitForURL(url => url.pathname === '/staff', { timeout: 10000 }).catch(() => {});
  await p(page, 1500);
  log('  ✓ staff added');

  // ══════════════════════════════════════════════════════════════════════════
  // 9. PROMOTIONS — Browse + Create with Discount
  // ══════════════════════════════════════════════════════════════════════════
  log('PROMOTIONS — Browse / Create with Discount Code');
  await go(page, '/promotions', 2000);
  await scroll(page, 2000);
  await go(page, '/promotions/new', 1500);
  await p(page, 800);
  // Title
  await page.getByLabel('Title').first().fill('Festive Keratin Offer').catch(() =>
    page.locator('input[placeholder*="title" i]').first().fill('Festive Keratin Offer').catch(() => {})
  );
  // Message
  await page.locator('textarea').first().fill(
    '🎉 Special festive offer! Get 20% off on all Keratin treatments. Book now and save big!'
  ).catch(() => {});
  // Offer code
  await page.getByLabel(/offer code/i).first().fill('KERATIN20').catch(() => {});
  await p(page, 1500);
  await scroll(page, 3000);
  await p(page, 1200);
  log('  ✓ promotion with discount code created');

  // Promotion simulator
  await go(page, '/promotions/simulator', 2000);
  await scroll(page, 2000);
  await p(page, 1200);
  log('  ✓ promotion simulator');

  // ══════════════════════════════════════════════════════════════════════════
  // 10. STORE — Categories + Products (with Discount) + Offers + Orders + Carts
  // ══════════════════════════════════════════════════════════════════════════
  log('STORE — Categories / Products / Discount / Offers / Orders / Carts');

  // Categories
  await go(page, '/store/categories', 2000);
  await scroll(page, 1500);
  await clickBtn(page, 'New Category');
  await openDialog(page).catch(() => {});
  await fill(page, 'Name', 'Hair Care Products');
  await p(page, 1000);
  await dlgBtn(page, 'Save');
  await closeDialog(page);
  await p(page, 1000);
  log('  ✓ category added');

  // Products — search, then add with discount
  await go(page, '/store/products', 2000);
  await scroll(page, 1500);
  await page.locator('input[placeholder*="Search"]').first().fill('shampoo').catch(() => {});
  await p(page, 1500);
  await page.locator('input[placeholder*="Search"]').first().fill('').catch(() => {});
  await p(page, 500);

  await clickBtn(page, 'New Product');
  await openDialog(page).catch(() => {});
  await p(page, 600);

  // General tab
  await fill(page, 'Product SKU', 'PRD-KERA-001');
  await fill(page, 'Product Name', 'Keratin Smoothing Shampoo');
  // Category dropdown
  await page.locator('.MuiDialog-root').getByLabel('Category').first().click({ timeout: 4000 }).catch(() => {});
  await p(page, 600);
  const catOpt = page.locator('[role="option"]:has-text("Hair Care")').first();
  if (await catOpt.isVisible({ timeout: 2000 }).catch(() => false)) await catOpt.click();
  else await page.keyboard.press('Escape').catch(() => {});
  await page.getByLabel('Description').first().fill('Professional salon-grade keratin shampoo, sulfate-free').catch(() => {});
  await p(page, 800);

  // Pricing & Inventory tab
  const pricingTab = page.locator('[role="tab"]:has-text("Pricing")');
  if (await pricingTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await pricingTab.click();
    await p(page, 700);
  }
  await fill(page, 'Cost Price (Supplier Price)', '450');
  await fill(page, 'Selling Price', '650');
  await page.getByLabel(/tax %/i).first().fill('18').catch(() => {});
  await fill(page, 'Base Unit', 'bottle');
  await p(page, 600);

  // Discount: Percent 10%
  const discTypeEl = page.getByLabel(/discount type/i).first();
  if (await discTypeEl.isVisible({ timeout: 2000 }).catch(() => false)) {
    await discTypeEl.click();
    await p(page, 500);
    const pctOpt = page.locator('[role="option"]:has-text("Percent")').first();
    if (await pctOpt.isVisible({ timeout: 1500 }).catch(() => false)) await pctOpt.click();
    else await page.keyboard.press('Escape').catch(() => {});
    await p(page, 400);
    await page.getByLabel(/discount value/i).first().fill('10').catch(() => {});
    await p(page, 500);
  }

  await page.getByLabel(/stock/i).first().fill('50').catch(() => {});
  await p(page, 1000);
  await scroll(page, 1500);
  await p(page, 800);
  await page.locator('.MuiDialog-root').getByRole('button', { name: /save|create/i }).first()
    .click({ timeout: ACTION_TO });
  await closeDialog(page);
  log('  ✓ product added with 10% discount');

  // Offers
  await go(page, '/store/offers', 2000);
  await scroll(page, 2000);
  const offerBtn = page.getByRole('button', { name: /new offer|add offer|create offer/i }).first();
  if (await offerBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await offerBtn.click();
    await openDialog(page).catch(() => {});
    await fill(page, 'Name', 'Summer Sale 15%');
    await page.getByLabel(/discount/i).first().fill('15').catch(() => {});
    await p(page, 1000);
    await dlgBtn(page, /save|create/);
    await closeDialog(page);
    log('  ✓ store offer/discount added');
  }

  // Catalog
  await go(page, '/store/catalog', 2000);
  await scroll(page, 2500);
  // Orders
  await go(page, '/store/orders', 2000);
  await scroll(page, 2000);
  // Carts
  await go(page, '/store/carts', 2000);
  await scroll(page, 2000);
  log('  ✓ store catalog / orders / carts viewed');

  // ══════════════════════════════════════════════════════════════════════════
  // 11. REPORTS + RETENTION + SETTINGS
  // ══════════════════════════════════════════════════════════════════════════
  log('REPORTS / RETENTION / SETTINGS');
  await go(page, '/reports', 2000);
  await scroll(page, 3000);
  await go(page, '/retention', 2000);
  await scroll(page, 2500);
  await go(page, '/settings', 2000);
  await scroll(page, 2500);

  // ══════════════════════════════════════════════════════════════════════════
  // 12. WHATSAPP — Config → Triggers → Menus → Workflows → Messages → Bot Simulator
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP');

  // Config
  await go(page, '/whatsapp/config', 2200);
  await scroll(page, 3000);
  await p(page, 1000);

  // Triggers — view, toggle
  await go(page, '/whatsapp/triggers', 2200);
  await scroll(page, 2500);
  await p(page, 800);
  const toggle = page.locator('.MuiSwitch-root').first();
  if (await toggle.isVisible({ timeout: 2000 }).catch(() => false)) {
    await toggle.click();
    await p(page, 1200);
    await toggle.click();   // toggle back
    await p(page, 1000);
    log('  ✓ trigger toggled');
  }

  // Menus
  await go(page, '/whatsapp', 2200);
  await scroll(page, 2500);
  await p(page, 800);

  // Workflows
  await go(page, '/whatsapp/workflows', 2200);
  await scroll(page, 2500);
  await p(page, 800);

  // Message Templates
  await go(page, '/whatsapp/messages', 2200);
  await scroll(page, 3000);
  await p(page, 800);
  // Expand first template section
  const accordion = page.locator('.MuiAccordion-root').first();
  if (await accordion.isVisible({ timeout: 2000 }).catch(() => false)) {
    await accordion.click();
    await p(page, 1500);
    await scroll(page, 2000);
    await p(page, 1000);
    log('  ✓ message template expanded');
  }

  // Bot Simulator — Full Booking Flow
  log('  BOT SIMULATOR — Booking Flow');
  await go(page, '/whatsapp/bot', 2500);
  await p(page, 1000);

  await botChip(page, 'Menu');        // → Main menu
  await botSend(page, '1', 3500);     // → Book appointment
  await botSend(page, '1', 3500);     // → Select professional / option
  await botSend(page, '1', 3500);     // → Select date
  await botSend(page, '1', 3500);     // → Select time slot
  await botSend(page, 'Priya Sharma', 3000); // → Customer name
  await botSend(page, '9876543210', 3500);   // → Phone → triggers booking
  await botSend(page, '1', 4000);     // → Confirm

  await p(page, 1500);
  await scroll(page, 2500);
  await p(page, 1000);

  // Services
  await botChip(page, 'Menu');
  await botSend(page, '2', 3000);     // Services

  // Location
  await botChip(page, 'Menu');
  await botSend(page, '3', 3000);     // Location

  // Cancel
  await botSend(page, 'cancel', 3000);
  await p(page, 1000);

  // Hi trigger
  await botSend(page, 'hi', 3000);
  await p(page, 1000);

  await scroll(page, 2500);
  await p(page, 1500);
  log('  ✓ WhatsApp bot simulator — full booking & cancel flow');

  // ══════════════════════════════════════════════════════════════════════════
  // 13. AI HUB
  // ══════════════════════════════════════════════════════════════════════════
  log('AI HUB');
  await go(page, '/ai', 2000);
  await scroll(page, 2000);
  await go(page, '/ai/appointments', 2000);
  await scroll(page, 2000);
  await go(page, '/ai/config', 2000);
  await scroll(page, 2000);

  // ══════════════════════════════════════════════════════════════════════════
  // 14. ADMIN
  // ══════════════════════════════════════════════════════════════════════════
  log('ADMIN — Tenants / Tracker / Cron Jobs');
  await go(page, '/tenants', 2000);
  await scroll(page, 2500);
  await go(page, '/admin/tenant-tracker', 2000);
  await scroll(page, 2500);
  await go(page, '/admin/cron-jobs', 2000);
  await scroll(page, 2000);

  // ══════════════════════════════════════════════════════════════════════════
  // FINALE — Dashboard
  // ══════════════════════════════════════════════════════════════════════════
  log('FINALE');
  await go(page, '/', 3000);
  await p(page, 2000);

  // ── Save ──────────────────────────────────────────────────────────────────
  console.log('\n💾 Saving video…');
  await page.close();
  const videoPath = await page.video()?.path();
  await context.close();
  await browser.close();

  const webmDest = path.join(VIDEO_DIR, `${TENANT}_FULL_DEMO.webm`);
  const candidates = fs.readdirSync(VIDEO_DIR)
    .filter(f => f.endsWith('.webm') && !f.includes('FULL_DEMO') && !f.includes('WHATSAPP'))
    .map(f => path.join(VIDEO_DIR, f))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);

  const src = (videoPath && fs.existsSync(videoPath)) ? videoPath : candidates[0];
  if (src) {
    fs.renameSync(src, webmDest);
    const sz = (fs.statSync(webmDest).size / 1024 / 1024).toFixed(1);
    console.log(`✅ WebM saved: ${webmDest} (${sz} MB)`);
  } else {
    console.error('⚠️  Could not locate recorded video.');
  }
});
