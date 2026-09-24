import { test, expect } from "@playwright/test";

// SDLCAIP2-45: Design System｜管理者儀表板頁 view-admin
//
// 沿用 design-system-foundation.spec.ts（SDLCAIP2-44）既有的登入繞過與 state/showView
// evaluate 手法。
// AC 對應：
// AC1 - view-admin 卡片延續既有 .card token（回歸確認）
// AC2 - view-admin 內表格改用 --ds-* token，且僅影響 view-admin（不影響共用 .action-table 基底規則）
// AC3 - 「依日期」「依使用者」子標題套用 design-system 字體規則
// AC4 - 窄螢幕（<480px）下表格不發生橫向溢出跑版
// AC5 - view-admin 內無殘留裝飾性 icon（回歸確認）
// AC6 - 範圍外畫面視覺不受非預期影響（回歸保護）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-admin-design-system-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

// view-admin 的表格資料一般透過 /api/admin/usage 取得（僅管理者角色可見）。
// 為了獨立於後端角色判斷之外驗證純樣式行為，直接以 evaluate 呼叫 showView('view-admin')
// 並手動填入一列表格資料，讓 th/td 有實際內容可供 computed style 檢查。
async function openViewAdminWithRow(page: import("@playwright/test").Page) {
  await page.evaluate(() => {
    const dateTbody = document.getElementById("admin-by-date-tbody")!;
    dateTbody.innerHTML = `<tr><td>2026-09-23</td><td>10</td><td>1000</td><td>2000</td><td>$0.1234</td></tr>`;
    const userTbody = document.getElementById("admin-by-user-tbody")!;
    userTbody.innerHTML = `<tr><td>e2e-view-admin-design-system-user@example.com</td><td>10</td><td>1000</td><td>2000</td><td>$0.1234</td></tr>`;
    (0, eval)("showView")("view-admin");
  });
  await expect(page.locator("#view-admin")).toBeVisible();
}

