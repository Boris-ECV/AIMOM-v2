import { test, expect } from "@playwright/test";

// SDLCAIP2-33: 語言偵測信心過低時的持續性警示徽章（e2e）
//
// 沿用 speaker-naming.spec.ts 的登入繞過手法（塞入假 id_token 到
// sessionStorage）與 state 注入手法（(0, eval)("state") 走一次間接 eval
// 取得 index.html 內嵌 <script> 的頂層詞法綁定），直接注入
// state.lowLanguageConfidence + state.minutes 並呼叫 renderMinutes()，
// 繞過完整上傳/轉錄流程（後端行為已由 src/tests/test_progress.py 涵蓋），
// 聚焦驗證本故事新增的前端渲染邏輯：#low-confidence-badge 是否根據
// state.lowLanguageConfidence 獨立顯示/隱藏，且與 #modified-badge
// 互不影響。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const MINUTES = {
  template: "general",
  meeting_info: { date: "", time: "", location: "", participants: [] },
  summary: "測試摘要",
  action_items: [],
  decisions: [],
  sections: [],
};

test.describe("語言信心過低警示徽章（SDLCAIP2-33）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-low-confidence-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();
  });

  test("AC: 信心過低時顯示徽章，與 #modified-badge 互不影響", async ({ page }) => {
    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = "e2e-low-conf-job";
      s.segments = [];
      s.minutes = minutes;
      s.lowLanguageConfidence = true;
      (0, eval)("showView")("view-result");
      (0, eval)("renderMinutes")();
    }, MINUTES);

    await expect(page.locator("#view-result")).toBeVisible();
    await expect(page.locator("#low-confidence-badge")).toBeVisible();
    await expect(page.locator("#low-confidence-badge")).toContainText(
      "偵測到的語言信心水準較低"
    );
    // 沿用 #modified-badge 的 warning 樣式常駐顯示，但兩者是獨立的 DOM
    // 元素/toggle 邏輯：#modified-badge 預設仍是隱藏的（尚未編輯過）。
    await expect(page.locator("#modified-badge")).toBeHidden();
  });

  test("AC: 信心正常時不顯示徽章", async ({ page }) => {
    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = "e2e-ok-conf-job";
      s.segments = [];
      s.minutes = minutes;
      s.lowLanguageConfidence = false;
      (0, eval)("showView")("view-result");
      (0, eval)("renderMinutes")();
    }, MINUTES);

    await expect(page.locator("#view-result")).toBeVisible();
    await expect(page.locator("#low-confidence-badge")).toBeHidden();
  });

  test("AC: 徽章顯示與 #modified-badge 的編輯狀態互相獨立（切換其一不影響另一個）", async ({ page }) => {
    await page.evaluate((minutes) => {
      const s = (0, eval)("state");
      s.jobId = "e2e-independent-job";
      s.segments = [];
      s.minutes = minutes;
      s.lowLanguageConfidence = true;
      (0, eval)("showView")("view-result");
      (0, eval)("renderMinutes")();
      // 模擬使用者編輯行為觸發 markModified()，只應影響 #modified-badge
      (0, eval)("markModified")();
    }, MINUTES);

    await expect(page.locator("#low-confidence-badge")).toBeVisible();
    await expect(page.locator("#modified-badge")).toBeVisible();
  });
});
