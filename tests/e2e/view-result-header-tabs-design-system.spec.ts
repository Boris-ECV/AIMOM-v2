import { test, expect, type Page } from "@playwright/test";

// SDLCAIP2-54: Design System｜view-result 標題／操作列／分頁 Tabs 套用設計系統
//
// 沿用 view-result-cards-design-system.spec.ts（SDLCAIP2-55）/
// view-result-transcript-design-system.spec.ts（SDLCAIP2-56）的登入繞過、
// resolveToken 動態解析 --ds-* token 手法，以及 result-action-row-layout.spec.ts
// （SDLCAIP2-42）的操作列排版回歸驗證手法。
// AC 對應：
// AC1 - #view-result h2 文字「會議紀錄」（無 emoji），token 18/26/600 + --ds-text-primary，
//       <480px 17/24
// AC2 - #result-meta caption token 13/18/400 + --ds-text-secondary
// AC3 - 1280px/480px 六控制項同排、順序不變、清除暫存/新錄音靠右對齊，按鈕文字不變（回歸）
// AC4 - 四個按鈕仍呼叫 regenerateSummary()/exportSelectedFormat()/cleanupAndReset()/
//       showView('view-upload')（回歸）
// AC5 - 兩個 select 套用 .input class（高度/邊框/圓角/focus），option 不變，
//       <480px width:auto 覆寫
// AC6 - .tab.active/.tab 顏色字重/底線/底部邊框 token 化，文字移除 emoji，switchTab() 回歸
//       （揭露：history-detail tabs 樣式同步變化）
// AC7 - <480px tabs 不換行、不溢出，等寬 flex:1
// AC8 - #modified-badge/#low-confidence-badge 符號與琥珀色不變（回歸）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-result-header-tabs-ds-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

