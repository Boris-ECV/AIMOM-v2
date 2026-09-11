import { test, expect } from "@playwright/test";

// SDLCAIP2-18: 逐字稿分頁講者命名 UI（e2e）
//
// 沿用 template-selection.spec.ts 的登入繞過手法（塞入假 id_token 到
// sessionStorage）與 state 注入手法（(0, eval)("state") 走一次間接 eval
// 取得 index.html 內嵌 <script> 的頂層詞法綁定）。
//
// POST /api/speaker-names 打的是 config.js 寫死的遠端 AWS API base URL，
// 不適合在 e2e 環境呼叫真實服務；用 page.route 攔截該請求，驗證的是
// 「前端收到回應之後的實際處理行為」（state.segments 整包覆蓋、
// state.speakers 清空、renderTranscript 重新渲染），這是本故事新增、
// 目前完全沒有涵蓋的前端邏輯，後端 /api/speaker-names 本身行為已由
// src/tests/test_speaker_names.py 涵蓋。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const INITIAL_SEGMENTS = [
  { start: 0, speaker: "SPEAKER_A", text: "大家好，我們開始開會。" },
  { start: 5, speaker: "SPEAKER_B", text: "好的，我先報告進度。" },
];

test.describe("講者命名 UI（SDLCAIP2-18）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-speaker-naming-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    // 直接注入逐字稿資料並切換到結果畫面 + 逐字稿分頁，繞過完整
    // 上傳/轉錄流程（已由其他測試涵蓋），聚焦驗證本故事新增行為。
    await page.evaluate((segments) => {
      const s = (0, eval)("state");
      s.jobId = "e2e-speaker-job-1";
      s.segments = segments;
      s.speakers = {};
      (0, eval)("renderTranscript")();
      (0, eval)("showView")("view-result");
      (0, eval)("switchTab")("transcript");
    }, INITIAL_SEGMENTS);
    await expect(page.locator("#view-result")).toBeVisible();
    await expect(page.locator("#tab-transcript")).toBeVisible();
  });

  test("AC1: 逐字稿分頁列出偵測到的講者標籤與命名輸入框", async ({ page }) => {
    const renameArea = page.locator("#speaker-rename-area");
    await expect(renameArea).toBeVisible();
    const rows = renameArea.locator(".rename-row");
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0).locator("label")).toHaveText("SPEAKER_A");
    await expect(rows.nth(0).locator("input")).toHaveValue("SPEAKER_A");
    await expect(rows.nth(1).locator("label")).toHaveText("SPEAKER_B");
    await expect(rows.nth(1).locator("input")).toHaveValue("SPEAKER_B");
  });

  test("AC5: 畫面明確告知命名的影響範圍（只更新逐字稿分頁與匯出檔案，不更新會議紀錄分頁）", async ({ page }) => {
    await expect(page.locator("#speaker-rename-area")).toContainText(
      "只會更新此逐字稿分頁與匯出檔案"
    );
    await expect(page.locator("#speaker-rename-area")).toContainText(
      "不會更新「會議紀錄」分頁的參與者／待辦事項負責人"
    );
  });

  test("AC2: 送出命名後呼叫後端 API 並更新逐字稿顯示（含匯出用資料來源 state.segments/state.speakers）", async ({ page }) => {
    let requestBody: any = null;
    const updatedResponse = {
      job_id: "e2e-speaker-job-1",
      speakers: ["王小明", "SPEAKER_B"],
      segments: [
        { start: 0, speaker: "王小明", text: "大家好，我們開始開會。" },
        { start: 5, speaker: "SPEAKER_B", text: "好的，我先報告進度。" },
      ],
    };
    await page.route("**/api/speaker-names", async (route) => {
      requestBody = route.request().postDataJSON();
      await route.fulfill({ status: 200, json: updatedResponse });
    });

    const rows = page.locator("#speaker-rename-area .rename-row");
    await rows.nth(0).locator("input").fill("王小明");
    await rows.nth(0).locator("input").dispatchEvent("change");

    await page.locator("#submit-speaker-names-btn").click();

    // request 只帶「已填寫且改動過」的項目，不含未改名的 SPEAKER_B
    await expect.poll(() => requestBody).toEqual({
      job_id: "e2e-speaker-job-1",
      speaker_names: { SPEAKER_A: "王小明" },
    });

    await expect(page.locator("#transcript-container")).toContainText("王小明");
    await expect(page.locator("#transcript-container")).not.toContainText("SPEAKER_A");

    const segmentsAfter = await page.evaluate(() => (0, eval)("state").segments);
    expect(segmentsAfter).toEqual(updatedResponse.segments);
    const speakersAfter = await page.evaluate(() => (0, eval)("state").speakers);
    expect(speakersAfter).toEqual({});
  });

  test("AC3: 不命名任何講者仍可正常使用會議紀錄（未點擊送出，標籤維持原始 AI 標籤）", async ({ page }) => {
    let requestCalled = false;
    await page.route("**/api/speaker-names", async (route) => {
      requestCalled = true;
      await route.fulfill({ status: 200, json: { job_id: "x", speakers: [], segments: [] } });
    });

    await expect(page.locator("#transcript-container")).toContainText("SPEAKER_A");
    await expect(page.locator("#transcript-container")).toContainText("SPEAKER_B");
    expect(requestCalled).toBe(false);

    const segments = await page.evaluate(() => (0, eval)("state").segments);
    expect(segments).toEqual(INITIAL_SEGMENTS);
  });

  test("AC4: 後端回傳未知標籤時前端不報錯", async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    await page.route("**/api/speaker-names", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          job_id: "e2e-speaker-job-1",
          speakers: ["SPEAKER_UNKNOWN"],
          segments: [{ start: 0, speaker: "SPEAKER_UNKNOWN", text: "未預期的講者標籤。" }],
        },
      });
    });

    await page.locator("#submit-speaker-names-btn").click();

    await expect(page.locator("#transcript-container")).toContainText("SPEAKER_UNKNOWN");
    expect(pageErrors).toEqual([]);
  });
});
