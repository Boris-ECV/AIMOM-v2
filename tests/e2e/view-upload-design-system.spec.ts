import { test, expect } from "@playwright/test";

// SDLCAIP2-47: Design System｜上傳畫面 view-upload
//
// 沿用 view-admin-design-system.spec.ts / design-system-foundation.spec.ts 既有的登入繞過手法。
// AC 對應：
// AC1 - #view-upload .card 沿用 SDLCAIP2-44 --ds-* .card 樣式（回歸，與另一畫面 .card 比對）
// AC2 - view-upload 卡片標題 <h2> 無 emoji，文字為「上傳錄音檔」
// AC3 - #drop-zone / #upload-btn 內無 <svg>，文字保留，#upload-btn 初始 disabled 且 disabled/reset 行為不變
// AC4 - #drop-zone 邊框色/圓角、hover + .dragover 邊框色/背景改用 --ds-* token（真實 computed RGB），舊值消失
// AC5 - #file-info 背景 --ds-badge-bg，#file-info .fname 文字色 --ds-text-primary（computed RGB）
// AC6 - #upload-btn 仍沿用全域 .btn/.btn-primary（回歸）
// AC7 - 窄螢幕（<480px）#upload-btn 高度 = --ds-control-h-mobile（44px）且全寬；.card padding = --ds-space-5（24px）；無橫向捲動
// AC8 - 其他畫面不受影響（header、另一畫面 .btn/.card 不變）且 #upload-error 顏色維持 var(--danger)

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-upload-design-system-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

