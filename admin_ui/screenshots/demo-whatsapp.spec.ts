/**
 * WHATSAPP DEEP-DIVE DEMO — ss_business_salon
 * Covers: Config → Triggers (view/toggle/edit) → Menus (view/create) →
 * Menu Editor → Menu Wizard → Workflows (view/create with steps) →
 * Message Templates (expand/edit) →
 * Bot Simulator (full booking flow + services + location + cancel + hi trigger)
 *
 * Run:
 *   PLAYWRIGHT_BROWSERS_PATH=0 npx playwright test screenshots/demo-whatsapp.spec.ts --timeout=3600000
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
const T           = 6000;   // default element timeout

// ─── Helpers ─────────────────────────────────────────────────────────────────
async function p(page: Page, ms = 1500) { await page.waitForTimeout(ms); }

async function go(page: Page, route: string, waitMs = 2200) {
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

/** Safe click — swallows errors */
async function clk(page: Page, locator: import('@playwright/test').Locator) {
  await locator.click({ timeout: T }).catch(() => {});
  await page.waitForTimeout(400);
}

/** Wait for MUI dialog to open */
async function openDlg(page: Page) {
  await page.waitForSelector('.MuiDialog-root', { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(600);
}

/** Wait for dialog to close */
async function closeDlg(page: Page) {
  await page.waitForSelector('.MuiDialog-root', { state: 'detached', timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(400);
}

/** Bot send — type and send a message, wait for bot reply */
async function botSend(page: Page, msg: string, waitMs = 3500) {
  await page.locator('input[placeholder*="Type your message"]').first().fill(msg).catch(() => {});
  await page.waitForTimeout(300);
  const sendBtn = page.locator('button').filter({ has: page.locator('[data-testid="SendIcon"]') }).first();
  if (await sendBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await sendBtn.click().catch(() => {});
  } else {
    await page.keyboard.press('Enter').catch(() => {});
  }
  await page.waitForTimeout(waitMs);
}

/** Click a quick-action chip */
async function botChip(page: Page, label: string) {
  await page.locator(`.MuiChip-root:has-text("${label}")`).first().click({ timeout: 3000 }).catch(() => {});
  await page.waitForTimeout(3500);
}

function log(msg: string) { console.log(`\n▶  ${msg}`); }

// ─────────────────────────────────────────────────────────────────────────────
test('ss_business_salon — WHATSAPP DEEP-DIVE DEMO', async () => {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(T);

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
  await page.click('button[type="submit"]', { timeout: 5000 });
  await page.waitForURL(url => !url.pathname.startsWith('/login'), { timeout: 20000 });
  await page.waitForLoadState('networkidle');
  await page.evaluate((t) => {
    localStorage.setItem('selected_tenant', t);
    window.dispatchEvent(new CustomEvent('tenant-change', { detail: t }));
  }, TENANT);
  await go(page, '/', 1800);
  if (await page.locator('button:has-text("Continue")').isVisible({ timeout: 1500 }).catch(() => false)) {
    await page.locator('select').first().selectOption(TENANT).catch(() => {});
    await page.locator('button:has-text("Continue")').click({ timeout: 3000 });
    await page.waitForLoadState('networkidle');
    await p(page, 800);
  }
  log('  ✓ Logged in → ss_business_salon selected');

  // ══════════════════════════════════════════════════════════════════════════
  // 2. WHATSAPP CONFIG — Provider, From Numbers, Webhook URL
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP — CONFIG');
  await go(page, '/whatsapp/config', 2500);
  await scroll(page, 3000);
  await p(page, 1500);
  // Show webhook simulator area
  const testBody = page.getByLabel(/body/i).first();
  if (await testBody.isVisible({ timeout: 2000 }).catch(() => false)) {
    await testBody.fill('hi').catch(() => {});
    await p(page, 1200);
  }
  await scroll(page, 2000);
  await p(page, 1500);
  log('  ✓ WhatsApp Config — provider, numbers, webhook URL');

  // ══════════════════════════════════════════════════════════════════════════
  // 3. TRIGGERS — Browse + Toggle Enable/Disable + Edit
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP — TRIGGERS');
  await go(page, '/whatsapp/triggers', 2500);
  await scroll(page, 3000);
  await p(page, 1000);

  // Toggle first trigger off then on to demonstrate
  const sw1 = page.locator('.MuiSwitch-root').first();
  if (await sw1.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, sw1);
    await p(page, 1500);
    await clk(page, sw1);  // re-enable
    await p(page, 1200);
    log('  ✓ trigger toggled enabled ↔ disabled');
  }

  // Open first trigger for editing
  const editTrigger = page.locator('[data-testid="EditIcon"]').first();
  if (await editTrigger.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, editTrigger);
    await page.waitForLoadState('networkidle').catch(() => {});
    await p(page, 2000);
    await scroll(page, 2500);
    await p(page, 1500);
    log('  ✓ trigger edit page viewed');
    await page.goBack();
    await page.waitForLoadState('networkidle').catch(() => {});
    await p(page, 1500);
  }

  // Scroll to webhook test panel
  await scroll(page, 2000);
  await p(page, 1500);

  // ══════════════════════════════════════════════════════════════════════════
  // 4. MENUS — Browse + Create + Open Editor
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP — MENUS');
  await go(page, '/whatsapp', 2500);
  await scroll(page, 2500);
  await p(page, 1000);

  // Create a new menu
  const createMenuBtn = page.getByRole('button', { name: /new menu|create menu|add/i }).first();
  if (await createMenuBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, createMenuBtn);
    await openDlg(page);
    // Fill menu ID (first input) and name (second input)
    const dlgInputs = page.locator('.MuiDialog-root input');
    await dlgInputs.nth(0).fill('demo_menu').catch(() => {});
    await dlgInputs.nth(1).fill('Demo Menu').catch(() => {});
    await p(page, 1000);
    await clk(page, page.locator('.MuiDialog-root').getByRole('button', { name: /create|save|ok/i }).first());
    await closeDlg(page);
    await p(page, 1500);
    log('  ✓ new menu created');
  }

  // View the published menu (click Edit/Open on first row)
  const menuEditBtn = page.locator('tbody tr').first().locator('button').first();
  if (await menuEditBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, menuEditBtn);
    await page.waitForLoadState('networkidle').catch(() => {});
    await p(page, 2500);
    await scroll(page, 3000);
    await p(page, 1500);
    log('  ✓ Menu Editor opened — showing menu tree and options');
    await page.goBack();
    await page.waitForLoadState('networkidle').catch(() => {});
    await p(page, 1500);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 5. MENU WIZARD
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP — MENU WIZARD');
  await go(page, '/whatsapp/wizard', 2500);
  await scroll(page, 3000);
  await p(page, 1500);
  log('  ✓ Menu Wizard shown — guided setup');

  // ══════════════════════════════════════════════════════════════════════════
  // 6. WORKFLOWS — Browse + Expand + Create New with Steps
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP — WORKFLOWS');
  await go(page, '/whatsapp/workflows', 2500);
  await scroll(page, 2500);
  await p(page, 1000);

  // Expand first workflow row to show steps
  const firstWfRow = page.locator('tbody tr').first().locator('button').first();
  if (await firstWfRow.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, firstWfRow);
    await p(page, 1500);
    await scroll(page, 2000);
    await p(page, 1200);
    log('  ✓ workflow steps expanded');
  }

  // Create a new workflow
  const newWfBtn = page.getByRole('button', { name: 'New Workflow' }).first();
  if (await newWfBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, newWfBtn);
    await openDlg(page);
    // Fill "Workflow ID" and "Display Name" (exact labels from WorkflowManager.tsx)
    await page.locator('.MuiDialog-root').getByLabel('Workflow ID').fill('demo_booking_flow').catch(() => {});
    await page.locator('.MuiDialog-root').getByLabel('Display Name').fill('Demo Booking Flow').catch(() => {});
    await p(page, 800);

    // Add a step
    const addStepBtn = page.locator('.MuiDialog-root').getByRole('button', { name: /add step/i }).first();
    if (await addStepBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await clk(page, addStepBtn);
      await p(page, 1200);
      log('  ✓ workflow step added');
    }
    await scroll(page, 1500);
    await p(page, 1000);

    // Close without saving (Cancel button exact label from code: "Cancel")
    await clk(page, page.locator('.MuiDialog-root').getByRole('button', { name: 'Cancel' }).first());
    await closeDlg(page);
    log('  ✓ workflow create form demonstrated');
  }

  // Edit existing salon_booking_flow
  const editWfBtn = page.locator('[aria-label="Edit"]').first();
  if (await editWfBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, editWfBtn);
    await openDlg(page);
    await scroll(page, 2000);
    await p(page, 2000);
    log('  ✓ salon_booking_flow — 8 steps shown');
    await clk(page, page.locator('.MuiDialog-root').getByRole('button', { name: 'Cancel' }).first());
    await closeDlg(page);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 7. MESSAGE TEMPLATES
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP — MESSAGE TEMPLATES');
  await go(page, '/whatsapp/messages', 2500);
  await scroll(page, 3000);
  await p(page, 1000);

  // Expand first accordion
  const acc1 = page.locator('.MuiAccordion-root').first();
  if (await acc1.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, acc1.locator('.MuiAccordionSummary-root').first());
    await p(page, 1500);
    await scroll(page, 2000);
    await p(page, 1000);
    log('  ✓ template section expanded');

    // Click edit icon on a template
    const editIcon = page.locator('[data-testid="EditOutlinedIcon"]').first();
    if (await editIcon.isVisible({ timeout: 2000 }).catch(() => false)) {
      await clk(page, editIcon);
      await openDlg(page);
      await p(page, 1500);
      await scroll(page, 1500);
      await p(page, 1200);
      // Close dialog
      await clk(page, page.locator('.MuiDialog-root button').filter({ hasText: /cancel|close/i }).first());
      await closeDlg(page);
      log('  ✓ template edit dialog shown');
    }
  }

  // Expand second accordion
  const acc2 = page.locator('.MuiAccordion-root').nth(1);
  if (await acc2.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clk(page, acc2.locator('.MuiAccordionSummary-root').first());
    await p(page, 1500);
    await scroll(page, 2000);
    await p(page, 1000);
    log('  ✓ second template section expanded');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 8. BOT SIMULATOR — Full Interactive Booking Flow
  // ══════════════════════════════════════════════════════════════════════════
  log('WHATSAPP BOT SIMULATOR — Full Booking Flow Demo');
  await go(page, '/whatsapp/bot', 2500);
  await p(page, 1500);
  await scroll(page, 1000);
  await p(page, 1000);

  // ─── Main Menu ─────────────────────────────────────────────────────────
  log('  → Main Menu');
  await botChip(page, 'Menu');
  await p(page, 1000);

  // ─── Book Appointment Flow (option 1) ──────────────────────────────────
  log('  → Booking appointment flow (1)');
  await botSend(page, '1', 3500);

  log('  → Select professional (1)');
  await botSend(page, '1', 3500);

  log('  → Select date (1)');
  await botSend(page, '1', 3500);

  log('  → Select time (1)');
  await botSend(page, '1', 3500);

  log('  → Customer name');
  await botSend(page, 'Priya Sharma', 3200);

  log('  → Customer phone');
  await botSend(page, '9876543210', 3500);

  log('  → Confirm booking (1)');
  await botSend(page, '1', 4000);

  await p(page, 1500);
  await scroll(page, 2000);
  await p(page, 1500);
  log('  ✓ Appointment booked via WhatsApp bot!');

  // ─── Services Menu (option 2) ────────────────────────────────────────
  log('  → Services & Prices (menu → 2)');
  await botChip(page, 'Menu');
  await botSend(page, '2', 3500);
  await scroll(page, 1500);
  await p(page, 1000);

  // ─── Location (option 3) ─────────────────────────────────────────────
  log('  → Location & Hours (menu → 3)');
  await botChip(page, 'Menu');
  await botSend(page, '3', 3200);
  await p(page, 1000);

  // ─── Cancel/Reschedule (option 4) ────────────────────────────────────
  log('  → Cancel/Reschedule (menu → 4)');
  await botChip(page, 'Menu');
  await botSend(page, '4', 3000);
  await p(page, 1000);

  // ─── Cancel keyword ──────────────────────────────────────────────────
  log('  → "cancel" keyword trigger');
  await botSend(page, 'cancel', 3200);
  await p(page, 1000);

  // ─── Hello trigger ───────────────────────────────────────────────────
  log('  → "hello" trigger');
  await botSend(page, 'hello', 3200);
  await p(page, 1000);

  // ─── Quick action chips ───────────────────────────────────────────────
  log('  → Quick chip: salon booking flow');
  const salonChip = page.locator('.MuiChip-root').filter({ hasText: /book|salon/i }).first();
  if (await salonChip.isVisible({ timeout: 2000 }).catch(() => false)) {
    await salonChip.click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(4000);
    await p(page, 1000);
    log('  ✓ Quick chip booking flow triggered');
  }

  await scroll(page, 3000);
  await p(page, 2000);
  log('  ✓ Bot Simulator demo complete — full conversation shown');

  // ══════════════════════════════════════════════════════════════════════════
  // FINALE — Back to WhatsApp Menus
  // ══════════════════════════════════════════════════════════════════════════
  log('FINALE — WhatsApp overview');
  await go(page, '/whatsapp', 2500);
  await scroll(page, 2000);
  await p(page, 2000);

  // ── Save ──────────────────────────────────────────────────────────────────
  console.log('\n💾 Saving WhatsApp demo video…');
  await page.close();
  const videoPath = await page.video()?.path();
  await context.close();
  await browser.close();

  const webmDest = path.join(VIDEO_DIR, `${TENANT}_WHATSAPP_DEMO.webm`);
  const candidates = fs.readdirSync(VIDEO_DIR)
    .filter(f => f.endsWith('.webm') && !f.includes('WHATSAPP_DEMO') && !f.includes('FULL_DEMO') && !f.includes('walkthrough'))
    .map(f => path.join(VIDEO_DIR, f))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);

  const src = (videoPath && fs.existsSync(videoPath)) ? videoPath : candidates[0];
  if (src) {
    fs.renameSync(src, webmDest);
    const sz = (fs.statSync(webmDest).size / 1024 / 1024).toFixed(1);
    console.log(`✅ WebM: ${webmDest} (${sz} MB)`);
  } else {
    console.error('⚠️  Could not locate video.');
  }
});
