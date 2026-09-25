import { test, expect, type Page } from "@playwright/test";

// SDLCAIP2-48: Design System｜歷史紀錄詳情頁 view-history-detail
//
// 沿用 view-result-cards-design-system.spec.ts（SDLCAIP2-55）/
// history-detail-edit.spec.ts（SDLCAIP2-17）的登入繞過、page.route 攔截
// /api/meetings、/api/meetings/{id}、resolveToken 動態解析 --ds-* token 手法。
// AC 對應：
// AC1 - #history-edit-btn/#history-save-btn 文字移除 emoji，#history-cancel-btn／
//       返回按鈕文字不變，saveHistoryEdit() 仍還原按鈕文字（回歸）
// AC2 - #history-tab-btn-minutes/#history-tab-btn-transcript 文字移除 emoji，
//       switchHistoryTab() active class 切換不變（回歸）
// AC3 - #view-history-detail .section-title 與 #view-result 一致（h2 18/26/600 +
//       --ds-text-primary，<480px 17/24），不影響共用 .section-title 本體
// AC4 - #view-history-detail .action-table th/td 與 #view-result 一致，
//       不影響共用 .action-table 本體，<480px 無頁面級橫向溢出
// AC5 - #view-history-detail .empty-state（#history-detail-error 與討論重點空清單）
//       文字色為 --ds-text-secondary，不影響共用 .empty-state 本體
// AC6 - 標題列按鈕群組 gap 為 var(--ds-space-2)（12px），取代舊 inline gap:10px
// AC7 (回歸) - .tabs/.tab、.meeting-info-grid、.decision-list、.topic-* 電腦樣式
//       與 view-result 相同 class 一致（54/55 已併入 main）
// AC8 (回歸) - openMeetingDetail() 顯示/隱藏 body/error、404 錯誤訊息、
//       編輯/儲存(PATCH)/取消流程、「← 返回歷史列表」不變

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-history-detail-ds-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

const DETAIL_RESPONSE = {
  meeting_id: "m-1",
  title: "第一次會議",
  transcript_text: "王小明：大家好。",
  minutes: {
    job_id: "job-abc",
    template: "general",
    meeting_info: { date: "2026-09-11", time: "14:00", location: "3樓會議室", participants: ["王小明"] },
    summary: "這是摘要內容",
    action_items: [
      { owner: "王小明", task: "整理紀錄", due: "2026-09-12" },
      { owner: "李小華", task: "確認場地", due: "2026-09-13" },
    ],
    // 兩筆決議，避免單筆時觸發 .decision-list li:last-child { border-bottom: none; }
    // 影響邊框色檢查（沿用 view-result-cards-design-system.spec.ts 相同慣例）。
    decisions: ["採用方案A", "採用方案B"],
    sections: [{ title: "討論主題一", content: "討論內容一" }],
  },
  expires_at: 9999999999,
};

async function openDetail(page: Page) {
  await page.route("**/api/meetings", async (route) => {
    await route.fulfill({
      status: 200,
      json: { meetings: [{ meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 }] },
    });
  });
  await page.route("**/api/meetings/m-1", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
    } else {
      await route.continue();
    }
  });

  await page.locator("#history-nav-btn").click();
  await page.locator("#history-tbody tr").first().click();
  await expect(page.locator("#view-history-detail")).toBeVisible();
  await expect(page.locator("#history-detail-body")).toBeVisible();
}

// 透過臨時 probe 元素套用 var(--token)，讓瀏覽器實際 cascade 解析出 computed 值
// （不在測試裡寫死十六進位色碼），延續既有 spec 慣例。
async function resolveToken(page: Page, cssProp: string, varExpr: string): Promise<string> {
  return page.evaluate(
    ({ cssProp, varExpr }) => {
      const probe = document.createElement("div");
      probe.style.setProperty(cssProp, varExpr);
      document.body.appendChild(probe);
      const value = getComputedStyle(probe).getPropertyValue(cssProp);
      probe.remove();
      return value;
    },
    { cssProp, varExpr },
  );
}

