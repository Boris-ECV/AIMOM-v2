import { test, expect } from "@playwright/test";

// SDLCAIP2-39: view-result 操作列 (action bar) 寬/窄螢幕下應維持單排不換行，
// 清除暫存／新錄音靠右對齊，且三顆按鈕（重新產生／匯出／清除暫存）只顯示文字、
// 不顯示 emoji 圖示。
//
// 沿用 template-select-style.spec.ts 既有的登入繞過與注入結果資料手法，
// 切換到結果畫面後直接用 getBoundingClientRect()/scrollWidth 驗證版面配置，
// 而不只是靠讀原始碼比對 CSS 規則文字。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const MINUTES = {
  job_id: "e2e-job-actionbar-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

test.describe("操作列 nowrap 與圖示移除（SDLCAIP2-39）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-action-bar-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = minutes.job_id;
      s.minutes = minutes;
      s.modified = false;
      (0, eval)("renderMinutes")();
      (0, eval)("showView")("view-result");
    }, MINUTES);
    await expect(page.locator("#view-result")).toBeVisible();
  });

  // AC1/AC2 輔助函式：擷取操作列所有「可見」子元素的 bounding box。
  // 注意：#result-action-group-content 內混雜 <label>（文字+下拉選單，較高）
  // 與 <button>（較矮），容器 align-items:center 會讓矮元素置中對齊、
  // 其 top 座標略低於高元素——這是同一排內正常的 flexbox 置中效果，
  // 不代表換行。因此改用「垂直範圍是否互相重疊」判斷是否同一排，
  // 而不是要求 top 座標逐一相等（後者在高度不一致的子元素上必然失敗，
  // 與是否換行無關）。
  async function getVisibleRects(page: import("@playwright/test").Page) {
    return page.evaluate(() => {
      const groups = [
        document.getElementById("result-action-group-content"),
        document.getElementById("result-action-group-reset"),
      ].filter((el): el is HTMLElement => !!el);
      const children: HTMLElement[] = [];
      for (const g of groups) {
        children.push(...(Array.from(g.children) as HTMLElement[]));
      }
      // #modified-badge / #low-confidence-badge 預設 display:none（依狀態才顯示），
      // 不在畫面上佔位，故排除隱藏元素。
      return children
        .filter((el) => getComputedStyle(el).display !== "none")
        .map((el) => {
          const r = el.getBoundingClientRect();
          return { top: r.top, bottom: r.bottom };
        });
    });
  }

  function allSameRow(rects: { top: number; bottom: number }[]): boolean {
    // 同一排 := 存在一個共同的水平線同時落在所有元素的 [top, bottom] 範圍內
    // （亦即所有元素的垂直範圍互相重疊），沒有任何元素被換到第二排。
    const maxTop = Math.max(...rects.map((r) => r.top));
    const minBottom = Math.min(...rects.map((r) => r.bottom));
    return maxTop < minBottom;
  }

  test("AC1: 1280px 寬螢幕下操作列所有元素同一排（不換行）", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    const rects = await getVisibleRects(page);
    expect(rects.length).toBeGreaterThan(0);
    expect(allSameRow(rects)).toBe(true);
  });

  test("AC2: 480px 窄螢幕下操作列仍維持單排並可水平捲動", async ({ page }) => {
    await page.setViewportSize({ width: 480, height: 900 });

    const rects = await getVisibleRects(page);
    expect(rects.length).toBeGreaterThan(0);
    expect(allSameRow(rects)).toBe(true);

    const outer = page.locator("#result-action-group-content").locator("..");
    const overflow = await outer.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      overflowX: getComputedStyle(el).overflowX,
    }));
    expect(overflow.overflowX).toBe("auto");
    expect(overflow.scrollWidth).toBeGreaterThan(overflow.clientWidth);
  });

  test("AC3: 1280px 寬度下 #result-action-group-reset 位於最右側，其餘控制項靠左、順序不變", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    const contentGroup = page.locator("#result-action-group-content");
    const resetGroup = page.locator("#result-action-group-reset");

    const contentBox = await contentGroup.boundingBox();
    const resetBox = await resetGroup.boundingBox();
    expect(contentBox).not.toBeNull();
    expect(resetBox).not.toBeNull();

    // reset group 位於 content group 右側
    expect(resetBox!.x).toBeGreaterThan(contentBox!.x + contentBox!.width - 1);

    // 內容群組維持原有相對順序：模板選單 -> 重新產生 -> 匯出格式選單 -> 匯出
    const order = await contentGroup.evaluate((el) => {
      const ids: string[] = [];
      for (const child of Array.from(el.children)) {
        const select = child.matches("select") ? child : child.querySelector("select");
        if (child.id === "template-select" || select?.id === "template-select") ids.push("template-select");
        else if (child.id === "regenerate-btn") ids.push("regenerate-btn");
        else if (select?.id === "export-format-select") ids.push("export-format-select");
        else if (child.id === "export-confirm-btn") ids.push("export-confirm-btn");
      }
      return ids;
    });
    expect(order).toEqual(["template-select", "regenerate-btn", "export-format-select", "export-confirm-btn"]);

    // reset group 內含 cleanup-btn、new-recording-btn，順序不變
    const resetOrder = await resetGroup.evaluate((el) =>
      Array.from(el.children).map((c) => (c as HTMLElement).id),
    );
    expect(resetOrder).toEqual(["cleanup-btn", "new-recording-btn"]);
  });

  test("AC4: 重新產生／匯出／清除暫存按鈕只顯示文字，不含 emoji 圖示", async ({ page }) => {
    await expect(page.locator("#regenerate-btn")).toHaveText("重新產生");
    await expect(page.locator("#export-confirm-btn")).toHaveText("匯出");
    await expect(page.locator("#cleanup-btn")).toHaveText("清除暫存");

    const texts = await page.evaluate(() => ({
      regenerate: document.getElementById("regenerate-btn")?.textContent ?? "",
      exportBtn: document.getElementById("export-confirm-btn")?.textContent ?? "",
      cleanup: document.getElementById("cleanup-btn")?.textContent ?? "",
    }));
    expect(texts.regenerate).not.toContain("🔄");
    expect(texts.exportBtn).not.toContain("⬇");
    expect(texts.cleanup).not.toContain("🗑");
  });

  test("AC5 (回歸): 三顆按鈕的 onclick 呼叫仍指向既有函式，未因本次純視覺變更改變", async ({ page }) => {
    const handlers = await page.evaluate(() => ({
      regenerate: document.getElementById("regenerate-btn")?.getAttribute("onclick"),
      exportBtn: document.getElementById("export-confirm-btn")?.getAttribute("onclick"),
      cleanup: document.getElementById("cleanup-btn")?.getAttribute("onclick"),
    }));
    expect(handlers.regenerate).toBe("regenerateSummary()");
    expect(handlers.exportBtn).toBe("exportSelectedFormat()");
    expect(handlers.cleanup).toBe("cleanupAndReset()");

    // 確認這些函式在頁面上確實存在（未被移除/改名），維持既有行為的呼叫面
    const fnTypes = await page.evaluate(() => ({
      regenerate: typeof (0, eval)("regenerateSummary"),
      exportBtn: typeof (0, eval)("exportSelectedFormat"),
      cleanup: typeof (0, eval)("cleanupAndReset"),
    }));
    expect(fnTypes.regenerate).toBe("function");
    expect(fnTypes.exportBtn).toBe("function");
    expect(fnTypes.cleanup).toBe("function");
  });
});
