import { test, expect } from "@playwright/test";

// SDLCAIP2-41: 頁首移除麥克風圖示，點擊標題可回首頁（e2e）
//
// 沿用 history-detail.spec.ts 的登入繞過手法（塞入假 id_token 到
// sessionStorage）。兩個 AC 都是頁首（純前端 DOM/JS）行為，不涉及後端
// API，因此不需要攔截任何請求。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-header-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

test.describe("頁首標題（SDLCAIP2-41）", () => {
  test.beforeEach(async ({ page }) => {
    await loginBypass(page);
  });

  test("AC1: 頁首不再顯示麥克風圖示", async ({ page }) => {
    const header = page.locator("header").first();
    await expect(header).toBeVisible();
    await expect(header.locator("h1")).toHaveText("會議錄音轉紀錄系統");
    // 標題左側（header 內）不應存在任何 svg 元素
    await expect(header.locator("svg")).toHaveCount(0);
  });

  test("AC2: 點擊頁首標題可回到首頁", async ({ page }) => {
    // 先離開首頁，切換到歷史紀錄畫面
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({ status: 200, json: { meetings: [] } });
    });
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();
    await expect(page.locator("#view-upload")).not.toHaveClass(/active/);

    // 點擊頁首標題文字
    await page.locator("header h1").click();

    // 畫面應切換回首頁
    await expect(page.locator("#view-upload")).toHaveClass(/active/);
    await expect(page.locator("#view-upload")).toBeVisible();
  });
});
