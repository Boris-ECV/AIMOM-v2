import { test, expect } from "@playwright/test";

const BACKEND_URL = "http://127.0.0.1:8000";

test.describe("smoke", () => {
  test("前端首頁可載入（未登入畫面）", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle("會議錄音轉紀錄系統");

    const authGate = page.locator("#auth-gate");
    await expect(authGate).toBeVisible();
    // SDLCAIP2-62 AC1: 登入頁文案簡化 — 標題簡化為「會議錄音轉紀錄系統」，
    // 不再顯示「請先登入才能使用」這行文字（刻意移除，非回歸）。
    await expect(authGate).toContainText("會議錄音轉紀錄系統");
    await expect(authGate).not.toContainText("請先登入才能使用");
  });

  test("後端健康檢查端點回應成功", async ({ request }) => {
    const res = await request.get(`${BACKEND_URL}/api/health`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});
