import { chromium } from 'playwright';
import { mkdir } from 'fs/promises';

const out = process.env.OUT_DIR;
await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
await page.goto('http://localhost:5173/r/demo', { waitUntil: 'networkidle' });
await page.screenshot({ path: `${out}/publico-reserva.png`, fullPage: true });
await page.goto('http://localhost:5173/admin/login', { waitUntil: 'networkidle' });
await page.fill('input[type="password"]', 'admin');
await page.click('button[type="submit"]');
await page.waitForURL('**/admin/reservas');
await page.setViewportSize({ width: 1280, height: 800 });
await page.screenshot({ path: `${out}/panel-reservas.png`, fullPage: true });
await page.goto('http://localhost:5173/admin/configuracion', { waitUntil: 'networkidle' });
await page.screenshot({ path: `${out}/panel-config.png`, fullPage: true });
await browser.close();
