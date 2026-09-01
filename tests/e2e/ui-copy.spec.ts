import { test, expect } from "@playwright/test";

// SDLCAIP2-7: 上傳頁與處理中頁面文案精簡驗收（e2e）
//
// 應用程式登入前只顯示 #auth-gate（見 smoke.spec.ts），#app-shell 內的上傳頁 /
// 處理中頁面文字要在「已登入」狀態下才會顯示。本專案的登入流程走 Cognito
// Hosted UI（無法在 e2e 直接完成真實 OAuth），但前端 parseJwtEmail() 只是
// base64 解碼 id_token 的 payload、不做簽章驗證，e2e_server.py 也已用
// dependency override 跳過後端的真實 Cognito 驗證 — 因此比照這個既有的
// 測試邊界，於 e2e 直接塞入一個假的 id_token 到 sessionStorage 來繞過登入畫面，
// 藉此驗證「已登入後」實際渲染出來的 DOM 文案，而不是用 skip 佔位。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

test.describe("上傳與處理中頁面文案精簡（SDLCAIP2-7）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-copy-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();
  });

  test("上傳頁顯示精簡後的拖放與隱私文案", async ({ page }) => {
    const uploadView = page.locator("#view-upload");
    await expect(uploadView).toBeVisible();
    await expect(uploadView).toContainText("拖放錄音檔至此，或點擊選取");
    await expect(uploadView).toContainText(
      "本系統不會儲存您的錄音檔，處理完成後可手動清除暫存資料。"
    );
    await expect(uploadView).not.toContainText("不長期");
  });

  test("處理中頁面顯示精簡後的階段文案且不含供應商/模型名稱", async ({ page }) => {
    // 直接切換到處理中頁面（沿用既有 showView()），驗證靜態階段文案，
    // 不必真的跑完整段轉錄流程（該行為已由 pytest 端對 /api/transcribe、
    // /api/status 的進度訊息做過驗證）。
    await page.evaluate(() => (window as any).showView("view-progress"));
    const progressView = page.locator("#view-progress");
    await expect(progressView).toBeVisible();

    await expect(progressView).toContainText("處理中（轉錄 + 發言人同步完成）");
    await expect(progressView).toContainText("摘要與整理");

    const progressHtml = await progressView.innerHTML();
    expect(progressHtml).not.toContain("AssemblyAI");
    expect(progressHtml).not.toContain("GPT-4o");
  });
});
