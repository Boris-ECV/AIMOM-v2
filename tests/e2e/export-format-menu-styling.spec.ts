import { test, expect } from "@playwright/test";

// SDLCAIP2-37: 會議紀錄結果頁面操作區塊視覺風格不一致、排列凌亂
//
// 沿用 template-select-style.spec.ts / export-format-menu.spec.ts 既有的
// 登入繞過與注入結果資料手法，切換到結果畫面後驗證：
// AC1 - #export-format-select 與 #template-select 樣式一致
// AC2 - #export-confirm-btn 與 #cleanup-btn / #new-recording-btn 樣式一致，
//       且 #export-confirm-btn 不再帶有 .btn-success class
// AC3 - #cleanup-btn / #new-recording-btn 靠右分組，與其他控制項有清楚
//       視覺區隔（分組間距 > 組內間距）
// AC4（既有匯出行為迴歸）已由 export-format-menu.spec.ts（SDLCAIP2-35）
// 涵蓋，此檔不重複驗證。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const MINUTES = {
  job_id: "e2e-job-action-style-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

test.describe("結果頁面操作區塊視覺風格一致性（SDLCAIP2-37）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-action-style-user@example.com"));
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

  test("AC1: #export-format-select 樣式與 #template-select 逐項一致", async ({ page }) => {
    const templateSelect = page.locator("#template-select");
    const exportFormatSelect = page.locator("#export-format-select");
    await expect(templateSelect).toBeVisible();
    await expect(exportFormatSelect).toBeVisible();

    const properties = [
      "borderWidth",
      "borderStyle",
      "borderColor",
      "borderRadius",
      "color",
      "fontFamily",
      "fontSize",
      "padding",
    ];

    const readStyle = (el: Element, props: string[]) => {
      const computed = getComputedStyle(el);
      return Object.fromEntries(props.map((p) => [p, computed.getPropertyValue(p) || (computed as any)[p]]));
    };

    const referenceStyle = await templateSelect.evaluate(readStyle, properties);
    const targetStyle = await exportFormatSelect.evaluate(readStyle, properties);

    expect(targetStyle).toEqual(referenceStyle);
  });

  test("AC2: #export-confirm-btn 樣式與 #cleanup-btn / #new-recording-btn 逐項一致，且不再帶 .btn-success", async ({
    page,
  }) => {
    const exportBtn = page.locator("#export-confirm-btn");
    const cleanupBtn = page.locator("#cleanup-btn");
    const newRecordingBtn = page.locator("#new-recording-btn");
    await expect(exportBtn).toBeVisible();
    await expect(cleanupBtn).toBeVisible();
    await expect(newRecordingBtn).toBeVisible();

    const exportClass = await exportBtn.getAttribute("class");
    expect(exportClass).not.toMatch(/\bbtn-success\b/);

    const properties = ["backgroundColor", "color", "border", "borderRadius", "fontSize", "padding"];
    const readStyle = (el: Element, props: string[]) => {
      const computed = getComputedStyle(el);
      return Object.fromEntries(props.map((p) => [p, computed.getPropertyValue(p) || (computed as any)[p]]));
    };

    const exportStyle = await exportBtn.evaluate(readStyle, properties);
    const cleanupStyle = await cleanupBtn.evaluate(readStyle, properties);
    const newRecordingStyle = await newRecordingBtn.evaluate(readStyle, properties);

    expect(exportStyle).toEqual(cleanupStyle);
    expect(cleanupStyle).toEqual(newRecordingStyle);
  });

  test("AC3: #cleanup-btn / #new-recording-btn 靠右分組，與其他控制項有清楚視覺區隔", async ({ page }) => {
    const exportBtn = page.locator("#export-confirm-btn");
    const cleanupBtn = page.locator("#cleanup-btn");
    const newRecordingBtn = page.locator("#new-recording-btn");

    const exportBox = await exportBtn.boundingBox();
    const cleanupBox = await cleanupBtn.boundingBox();
    const newRecordingBox = await newRecordingBtn.boundingBox();
    expect(exportBox).not.toBeNull();
    expect(cleanupBox).not.toBeNull();
    expect(newRecordingBox).not.toBeNull();

    // #cleanup-btn 的左邊界大於 #export-confirm-btn 的右邊界
    expect(cleanupBox!.x).toBeGreaterThan(exportBox!.x + exportBox!.width);

    // 分組間距（export -> cleanup）大於組內間距（cleanup -> new-recording）
    const groupGap = cleanupBox!.x - (exportBox!.x + exportBox!.width);
    const withinGroupGap = newRecordingBox!.x - (cleanupBox!.x + cleanupBox!.width);
    expect(withinGroupGap).toBeLessThan(groupGap);
  });
});
