import { test, expect, type Page } from "@playwright/test";

// SDLCAIP2-56: Design System｜view-result 逐字稿分頁（發言人重命名區 + 逐字稿列表）套用設計系統
//
// 沿用 speaker-naming.spec.ts（SDLCAIP2-18）的登入繞過與 state 注入手法，
// 以及 view-history-design-system.spec.ts / view-admin-design-system.spec.ts
// （SDLCAIP2-45/50）以 getComputedStyle 動態解析 --ds-* token 實際值後再用
// toHaveCSS 斷言的手法（避免把 token 十六進位值寫死在測試裡）。
// AC 對應：
// AC1 - #speaker-rename-area h4 文字移除 🎤 前綴
// AC2 - #speaker-rename-area 灰階 token 化（background/border/radius/h4 color），
//       .rename-row input 邊框/圓角/高度 token 化，送出按鈕維持共用 .btn 系列 class
// AC3 - .seg-row/.seg-time/.seg-text 套用 --ds-* token
// AC4 - .speaker-chip 圓角/字級 token 化，行內動態 background 指派邏輯不變
// AC5 - <480px .seg-row 垂直堆疊，不橫向溢出、不重疊
// AC6 - submitSpeakerNames() API 呼叫與 #rename-rows 綁定回歸
// 附加：view-history-detail 逐字稿 <pre> 不受影響（範圍外保護）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const SEGMENTS = [
  { start: 0, speaker: "SPEAKER_A", text: "大家好，我們開始開會。" },
  { start: 5, speaker: "SPEAKER_B", text: "好的，我先報告進度。" },
];