// 讓 view-result 顯示至少一列 .action-table 資料，作為範圍外（AC2/AC6）比對基準。
async function openViewResultWithRow(page: import("@playwright/test").Page) {
  await page.evaluate(() => {
    const s = (0, eval)("state");
    s.jobId = "e2e-view-admin-ds-1";
    s.minutes = {
      job_id: "e2e-view-admin-ds-1",
      template: "general",
      meeting_info: { date: "", time: "", location: "", participants: [] },
      summary: "",
      // 兩列資料，避免只有單列時觸發 tr:last-child td { border-bottom: none; } 影響邊框色檢查
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

test.describe("Design System｜管理者儀表板頁 view-admin（SDLCAIP2-45）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
  });

  test("AC1: view-admin 卡片延續既有 .card token（回歸確認）", async ({ page }) => {
    await openViewAdminWithRow(page);
    const card = page.locator("#view-admin .card").first();
    const styles = await card.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderColor: cs.borderColor, borderRadius: cs.borderRadius };
    });
    expect(styles.background).toBe("rgb(255, 255, 255)"); // --ds-surface
    expect(styles.borderColor).toBe("rgb(228, 227, 223)"); // --ds-border #E4E3DF
    expect(styles.borderRadius).toBe("10px"); // --ds-radius-md
  });

  test("AC2 + AC6: view-admin 表格改用 --ds-* token，且不影響共用 .action-table 基底規則", async ({ page }) => {
    await openViewAdminWithRow(page);

    const adminTh = page.locator("#view-admin .action-table th").first();
    const adminThStyles = await adminTh.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, color: cs.color, borderBottomColor: cs.borderBottomColor };
    });
    expect(adminThStyles.background).toBe("rgb(239, 238, 234)"); // --ds-badge-bg
    expect(adminThStyles.color).toBe("rgb(107, 106, 100)"); // --ds-text-secondary
    expect(adminThStyles.borderBottomColor).toBe("rgb(228, 227, 223)"); // --ds-border

    const adminTd = page.locator("#view-admin .action-table td").first();
    const adminTdStyles = await adminTd.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { color: cs.color, borderBottomColor: cs.borderBottomColor };
    });
    expect(adminTdStyles.color).toBe("rgb(31, 30, 28)"); // --ds-text-primary
    expect(adminTdStyles.borderBottomColor).toBe("rgb(228, 227, 223)"); // --ds-border

    // 關鍵回歸保護：view-result 的共用 .action-table 基底規則不得被 view-admin 的範圍限定選取器影響
    await openViewResultWithRow(page);
    const resultTh = page.locator("#view-result .action-table th").first();
    const resultThStyles = await resultTh.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, color: cs.color, borderBottomColor: cs.borderBottomColor };
    });
    expect(resultThStyles.background).toBe("rgb(248, 250, 252)"); // 舊 --bg #F8FAFC，未被覆寫
    expect(resultThStyles.color).toBe("rgb(100, 116, 139)"); // 舊 --muted #64748B，未被覆寫
    expect(resultThStyles.borderBottomColor).toBe("rgb(226, 232, 240)"); // 舊 --border #E2E8F0，未被覆寫
    // 確認明確不等於新 view-admin 專用 token 數值
    expect(resultThStyles.background).not.toBe("rgb(239, 238, 234)");
    expect(resultThStyles.color).not.toBe("rgb(107, 106, 100)");
    expect(resultThStyles.borderBottomColor).not.toBe("rgb(228, 227, 223)");

    const resultTd = page.locator("#view-result .action-table td").first();
    const resultTdBorder = await resultTd.evaluate((el) => getComputedStyle(el).borderBottomColor);
    expect(resultTdBorder).toBe("rgb(226, 232, 240)"); // 舊 --border，未被覆寫
    expect(resultTdBorder).not.toBe("rgb(228, 227, 223)");
  });

  test("AC3: 「依日期」「依使用者」子標題套用 design-system 字體規則", async ({ page }) => {
    await openViewAdminWithRow(page);
    const h4s = page.locator("#view-admin h4");
    await expect(h4s).toHaveCount(2);
    const first = await h4s.first().evaluate((el) => {
      const cs = getComputedStyle(el);
      return { fontSize: cs.fontSize, fontWeight: cs.fontWeight, color: cs.color, lineHeight: cs.lineHeight };
    });
    expect(first.fontSize).toBe("14px");
    expect(first.fontWeight).toBe("500");
    expect(first.color).toBe("rgb(107, 106, 100)"); // --ds-text-secondary
    expect(first.lineHeight).toBe("20px");

    // 不影響同一 .card 內既有 .section-title
    const sectionTitle = page.locator("#view-admin .section-title").first();
    const sectionTitleStyles = await sectionTitle.evaluate((el) => getComputedStyle(el).fontSize);
    expect(sectionTitleStyles).not.toBe("14px");
  });

  test("AC4: 窄螢幕（<480px）下表格不發生橫向溢出跑版", async ({ page }) => {
    await openViewAdminWithRow(page);
    await page.setViewportSize({ width: 375, height: 800 });

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);

    const wrapper = page.locator("#view-admin .ds-table-scroll").first();
    const wrapperOverflowX = await wrapper.evaluate((el) => getComputedStyle(el).overflowX);
    expect(wrapperOverflowX).toBe("auto");

    const tableMinWidth = await page.locator("#view-admin .action-table").first().evaluate((el) => getComputedStyle(el).minWidth);
    expect(tableMinWidth).toBe("560px");
  });

  test("AC5: view-admin 內無殘留裝飾性 icon（回歸確認）", async ({ page }) => {
    await openViewAdminWithRow(page);
    const html = await page.locator("#view-admin").innerHTML();
    // eslint-disable-next-line no-misleading-character-class
    const emojiPattern = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    expect(emojiPattern.test(html)).toBe(false);
  });

  test("AC6: 範圍外畫面（view-upload header）視覺不受本票影響", async ({ page }) => {
    // 對照組：view-upload 卡片（沿用 SDLCAIP2-44 既有 token），確認本票未新增非預期覆寫
    const card = page.locator("#view-upload .card").first();
    const styles = await card.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderRadius: cs.borderRadius, padding: cs.padding };
    });
    expect(styles.background).toBe("rgb(255, 255, 255)");
    expect(styles.borderRadius).toBe("10px");
    expect(styles.padding).toBe("32px");

    const adminBtnText = await page.locator("#history-nav-btn").evaluate((el) => el.textContent || "");
    expect(adminBtnText.trim()).toBe("歷史紀錄");
  });
});
