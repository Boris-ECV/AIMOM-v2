import { test, expect } from "@playwright/test";

// SDLCAIP2-32: 已保留會議紀錄歷史列表與詳情唯讀瀏覽 UI（e2e）
//
// 沿用 speaker-naming.spec.ts 的登入繞過手法（塞入假 id_token 到
// sessionStorage）。GET /api/meetings 與 GET /api/meetings/{id} 打的是
// config.js 寫死的遠端 AWS API base URL，不適合在 e2e 環境呼叫真實服務；
// 用 page.route 攔截這兩個請求，驗證的是「前端收到回應之後的實際處理
// 行為」（清單渲染/空狀態切換、點擊列表項目導向詳情頁並呼叫對應 API、
// 詳情頁唯讀渲染、404 顯示錯誤並可返回列表）——這些都是本故事新增、
// 目前完全沒有涵蓋的前端邏輯，因此本故事宣告需要 e2e 覆蓋。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-history-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

test.describe("歷史紀錄列表與詳情唯讀瀏覽（SDLCAIP2-32）", () => {
  test.beforeEach(async ({ page }) => {
    await loginBypass(page);
  });

  test("AC1: 歷史列表顯示已保留的會議紀錄", async ({ page }) => {
    let requested = false;
    await page.route("**/api/meetings", async (route) => {
      requested = true;
      await route.fulfill({
        status: 200,
        json: {
          meetings: [
            { meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 },
            { meeting_id: "m-2", title: "第二次會議", created_at: 1735776000, expires_at: 9999999999 },
          ],
        },
      });
    });

    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();
    expect(requested).toBe(true);

    await expect(page.locator("#history-table")).toBeVisible();
    await expect(page.locator("#history-empty")).toBeHidden();
    const rows = page.locator("#history-tbody tr");
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText("第一次會議");
    await expect(rows.nth(1)).toContainText("第二次會議");
  });

  test("AC2: 無任何已保留紀錄時顯示空狀態", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({ status: 200, json: { meetings: [] } });
    });

    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();

    await expect(page.locator("#history-empty")).toBeVisible();
    await expect(page.locator("#history-empty")).toContainText("尚無已保留的會議紀錄");
    await expect(page.locator("#history-table")).toBeHidden();
  });

  test("AC3: 點擊列表項目導向該筆紀錄的詳情頁", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({
        status: 200,
        json: { meetings: [{ meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 }] },
      });
    });

    let detailRequested = "";
    await page.route("**/api/meetings/m-1", async (route) => {
      detailRequested = route.request().url();
      await route.fulfill({
        status: 200,
        json: {
          meeting_id: "m-1",
          title: "第一次會議",
          transcript_text: "逐字稿內容",
          minutes: {
            meeting_info: { date: "", time: "", location: "", participants: [] },
            summary: "摘要內容",
            action_items: [],
            decisions: [],
            sections: [],
          },
          expires_at: 9999999999,
        },
      });
    });

    await page.locator("#history-nav-btn").click();
    await page.locator("#history-tbody tr").first().click();

    await expect(page.locator("#view-history-detail")).toBeVisible();
    expect(detailRequested).toContain("/api/meetings/m-1");
  });

  test("AC4: 詳情頁以唯讀方式顯示完整內容", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({
        status: 200,
        json: { meetings: [{ meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 }] },
      });
    });
    await page.route("**/api/meetings/m-1", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          meeting_id: "m-1",
          title: "第一次會議",
          transcript_text: "王小明：大家好。",
          minutes: {
            meeting_info: { date: "2026-09-11", time: "14:00", location: "3樓會議室", participants: ["王小明"] },
            summary: "這是摘要內容",
            action_items: [{ owner: "王小明", task: "整理紀錄", due: "2026-09-12" }],
            decisions: ["採用方案A"],
            sections: [{ title: "討論主題一", content: "討論內容一" }],
          },
          expires_at: 9999999999,
        },
      });
    });

    await page.locator("#history-nav-btn").click();
    await page.locator("#history-tbody tr").first().click();
    await expect(page.locator("#view-history-detail")).toBeVisible();
    await expect(page.locator("#history-detail-body")).toBeVisible();
    await expect(page.locator("#history-detail-error")).toBeHidden();

    await expect(page.locator("#history-detail-title")).toHaveText("第一次會議");
    await expect(page.locator("#history-summary-text")).toHaveText("這是摘要內容");
    await expect(page.locator("#history-action-tbody tr td")).toContainText(["王小明", "整理紀錄", "2026-09-12"]);
    await expect(page.locator("#history-decision-list li")).toContainText(["採用方案A"]);
    await page.locator("#history-topics-container .topic-header").click();
    await expect(page.locator("#history-topics-container")).toContainText("討論內容一");

    // 唯讀：欄位皆不可編輯
    const summaryEditable = await page.locator("#history-summary-text").getAttribute("contenteditable");
    expect(summaryEditable).toBeNull();
    const tdEditable = await page.locator("#history-action-tbody td").first().getAttribute("contenteditable");
    expect(tdEditable).toBeNull();

    // 逐字稿分頁
    await page.locator("#history-tab-btn-transcript").click();
    await expect(page.locator("#history-tab-transcript")).toBeVisible();
    await expect(page.locator("#history-transcript-container")).toContainText("王小明：大家好。");
  });

  test("AC5: 詳情頁遇到 404 時顯示錯誤並可返回列表", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({
        status: 200,
        json: { meetings: [{ meeting_id: "m-deleted", title: "已刪除會議", created_at: 1735689600, expires_at: 9999999999 }] },
      });
    });
    await page.route("**/api/meetings/m-deleted", async (route) => {
      await route.fulfill({ status: 404, json: { detail: "找不到此會議紀錄" } });
    });

    await page.locator("#history-nav-btn").click();
    await page.locator("#history-tbody tr").first().click();

    await expect(page.locator("#view-history-detail")).toBeVisible();
    await expect(page.locator("#history-detail-error")).toBeVisible();
    await expect(page.locator("#history-detail-error-msg")).toHaveText("找不到此會議紀錄");
    await expect(page.locator("#history-detail-body")).toBeHidden();

    await page.locator("#history-detail-error button").click();
    await expect(page.locator("#view-history")).toBeVisible();
  });
});
