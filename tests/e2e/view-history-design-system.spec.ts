import { test, expect } from "@playwright/test";

// SDLCAIP2-50: Design System｜歷史紀錄列表頁 view-history
//
// 沿用 view-admin-design-system.spec.ts（SDLCAIP2-45）與 history-detail.spec.ts
// （SDLCAIP2-32）既有的登入繞過、page.route 攔截 /api/meetings 手法。
// AC 對應：
// AC1 - view-history 卡片延續既有 .card token（回歸確認）
// AC2 - #history-table 改用 --ds-* token，且僅影響 view-history（不影響共用 .action-table 基底規則）
// AC3 - #history-empty 文字色改用 --ds-* token，且不影響共用 .empty-state 基底規則
// AC4 - .section-title 文字無裝飾性 emoji，為「歷史紀錄」
// AC5 - 窄螢幕（<480px）有資料列時不發生頁面橫向溢出、表格欄位可讀
// AC6 - 點擊列表項目仍呼叫 openMeetingDetail 並顯示 #view-history-detail（回歸）
// AC7 - /api/meetings 回傳空陣列時 #history-table 隱藏、#history-empty 顯示（回歸）
// AC8 - 其他頁面的 .action-table/.empty-state/.card 不受影響（回歸保護）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-history-design-system-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

