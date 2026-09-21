import { test, expect } from "@playwright/test";

// SDLCAIP2-40: 會議紀錄結果頁操作區塊應回復至 SDLCAIP2-39 合併前的呈現方式
//
// SDLCAIP2-39 (commit 9b9d4e4) 曾為 #view-result 操作列外層容器與子分組加上
// flex-wrap:nowrap / overflow-x:auto，並移除三顆按鈕的 emoji 前綴。
// SDLCAIP2-40 以 git revert 撤銷該 commit。本檔驗證撤銷後的實際渲染結果
// 符合回復前（pre-SDLCAIP2-39）的呈現方式。
//
// 沿用 template-select-style.spec.ts / export-format-menu-styling.spec.ts
// 既有的登入繞過與注入結果資料手法，切換到結果畫面後驗證：
// AC1 - .btn-row 外層容器 inline style 不含 nowrap/overflow-x:auto，
//       flex-wrap 行為回復為共用 .btn-row class 的 wrap
// AC2 - #result-action-group-content inline style 不含 flex-wrap:nowrap
// AC3 - #result-action-group-reset inline style 不含 flex-wrap:nowrap
// AC4 - 三顆按鈕文字恢復 emoji 前綴
// AC5（回歸）- 按鈕 id/class/onclick 與元素順序、對應函式皆不受影響

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const MINUTES = {
  job_id: "e2e-job-action-restore-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

test.describe("結果頁面操作區塊回復 SDLCAIP2-39 合併前呈現方式（SDLCAIP2-40）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-action-restore-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = minutes.job_id;
      s.minutes = minutes;
      s.modified = false;
      (0, eval)("renderMinutes")();
      (0, eval)("showView")("view-result");
    }, MINUTES);
    await expect(page.locator("#view-result")).toBeVisible();
  });

  test("AC1: 操作列外層容器（.btn-row，含 #result-action-group-content/-reset 的父容器）inline style 不含 nowrap/overflow-x:auto，flex-wrap 回復為 wrap", async ({
    page,
  }) => {
    const outer = page.locator("#result-action-group-content").locator("..");
    await expect(outer).toHaveClass(/\bbtn-row\b/);

    const inlineStyle = await outer.getAttribute("style");
    expect(inlineStyle ?? "").not.toMatch(/flex-wrap\s*:\s*nowrap/);
    expect(inlineStyle ?? "").not.toMatch(/overflow-x\s*:\s*auto/);

    const computedFlexWrap = await outer.evaluate((el) => getComputedStyle(el).flexWrap);
    expect(computedFlexWrap).toBe("wrap");

    const computedOverflowX = await outer.evaluate((el) => getComputedStyle(el).overflowX);
    expect(computedOverflowX).not.toBe("auto");
  });

  test("AC2: #result-action-group-content inline style 不含 flex-wrap:nowrap", async ({ page }) => {
    const el = page.locator("#result-action-group-content");
    await expect(el).toBeVisible();
    const inlineStyle = await el.getAttribute("style");
    expect(inlineStyle ?? "").not.toMatch(/flex-wrap\s*:\s*nowrap/);
  });

  test("AC3: #result-action-group-reset inline style 不含 flex-wrap:nowrap", async ({ page }) => {
    const el = page.locator("#result-action-group-reset");
    await expect(el).toBeVisible();
    const inlineStyle = await el.getAttribute("style");
    expect(inlineStyle ?? "").not.toMatch(/flex-wrap\s*:\s*nowrap/);
  });

  test("AC4: 三顆按鈕的 emoji 圖示恢復顯示", async ({ page }) => {
    await expect(page.locator("#regenerate-btn")).toHaveText("🔄 重新產生");
    await expect(page.locator("#export-confirm-btn")).toHaveText("⬇ 匯出");
    await expect(page.locator("#cleanup-btn")).toHaveText("🗑 清除暫存");
  });

  test("AC5（回歸）: 按鈕 id/class/onclick 屬性與元素順序不受影響，對應函式仍存在", async ({ page }) => {
    const regenerate = page.locator("#regenerate-btn");
    const exportBtn = page.locator("#export-confirm-btn");
    const cleanup = page.locator("#cleanup-btn");
    const newRecording = page.locator("#new-recording-btn");

    await expect(regenerate).toHaveAttribute("class", "btn btn-outline btn-sm");
    await expect(regenerate).toHaveAttribute("onclick", "regenerateSummary()");

    await expect(exportBtn).toHaveAttribute("class", "btn btn-outline btn-sm");
    await expect(exportBtn).toHaveAttribute("onclick", "exportSelectedFormat()");

    await expect(cleanup).toHaveAttribute("class", "btn btn-outline btn-sm");
    await expect(cleanup).toHaveAttribute("onclick", "cleanupAndReset()");

    await expect(newRecording).toHaveAttribute("onclick", "showView('view-upload')");

    // 元素順序：cleanup-btn 應在 new-recording-btn 之前（同一組內，DOM 順序不變）
    const resetGroupChildrenIds = await page
      .locator("#result-action-group-reset")
      .evaluate((el) => Array.from(el.children).map((c) => c.id));
    expect(resetGroupChildrenIds).toEqual(["cleanup-btn", "new-recording-btn"]);

    // 對應函式仍存在於全域範疇
    const fnsExist = await page.evaluate(() => {
      return {
        regenerateSummary: typeof (0, eval)("regenerateSummary") === "function",
        exportSelectedFormat: typeof (0, eval)("exportSelectedFormat") === "function",
        cleanupAndReset: typeof (0, eval)("cleanupAndReset") === "function",
      };
    });
    expect(fnsExist).toEqual({
      regenerateSummary: true,
      exportSelectedFormat: true,
      cleanupAndReset: true,
    });
  });
});
