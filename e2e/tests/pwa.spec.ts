import { expect, test } from "@playwright/test";

test.describe("PWA", () => {
  test("serves web manifest", async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/manifest.webmanifest`);
    expect(response.ok()).toBeTruthy();
    const manifest = await response.json();
    expect(manifest.name || manifest.short_name).toBeTruthy();
    expect(manifest.theme_color || manifest.background_color).toBeTruthy();
  });

  test("registers a service worker after load", async ({ page }) => {
    await page.goto("/");
    // Unauthenticated users still get the SPA shell + SW from the built PWA.
    await page.waitForLoadState("networkidle");

    const swReady = await page.waitForFunction(async () => {
      if (!("serviceWorker" in navigator)) {
        return false;
      }
      const registration = await navigator.serviceWorker.getRegistration();
      return Boolean(registration);
    }, { timeout: 30_000 });

    expect(await swReady.jsonValue()).toBeTruthy();
  });
});
