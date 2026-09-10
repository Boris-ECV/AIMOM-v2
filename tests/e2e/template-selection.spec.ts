import { test, expect } from "@playwright/test";

// SDLCAIP2-15: 前端會議模板選擇 UI 與重新產生流程（e2e）
//
// 沿用 ui-copy.spec.ts 既有的登入繞過手法（塞入假 id_token 到
// sessionStorage）。/api/summarize 呼叫的是 config.js 內寫死的遠端
// AWS API base URL（非本機 e2e_server），且該端點需要真實 LLM 供應商
// 憑證才能成功回應，不適合在 e2e 環境呼叫真實服務；改用 Playwright
// page.route 攔截該請求，驗證的是「前端收到 SummarizeResponse 之後
// 的實際處理行為」（整包覆蓋 state.minutes、confirm() 取消/確認閘門），
// 這正是本故事新增、目前完全沒有涵蓋的前端邏輯，而不是重新驗證後端
// /api/summarize 本身（該端點行為已由 src/tests/test_summarize.py 用
// mock LLM client 涵蓋）。
//
// index.html 的 <script> 是傳統（非 module）內嵌腳本：`function xxx(){}`
// 宣告會成為 window 的屬性，但頂層 `const state = {...}` 只存在於該
// script 的全域詞法環境，不是 window/globalThis 的可列舉屬性。
// page.evaluate() 注入的程式碼與頁面共用同一個 realm，因此用
// `(0, eval)("state")` 走一次間接 eval（在全域作用域求值）就能取得同一個
// 綁定；直接寫裸 `state` 在 TypeScript 編譯／lint 下會被當成未宣告變數，
// 用 eval 字串規避這個問題。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const INITIAL_MINUTES = {
  job_id: "e2e-job-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

const REGENERATED_MINUTES = {
  job_id: "e2e-job-1",
  template: "retro",
  meeting_info: { date: "", time: "", location: "", participants: [] },
  summary: "重新產生的摘要",
  action_items: [],
  decisions: [],
  sections: [
    { title: "Keep", content: "維持每週同步會議" },
    { title: "Problem", content: "需求變動頻繁" },
    { title: "Try", content: "導入自動化測試" },
  ],
};

test.describe("模板選擇與重新產生（SDLCAIP2-15）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-template-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    // 直接注入既有結果資料並切換到結果畫面，繞過完整上傳/轉錄/首次
    // 摘要流程（該流程已由其他測試涵蓋），聚焦驗證本故事新增的行為。
    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = minutes.job_id;
      s.minutes = minutes;
      s.modified = false;
      (0, eval)("renderMinutes")();
      (0, eval)("showView")("view-result");
    }, INITIAL_MINUTES);
    await expect(page.locator("#view-result")).toBeVisible();
  });

  test("模板下拉選單列出 5 個內建模板，初始選中值來自 minutes.template", async ({ page }) => {
    const select = page.locator("#template-select");
    const optionValues = await select.locator("option").allTextContents();
    expect(optionValues).toEqual(["一般會議", "專案進度會議", "客戶業務會議", "腦力激盪", "Retro"]);
    await expect(select).toHaveValue("general");
  });

  test("AC1: 選擇新模板並點擊重新產生，整包覆蓋 state.minutes（非僅 sections）", async ({ page }) => {
    let requestBody: any = null;
    await page.route("**/api/summarize", async (route) => {
      requestBody = route.request().postDataJSON();
      await route.fulfill({ status: 200, json: REGENERATED_MINUTES });
    });

    await page.locator("#template-select").selectOption("retro");
    await page.locator("#regenerate-btn").click();

    await expect(page.locator("#view-result")).toContainText("重新產生的摘要");

    expect(requestBody).toEqual({ job_id: "e2e-job-1", template: "retro" });

    const minutesAfter = await page.evaluate(() => (0, eval)("state").minutes);
    expect(minutesAfter).toEqual(REGENERATED_MINUTES);
    // 舊資料（原始摘要/決議/section）完全被取代，而非合併殘留
    expect(minutesAfter.decisions).toEqual([]);
    expect(minutesAfter.sections.map((sec: any) => sec.title)).toEqual(["Keep", "Problem", "Try"]);

    const modified = await page.evaluate(() => (0, eval)("state").modified);
    expect(modified).toBe(false);
  });

  test("edge case: state.modified=true 時取消 confirm() 對話框，不送出請求、minutes 不變", async ({ page }) => {
    let requestCalled = false;
    await page.route("**/api/summarize", async (route) => {
      requestCalled = true;
      await route.fulfill({ status: 200, json: REGENERATED_MINUTES });
    });

    await page.evaluate(() => (0, eval)("markModified")());
    await expect(page.locator("#modified-badge")).toBeVisible();

    page.once("dialog", (dialog) => dialog.dismiss());
    await page.locator("#template-select").selectOption("retro");
    await page.locator("#regenerate-btn").click();
    // 給事件迴圈時間讓 dialog 處理完成（若真的會送出請求）
    await page.waitForTimeout(300);

    expect(requestCalled).toBe(false);
    const minutesAfter = await page.evaluate(() => (0, eval)("state").minutes);
    expect(minutesAfter).toEqual(INITIAL_MINUTES);
    await expect(page.locator("#view-result")).toContainText("原始摘要");
  });

  test("edge case: state.modified=true 時確認 confirm() 對話框，照常送出請求並覆蓋 minutes", async ({ page }) => {
    await page.route("**/api/summarize", async (route) => {
      await route.fulfill({ status: 200, json: REGENERATED_MINUTES });
    });

    await page.evaluate(() => (0, eval)("markModified")());
    page.once("dialog", (dialog) => dialog.accept());
    await page.locator("#template-select").selectOption("retro");
    await page.locator("#regenerate-btn").click();

    await expect(page.locator("#view-result")).toContainText("重新產生的摘要");
    const minutesAfter = await page.evaluate(() => (0, eval)("state").minutes);
    expect(minutesAfter).toEqual(REGENERATED_MINUTES);
  });
});
