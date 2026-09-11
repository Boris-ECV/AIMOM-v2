import { test, expect } from "@playwright/test";

// SDLCAIP2-35: 匯出功能的四種格式整合為單一下拉選單 + 確認按鈕（e2e）
//
// 沿用 template-selection.spec.ts 既有手法：假 id_token 繞過登入、直接
// 注入 state.minutes 並切換到 view-result，聚焦驗證本故事新增的
// exportSelectedFormat() 分派邏輯與 UI 結構本身，不重新驗證
// exportMarkdown()/exportPlainText()/exportServerFile() 內部的檔案產生
// 邏輯（ticket 明確排除範圍，且該邏輯本身未變更）。做法是把這三個既有
// 全域函式（非 module 內嵌 <script> 的函式宣告會成為 window 屬性）換成
// spy，驗證「選單目前選取哪個格式、點擊匯出按鈕後，就呼叫對應的那個
// 既有函式（含正確參數）」。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const INITIAL_MINUTES = {
  job_id: "e2e-job-export-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

test.describe("匯出格式選單（SDLCAIP2-35）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-export-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = minutes.job_id;
      s.minutes = minutes;
      s.modified = false;
      (0, eval)("renderMinutes")();
      (0, eval)("showView")("view-result");
    }, INITIAL_MINUTES);
    await expect(page.locator("#view-result")).toBeVisible();

    // 把既有的匯出函式換成 spy，記錄被呼叫的名稱與參數，不執行真正的
    // 檔案下載邏輯（該邏輯不在本故事範圍內，也未被本故事變更）。
    await page.evaluate(() => {
      (window as any).__exportCalls = [];
      (0, eval)(
        "window.exportMarkdown = () => { window.__exportCalls.push(['exportMarkdown']); };" +
        "window.exportPlainText = () => { window.__exportCalls.push(['exportPlainText']); };" +
        "window.exportServerFile = (format) => { window.__exportCalls.push(['exportServerFile', format]); };"
      );
    });
  });

  test("結果頁面不再顯示 4 顆並排匯出按鈕，改為單一下拉選單 + 確認按鈕", async ({ page }) => {
    await expect(page.getByRole("button", { name: /匯出 Markdown/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /匯出純文字/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /匯出 Word/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /匯出 PDF/ })).toHaveCount(0);

    const select = page.locator("#export-format-select");
    await expect(select).toBeVisible();
    const optionValues = await select.locator("option").evaluateAll((opts) =>
      opts.map((o) => (o as HTMLOptionElement).value)
    );
    expect(optionValues).toEqual(["markdown", "plaintext", "docx", "pdf"]);
    const optionLabels = await select.locator("option").allTextContents();
    expect(optionLabels).toEqual(["Markdown", "純文字", "Word", "PDF"]);

    await expect(page.locator("#export-confirm-btn")).toBeVisible();
    await expect(page.locator("#export-confirm-btn")).toHaveText(/匯出/);
  });

  test("下拉選單預設選取第一個選項 Markdown", async ({ page }) => {
    await expect(page.locator("#export-format-select")).toHaveValue("markdown");
  });

  test("選取 Markdown 並點擊匯出，呼叫 exportMarkdown()", async ({ page }) => {
    await page.locator("#export-format-select").selectOption("markdown");
    await page.locator("#export-confirm-btn").click();
    const calls = await page.evaluate(() => (window as any).__exportCalls);
    expect(calls).toEqual([["exportMarkdown"]]);
  });

  test("選取純文字並點擊匯出，呼叫 exportPlainText()", async ({ page }) => {
    await page.locator("#export-format-select").selectOption("plaintext");
    await page.locator("#export-confirm-btn").click();
    const calls = await page.evaluate(() => (window as any).__exportCalls);
    expect(calls).toEqual([["exportPlainText"]]);
  });

  test("選取 Word 並點擊匯出，呼叫 exportServerFile('docx')", async ({ page }) => {
    await page.locator("#export-format-select").selectOption("docx");
    await page.locator("#export-confirm-btn").click();
    const calls = await page.evaluate(() => (window as any).__exportCalls);
    expect(calls).toEqual([["exportServerFile", "docx"]]);
  });

  test("選取 PDF 並點擊匯出，呼叫 exportServerFile('pdf')", async ({ page }) => {
    await page.locator("#export-format-select").selectOption("pdf");
    await page.locator("#export-confirm-btn").click();
    const calls = await page.evaluate(() => (window as any).__exportCalls);
    expect(calls).toEqual([["exportServerFile", "pdf"]]);
  });
});
