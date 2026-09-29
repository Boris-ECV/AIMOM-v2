import { test, expect, type Page } from "@playwright/test";

// SDLCAIP2-55: Design System｜view-result「會議紀錄」分頁（#tab-minutes）五張卡片套用設計系統
//
// 沿用 view-result-transcript-design-system.spec.ts（SDLCAIP2-56）/
// view-progress-design-system.spec.ts（SDLCAIP2-46）的登入繞過、resolveToken 動態解析
// --ds-* token 手法，以及 view-admin-design-system.spec.ts 的 openViewResultWithRow
// 灌入 minutes 資料手法。
// AC 對應：
// AC1 - #view-result .section-title 套用 Heading h2/h2-mobile + --ds-text-primary；
//       不外洩到 view-admin/view-history 既有 .section-title
// AC2 - .meeting-info-grid label/input token 化，focus-visible outline，<480px 單欄，
//       onchange markModified() 回歸
// AC3 - #summary-text Body token 化，contenteditable 編輯提示色 token 化
// AC4 - #view-result .action-table th/td token 化；原 CROSS-VIEW LEAK GUARD（#view-history-detail
//       .action-table th 維持舊共用本體值）已於 SDLCAIP2-48 AC4 取代，該視圖也改用相同 token 值
// AC5 - .decision-list li 邊框/li::before 顏色 token 化，不留舊綠色
// AC6 - .topic-item/.topic-header/.topic-body token 化，hover、toggleTopic() 回歸
// AC7 - <480px 待辦事項表格捲動容器，不造成頁面級橫向溢出
// AC8 - 編輯/儲存 JS 行為回歸（#action-tbody/#decision-list/#topics-container）
// 附加 - SDLCAIP2-59/60：#template-select / #export-format-select 與
//        .meeting-info-grid input 電腦樣式仍一致（既有 SDLCAIP2-36/37 spec 已覆蓋，這裡只做簡短複查）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-result-cards-ds-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

const MINUTES = {
  job_id: "e2e-cards-ds-1",
  template: "general",
  meeting_info: { date: "2026-09-25", time: "10:00", location: "會議室 A", participants: ["王小明"] },
  summary: "這是一段摘要內容，用來檢查 #summary-text 的字體樣式。",
  action_items: [
    { owner: "王小明", task: "整理紀錄", due: "2026-09-30" },
    { owner: "李小華", task: "確認場地", due: "2026-10-01" },
  ],
  decisions: ["原始決議一", "原始決議二"],
  sections: [{ title: "討論重點一", content: "討論內容一" }],
};

async function openViewResultWithCards(page: Page, minutes: unknown = MINUTES) {
  await page.evaluate((m) => {
    const s = (0, eval)("state");
    s.jobId = (m as { job_id: string }).job_id;
    s.minutes = m;
    s.modified = false;
    (0, eval)("renderMinutes")();
    (0, eval)("showView")("view-result");
  }, minutes);
  await expect(page.locator("#view-result")).toBeVisible();
  await expect(page.locator("#tab-minutes")).toBeVisible();
}

async function openViewHistoryDetail(page: Page) {
  await page.route("**/api/meetings/m-cards-ds-1", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        meeting_id: "m-cards-ds-1",
        title: "跨頁保護驗證會議",
        transcript_text: "逐字稿內容",
        minutes: MINUTES,
        expires_at: 9999999999,
      },
    });
  });
  await page.evaluate(() => (0, eval)("openMeetingDetail")("m-cards-ds-1"));
  await expect(page.locator("#view-history-detail")).toBeVisible();
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

