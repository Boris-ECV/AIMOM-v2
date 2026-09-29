import { test, expect } from "@playwright/test";

// SDLCAIP2-42: 會議紀錄結果頁操作列排版與按鈕文字
//
// 沿用 action-bar-restore.spec.ts / template-select-style.spec.ts 既有的
// 登入繞過與注入結果資料手法，切換到結果畫面後驗證：
// AC1 - 標題（<h2>）獨立佔一行
// AC2 - #result-meta 獨立佔一行，不與標題或操作列同排
// AC3 - 操作列獨立一行、內部左右分佈、不使用橫向捲動、允許 flex-wrap 換行
// AC4 - 三顆按鈕（重新產生/匯出/清除暫存）僅顯示文字，不含 emoji；新錄音文字不變
// AC5（回歸）- 按鈕行為/id/class/onclick/元素數量與順序不受影響

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const MINUTES = {
  job_id: "e2e-job-action-row-layout-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

test.describe("結果頁操作列排版與按鈕文字（SDLCAIP2-42）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-action-row-layout-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = minutes.job_id;
      s.minutes = minutes;
      s.modified = false;
      (0, eval)("renderMinutes")();
      (0, eval)("showView")("view-result");
      document.getElementById("result-meta").textContent = `Job ID: ${minutes.job_id} | 0 段逐字稿`;
    }, MINUTES);
    await expect(page.locator("#view-result")).toBeVisible();
  });

  test("AC1: 標題（<h2>）獨立佔一行", async ({ page }) => {
    const view = page.locator("#view-result");
    const heading = view.locator("h2").first();
    await expect(heading).toBeVisible();
    // superseded by SDLCAIP2-54 AC1: h2 emoji removed ("📋 會議紀錄" -> "會議紀錄")
    await expect(heading).toHaveText("會議紀錄");

    const meta = page.locator("#result-meta");
    const headingBox = await heading.boundingBox();
    const metaBox = await meta.boundingBox();
    expect(headingBox).not.toBeNull();
    expect(metaBox).not.toBeNull();
    // 標題與 meta 應為不同列（垂直不重疊）
    expect(headingBox!.y + headingBox!.height).toBeLessThanOrEqual(metaBox!.y + 1);
  });

  test("AC2: #result-meta 獨立佔一行，不與標題或操作列同排", async ({ page }) => {
    const meta = page.locator("#result-meta");
    await expect(meta).toBeVisible();

    const actionRow = page.locator("#result-action-group-content").locator("..");
    const metaBox = await meta.boundingBox();
    const actionRowBox = await actionRow.boundingBox();
    expect(metaBox).not.toBeNull();
    expect(actionRowBox).not.toBeNull();
    // meta 應在操作列之上，且兩者不垂直重疊
    expect(metaBox!.y + metaBox!.height).toBeLessThanOrEqual(actionRowBox!.y + 1);
  });

  test("AC3: 操作列獨立一行、內部左右分佈、不使用橫向捲動、允許 flex-wrap 換行", async ({ page }) => {
    const outer = page.locator("#result-action-group-content").locator("..");
    await expect(outer).toHaveClass(/\bbtn-row\b/);

    const inlineStyle = await outer.getAttribute("style");
    expect(inlineStyle ?? "").not.toMatch(/overflow-x\s*:\s*auto/);
    expect(inlineStyle ?? "").not.toMatch(/flex-wrap\s*:\s*nowrap/);

    const computedOverflowX = await outer.evaluate((el) => getComputedStyle(el).overflowX);
    expect(computedOverflowX).not.toBe("auto");
    expect(computedOverflowX).not.toBe("scroll");

    const computedFlexWrap = await outer.evaluate((el) => getComputedStyle(el).flexWrap);
    expect(computedFlexWrap).toBe("wrap");

    const computedJustify = await outer.evaluate((el) => getComputedStyle(el).justifyContent);
    expect(computedJustify).toBe("space-between");

    // 左側群組維持相對順序：badge -> badge -> 模板選單 -> 重新產生 -> 匯出格式 -> 匯出
    const leftGroupIds = await page
      .locator("#result-action-group-content")
      .evaluate((el) =>
        Array.from(el.children)
          .map((c) => c.id)
          .filter((id) => id),
      );
    expect(leftGroupIds).toEqual([
      "modified-badge",
      "low-confidence-badge",
      "regenerate-btn",
      "export-confirm-btn",
    ]);
    // 模板/匯出格式為 <label><select> 結構，確認相對於按鈕的順序仍是
    // 模板選單 -> 重新產生 -> 匯出格式 -> 匯出
    const leftGroupTagOrder = await page
      .locator("#result-action-group-content")
      .evaluate((el) => Array.from(el.children).map((c) => c.tagName + (c.id ? `#${c.id}` : "")));
    const regenIdx = leftGroupTagOrder.findIndex((s) => s.includes("regenerate-btn"));
    const exportIdx = leftGroupTagOrder.findIndex((s) => s.includes("export-confirm-btn"));
    expect(regenIdx).toBeGreaterThan(-1);
    expect(exportIdx).toBeGreaterThan(regenIdx);

    // 右側群組（清除暫存、新錄音）並排靠右對齊：右群組整體應位於左群組右側
    const leftBox = await page.locator("#result-action-group-content").boundingBox();
    const rightGroup = page.locator("#result-action-group-reset");
    const rightBox = await rightGroup.boundingBox();
    expect(leftBox).not.toBeNull();
    expect(rightBox).not.toBeNull();
    expect(rightBox!.x).toBeGreaterThanOrEqual(leftBox!.x);

    const rightGroupIds = await rightGroup.evaluate((el) => Array.from(el.children).map((c) => c.id));
    expect(rightGroupIds).toEqual(["cleanup-btn", "new-recording-btn"]);
  });

  test("AC4: 三顆按鈕僅顯示文字，不含 emoji；新錄音文字不變", async ({ page }) => {
    await expect(page.locator("#regenerate-btn")).toHaveText("重新產生");
    await expect(page.locator("#export-confirm-btn")).toHaveText("匯出");
    await expect(page.locator("#cleanup-btn")).toHaveText("清除暫存");
    await expect(page.locator("#new-recording-btn")).toHaveText("+ 新錄音");
  });

  test("AC5（回歸）: 按鈕行為與元素結構不受影響", async ({ page }) => {
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

    const resetGroupChildrenIds = await page
      .locator("#result-action-group-reset")
      .evaluate((el) => Array.from(el.children).map((c) => c.id));
    expect(resetGroupChildrenIds).toEqual(["cleanup-btn", "new-recording-btn"]);

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

    // 點擊 新錄音 應切換回上傳畫面（實際呼叫既有 showView 行為的觀察結果）
    await newRecording.click();
    await expect(page.locator("#view-upload")).toHaveClass(/active/);
  });
});