async function mockMeetingsList(page: import("@playwright/test").Page) {
  await page.route("**/api/meetings", async (route) => {
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
}

// 讓 view-result 顯示至少兩列 .action-table 資料，作為範圍外（AC2/AC8）比對基準。
// 兩列避免只有單列時觸發 tr:last-child td { border-bottom: none; } 影響邊框色檢查。
async function openViewResultWithRow(page: import("@playwright/test").Page) {
  await page.evaluate(() => {
    const s = (0, eval)("state");
    s.jobId = "e2e-view-history-ds-1";
    s.minutes = {
      job_id: "e2e-view-history-ds-1",
      template: "general",
      meeting_info: { date: "", time: "", location: "", participants: [] },
      summary: "",
      action_items: [
        { owner: "王小明", task: "整理紀錄", due: "2026-09-30" },
        { owner: "李小華", task: "確認場地", due: "2026-10-01" },
      ],
      decisions: [],
      sections: [],
    };
    (0, eval)("renderMinutes")();
    (0, eval)("showView")("view-result");
  });
  await expect(page.locator("#view-result")).toBeVisible();
}

test.describe("Design System｜歷史紀錄列表頁 view-history（SDLCAIP2-50）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
  });

  test("AC1: view-history 卡片延續既有 .card token（回歸確認）", async ({ page }) => {
    await mockMeetingsList(page);
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();

    const card = page.locator("#view-history .card").first();
    await expect(card).toHaveCSS("background-color", "rgb(255, 255, 255)"); // --ds-surface
    await expect(card).toHaveCSS("border-color", "rgb(228, 227, 223)"); // --ds-border #E4E3DF
    await expect(card).toHaveCSS("border-radius", "10px"); // --ds-radius-md
  });

  test("AC2 + AC8: #history-table 改用 --ds-* token，且不影響共用 .action-table 基底規則", async ({ page }) => {
    await mockMeetingsList(page);
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#history-table")).toBeVisible();

    const th = page.locator("#history-table th").first();
    await expect(th).toHaveCSS("background-color", "rgb(239, 238, 234)"); // --ds-badge-bg
    await expect(th).toHaveCSS("color", "rgb(107, 106, 100)"); // --ds-text-secondary
    await expect(th).toHaveCSS("border-bottom-color", "rgb(228, 227, 223)"); // --ds-border
    await expect(th).toHaveCSS("font-size", "13px");

    const td = page.locator("#history-tbody tr").first().locator("td").first();
    await expect(td).toHaveCSS("color", "rgb(31, 30, 28)"); // --ds-text-primary
    await expect(td).toHaveCSS("border-bottom-color", "rgb(228, 227, 223)"); // --ds-border
    await expect(td).toHaveCSS("font-size", "13px");

    // 關鍵回歸保護：view-result 的共用 .action-table 基底規則不得被 view-history 的範圍限定選取器影響
    await openViewResultWithRow(page);
    const resultTh = page.locator("#view-result .action-table th").first();
    await expect(resultTh).toHaveCSS("background-color", "rgb(248, 250, 252)"); // 舊 --bg #F8FAFC，未被覆寫
    await expect(resultTh).toHaveCSS("color", "rgb(100, 116, 139)"); // 舊 --muted #64748B，未被覆寫
    await expect(resultTh).toHaveCSS("border-bottom-color", "rgb(226, 232, 240)"); // 舊 --border #E2E8F0，未被覆寫

    const resultTd = page.locator("#view-result .action-table td").first();
    await expect(resultTd).toHaveCSS("border-bottom-color", "rgb(226, 232, 240)"); // 舊 --border，未被覆寫
  });

  test("AC3 + AC8: #history-empty 文字色改用 --ds-* token，且不影響共用 .empty-state 基底規則", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({ status: 200, json: { meetings: [] } });
    });
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#history-empty")).toBeVisible();
    await expect(page.locator("#history-empty")).toHaveCSS("color", "rgb(107, 106, 100)"); // --ds-text-secondary

    // 關鍵回歸保護：另一個共用 .empty-state（#history-detail-error，404 情境）不得被本票覆寫
    await page.route("**/api/meetings/m-missing", async (route) => {
      await route.fulfill({ status: 404, json: { detail: "找不到此會議紀錄" } });
    });
    await page.evaluate(() => (0, eval)("openMeetingDetail")("m-missing"));
    await expect(page.locator("#history-detail-error")).toBeVisible();
    await expect(page.locator("#history-detail-error")).toHaveCSS("color", "rgb(100, 116, 139)"); // 舊 --muted，未被覆寫
  });

  test("AC4: .section-title 文字無裝飾性 emoji，為「歷史紀錄」", async ({ page }) => {
    await mockMeetingsList(page);
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();

    const titleText = await page.locator("#view-history .section-title").first().textContent();
    expect(titleText?.trim()).toBe("歷史紀錄");
    // eslint-disable-next-line no-misleading-character-class
    const emojiPattern = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    expect(emojiPattern.test(titleText || "")).toBe(false);
  });

  test("AC5: 窄螢幕（<480px）有資料列時不發生頁面橫向溢出、表格欄位可讀", async ({ page }) => {
    await mockMeetingsList(page);
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#history-table")).toBeVisible();

    await page.setViewportSize({ width: 375, height: 800 });

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);

    const wrapper = page.locator("#view-history .ds-table-scroll").first();
    await expect(wrapper).toHaveCSS("overflow-x", "auto");

    const table = page.locator("#view-history .action-table").first();
    await expect(table).toHaveCSS("min-width", "420px");
  });

  test("AC6: 點擊列表項目仍呼叫 openMeetingDetail 並顯示 #view-history-detail（回歸）", async ({ page }) => {
    await mockMeetingsList(page);

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

  test("AC7: /api/meetings 回傳空陣列時 #history-table 隱藏、#history-empty 顯示（回歸）", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({ status: 200, json: { meetings: [] } });
    });

    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();

    await expect(page.locator("#history-empty")).toBeVisible();
    await expect(page.locator("#history-empty")).toContainText("尚無已保留的會議紀錄");
    await expect(page.locator("#history-table")).toBeHidden();
  });

  test("AC8: 範圍外畫面（view-upload .card）視覺不受本票影響", async ({ page }) => {
    const card = page.locator("#view-upload .card").first();
    await expect(card).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(card).toHaveCSS("border-radius", "10px");
    await expect(card).toHaveCSS("padding", "32px");
  });
});