test.describe("Design System｜view-result 會議紀錄分頁五張卡片（SDLCAIP2-55）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
    await openViewResultWithCards(page);
  });

  test("AC1: #view-result .section-title 套用 Heading h2 token，不外洩到 view-admin/view-history", async ({
    page,
  }) => {
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");
    const title = page.locator("#view-result .section-title").first();
    await expect(title).toHaveCSS("font-size", "18px");
    await expect(title).toHaveCSS("line-height", "26px");
    await expect(title).toHaveCSS("font-weight", "600");
    await expect(title).toHaveCSS("color", textPrimary);

    await page.setViewportSize({ width: 375, height: 800 });
    await expect(title).toHaveCSS("font-size", "17px");
    await expect(title).toHaveCSS("line-height", "24px");
    await page.setViewportSize({ width: 1280, height: 900 });

    // 不外洩：其他畫面既有 .section-title 維持原本字級（非 18px）
    await page.evaluate(() => {
      const dateTbody = document.getElementById("admin-by-date-tbody")!;
      dateTbody.innerHTML = `<tr><td>2026-09-23</td><td>10</td><td>1000</td><td>2000</td><td>$0.1234</td></tr>`;
      (0, eval)("showView")("view-admin");
    });
    const adminTitle = page.locator("#view-admin .section-title").first();
    await expect(adminTitle).toBeVisible();
    const adminFontSize = await adminTitle.evaluate((el) => getComputedStyle(el).fontSize);
    expect(adminFontSize).not.toBe("18px");

    await page.evaluate(() => (0, eval)("showView")("view-history"));
    const historyTitle = page.locator("#view-history .section-title").first();
    await expect(historyTitle).toBeVisible();
    const historyFontSize = await historyTitle.evaluate((el) => getComputedStyle(el).fontSize);
    expect(historyFontSize).not.toBe("18px");
  });

  test("AC2: .meeting-info-grid label/input token 化、grid gap、focus-visible，<480px 單欄", async ({ page }) => {
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    const borderStrong = await resolveToken(page, "border-color", "var(--ds-border-strong)");
    const radiusSm = await resolveToken(page, "border-radius", "var(--ds-radius-sm)");
    const controlHDesktop = await resolveToken(page, "height", "var(--ds-control-h-desktop)");
    const focusRing = await resolveToken(page, "outline-color", "var(--ds-focus-ring)");
    const space4 = await resolveToken(page, "gap", "var(--ds-space-4)");

    const label = page.locator(".meeting-info-grid label").first();
    await expect(label).toHaveCSS("color", textSecondary);
    await expect(label).toHaveCSS("font-size", "13px");
    await expect(label).toHaveCSS("line-height", "18px");

    const input = page.locator("#meeting-date");
    await expect(input).toHaveCSS("border-color", borderStrong);
    await expect(input).toHaveCSS("border-radius", radiusSm);
    await expect(input).toHaveCSS("height", controlHDesktop);

    const grid = page.locator(".meeting-info-grid").first();
    await expect(grid).toHaveCSS("gap", space4);

    // focus-visible: 用鍵盤 Tab 聚焦（非滑鼠 click），outline 應為 2px --ds-focus-ring
    await input.focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    await expect(input).toBeFocused();
    await expect(input).toHaveCSS("outline-color", focusRing);
    await expect(input).toHaveCSS("outline-width", "2px");

    // <480px 單欄，寬度 100%
    await page.setViewportSize({ width: 375, height: 800 });
    const controlHMobile = await resolveToken(page, "height", "var(--ds-control-h-mobile)");
    await expect(grid).toHaveCSS("grid-template-columns", /^\d+(\.\d+)?px$/);
    const mobileInput = page.locator("#meeting-date");
    await expect(mobileInput).toHaveCSS("height", controlHMobile);
    const inputBox = await mobileInput.boundingBox();
    const gridBox = await grid.boundingBox();
    expect(inputBox).not.toBeNull();
    expect(gridBox).not.toBeNull();
    // 單欄下 input 寬度應接近 grid 容器寬度（100%，允許 grid padding/border 誤差）
    expect(inputBox!.width).toBeGreaterThan(gridBox!.width - 5);
  });

  test("AC2 回歸: onchange markModified() 打字+change 顯示 #modified-badge", async ({ page }) => {
    const badge = page.locator("#modified-badge");
    await expect(badge).toBeHidden();

    const input = page.locator("#meeting-location");
    await input.fill("3樓會議室");
    await input.dispatchEvent("change");

    await expect(badge).toBeVisible();
    await expect(badge).toContainText("未儲存修改");
  });

  test("AC3: #summary-text Body token 化（桌面/手機），contenteditable 編輯提示色 token 化", async ({ page }) => {
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");
    const summary = page.locator("#summary-text");
    await expect(summary).toHaveCSS("color", textPrimary);
    await expect(summary).toHaveCSS("font-size", "15px");
    await expect(summary).toHaveCSS("line-height", "28px");

    await page.setViewportSize({ width: 375, height: 800 });
    await expect(summary).toHaveCSS("font-size", "14px");
    await expect(summary).toHaveCSS("line-height", "26px");
    await page.setViewportSize({ width: 1280, height: 900 });

    const focusRing = await resolveToken(page, "outline-color", "var(--ds-focus-ring)");
    const badgeBg = await resolveToken(page, "background-color", "var(--ds-badge-bg)");
    await summary.dblclick();
    await expect(summary).toHaveAttribute("contenteditable", "true");
    await expect(summary).toHaveCSS("outline-color", focusRing);
    await expect(summary).toHaveCSS("background-color", badgeBg);
  });

  test("AC4: #view-result .action-table th/td token 化；跨頁洩漏保護 #view-history-detail 維持舊值", async ({
    page,
  }) => {
    const badgeBg = await resolveToken(page, "background-color", "var(--ds-badge-bg)");
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    const border = await resolveToken(page, "border-bottom-color", "var(--ds-border)");
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");

    const th = page.locator("#view-result .action-table th").first();
    await expect(th).toHaveCSS("background-color", badgeBg);
    await expect(th).toHaveCSS("color", textSecondary);
    await expect(th).toHaveCSS("border-bottom-color", border);
    await expect(th).toHaveCSS("font-size", "13px");

    const td = page.locator("#view-result .action-table td").first();
    await expect(td).toHaveCSS("color", textPrimary);
    await expect(td).toHaveCSS("border-bottom-color", border);
    await expect(td).toHaveCSS("font-size", "13px");

    // 原 CROSS-VIEW LEAK GUARD 斷言 view-history-detail 的 .action-table th 維持舊共用本體值，
    // 已被 SDLCAIP2-48 AC4 取代（superseded by SDLCAIP2-48 AC4）：該票為 #view-history-detail
    // 新增了與 #view-result 相同數值的範圍限定覆寫規則，此處改為斷言新 token 值一致。
    await openViewHistoryDetail(page);
    const detailTh = page.locator("#view-history-detail .action-table th").first();
    await expect(detailTh).toBeVisible();
    await expect(detailTh).toHaveCSS("background-color", badgeBg);
    await expect(detailTh).toHaveCSS("color", textSecondary);
    await expect(detailTh).toHaveCSS("border-bottom-color", border);
    await expect(detailTh).toHaveCSS("font-size", "13px");
  });

  test("AC5: .decision-list li 邊框/li::before 顏色 token 化，不留舊綠色", async ({ page }) => {
    const border = await resolveToken(page, "border-bottom-color", "var(--ds-border)");
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");
    const success = await resolveToken(page, "color", "var(--success)");

    const li = page.locator(".decision-list li").first();
    await expect(li).toHaveCSS("border-bottom-color", border);

    const beforeColor = await li.evaluate((el) => getComputedStyle(el, "::before").color);
    expect(beforeColor).toBe(textPrimary);
    expect(beforeColor).not.toBe("rgb(34, 197, 94)");
    expect(beforeColor).not.toBe(success);
  });

  test("AC6: .topic-item/.topic-header/.topic-body token 化，hover 與 toggleTopic() 回歸", async ({ page }) => {
    const border = await resolveToken(page, "border-color", "var(--ds-border)");
    const badgeBg = await resolveToken(page, "background-color", "var(--ds-badge-bg)");
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    const fontSans = await resolveToken(page, "font-family", "var(--ds-font-sans)");

    const item = page.locator(".topic-item").first();
    await expect(item).toHaveCSS("border-color", border);

    const header = page.locator(".topic-header").first();
    await expect(header).toHaveCSS("background-color", badgeBg);
    await expect(header).toHaveCSS("color", textPrimary);

    const body = page.locator("#topic-body-0");
    await expect(body).toHaveCSS("color", textSecondary);
    await expect(body).toHaveCSS("font-family", fontSans);
    await expect(body).not.toHaveClass(/open/);

    await header.hover();
    const hoverBg = await header.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(hoverBg).toBe(border);
    expect(hoverBg).not.toBe(badgeBg);

    await header.click();
    await expect(body).toHaveClass(/open/);
    await expect(body).toBeVisible();
    await header.click();
    await expect(body).not.toHaveClass(/open/);
  });

  test("AC7: <480px 待辦事項表格用 .ds-table-scroll 捲動容器，不造成頁面級橫向溢出", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);

    const wrapper = page.locator("#view-result .ds-table-scroll").first();
    await expect(wrapper).toHaveCSS("overflow-x", "auto");

    const table = page.locator("#view-result .action-table").first();
    await expect(table).toHaveCSS("min-width", "500px");
  });

  test("AC8 回歸: 待辦事項雙擊編輯 + markModified 顯示 #modified-badge；相關 id/class 存在", async ({ page }) => {
    await expect(page.locator("#action-tbody")).toBeAttached();
    await expect(page.locator("#decision-list")).toBeAttached();
    await expect(page.locator("#topics-container")).toBeAttached();
    await expect(page.locator("#action-tbody tr")).toHaveCount(2);

    const badge = page.locator("#modified-badge");
    await expect(badge).toBeHidden();

    const cell = page.locator("#action-tbody tr").first().locator("td").first();
    await cell.dblclick();
    await expect(cell).toHaveAttribute("contenteditable", "true");
    await cell.evaluate((el) => {
      el.textContent = "陳大文";
    });
    await cell.blur();

    await expect(badge).toBeVisible();
  });

  test("附加(SDLCAIP2-59/60 複查): #template-select / #export-format-select 電腦樣式仍與 .meeting-info-grid input 一致", async ({
    page,
  }) => {
    const properties = ["borderWidth", "borderStyle", "borderColor", "borderRadius", "color", "fontFamily", "fontSize", "padding"];

    async function styleOf(selector: string) {
      return page.locator(selector).first().evaluate((el, props: string[]) => {
        const computed = getComputedStyle(el);
        return Object.fromEntries(props.map((p) => [p, (computed as any)[p]]));
      }, properties);
    }

    const referenceStyle = await styleOf(".meeting-info-grid input");
    expect(await styleOf("#template-select")).toEqual(referenceStyle);
    expect(await styleOf("#export-format-select")).toEqual(referenceStyle);
  });
});