async function loginBypass(page: Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-result-transcript-ds-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

async function openTranscriptTab(page: Page, jobId = "e2e-transcript-ds-1", segments: unknown = SEGMENTS) {
  await page.evaluate(
    ({ jobId, segments }) => {
      const s = (0, eval)("state");
      s.jobId = jobId;
      s.segments = segments;
      s.speakers = {};
      (0, eval)("renderTranscript")();
      (0, eval)("showView")("view-result");
      (0, eval)("switchTab")("transcript");
    },
    { jobId, segments },
  );
  await expect(page.locator("#view-result")).toBeVisible();
  await expect(page.locator("#tab-transcript")).toBeVisible();
}

// 解析 --ds-* token 在瀏覽器中實際被 getComputedStyle 解析出的值（非測試裡寫死十六進位），
// 透過臨時 probe 元素套用 var(--token) 讀出解析結果，再拿來跟目標元素的 toHaveCSS 比對。
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

test.describe("Design System｜view-result 逐字稿分頁（SDLCAIP2-56）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
    await openTranscriptTab(page);
  });

  test("AC1: 發言人重命名區 h4 文字移除 🎤 前綴", async ({ page }) => {
    const h4 = page.locator("#speaker-rename-area h4");
    await expect(h4).toHaveText("發言人重命名（點擊輸入框修改名稱）");
    const text = await h4.textContent();
    expect(text || "").not.toContain("🎤");
  });

  test("AC2: #speaker-rename-area 灰階 token 化，不留舊綠色，h4 用 --ds-text-secondary", async ({ page }) => {
    const area = page.locator("#speaker-rename-area");
    const surface = await resolveToken(page, "background-color", "var(--ds-surface)");
    const border = await resolveToken(page, "border-color", "var(--ds-border)");
    const radiusMd = await resolveToken(page, "border-radius", "var(--ds-radius-md)");
    await expect(area).toHaveCSS("background-color", surface);
    await expect(area).toHaveCSS("border-color", border);
    await expect(area).toHaveCSS("border-radius", radiusMd);

    // 明確排除舊綠色值（第一輪 G1 退回意見：不可留 success 綠色）
    await expect(area).not.toHaveCSS("background-color", "rgb(240, 253, 244)");
    await expect(area).not.toHaveCSS("border-color", "rgb(187, 247, 208)");

    const h4 = page.locator("#speaker-rename-area h4");
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    await expect(h4).toHaveCSS("color", textSecondary);
    // 排除舊 --success 綠色
    await expect(h4).not.toHaveCSS("color", "rgb(34, 197, 94)");

    const input = page.locator(".rename-row input").first();
    const borderStrong = await resolveToken(page, "border-color", "var(--ds-border-strong)");
    const radiusSm = await resolveToken(page, "border-radius", "var(--ds-radius-sm)");
    const controlHDesktop = await resolveToken(page, "height", "var(--ds-control-h-desktop)");
    await expect(input).toHaveCSS("border-color", borderStrong);
    await expect(input).toHaveCSS("border-radius", radiusSm);
    await expect(input).toHaveCSS("height", controlHDesktop);

    const submitBtn = page.locator("#submit-speaker-names-btn");
    await expect(submitBtn).toHaveClass(/\bbtn\b/);
    await expect(submitBtn).toHaveClass(/\bbtn-primary\b/);
    await expect(submitBtn).toHaveClass(/\bbtn-sm\b/);
  });

  test("AC2 (手機): .rename-row input 高度改用 --ds-control-h-mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    const input = page.locator(".rename-row input").first();
    const controlHMobile = await resolveToken(page, "height", "var(--ds-control-h-mobile)");
    await expect(input).toHaveCSS("height", controlHMobile);
  });

  test("AC3: .seg-row/.seg-time/.seg-text 套用 --ds-* token", async ({ page }) => {
    const row = page.locator(".seg-row").first();
    const border = await resolveToken(page, "border-bottom-color", "var(--ds-border)");
    await expect(row).toHaveCSS("border-bottom-color", border);

    const time = page.locator(".seg-time").first();
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    const fontMono = await resolveToken(page, "font-family", "var(--ds-font-mono)");
    await expect(time).toHaveCSS("color", textSecondary);
    await expect(time).toHaveCSS("font-family", fontMono);

    const text = page.locator(".seg-text").first();
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");
    await expect(text).toHaveCSS("color", textPrimary);
    await expect(text).toHaveCSS("font-size", "15px");
    await expect(text).toHaveCSS("line-height", "28px");
  });

  test("AC4: .speaker-chip 圓角/字級 token 化，動態 background 顏色仍套用且不同講者不同色", async ({ page }) => {
    const chips = page.locator(".speaker-chip");
    await expect(chips).toHaveCount(2);

    const radiusPill = await resolveToken(page, "border-radius", "var(--ds-radius-pill)");
    await expect(chips.first()).toHaveCSS("border-radius", radiusPill);
    await expect(chips.nth(1)).toHaveCSS("border-radius", radiusPill);
    await expect(chips.first()).toHaveCSS("font-size", "13px");
    await expect(chips.nth(1)).toHaveCSS("font-size", "13px");

    const colorA = await chips.first().evaluate((el) => getComputedStyle(el).backgroundColor);
    const colorB = await chips.nth(1).evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(colorA).toBeTruthy();
    expect(colorB).toBeTruthy();
    expect(colorA).not.toBe(colorB);

    // 行內動態 style 仍存在（非本票新增規則覆寫掉）
    const inlineBg = await chips.first().evaluate((el) => (el as HTMLElement).style.backgroundColor);
    expect(inlineBg).toBeTruthy();
  });

  test("AC5: <480px .seg-row 垂直堆疊，不橫向溢出、三欄不重疊", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });

    const row = page.locator(".seg-row").first();
    await expect(row).toHaveCSS("flex-direction", "column");

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);

    const timeBox = await row.locator(".seg-time").boundingBox();
    const speakerBox = await row.locator(".seg-speaker").boundingBox();
    const textBox = await row.locator(".seg-text").boundingBox();
    expect(timeBox).not.toBeNull();
    expect(speakerBox).not.toBeNull();
    expect(textBox).not.toBeNull();

    // 三行堆疊：依 DOM 順序時間 -> 講者 -> 文字，各自的垂直範圍不重疊（y 值遞增且不交疊）
    expect(timeBox!.y + timeBox!.height).toBeLessThanOrEqual(speakerBox!.y + 1);
    expect(speakerBox!.y + speakerBox!.height).toBeLessThanOrEqual(textBox!.y + 1);
  });

  test("AC6: 送出命名仍呼叫 /api/speaker-names 並帶相同 payload；#rename-rows 綁定不變（回歸）", async ({ page }) => {
    let requestBody: unknown = null;
    await page.route("**/api/speaker-names", async (route) => {
      requestBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        json: {
          job_id: "e2e-transcript-ds-1",
          speakers: ["王小明", "SPEAKER_B"],
          segments: [
            { start: 0, speaker: "王小明", text: "大家好，我們開始開會。" },
            { start: 5, speaker: "SPEAKER_B", text: "好的，我先報告進度。" },
          ],
        },
      });
    });

    const rows = page.locator("#rename-rows .rename-row");
    await expect(rows).toHaveCount(2);
    const firstInput = rows.nth(0).locator("input");
    const onchangeAttr = await firstInput.getAttribute("onchange");
    expect(onchangeAttr).toContain("renameSpeaker(");

    await firstInput.fill("王小明");
    await firstInput.dispatchEvent("change");
    await page.locator("#submit-speaker-names-btn").click();

    await expect.poll(() => requestBody).toEqual({
      job_id: "e2e-transcript-ds-1",
      speaker_names: { SPEAKER_A: "王小明" },
    });

    await expect(page.locator("#transcript-container")).toContainText("王小明");
  });

  test("範圍外保護: view-history-detail 逐字稿 <pre> 不受本票 CSS 影響", async ({ page }) => {
    await page.route("**/api/meetings/m-transcript-ds", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          meeting_id: "m-transcript-ds",
          title: "範圍外驗證會議",
          transcript_text: "純文字逐字稿內容，不含 .seg-row 結構。",
          minutes: {
            meeting_info: { date: "", time: "", location: "", participants: [] },
            summary: "",
            action_items: [],
            decisions: [],
            sections: [],
          },
          expires_at: 9999999999,
        },
      });
    });
    await page.evaluate(() => (0, eval)("openMeetingDetail")("m-transcript-ds"));
    await expect(page.locator("#view-history-detail")).toBeVisible();
    await page.evaluate(() => (0, eval)("switchHistoryTab")("transcript"));

    const pre = page.locator("#history-transcript-container pre");
    await expect(pre).toBeVisible();
    await expect(pre).toContainText("純文字逐字稿內容");
    // 不含本票新增的任何 class 選取器
    const hasSegClasses = await page.evaluate(
      () => document.querySelectorAll("#history-transcript-container .seg-row, #history-transcript-container .speaker-chip").length,
    );
    expect(hasSegClasses).toBe(0);
  });
});