const MINUTES = {
  job_id: "e2e-header-tabs-ds-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

async function openViewResult(page: Page, minutes: unknown = MINUTES) {
  await page.evaluate((m) => {
    const s = (0, eval)("state");
    s.jobId = (m as { job_id: string }).job_id;
    s.minutes = m;
    s.modified = false;
    (0, eval)("renderMinutes")();
    (0, eval)("showView")("view-result");
    document.getElementById("result-meta")!.textContent = `Job ID: ${(m as { job_id: string }).job_id} | 0 段逐字稿`;
  }, minutes);
  await expect(page.locator("#view-result")).toBeVisible();
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

test.describe("Design System｜view-result 標題／操作列／分頁 Tabs（SDLCAIP2-54）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
    await openViewResult(page);
  });

  test("AC1: h2 文字「會議紀錄」（無 emoji），token 18/26/600 + --ds-text-primary", async ({ page }) => {
    const h2 = page.locator("#view-result h2");
    await expect(h2).toHaveText("會議紀錄");
    const text = await h2.textContent();
    expect(text || "").not.toContain("📋");

    await expect(h2).toHaveCSS("font-size", "18px");
    await expect(h2).toHaveCSS("line-height", "26px");
    await expect(h2).toHaveCSS("font-weight", "600");
    const textPrimary = await resolveToken(page, "color", "var(--ds-text-primary)");
    await expect(h2).toHaveCSS("color", textPrimary);
  });

  test("AC1 (手機): <480px h2 17px/24px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    const h2 = page.locator("#view-result h2");
    await expect(h2).toHaveCSS("font-size", "17px");
    await expect(h2).toHaveCSS("line-height", "24px");
  });

  test("AC2: #result-meta caption token 13/18/400 + --ds-text-secondary", async ({ page }) => {
    const meta = page.locator("#result-meta");
    await expect(meta).toHaveCSS("font-size", "13px");
    await expect(meta).toHaveCSS("line-height", "18px");
    await expect(meta).toHaveCSS("font-weight", "400");
    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    await expect(meta).toHaveCSS("color", textSecondary);
  });

  const CONTROL_IDS = [
    "#template-select",
    "#regenerate-btn",
    "#export-format-select",
    "#export-confirm-btn",
    "#cleanup-btn",
    "#new-recording-btn",
  ];

  async function assertControlTextsAndOrder(page: Page) {
    const boxes = [];
    for (const id of CONTROL_IDS) {
      const box = await page.locator(id).boundingBox();
      expect(box).not.toBeNull();
      boxes.push(box!);
    }

    // 左側四項閱讀順序（同排時 x 遞增；換行時新行 y 更大）：template -> regenerate -> export-format -> export
    for (let i = 1; i < 4; i++) {
      const prev = boxes[i - 1];
      const cur = boxes[i];
      const sameRow = Math.abs(cur.y - prev.y) <= 4;
      if (sameRow) {
        expect(cur.x).toBeGreaterThanOrEqual(prev.x);
      } else {
        expect(cur.y).toBeGreaterThan(prev.y);
      }
    }
    // cleanup -> new-recording：同排時 x 遞增，換行時新行在 cleanup 之後
    const cleanupBox = boxes[4];
    const newRecordingBox = boxes[5];
    const sameRow = Math.abs(newRecordingBox.y - cleanupBox.y) <= 4;
    if (sameRow) {
      expect(newRecordingBox.x).toBeGreaterThanOrEqual(cleanupBox.x);
    } else {
      expect(newRecordingBox.y).toBeGreaterThan(cleanupBox.y);
    }

    // 按鈕文字不變
    await expect(page.locator("#regenerate-btn")).toHaveText("重新產生");
    await expect(page.locator("#export-confirm-btn")).toHaveText("匯出");
    await expect(page.locator("#cleanup-btn")).toHaveText("清除暫存");
    await expect(page.locator("#new-recording-btn")).toHaveText("+ 新錄音");

    return boxes;
  }

  test("AC3 (1280px 回歸): 六控制項同排、順序不變、右側靠右、按鈕文字不變", async ({ page }) => {
    const boxes = await assertControlTextsAndOrder(page);

    // 1280px 容器夠寬，六個控制項應在同一視覺列（同排不換行）
    const tops = boxes.map((b) => b.y);
    expect(Math.max(...tops) - Math.min(...tops)).toBeLessThanOrEqual(6);

    // 清除暫存/新錄音靠右對齊：右緣接近容器（.btn-row 外層）右緣
    const container = page.locator("#result-action-group-content").locator("..");
    const containerBox = await container.boundingBox();
    expect(containerBox).not.toBeNull();
    const newRecordingBox = boxes[5];
    expect(containerBox!.x + containerBox!.width - (newRecordingBox.x + newRecordingBox.width)).toBeLessThanOrEqual(4);
  });

  // 註：480px 容器（main max-width:900px, padding 24px -> 內容區僅 432px）本就無法讓六個
  // 帶 label 的控制項擠進單一橫排，且獨占一行的「清除暫存/新錄音」群組因 flex-wrap 換行後
  // justify-content:space-between 對單一子群組不生效，實測也不會貼齊容器右緣。這兩點皆為
  // 本票開始之前即存在的行為 —— 已用 HEAD~1（SDLCAIP2-55 版本，本票變更前）的 index.html
  // 實測比對，換行位置與各元素像素座標（x/y）與本票之後幾乎一致（僅 1px 內差異，屬瀏覽器
  // layout 捨入），證實本票（AC5 的 .input + width:auto 中和覆寫）沒有讓 480px 的換行狀態
  // 變得比 pre-story 更差。與 docs/design/SDLCAIP2-54.md 決策 3 的結論一致：AC3「480px
  // 不變」在此語境下指「本票不得新增任何進一步影響換行狀態的 CSS」，而非「六控制項需真正
  // 擠進單一橫排且靠右對齊」（後者原本就不成立，非本票造成）。
  // 因此這裡改為驗證：換行後的閱讀順序（左到右／由上到下）不變、按鈕文字不變、且各元素的
  // 像素座標與 pre-story 實測快照一致（±3px 容忍度）—— 這才是本票語境下真正可驗證的迴歸。
  const PRE_STORY_480_SNAPSHOT: Record<string, { x: number; y: number }> = {
    "#template-select": { x: 53, y: 175 },
    "#regenerate-btn": { x: 193, y: 175 },
    "#export-format-select": { x: 339, y: 175 },
    "#export-confirm-btn": { x: 24, y: 225 },
    "#cleanup-btn": { x: 24, y: 275 },
    "#new-recording-btn": { x: 115, y: 275 },
  };

  test("AC3 (480px 回歸): 換行順序與座標與 pre-story 快照一致、按鈕文字不變", async ({ page }) => {
    await page.setViewportSize({ width: 480, height: 800 });
    const boxes = await assertControlTextsAndOrder(page);

    CONTROL_IDS.forEach((id, i) => {
      const expected = PRE_STORY_480_SNAPSHOT[id];
      expect(Math.abs(boxes[i].x - expected.x)).toBeLessThanOrEqual(3);
      expect(Math.abs(boxes[i].y - expected.y)).toBeLessThanOrEqual(3);
    });
  });

  test("AC4 (回歸): 按鈕仍呼叫既有函式，參數不變", async ({ page }) => {
    await expect(page.locator("#regenerate-btn")).toHaveAttribute("onclick", "regenerateSummary()");
    await expect(page.locator("#export-confirm-btn")).toHaveAttribute("onclick", "exportSelectedFormat()");
    await expect(page.locator("#cleanup-btn")).toHaveAttribute("onclick", "cleanupAndReset()");
    await expect(page.locator("#new-recording-btn")).toHaveAttribute("onclick", "showView('view-upload')");

    const fnsExist = await page.evaluate(() => ({
      regenerateSummary: typeof (0, eval)("regenerateSummary") === "function",
      exportSelectedFormat: typeof (0, eval)("exportSelectedFormat") === "function",
      cleanupAndReset: typeof (0, eval)("cleanupAndReset") === "function",
    }));
    expect(fnsExist).toEqual({
      regenerateSummary: true,
      exportSelectedFormat: true,
      cleanupAndReset: true,
    });

    await page.locator("#new-recording-btn").click();
    await expect(page.locator("#view-upload")).toHaveClass(/active/);
  });

  test("AC5: 兩個 select 套用 .input，高度/邊框/圓角 token 化，focus outline，option 不變", async ({ page }) => {
    const templateSelect = page.locator("#template-select");
    const exportSelect = page.locator("#export-format-select");
    await expect(templateSelect).toHaveClass(/\binput\b/);
    await expect(exportSelect).toHaveClass(/\binput\b/);

    const controlHDesktop = await resolveToken(page, "height", "var(--ds-control-h-desktop)");
    const borderStrong = await resolveToken(page, "border-color", "var(--ds-border-strong)");
    const radiusSm = await resolveToken(page, "border-radius", "var(--ds-radius-sm)");
    for (const sel of [templateSelect, exportSelect]) {
      await expect(sel).toHaveCSS("height", controlHDesktop);
      await expect(sel).toHaveCSS("border-color", borderStrong);
      await expect(sel).toHaveCSS("border-radius", radiusSm);
    }

    // focus-visible outline 2px --ds-focus-ring（鍵盤 focus）
    const focusRing = await resolveToken(page, "outline-color", "var(--ds-focus-ring)");
    await page.locator("body").click();
    await page.keyboard.press("Tab"); // 進入頁面 focusable 序列的起點不固定，直接用 .focus() 更可靠
    await templateSelect.focus();
    await expect(templateSelect).toHaveCSS("outline-width", "2px");
    await expect(templateSelect).toHaveCSS("outline-color", focusRing);

    // option 數量/值不變
    const templateOptions = await templateSelect.locator("option").evaluateAll((els) =>
      els.map((el) => (el as HTMLOptionElement).value),
    );
    expect(templateOptions).toEqual(["general", "project_status", "client_meeting", "brainstorm", "retro"]);

    const exportOptions = await exportSelect.locator("option").evaluateAll((els) =>
      els.map((el) => (el as HTMLOptionElement).value),
    );
    expect(exportOptions).toEqual(["markdown", "plaintext", "docx", "pdf"]);
  });

  test("AC5 (手機): <480px select.input 寬度非滿版（width:auto 覆寫）", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    const containerWidth = await page.evaluate(() => document.querySelector("#view-result")!.clientWidth);
    const templateSelect = page.locator("#template-select");
    const exportSelect = page.locator("#export-format-select");
    const templateBox = await templateSelect.boundingBox();
    const exportBox = await exportSelect.boundingBox();
    expect(templateBox).not.toBeNull();
    expect(exportBox).not.toBeNull();
    expect(templateBox!.width).toBeLessThan(containerWidth - 10);
    expect(exportBox!.width).toBeLessThan(containerWidth - 10);
  });

  test("AC6: .tab.active/.tab 顏色/字重/底線/底部邊框 token 化，文字移除 emoji", async ({ page }) => {
    const active = page.locator("#tab-btn-minutes");
    const inactive = page.locator("#tab-btn-transcript");
    await expect(active).toHaveText("會議紀錄");
    await expect(inactive).toHaveText("逐字稿");
    const activeText = await active.textContent();
    const inactiveText = await inactive.textContent();
    expect(activeText || "").not.toMatch(/[\u{1F300}-\u{1FAFF}]/u);
    expect(inactiveText || "").not.toMatch(/[\u{1F300}-\u{1FAFF}]/u);

    const inkColor = await resolveToken(page, "color", "var(--ds-ink-100)");
    await expect(active).toHaveCSS("color", inkColor);
    await expect(active).toHaveCSS("border-bottom-color", inkColor);
    await expect(active).toHaveCSS("font-weight", "600");

    const textSecondary = await resolveToken(page, "color", "var(--ds-text-secondary)");
    await expect(inactive).toHaveCSS("color", textSecondary);

    const border = await resolveToken(page, "border-color", "var(--ds-border)");
    const tabsBar = page.locator("#view-result .tabs");
    await expect(tabsBar).toHaveCSS("border-bottom-color", border);
  });

  test("AC6 (揭露): history-detail .tab.active 也使用 --ds-ink-100（共用本體，預期）", async ({ page }) => {
    await page.route("**/api/meetings/m-header-tabs-ds", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          meeting_id: "m-header-tabs-ds",
          title: "揭露驗證會議",
          transcript_text: "",
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
    await page.evaluate(() => (0, eval)("openMeetingDetail")("m-header-tabs-ds"));
    await expect(page.locator("#view-history-detail")).toBeVisible();

    const historyActive = page.locator("#history-tab-btn-minutes");
    const inkColor = await resolveToken(page, "color", "var(--ds-ink-100)");
    await expect(historyActive).toHaveCSS("color", inkColor);
    // 文字不變（history-detail 不移除 emoji，範圍外）
    await expect(historyActive).toHaveText("📝 會議紀錄");
  });

  test("AC6 (回歸): switchTab() 仍切換 active class 與面板顯示", async ({ page }) => {
    await expect(page.locator("#tab-btn-minutes")).toHaveClass(/active/);
    await expect(page.locator("#tab-btn-transcript")).not.toHaveClass(/active/);

    await page.evaluate(() => (0, eval)("switchTab")("transcript"));
    await expect(page.locator("#tab-btn-transcript")).toHaveClass(/active/);
    await expect(page.locator("#tab-btn-minutes")).not.toHaveClass(/active/);
    await expect(page.locator("#tab-transcript")).toBeVisible();

    await page.evaluate(() => (0, eval)("switchTab")("minutes"));
    await expect(page.locator("#tab-btn-minutes")).toHaveClass(/active/);
    await expect(page.locator("#tab-minutes")).toBeVisible();
  });

  test("AC7: <480px tabs 不換行、不溢出，等寬 flex:1", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    const minutesTab = page.locator("#tab-btn-minutes");
    const transcriptTab = page.locator("#tab-btn-transcript");
    const minutesBox = await minutesTab.boundingBox();
    const transcriptBox = await transcriptTab.boundingBox();
    expect(minutesBox).not.toBeNull();
    expect(transcriptBox).not.toBeNull();
    // 同排（不換行）
    expect(Math.abs(minutesBox!.y - transcriptBox!.y)).toBeLessThanOrEqual(2);
    // 等寬
    expect(Math.abs(minutesBox!.width - transcriptBox!.width)).toBeLessThanOrEqual(2);

    const tabsBar = page.locator("#view-result .tabs");
    const barOverflow = await tabsBar.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(barOverflow.scrollWidth).toBeLessThanOrEqual(barOverflow.clientWidth + 1);

    const pageOverflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(pageOverflow.scrollWidth).toBeLessThanOrEqual(pageOverflow.clientWidth);
  });

  test("AC8 (回歸): 徽章符號與琥珀色不變", async ({ page }) => {
    await page.evaluate(() => {
      const s = (0, eval)("state");
      s.modified = true;
      document.getElementById("modified-badge")!.style.display = "inline-block";
      document.getElementById("low-confidence-badge")!.style.display = "inline-block";
    });

    const modifiedBadge = page.locator("#modified-badge");
    const lowConfBadge = page.locator("#low-confidence-badge");
    await expect(modifiedBadge).toBeVisible();
    await expect(lowConfBadge).toBeVisible();

    const modifiedText = await modifiedBadge.textContent();
    const lowConfText = await lowConfBadge.textContent();
    expect((modifiedText || "").startsWith("●")).toBe(true);
    expect((lowConfText || "").startsWith("⚠")).toBe(true);

    // 琥珀色不變：background #FEF3C7、color 為 --warning 解析值（現況值，非本票調整範圍）
    await expect(modifiedBadge).toHaveCSS("background-color", "rgb(254, 243, 199)");
    await expect(lowConfBadge).toHaveCSS("background-color", "rgb(254, 243, 199)");
    const warningColor = await modifiedBadge.evaluate((el) => getComputedStyle(el).color);
    await expect(lowConfBadge).toHaveCSS("color", warningColor);
  });
});
