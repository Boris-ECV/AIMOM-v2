import { test, expect } from "@playwright/test";

// SDLCAIP2-17: 已保留會議紀錄詳情頁編輯 UI（拆分後改寫範圍）（e2e）
//
// 沿用 history-detail.spec.ts 的登入繞過手法（塞入假 id_token 到
// sessionStorage）與 page.route 攔截手法。GET/PATCH /api/meetings/{id}
// 打的是 config.js 寫死的遠端 AWS API base URL，不適合在 e2e 環境呼叫
// 真實服務；用 page.route 攔截，驗證的是「前端收到回應之後的實際處理
// 行為」（編輯模式切換、儲存成功後重新渲染唯讀內容、儲存失敗/404 時
// 保留使用者輸入且不切回唯讀模式）——這些都是本故事新增、目前完全沒有
// 涵蓋的前端邏輯，因此本故事宣告需要 e2e 覆蓋。PATCH /api/meetings/{id}
// 後端本身行為已由 src/tests/test_history.py 涵蓋。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function loginBypass(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-history-edit-user@example.com"));
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
    action_items: [{ owner: "王小明", task: "整理紀錄", due: "2026-09-12" }],
    decisions: ["採用方案A"],
    sections: [{ title: "討論主題一", content: "討論內容一" }],
  },
  expires_at: 9999999999,
};

async function openDetail(page: import("@playwright/test").Page) {
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

test.describe("已保留會議紀錄詳情頁編輯 UI（SDLCAIP2-17）", () => {
  test.beforeEach(async ({ page }) => {
    await loginBypass(page);
  });

  test("AC1: 點擊「編輯」切換為可輸入狀態並顯示儲存/取消按鈕", async ({ page }) => {
    await openDetail(page);

    await expect(page.locator("#history-edit-btn")).toBeVisible();
    await expect(page.locator("#history-save-btn")).toBeHidden();
    await expect(page.locator("#history-cancel-btn")).toBeHidden();
    await expect(page.locator("#history-date")).toBeDisabled();

    await page.locator("#history-edit-btn").click();

    await expect(page.locator("#history-edit-btn")).toBeHidden();
    await expect(page.locator("#history-save-btn")).toBeVisible();
    await expect(page.locator("#history-cancel-btn")).toBeVisible();
    await expect(page.locator("#history-date")).toBeEnabled();

    // 雙擊摘要進入 contenteditable（沿用 view-result 既有機制）
    await page.locator("#history-summary-text").dblclick();
    await expect(page.locator("#history-summary-text")).toHaveAttribute("contenteditable", "true");
  });

  test("AC2: 儲存成功後畫面切回唯讀並顯示最新內容與成功提示", async ({ page }) => {
    let patchBody: any = null;
    await page.route("**/api/meetings/m-1", async (route) => {
      if (route.request().method() === "PATCH") {
        patchBody = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          json: {
            ...DETAIL_RESPONSE,
            minutes: { ...DETAIL_RESPONSE.minutes, summary: "更新後的摘要" },
          },
        });
      } else {
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      }
    });
    await page.route("**/api/meetings", async (route) => {
      await route.fulfill({
        status: 200,
        json: { meetings: [{ meeting_id: "m-1", title: "第一次會議", created_at: 1735689600, expires_at: 9999999999 }] },
      });
    });

    await page.locator("#history-nav-btn").click();
    await page.locator("#history-tbody tr").first().click();
    await expect(page.locator("#history-detail-body")).toBeVisible();

    await page.locator("#history-edit-btn").click();
    await page.locator("#history-summary-text").dblclick();
    await page.locator("#history-summary-text").fill("更新後的摘要");
    await page.locator("#history-summary-text").blur();

    await page.locator("#history-save-btn").click();

    await expect(page.locator("#toast")).toContainText("已儲存");
    await expect(page.locator("#history-summary-text")).toHaveText("更新後的摘要");
    await expect(page.locator("#history-edit-btn")).toBeVisible();
    await expect(page.locator("#history-save-btn")).toBeHidden();
    await expect(page.locator("#history-cancel-btn")).toBeHidden();
    await expect(page.locator("#history-summary-text")).not.toHaveAttribute("contenteditable", "true");

    expect(patchBody).not.toBeNull();
    expect(patchBody.job_id).toBe("job-abc");
    expect(patchBody.template).toBe("general");
    expect(patchBody.summary).toBe("更新後的摘要");
  });

  test("AC3: 儲存失敗（網路錯誤）時保留輸入且停留編輯模式", async ({ page }) => {
    await openDetail(page);

    await page.route("**/api/meetings/m-1", async (route) => {
      if (route.request().method() === "PATCH") {
        await route.abort("failed");
      } else {
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      }
    });

    await page.locator("#history-edit-btn").click();
    await page.locator("#history-summary-text").dblclick();
    await page.locator("#history-summary-text").fill("尚未送出成功的修改");
    await page.locator("#history-summary-text").blur();

    await page.locator("#history-save-btn").click();

    await expect(page.locator("#toast")).toContainText("儲存失敗");
    await expect(page.locator("#history-summary-text")).toHaveText("尚未送出成功的修改");
    await expect(page.locator("#history-save-btn")).toBeVisible();
    await expect(page.locator("#history-cancel-btn")).toBeVisible();
    await expect(page.locator("#history-edit-btn")).toBeHidden();
  });

  test("AC4: PATCH 回應 404 時顯示「找不到此會議紀錄」且不遺失輸入、不切回唯讀", async ({ page }) => {
    await openDetail(page);

    await page.route("**/api/meetings/m-1", async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({ status: 404, json: { detail: "找不到此會議紀錄" } });
      } else {
        await route.fulfill({ status: 200, json: DETAIL_RESPONSE });
      }
    });

    await page.locator("#history-edit-btn").click();
    await page.locator("#history-summary-text").dblclick();
    await page.locator("#history-summary-text").fill("刪除前的最後編輯");
    await page.locator("#history-summary-text").blur();

    await page.locator("#history-save-btn").click();

    await expect(page.locator("#toast")).toContainText("找不到此會議紀錄");
    await expect(page.locator("#history-summary-text")).toHaveText("刪除前的最後編輯");
    await expect(page.locator("#history-save-btn")).toBeVisible();
    await expect(page.locator("#history-cancel-btn")).toBeVisible();
    await expect(page.locator("#history-edit-btn")).toBeHidden();
  });

  test("取消編輯會捨棄未儲存的變更並還原唯讀畫面", async ({ page }) => {
    await openDetail(page);

    await page.locator("#history-edit-btn").click();
    await page.locator("#history-summary-text").dblclick();
    await page.locator("#history-summary-text").fill("這段修改會被捨棄");
    await page.locator("#history-summary-text").blur();

    await page.locator("#history-cancel-btn").click();

    await expect(page.locator("#history-summary-text")).toHaveText("這是摘要內容");
    await expect(page.locator("#history-edit-btn")).toBeVisible();
    await expect(page.locator("#history-save-btn")).toBeHidden();
    await expect(page.locator("#history-cancel-btn")).toBeHidden();
  });
});
