import { test, expect } from "@playwright/test";

// SDLCAIP2-44: Design System｜基礎建設（導入全站色彩／字體／間距 token 並調整共用樣式與共用頁首）
//
// 沿用 header-mic-icon.spec.ts / result-action-row-layout.spec.ts 既有的登入繞過手法。
// AC 對應：
// AC1 - tokens 已導入頁面（完整 token 集合 + Google Fonts 連結）
// AC2 - 共用 .btn 樣式改用 token（含手機版 --ds-control-h-mobile）
// AC3 - 共用 .card 樣式改用 token（含手機版 --ds-space-5 內距）
// AC4 - 共用 badge 樣式改用 token（中性灰階、圓角 pill）
// AC5 - 新增可重用的 .input class（不套用到現有元素）
// AC6 - 頁首移除裝飾性 icon（📊/📜 前綴）
// AC7 - 頁首 RWD：桌面版維持單列
// AC8 - 頁首 RWD：手機版拆成兩列
// AC9 - 範圍外畫面視覺不受影響（既有未加前綴變數不應被覆寫）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-design-system-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

test.describe("Design System 基礎建設（SDLCAIP2-44）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
  });

  test("AC1: tokens 已導入頁面（完整 token 集合 + Google Fonts）", async ({ page }) => {
    const tokens = await page.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      return {
        bg: cs.getPropertyValue("--ds-bg").trim(),
        surface: cs.getPropertyValue("--ds-surface").trim(),
        border: cs.getPropertyValue("--ds-border").trim(),
        textPrimary: cs.getPropertyValue("--ds-text-primary").trim(),
        fontSans: cs.getPropertyValue("--ds-font-sans").trim(),
        fontMono: cs.getPropertyValue("--ds-font-mono").trim(),
        space1: cs.getPropertyValue("--ds-space-1").trim(),
        space5: cs.getPropertyValue("--ds-space-5").trim(),
        radiusSm: cs.getPropertyValue("--ds-radius-sm").trim(),
        radiusPill: cs.getPropertyValue("--ds-radius-pill").trim(),
        controlHDesktop: cs.getPropertyValue("--ds-control-h-desktop").trim(),
        controlHMobile: cs.getPropertyValue("--ds-control-h-mobile").trim(),
        headerHDesktop: cs.getPropertyValue("--ds-header-h-desktop").trim(),
        headerHMobile: cs.getPropertyValue("--ds-header-h-mobile").trim(),
        breakpointMobile: cs.getPropertyValue("--ds-breakpoint-mobile").trim(),
      };
    });
    expect(tokens.bg).toBe("#F6F5F3");
    expect(tokens.surface).toBe("#FFFFFF");
    expect(tokens.border).toBe("#E4E3DF");
    expect(tokens.textPrimary).toBe("#1F1E1C");
    expect(tokens.fontSans).toContain("Noto Sans TC");
    expect(tokens.fontMono).toContain("JetBrains Mono");
    expect(tokens.space1).toBe("8px");
    expect(tokens.space5).toBe("24px");
    expect(tokens.radiusSm).toBe("6px");
    expect(tokens.radiusPill).toBe("999px");
    expect(tokens.controlHDesktop).toBe("40px");
    expect(tokens.controlHMobile).toBe("44px");
    expect(tokens.headerHDesktop).toBe("72px");
    expect(tokens.headerHMobile).toBe("56px");
    expect(tokens.breakpointMobile).toBe("480px");

    const fontLinkHrefs = await page.evaluate(() =>
      Array.from(document.querySelectorAll('head link[rel="stylesheet"]')).map((l) => l.getAttribute("href") || ""),
    );
    const googleFontsHref = fontLinkHrefs.find((h) => h.includes("fonts.googleapis.com"));
    expect(googleFontsHref).toBeTruthy();
    expect(googleFontsHref).toContain("Noto+Sans+TC");
    expect(googleFontsHref).toContain("JetBrains+Mono");
  });

  test("AC2: 共用 .btn 樣式改用 token", async ({ page }) => {
    const btn = page.locator("#history-nav-btn");
    const styles = await btn.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { height: cs.height, borderRadius: cs.borderRadius, fontSize: cs.fontSize };
    });
    expect(styles.height).toBe("40px"); // --ds-control-h-desktop
    expect(styles.borderRadius).toBe("6px"); // --ds-radius-sm

    // 手機版：高度改用 --ds-control-h-mobile
    await page.setViewportSize({ width: 375, height: 800 });
    const mobileHeight = await btn.evaluate((el) => getComputedStyle(el).height);
    expect(mobileHeight).toBe("44px");
  });

  test("AC3: 共用 .card 樣式改用 token", async ({ page }) => {
    const card = page.locator("#view-upload .card").first();
    const styles = await card.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderRadius: cs.borderRadius, padding: cs.padding };
    });
    expect(styles.background).toBe("rgb(255, 255, 255)"); // --ds-surface
    expect(styles.borderRadius).toBe("10px"); // --ds-radius-md
    expect(styles.padding).toBe("32px"); // --ds-space-6

    // 手機版：內距改用 --ds-space-5（24px）
    await page.setViewportSize({ width: 375, height: 800 });
    const mobilePadding = await card.evaluate((el) => getComputedStyle(el).padding);
    expect(mobilePadding).toBe("24px");
  });

  test("AC4: 共用 badge 樣式改用 token（中性灰階、pill 圓角）", async ({ page }) => {
    // 切換到結果畫面以取得 .section-title .badge（「未提及可手動填寫」）
    await page.evaluate(() => {
      const s = (0, eval)("state");
      s.jobId = "e2e-ds-badge-1";
      s.minutes = {
        job_id: "e2e-ds-badge-1",
        template: "general",
        meeting_info: { date: "", time: "", location: "", participants: [] },
        summary: "",
        action_items: [],
        decisions: [],
        sections: [],
      };
      (0, eval)("renderMinutes")();
      (0, eval)("showView")("view-result");
    });
    const badge = page.locator("#view-result .section-title .badge").first();
    await expect(badge).toBeVisible();
    const styles = await badge.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderRadius: cs.borderRadius, color: cs.color };
    });
    expect(styles.background).toBe("rgb(239, 238, 234)"); // --ds-badge-bg #EFEEEA, not blue #DBEAFE
    expect(styles.background).not.toBe("rgb(219, 234, 254)"); // old blue #DBEAFE
    expect(styles.borderRadius).toBe("999px"); // --ds-radius-pill
    expect(styles.color).toBe("rgb(107, 106, 100)"); // --ds-badge-text -> --ds-text-secondary #6B6A64
  });

  test("AC5: 新增可重用的 .input class（不套用到現有元素）", async ({ page }) => {
    const inputStyles = await page.evaluate(() => {
      const probe = document.createElement("input");
      probe.className = "input";
      document.body.appendChild(probe);
      const cs = getComputedStyle(probe);
      const result = { height: cs.height, borderRadius: cs.borderRadius, background: cs.backgroundColor };
      probe.remove();
      return result;
    });
    expect(inputStyles.height).toBe("40px");
    expect(inputStyles.borderRadius).toBe("6px");
    expect(inputStyles.background).toBe("rgb(255, 255, 255)");

    // 既有畫面專屬 input（例如會議資訊日期欄位）不應套用 .input class / token 高度
    const meetingDateInput = page.locator("#meeting-date");
    await expect(meetingDateInput).not.toHaveClass(/\binput\b/);
  });

  test("AC6: 頁首移除裝飾性 icon（📊/📜 前綴）", async ({ page }) => {
    const adminBtnText = await page.locator("#admin-dashboard-btn").evaluate((el) => el.textContent || "");
    const historyBtnText = await page.locator("#history-nav-btn").evaluate((el) => el.textContent || "");
    expect(adminBtnText).not.toContain("📊");
    expect(adminBtnText.trim()).toBe("管理者儀表板");
    expect(historyBtnText).not.toContain("📜");
    expect(historyBtnText.trim()).toBe("歷史紀錄");

    // view-history section-title 的 📜 已由 SDLCAIP2-50 移除，改由該工單的測試驗證
  });

  test("AC7: 頁首 RWD — 桌面版（≥480px）維持單列", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const header = page.locator("header").first();
    const headerHeight = await header.evaluate((el) => getComputedStyle(el).height);
    expect(headerHeight).toBe("72px"); // --ds-header-h-desktop, 單列高度

    // 桌面版 .header-secondary 為 display:contents，讓子元素直接參與 header 排版
    // （因此 .header-secondary 本身沒有 boundingBox，改用其子元素驗證是否同列）
    const secondaryDisplay = await page.locator(".header-secondary").evaluate((el) => getComputedStyle(el).display);
    expect(secondaryDisplay).toBe("contents");

    const titleBox = await page.locator("header h1").boundingBox();
    const logoutBox = await page.locator("header > .btn").boundingBox();
    const historyBtnBox = await page.locator("#history-nav-btn").boundingBox();
    expect(titleBox).not.toBeNull();
    expect(logoutBox).not.toBeNull();
    expect(historyBtnBox).not.toBeNull();
    // 桌面單列：標題、次要導覽子元素、登出按鈕垂直中心應大致落在同一列（不換行）
    const titleMidY = titleBox!.y + titleBox!.height / 2;
    const historyMidY = historyBtnBox!.y + historyBtnBox!.height / 2;
    const logoutMidY = logoutBox!.y + logoutBox!.height / 2;
    expect(Math.abs(titleMidY - historyMidY)).toBeLessThan(5);
    expect(Math.abs(titleMidY - logoutMidY)).toBeLessThan(5);
  });

  test("AC8: 頁首 RWD — 手機版（<480px）拆成兩列", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    const titleBox = await page.locator("header h1").boundingBox();
    const secondaryBox = await page.locator(".header-secondary").boundingBox();
    expect(titleBox).not.toBeNull();
    expect(secondaryBox).not.toBeNull();
    // 手機兩列：第二列（次要導覽）應在標題列下方，不與標題同一列
    expect(secondaryBox!.y).toBeGreaterThanOrEqual(titleBox!.y + titleBox!.height - 1);

    // 第一列僅標題＋登出按鈕：副標隱藏
    await expect(page.locator(".header-subtitle")).toBeHidden();

    // 次要導覽列可橫向捲動
    const overflowX = await page.locator(".header-secondary").evaluate((el) => getComputedStyle(el).overflowX);
    expect(overflowX).toBe("auto");

    // 次要導覽列含管理者儀表板/歷史紀錄/使用者 email
    const secondaryText = await page.locator(".header-secondary").evaluate((el) => el.textContent || "");
    expect(secondaryText).toContain("歷史紀錄");
    expect(secondaryText).toContain("e2e-design-system-user@example.com");
  });

  test("AC9: 範圍外畫面視覺不受影響（既有未加前綴變數不被覆寫）", async ({ page }) => {
    const dropZoneStyles = await page.locator("#drop-zone").evaluate((el) => {
      const cs = getComputedStyle(el);
      return { borderRadius: cs.borderRadius };
    });
    expect(dropZoneStyles.borderRadius).toBe("10px"); // var(--radius), 未被 --ds-* 覆寫

    const rootVars = await page.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      return {
        bg: cs.getPropertyValue("--bg").trim(),
        border: cs.getPropertyValue("--border").trim(),
        primary: cs.getPropertyValue("--primary").trim(),
      };
    });
    expect(rootVars.bg).toBe("#F8FAFC");
    expect(rootVars.border).toBe("#E2E8F0");
    expect(rootVars.primary).toBe("#2563EB");
  });
});
