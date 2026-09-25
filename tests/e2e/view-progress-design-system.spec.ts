import { test, expect } from "@playwright/test";

// SDLCAIP2-46: Design System｜轉錄進度畫面 view-progress
//
// 沿用 view-upload-design-system.spec.ts / view-history-design-system.spec.ts 既有的登入繞過手法。
// AC 對應：
// AC1 - #view-progress .card <h2> 文字為「處理中...」，無 emoji
// AC2 - #icon-uploaded/#icon-transcribed/#icon-done 內無 emoji 文字，三態 class 切換後底色/邊框可分辨（互不相同）
// AC3 - .stage-icon.done/.active/.waiting、.progress-bar、.progress-bar-wrap 的 background/color/border
//       改用 --ds-* token（動態解析 token 值），舊值（#DCFCE7/#DBEAFE/舊 --primary 藍）消失
// AC4 - h2/.stage-label/.stage-msg/.progress-pct/#progress-message 的 font-family 皆為 --ds-font-sans
// AC5 - .stage-list gap/margin、.stage-item gap/padding 改用 --ds-space-* token
// AC6 - #progress-message 套用 Badge 樣式（background/border/color/border-radius=--ds-radius-pill，
//       無 cursor:pointer）；空字串時 :empty 隱藏
// AC7 - 取消按鈕仍為 .btn.btn-outline.btn-sm，onclick 含 cancelJob，cursor:pointer，與 badge 視覺明確不同
// AC8 - updateProgressUI() 更新 #progress-bar 寬度／#progress-pct／#progress-message 文字與 icon class（回歸）
// AC9 - 其他畫面共用樣式不受影響（view-result .section-title .badge、view-upload .card）

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-view-progress-design-system-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

async function openProgressView(page: import("@playwright/test").Page) {
  await page.evaluate(() => {
    (0, eval)("showView")("view-progress");
  });
  await expect(page.locator("#view-progress")).toBeVisible();
}

// 用瀏覽器實際 cascade 解析 --ds-* token（含巢狀 var() 參照），回傳 computed rgb() 字串，
// 比手動對照色碼表更可靠（避免測試自己抄錯 hex → rgb 換算）。
async function resolveTokenRgb(page: import("@playwright/test").Page, varName: string): Promise<string> {
  return page.evaluate((v) => {
    const tmp = document.createElement("div");
    tmp.style.color = `var(${v})`;
    document.body.appendChild(tmp);
    const rgb = getComputedStyle(tmp).color;
    tmp.remove();
    return rgb;
  }, varName);
}

// eslint-disable-next-line no-misleading-character-class
const emojiPattern = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;