test.describe("Design System｜上傳畫面 view-upload（SDLCAIP2-47）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
    await expect(page.locator("#view-upload")).toBeVisible();
  });

  test("AC1: #view-upload .card 沿用 SDLCAIP2-44 --ds-* .card 樣式（回歸，與 view-admin .card 比對）", async ({ page }) => {
    const uploadCard = page.locator("#view-upload .card").first();
    const uploadStyles = await uploadCard.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderColor: cs.borderColor, borderRadius: cs.borderRadius, padding: cs.padding };
    });
    expect(uploadStyles.background).toBe("rgb(255, 255, 255)"); // --ds-surface
    expect(uploadStyles.borderColor).toBe("rgb(228, 227, 223)"); // --ds-border #E4E3DF
    expect(uploadStyles.borderRadius).toBe("10px"); // --ds-radius-md
    expect(uploadStyles.padding).toBe("32px"); // --ds-space-6

    // 與另一畫面（view-admin）的 .card 比對，確認同一份共用 token，不是 view-upload 專屬覆寫
    await page.route("**/api/me", (route) => route.fulfill({ status: 200, json: { role: "admin" } }));
    await page.route("**/api/admin/usage", (route) =>
      route.fulfill({ status: 200, json: { by_date: [], by_user: [], total_calls: 0, total_estimated_cost: 0 } })
    );
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();
    await expect(page.locator("#admin-dashboard-btn")).toBeVisible();
    await page.locator("#admin-dashboard-btn").click();
    await expect(page.locator("#view-admin")).toBeVisible();
    const adminCard = page.locator("#view-admin .card").first();
    const adminStyles = await adminCard.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderColor: cs.borderColor, borderRadius: cs.borderRadius };
    });
    expect(adminStyles).toEqual({
      background: uploadStyles.background,
      borderColor: uploadStyles.borderColor,
      borderRadius: uploadStyles.borderRadius,
    });
  });

  test("AC2: <h2> 標題無 emoji，文字為「上傳錄音檔」", async ({ page }) => {
    const h2 = page.locator("#view-upload .card h2").first();
    const text = await h2.evaluate((el) => el.textContent || "");
    expect(text.trim()).toBe("上傳錄音檔");
    // eslint-disable-next-line no-misleading-character-class
    const emojiPattern = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    expect(emojiPattern.test(text)).toBe(false);
  });

  test("AC3: #drop-zone / #upload-btn 內無 <svg>，文字保留，#upload-btn 初始 disabled", async ({ page }) => {
    const dropZoneSvgCount = await page.locator("#drop-zone svg").count();
    expect(dropZoneSvgCount).toBe(0);
    const uploadBtnSvgCount = await page.locator("#upload-btn svg").count();
    expect(uploadBtnSvgCount).toBe(0);

    const dropZoneText = await page.locator("#drop-zone").evaluate((el) => el.textContent || "");
    expect(dropZoneText).toContain("拖放錄音檔至此，或點擊選取");

    const btn = page.locator("#upload-btn");
    await expect(btn).toHaveText(/開始處理/);
    await expect(btn).toBeDisabled();
  });

  test("AC3 續: disabled/reset 行為不變 — 選檔後啟用，重新整理回到初始 disabled 狀態", async ({ page }) => {
    const btn = page.locator("#upload-btn");
    await expect(btn).toBeDisabled();

    await page.evaluate(() => {
      const file = new File(["fake audio bytes"], "meeting.mp3", { type: "audio/mpeg" });
      (0, eval)("setFile")(file);
    });
    await expect(btn).toBeEnabled();
    await expect(btn).toHaveText(/開始處理/);

    // 呼叫 resetState() 還原成初始（尚未選檔）狀態，disabled 行為應與頁面首次載入一致
    await page.evaluate(() => {
      (0, eval)("resetState")();
    });
    await expect(btn).toBeDisabled();
    await expect(btn).toHaveText(/開始處理/);
    await expect(page.locator("#file-info")).toBeHidden();
  });

  test("AC4: #drop-zone 邊框/圓角、hover 與 .dragover 邊框色/背景改用 --ds-* token（computed RGB），舊值消失", async ({ page }) => {
    const dropZone = page.locator("#drop-zone");
    const baseStyles = await dropZone.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { borderColor: cs.borderColor, borderRadius: cs.borderRadius };
    });
    expect(baseStyles.borderColor).toBe("rgb(210, 208, 202)"); // --ds-border-strong #D2D0CA
    expect(baseStyles.borderRadius).toBe("10px"); // --ds-radius-md

    // hover（CSS 有 transition: border-color .2s, background .2s，等待轉場結束再讀值避免抓到中間色）
    await dropZone.hover();
    await page.waitForTimeout(400);
    const hoverStyles = await dropZone.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { borderColor: cs.borderColor, background: cs.backgroundColor };
    });
    expect(hoverStyles.borderColor).toBe("rgb(31, 30, 28)"); // --ds-ink-100 #1F1E1C
    expect(hoverStyles.background).toBe("rgb(239, 238, 234)"); // --ds-badge-bg #EFEEEA
    expect(hoverStyles.background).not.toBe("rgb(239, 246, 255)"); // 舊值 #EFF6FF 已消失

    // .dragover class（不依賴 hover 移出，直接透過 class 驗證，較穩定）
    await page.mouse.move(0, 0);
    await page.evaluate(() => document.getElementById("drop-zone")!.classList.add("dragover"));
    const dragoverStyles = await dropZone.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { borderColor: cs.borderColor, background: cs.backgroundColor };
    });
    expect(dragoverStyles.borderColor).toBe("rgb(31, 30, 28)"); // --ds-ink-100
    expect(dragoverStyles.background).toBe("rgb(239, 238, 234)"); // --ds-badge-bg
    expect(dragoverStyles.background).not.toBe("rgb(239, 246, 255)");
    await page.evaluate(() => document.getElementById("drop-zone")!.classList.remove("dragover"));
  });

  test("AC5: #file-info 背景 --ds-badge-bg，#file-info .fname 文字色 --ds-text-primary（computed RGB）", async ({ page }) => {
    await page.evaluate(() => {
      const file = new File(["fake audio bytes"], "meeting.mp3", { type: "audio/mpeg" });
      (0, eval)("setFile")(file);
    });
    await expect(page.locator("#file-info")).toBeVisible();

    const fileInfoBg = await page.locator("#file-info").evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(fileInfoBg).toBe("rgb(239, 238, 234)"); // --ds-badge-bg #EFEEEA

    const fnameColor = await page.locator("#file-info .fname").evaluate((el) => getComputedStyle(el).color);
    expect(fnameColor).toBe("rgb(31, 30, 28)"); // --ds-text-primary #1F1E1C
    expect(fnameColor).not.toBe("rgb(37, 99, 235)"); // 舊值 var(--primary) #2563EB 已消失
  });

  test("AC6: #upload-btn 仍沿用全域 .btn/.btn-primary（回歸）", async ({ page }) => {
    await page.evaluate(() => {
      const file = new File(["fake audio bytes"], "meeting.mp3", { type: "audio/mpeg" });
      (0, eval)("setFile")(file);
    });
    const btn = page.locator("#upload-btn");
    await expect(btn).toBeEnabled();
    const styles = await btn.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { height: cs.height, borderRadius: cs.borderRadius, background: cs.backgroundColor, color: cs.color };
    });
    expect(styles.height).toBe("40px"); // --ds-control-h-desktop
    expect(styles.borderRadius).toBe("6px"); // --ds-radius-sm
    expect(styles.background).toBe("rgb(31, 30, 28)"); // --ds-ink-100（.btn-primary 背景）
    expect(styles.color).toBe("rgb(246, 245, 243)"); // --ds-bg（.btn-primary 文字）
  });

  test("AC7: 窄螢幕（<480px）#upload-btn 高度=44px 全寬、.card padding=24px，無橫向捲動", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });

    const btn = page.locator("#upload-btn");
    const btnStyles = await btn.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { height: cs.height, width: cs.width };
    });
    expect(btnStyles.height).toBe("44px"); // --ds-control-h-mobile

    const card = page.locator("#view-upload .card").first();
    const cardBox = await card.boundingBox();
    const btnBox = await btn.boundingBox();
    expect(cardBox).not.toBeNull();
    expect(btnBox).not.toBeNull();
    // 全寬：按鈕寬度應與卡片內容寬度（卡片寬度 - 左右 padding）大致相等
    const cardPadding = await card.evaluate((el) => getComputedStyle(el).padding);
    expect(cardPadding).toBe("24px"); // --ds-space-5
    expect(Math.abs(btnBox!.width - (cardBox!.width - 48))).toBeLessThanOrEqual(2);

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);
  });

  test("AC8: 其他畫面不受影響（header、view-admin .btn/.card 不變）且 #upload-error 顏色維持 var(--danger)", async ({ page }) => {
    const dangerVar = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--danger").trim());
    expect(dangerVar).toBe("#DC2626");

    const uploadErrorColor = await page.locator("#upload-error").evaluate((el) => getComputedStyle(el).color);
    expect(uploadErrorColor).toBe("rgb(220, 38, 38)"); // var(--danger) #DC2626

    // header 不受影響
    const headerHeight = await page.locator("header").first().evaluate((el) => getComputedStyle(el).height);
    expect(headerHeight).toBe("72px"); // --ds-header-h-desktop，SDLCAIP2-44 既有規則

    // 另一畫面（view-admin）的 .btn/.card 不受本票影響
    await page.route("**/api/me", (route) => route.fulfill({ status: 200, json: { role: "admin" } }));
    await page.route("**/api/admin/usage", (route) =>
      route.fulfill({ status: 200, json: { by_date: [], by_user: [], total_calls: 0, total_estimated_cost: 0 } })
    );
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();
    await expect(page.locator("#admin-dashboard-btn")).toBeVisible();
    await page.locator("#admin-dashboard-btn").click();
    await expect(page.locator("#view-admin")).toBeVisible();

    const adminCard = page.locator("#view-admin .card").first();
    const adminCardStyles = await adminCard.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderRadius: cs.borderRadius };
    });
    expect(adminCardStyles.background).toBe("rgb(255, 255, 255)");
    expect(adminCardStyles.borderRadius).toBe("10px");

    const logoutBtn = page.locator("header > .btn").first();
    const logoutBtnStyles = await logoutBtn.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { height: cs.height, borderRadius: cs.borderRadius };
    });
    expect(logoutBtnStyles.height).toBe("40px");
    expect(logoutBtnStyles.borderRadius).toBe("6px");
  });
});