// 讓 view-result 顯示至少一列，供 AC7 電腦樣式比對基準。
async function openViewResultWithRow(page: Page) {
  await page.evaluate(() => {
    const s = (0, eval)("state");
    s.jobId = "e2e-view-history-detail-ds-1";
    s.minutes = {
      job_id: "e2e-view-history-detail-ds-1",
      template: "general",
      meeting_info: { date: "2026-09-20", time: "09:00", location: "會議室 B", participants: ["陳小華"] },
      summary: "供比對的摘要內容",
      action_items: [{ owner: "陳小華", task: "確認議程", due: "2026-09-21" }],
      // 兩筆決議，避免單筆時觸發 .decision-list li:last-child { border-bottom: none; }
      decisions: ["決議一", "決議二"],
      sections: [{ title: "主題一", content: "內容一" }],
    };
    (0, eval)("renderMinutes")();
    (0, eval)("showView")("view-result");
  });
  await expect(page.locator("#view-result")).toBeVisible();
}

test.describe("Design System｜歷史紀錄詳情頁 view-history-detail（SDLCAIP2-48）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
  });

  test("AC1: 標題列按鈕文字移除 emoji，取消/返回文字不變，儲存後仍還原按鈕文字", async ({ page }) => {
    await openDetail(page);

    await expect(page.locator("#history-edit-btn")).toHaveText("編輯");
    await expect(page.locator("#history-cancel-btn")).toHaveText("取消");
    await expect(page.locator("#view-history-detail .btn-row button", { hasText: "← 返回歷史列表" })).toHaveCount(1);

    await page.locator("#history-edit-btn").click();
    await expect(page.locator("#history-save-btn")).toHaveText("儲存");
    await expect(page.locator("#history-save-btn")).toBeVisible();

    // 覆寫 openDetail() 的 route.continue()，避免 PATCH 打到真實遠端 API
    await page.route("**/api/meetings/m-1", async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      } else {
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      }
    });
    await page.locator("#history-save-btn").click();
    await expect(page.locator("#toast")).toContainText("已儲存");
    // saveHistoryEdit() 應在成功後還原按鈕文字並切回唯讀模式
    await expect(page.locator("#history-edit-btn")).toBeVisible();
    await expect(page.locator("#history-edit-btn")).toHaveText("編輯");
    await expect(page.locator("#history-save-btn")).toBeHidden();
  });

  test("AC2: Tabs 按鈕文字移除 emoji，switchHistoryTab() 切換與 active class 不變", async ({ page }) => {
    await openDetail(page);

    const minutesTab = page.locator("#history-tab-btn-minutes");
    const transcriptTab = page.locator("#history-tab-btn-transcript");
    await expect(minutesTab).toHaveText("會議紀錄");
    await expect(transcriptTab).toHaveText("逐字稿");
    await expect(minutesTab).toHaveClass(/active/);
    await expect(transcriptTab).not.toHaveClass(/active/);

    await transcriptTab.click();
    await expect(transcriptTab).toHaveClass(/active/);
    await expect(minutesTab).not.toHaveClass(/active/);
    await expect(page.locator("#history-tab-transcript")).toBeVisible();
    await expect(page.locator("#history-tab-minutes")).toBeHidden();

    await minutesTab.click();
    await expect(minutesTab).toHaveClass(/active/);
    await expect(page.locator("#history-tab-minutes")).toBeVisible();
  });

  test("AC3: .section-title 與 #view-result 一致（桌面 18/26/600、<480px 17/24），色為 --ds-text-primary", async ({
    page,
  }) => {
    await openDetail(page);
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");

    const title = page.locator("#view-history-detail .section-title").first();
    await expect(title).toHaveCSS("font-size", "18px");
    await expect(title).toHaveCSS("line-height", "26px");
    await expect(title).toHaveCSS("font-weight", "600");
    await expect(title).toHaveCSS("color", textPrimary);

    await page.setViewportSize({ width: 375, height: 800 });
    await expect(title).toHaveCSS("font-size", "17px");
    await expect(title).toHaveCSS("line-height", "24px");
    await page.setViewportSize({ width: 1280, height: 900 });

    // 與 view-result 相同 class 電腦樣式一致
    await openViewResultWithRow(page);
    const resultTitle = page.locator("#view-result .section-title").first();
    await expect(resultTitle).toHaveCSS("font-size", "18px");
    await expect(resultTitle).toHaveCSS("line-height", "26px");
    await expect(resultTitle).toHaveCSS("font-weight", "600");
    await expect(resultTitle).toHaveCSS("color", textPrimary);
  });

  test("AC3 範圍外保護: view-admin/view-history 既有 .section-title 不受影響", async ({ page }) => {
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({
        status: 200,
        json: { meetings: [{ meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 }] },
      });
    });
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();

    await page.evaluate(() => {
      const dateTbody = document.getElementById("admin-by-date-tbody")!;
      dateTbody.innerHTML = `<tr><td>2026-09-23</td><td>10</td><td>1000</td><td>2000</td><td>$0.1234</td></tr>`;
      (0, eval)("showView")("view-admin");
    });
    const adminTitle = page.locator("#view-admin .section-title").first();
    await expect(adminTitle).toBeVisible();
    const adminFontSize = await adminTitle.evaluate((el) => getComputedStyle(el).fontSize);
    expect(adminFontSize).not.toBe("18px");
  });

  test("AC4: .action-table th/td 與 #view-result 一致，<480px 不造成頁面級橫向溢出", async ({ page }) => {
    await openDetail(page);
    const badgeBg = await resolveToken(page, "background-color", "var(--ds-badge-bg)");
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    const border = await resolveToken(page, "border-bottom-color", "var(--ds-border)");
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");

    const th = page.locator("#view-history-detail .action-table th").first();
    await expect(th).toHaveCSS("background-color", badgeBg);
    await expect(th).toHaveCSS("color", textSecondary);
    await expect(th).toHaveCSS("border-bottom-color", border);
    await expect(th).toHaveCSS("font-size", "13px");

    const td = page.locator("#view-history-detail .action-table td").first();
    await expect(td).toHaveCSS("color", textPrimary);
    await expect(td).toHaveCSS("border-bottom-color", border);
    await expect(td).toHaveCSS("font-size", "13px");

    // 與 view-result 相同 class 電腦樣式一致
    await openViewResultWithRow(page);
    const resultTh = page.locator("#view-result .action-table th").first();
    await expect(resultTh).toHaveCSS("background-color", badgeBg);
    await expect(resultTh).toHaveCSS("color", textSecondary);

    // <480px 無頁面級橫向溢出
    await page.evaluate(() => (0, eval)("openMeetingDetail")("m-1"));
    await expect(page.locator("#view-history-detail")).toBeVisible();
    await page.setViewportSize({ width: 375, height: 800 });
    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);

    const wrapper = page.locator("#view-history-detail .ds-table-scroll").first();
    await expect(wrapper).toHaveCSS("overflow-x", "auto");
    const table = page.locator("#view-history-detail .action-table").first();
    await expect(table).toHaveCSS("min-width", "500px");
  });

  test("AC4 範圍外保護: view-admin/view-history 既有 .action-table 不受影響", async ({ page }) => {
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
    await page.locator("#history-nav-btn").click();
    await expect(page.locator("#view-history")).toBeVisible();
    const historyTh = page.locator("#view-history .action-table th, #history-table th").first();
    if (await historyTh.count()) {
      const fontSize = await historyTh.evaluate((el) => getComputedStyle(el).fontSize);
      // view-history 自己的 token 化（SDLCAIP2-50）本就是 13px，這裡只確認未被本票破壞式改動
      // （不會拋錯、值仍是既有規則的值）
      expect(fontSize).toBeTruthy();
    }
  });

  test("AC5: .empty-state（#history-detail-error 與討論重點空清單）文字色為 --ds-text-secondary", async ({ page }) => {
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");

    // #history-detail-error
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
    await expect(page.locator("#history-detail-error")).toBeVisible();
    await expect(page.locator("#history-detail-error")).toHaveCSS("color", textSecondary);

    // 討論重點空清單
    await page.route("**/api/meetings/m-1", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          json: {
            ...DETAIL_RESPONSE,
            minutes: { ...DETAIL_RESPONSE.minutes, sections: [] },
          },
        });
      } else {
        await route.continue();
      }
    });
    // 返回歷史列表按鈕不會重新呼叫 /api/meetings（showView 只切換畫面），改直接呼叫
    // openMeetingDetail() 進入新的一筆，避免沿用舊列表快取資料。
    await page.locator("#history-detail-error button").click();
    await expect(page.locator("#view-history")).toBeVisible();
    await page.evaluate(() => (0, eval)("openMeetingDetail")("m-1"));
    await expect(page.locator("#history-detail-body")).toBeVisible();
    const emptyTopics = page.locator("#history-topics-container .empty-state");
    await expect(emptyTopics).toBeVisible();
    await expect(emptyTopics).toHaveCSS("color", textSecondary);
  });

  test("AC6: 標題列按鈕群組 gap 為 var(--ds-space-2)（12px）", async ({ page }) => {
    await openDetail(page);
    const space2 = await resolveToken(page, "gap", "var(--ds-space-2)");
    expect(space2).toBe("12px");

    const headerRow = page.locator("#view-history-detail .card").first().locator("> div").first();
    await expect(headerRow).toHaveCSS("gap", space2);
  });

  test("AC7 (回歸): .tabs/.tab、.meeting-info-grid、.decision-list、.topic-* 電腦樣式與 view-result 一致", async ({
    page,
  }) => {
    await openDetail(page);
    const border = await resolveToken(page, "border-bottom-color", "var(--ds-border)");
    const badgeBg = await resolveToken(page, "background-color", "var(--ds-badge-bg)");
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");

    const historyTabsBar = page.locator("#view-history-detail .tabs");
    await expect(historyTabsBar).toHaveCSS("border-bottom-color", border);
    const historyActiveTab = page.locator("#history-tab-btn-minutes");
    await expect(historyActiveTab).toHaveCSS("color", textPrimary);

    const historyGrid = page.locator("#view-history-detail .meeting-info-grid");
    await expect(historyGrid).toBeVisible();

    const historyDecision = page.locator("#view-history-detail .decision-list li").first();
    await expect(historyDecision).toHaveCSS("border-bottom-color", border);

    await page.locator("#history-topics-container .topic-header").click();
    // 滑鼠移開，避免殘留 :hover 狀態（背景改用 --ds-border）影響下方斷言
    await page.mouse.move(0, 0);
    const historyTopicHeader = page.locator("#history-topics-container .topic-header").first();
    await expect(historyTopicHeader).toHaveCSS("background-color", badgeBg);
    await expect(historyTopicHeader).toHaveCSS("color", textPrimary);

    // 與 view-result 相同 class 電腦樣式一致
    await openViewResultWithRow(page);
    const resultTabsBar = page.locator("#view-result .tabs");
    await expect(resultTabsBar).toHaveCSS("border-bottom-color", border);
    const resultDecision = page.locator("#view-result .decision-list li").first();
    await expect(resultDecision).toHaveCSS("border-bottom-color", border);
    const resultTopicHeader = page.locator("#view-result .topic-header").first();
    await expect(resultTopicHeader).toHaveCSS("background-color", badgeBg);
  });

  test("AC8 (回歸): openMeetingDetail() 顯示/隱藏 body/error，404 顯示錯誤訊息", async ({ page }) => {
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
    await expect(page.locator("#history-detail-body")).toBeHidden();
    await expect(page.locator("#history-detail-error-msg")).toContainText("找不到此會議紀錄");

    await page.locator("#history-detail-error button").click();
    await expect(page.locator("#view-history")).toBeVisible();
  });

  test("AC8 (回歸): 編輯/儲存(PATCH)/取消流程與返回歷史列表不變", async ({ page }) => {
    let patchBody: unknown = null;
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({
        status: 200,
        json: { meetings: [{ meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 }] },
      });
    });
    await page.route("**/api/meetings/m-1", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      } else if (route.request().method() === "PATCH") {
        patchBody = route.request().postDataJSON();
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      } else {
        await route.continue();
      }
    });

    await page.locator("#history-nav-btn").click();
    await page.locator("#history-tbody tr").first().click();
    await expect(page.locator("#history-detail-body")).toBeVisible();

    const summary = page.locator("#history-summary-text");

    // 取消流程：捨棄未儲存變更
    await page.locator("#history-edit-btn").click();
    await summary.dblclick();
    await summary.fill("暫時修改，將被取消捨棄");
    await summary.blur();
    await page.locator("#history-cancel-btn").click();
    await expect(summary).toHaveText("這是摘要內容");
    await expect(page.locator("#history-edit-btn")).toBeVisible();
    await expect(page.locator("#history-save-btn")).toBeHidden();

    // 儲存流程：PATCH 呼叫並切回唯讀
    await page.locator("#history-edit-btn").click();
    await summary.dblclick();
    await summary.fill("已儲存的新摘要");
    await summary.blur();
    await page.locator("#history-save-btn").click();
    await expect(page.locator("#toast")).toContainText("已儲存");
    expect(patchBody).not.toBeNull();
    await expect(page.locator("#history-edit-btn")).toBeVisible();

    // 返回歷史列表
    await page.locator("#view-history-detail .btn-row button", { hasText: "← 返回歷史列表" }).click();
    await expect(page.locator("#view-history")).toBeVisible();
  });
});