test.describe("Design System｜轉錄進度畫面 view-progress（SDLCAIP2-46）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await loginBypass(page);
    await openProgressView(page);
  });

  test("AC1: <h2> 標題無 emoji，文字為「處理中...」", async ({ page }) => {
    const h2 = page.locator("#view-progress .card h2").first();
    const text = await h2.evaluate((el) => el.textContent || "");
    expect(text.trim()).toBe("處理中...");
    expect(emojiPattern.test(text)).toBe(false);
  });

  test("AC2: 三個 stage icon 內無 emoji 文字，waiting/active/done 三態底色與邊框互不相同", async ({ page }) => {
    for (const id of ["icon-uploaded", "icon-transcribed", "icon-done"]) {
      const text = await page.locator(`#${id}`).evaluate((el) => el.textContent || "");
      expect(text.trim()).toBe("");
      expect(emojiPattern.test(text)).toBe(false);
    }

    const icon = page.locator("#icon-uploaded");
    async function styleFor(className: string) {
      await page.evaluate((cn) => {
        document.getElementById("icon-uploaded")!.className = cn;
      }, className);
      return icon.evaluate((el) => {
        const cs = getComputedStyle(el);
        return { background: cs.backgroundColor, border: cs.borderColor };
      });
    }

    const waiting = await styleFor("stage-icon waiting");
    const active = await styleFor("stage-icon active");
    const done = await styleFor("stage-icon done");

    // 三態互不相同（背景或邊框其中一項不同即可視為可分辨，但這裡兩者皆應不同）
    expect(waiting.background).not.toBe(active.background);
    expect(active.background).not.toBe(done.background);
    expect(waiting.background).not.toBe(done.background);
    expect(waiting.border).not.toBe(active.border);
  });

  test("AC3: .stage-icon 三態 / .progress-bar / .progress-bar-wrap 改用 --ds-* token，舊值消失", async ({ page }) => {
    const badgeBg = await resolveTokenRgb(page, "--ds-badge-bg");
    const badgeBorder = await resolveTokenRgb(page, "--ds-badge-border");
    const badgeText = await resolveTokenRgb(page, "--ds-badge-text");
    const ink100 = await resolveTokenRgb(page, "--ds-ink-100");
    const dsBg = await resolveTokenRgb(page, "--ds-bg");
    const dsSurface = await resolveTokenRgb(page, "--ds-surface");
    const dsTextSecondary = await resolveTokenRgb(page, "--ds-text-secondary");
    const dsBorderStrong = await resolveTokenRgb(page, "--ds-border-strong");
    const dsBorder = await resolveTokenRgb(page, "--ds-border");

    await page.evaluate(() => {
      document.getElementById("icon-uploaded")!.className = "stage-icon done";
      document.getElementById("icon-transcribed")!.className = "stage-icon active";
      document.getElementById("icon-done")!.className = "stage-icon waiting";
    });

    const doneIcon = page.locator("#icon-uploaded");
    await expect(doneIcon).toHaveCSS("background-color", badgeBg);
    await expect(doneIcon).toHaveCSS("border-color", badgeBorder);
    await expect(doneIcon).toHaveCSS("color", badgeText);
    await expect(doneIcon).not.toHaveCSS("background-color", "rgb(220, 252, 231)"); // 舊 #DCFCE7

    const activeIcon = page.locator("#icon-transcribed");
    await expect(activeIcon).toHaveCSS("background-color", ink100);
    await expect(activeIcon).toHaveCSS("border-color", ink100);
    await expect(activeIcon).toHaveCSS("color", dsBg);
    await expect(activeIcon).not.toHaveCSS("background-color", "rgb(219, 234, 254)"); // 舊 #DBEAFE
    await expect(activeIcon).not.toHaveCSS("color", "rgb(37, 99, 235)"); // 舊 --primary #2563EB

    const waitingIcon = page.locator("#icon-done");
    await expect(waitingIcon).toHaveCSS("background-color", dsSurface);
    await expect(waitingIcon).toHaveCSS("border-color", dsBorderStrong);
    await expect(waitingIcon).toHaveCSS("color", dsTextSecondary);

    const progressBar = page.locator("#progress-bar");
    await expect(progressBar).toHaveCSS("background-color", ink100);
    await expect(progressBar).not.toHaveCSS("background-color", "rgb(37, 99, 235)"); // 舊 --primary

    const progressBarWrap = page.locator(".progress-bar-wrap");
    await expect(progressBarWrap).toHaveCSS("background-color", dsBorder);
  });

  test("AC4: h2/.stage-label/.stage-msg/.progress-pct/#progress-message font-family 皆為 --ds-font-sans", async ({
    page,
  }) => {
    const dsFontSans = await page.evaluate(() => {
      const tmp = document.createElement("div");
      tmp.style.fontFamily = "var(--ds-font-sans)";
      document.body.appendChild(tmp);
      const ff = getComputedStyle(tmp).fontFamily;
      tmp.remove();
      return ff;
    });

    await page.evaluate(() => {
      document.getElementById("progress-message")!.textContent = "處理中";
    });

    const selectors = [
      "#view-progress .card h2",
      ".stage-label",
      ".stage-msg",
      "#progress-pct",
      "#progress-message",
    ];
    for (const sel of selectors) {
      await expect(page.locator(sel).first()).toHaveCSS("font-family", dsFontSans);
    }
  });

  test("AC5: .stage-list gap/margin、.stage-item gap/padding 改用 --ds-space-* token", async ({ page }) => {
    const space2 = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--ds-space-2").trim());
    const space3 = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--ds-space-3").trim());
    const space4 = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--ds-space-4").trim());
    const space5 = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--ds-space-5").trim());
    expect(space2).toBe("12px");
    expect(space3).toBe("16px");
    expect(space4).toBe("20px");
    expect(space5).toBe("24px");

    const stageList = page.locator(".stage-list");
    const listStyles = await stageList.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { gap: cs.gap, marginTop: cs.marginTop, marginBottom: cs.marginBottom };
    });
    expect(listStyles.gap).toBe("12px"); // --ds-space-2
    expect(listStyles.marginTop).toBe("24px"); // --ds-space-5
    expect(listStyles.marginBottom).toBe("24px"); // --ds-space-5

    const stageItem = page.locator(".stage-item").first();
    const itemStyles = await stageItem.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { gap: cs.gap, paddingTop: cs.paddingTop, paddingLeft: cs.paddingLeft };
    });
    expect(itemStyles.gap).toBe("16px"); // --ds-space-3
    expect(itemStyles.paddingTop).toBe("16px"); // --ds-space-3
    expect(itemStyles.paddingLeft).toBe("20px"); // --ds-space-4
  });

  test("AC6: #progress-message 套用 Badge 樣式；空字串時 :empty 隱藏", async ({ page }) => {
    const badgeBg = await resolveTokenRgb(page, "--ds-badge-bg");
    const badgeBorder = await resolveTokenRgb(page, "--ds-badge-border");
    const badgeText = await resolveTokenRgb(page, "--ds-badge-text");
    const radiusPill = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue("--ds-radius-pill").trim(),
    );
    expect(radiusPill).toBe("999px");

    const msg = page.locator("#progress-message");
    await page.evaluate(() => {
      document.getElementById("progress-message")!.textContent = "轉錄中...";
    });
    await expect(msg).toHaveCSS("background-color", badgeBg);
    await expect(msg).toHaveCSS("border-color", badgeBorder);
    await expect(msg).toHaveCSS("color", badgeText);
    await expect(msg).toHaveCSS("border-radius", "999px");
    const cursor = await msg.evaluate((el) => getComputedStyle(el).cursor);
    expect(cursor).not.toBe("pointer");
    await expect(msg).toBeVisible();

    await page.evaluate(() => {
      document.getElementById("progress-message")!.textContent = "";
    });
    await expect(msg).toBeHidden();
  });

  test("AC7: 取消按鈕仍為 .btn.btn-outline.btn-sm，onclick 含 cancelJob，cursor:pointer，與 badge 視覺明確不同", async ({
    page,
  }) => {
    const cancelBtn = page.locator("#view-progress button", { hasText: "取消" }).first();
    await expect(cancelBtn).toBeVisible();
    const classAttr = await cancelBtn.getAttribute("class");
    expect(classAttr).toContain("btn");
    expect(classAttr).toContain("btn-outline");
    expect(classAttr).toContain("btn-sm");
    const onclickAttr = await cancelBtn.getAttribute("onclick");
    expect(onclickAttr).toContain("cancelJob");

    const btnStyles = await cancelBtn.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { cursor: cs.cursor, borderRadius: cs.borderRadius };
    });
    expect(btnStyles.cursor).toBe("pointer");
    // badge 為 pill (999px)，按鈕沿用全域 --ds-radius-sm (6px)，形狀明確不同
    expect(btnStyles.borderRadius).not.toBe("999px");
  });

  test("AC8: updateProgressUI() 更新 #progress-bar 寬度／#progress-pct／#progress-message 與 icon class（回歸）", async ({
    page,
  }) => {
    await page.evaluate(() => {
      (0, eval)("updateProgressUI")({ progress: 45, message: "轉錄中...", stage: "transcribing" });
    });

    const width = await page.locator("#progress-bar").evaluate((el) => (el as HTMLElement).style.width);
    expect(width).toBe("45%");
    await expect(page.locator("#progress-pct")).toHaveText("45%");
    await expect(page.locator("#progress-message")).toHaveText("轉錄中...");

    await expect(page.locator("#icon-uploaded")).toHaveClass("stage-icon done");
    await expect(page.locator("#icon-transcribed")).toHaveClass("stage-icon active");
    await expect(page.locator("#icon-done")).toHaveClass("stage-icon waiting");
  });

  test("AC9: 其他畫面共用樣式不受影響（view-result .section-title .badge、view-upload .card）", async ({ page }) => {
    await page.evaluate(() => {
      const s = (0, eval)("state");
      s.jobId = "e2e-ds-progress-badge-1";
      s.minutes = {
        job_id: "e2e-ds-progress-badge-1",
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
    const resultBadge = page.locator("#view-result .section-title .badge").first();
    await expect(resultBadge).toBeVisible();
    const resultBadgeStyles = await resultBadge.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderRadius: cs.borderRadius };
    });
    expect(resultBadgeStyles.background).toBe("rgb(239, 238, 234)"); // --ds-badge-bg
    expect(resultBadgeStyles.borderRadius).toBe("999px");

    await page.evaluate(() => {
      (0, eval)("showView")("view-upload");
    });
    const uploadCard = page.locator("#view-upload .card").first();
    const uploadCardStyles = await uploadCard.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { background: cs.backgroundColor, borderRadius: cs.borderRadius, padding: cs.padding };
    });
    expect(uploadCardStyles.background).toBe("rgb(255, 255, 255)"); // --ds-surface
    expect(uploadCardStyles.borderRadius).toBe("10px"); // --ds-radius-md
    expect(uploadCardStyles.padding).toBe("32px"); // --ds-space-6
  });
});
