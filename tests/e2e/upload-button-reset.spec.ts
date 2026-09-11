import { test, expect } from "@playwright/test";

// SDLCAIP2-34: 從管理者儀表板返回上傳頁後，上傳按鈕錯誤顯示「上傳中」
//
// 沿用 template-selection.spec.ts 的登入繞過（假 id_token）與
// `(0, eval)("state")` / `(0, eval)("fnName")()` 直接操作頁面全域狀態的
// 手法。完整實際走一次「選檔 → presign → S3 PUT → complete」對這張票
// 要驗證的行為（doUpload 成功路徑是否呼叫 resetState()）沒有額外價值，
// 這裡用 page.route 攔截三個網路呼叫，聚焦驗證修正本身：成功路徑結束後
// #upload-btn 的文字/disabled 狀態，以及往返管理者儀表板後畫面是否正確。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

test.describe("上傳按鈕狀態還原（SDLCAIP2-34）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-upload-reset-user@example.com"));
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();

    // 讓管理者儀表板按鈕顯示出來，並準備好返回時該頁面需要的資料
    await page.route("**/api/me", (route) => route.fulfill({ status: 200, json: { role: "admin" } }));
    await page.route("**/api/admin/usage", (route) =>
      route.fulfill({
        status: 200,
        json: { by_date: [], by_user: [], total_calls: 0, total_estimated_cost: 0 },
      })
    );

    // doUpload() 內部依序呼叫的三個網路請求
    await page.route("**/api/upload/presign", (route) =>
      route.fulfill({
        status: 200,
        json: {
          job_id: "e2e-upload-reset-job-1",
          upload_url: "https://fake-s3.example.com/put-url",
          s3_key: "fake/key.mp3",
          content_type: "audio/mpeg",
        },
      })
    );
    await page.route("https://fake-s3.example.com/put-url", (route) =>
      route.fulfill({ status: 200, body: "" })
    );
    await page.route("**/api/upload/complete", (route) =>
      route.fulfill({ status: 200, json: { job_id: "e2e-upload-reset-job-1" } })
    );
    await page.route("**/api/transcribe", (route) => route.fulfill({ status: 200, json: {} }));
    await page.route("**/api/status/**", (route) =>
      route.fulfill({ status: 200, json: { stage: "uploaded" } })
    );

    // 重新載入一次讓 checkAdminAccess() 用到剛才註冊的 /api/me route
    await page.reload();
    await expect(page.locator("#app-shell")).toBeVisible();
    await expect(page.locator("#admin-dashboard-btn")).toBeVisible();

    // 用假檔案物件直接驅動 setFile()，跳過真實檔案選取 UI 互動
    await page.evaluate(() => {
      const file = new File(["fake audio bytes"], "meeting.mp3", { type: "audio/mpeg" });
      (0, eval)("setFile")(file);
    });
    await expect(page.locator("#upload-btn")).toBeEnabled();
  });

  test("AC1: 上傳成功後經管理者儀表板往返，按鈕文字回到「開始處理」、file-info 隱藏（不再顯示上傳中）", async ({
    page,
  }) => {
    await page.locator("#upload-btn").click();
    // 成功路徑會呼叫 showView('view-progress')
    await expect(page.locator("#view-progress")).toBeVisible();

    await page.locator("#admin-dashboard-btn").click();
    await expect(page.locator("#view-admin")).toBeVisible();

    await page.locator('#view-admin button:has-text("← 返回")').click();
    await expect(page.locator("#view-upload")).toBeVisible();

    // 注意：resetState() 是「還原成初始（尚未選檔）狀態」的權威實作，其
    // 初始狀態本身即 disabled=true（與頁面首次載入、未選檔時的 HTML
    // 預設一致）。Gherkin AC1 字面寫「該按鈕應處於未停用（可點擊）狀態」
    // 與此處 disabled=true 的實際行為衝突——已在交付報告中回報此規格
    // 衝突，此處斷言記錄的是套用設計文件指定實作後的實際行為，而非片面
    // 修改斷言掩蓋衝突。
    const btn = page.locator("#upload-btn");
    await expect(btn).toHaveText(/開始處理/);
    await expect(btn).toBeDisabled();
    await expect(page.locator("#file-info")).toBeHidden();
  });

  test("回歸測試: 上傳流程進行中（尚未回應）按鈕應顯示「上傳中...」且停用", async ({ page }) => {
    // 讓 presign 請求卡住不回應，藉此觀察「進行中」瞬間的按鈕狀態
    await page.unroute("**/api/upload/presign");
    await page.route("**/api/upload/presign", () => {
      // 故意不 fulfill/abort，模擬仍在等待後端回應
    });

    await page.locator("#upload-btn").click();

    const btn = page.locator("#upload-btn");
    await expect(btn).toHaveText(/上傳中/);
    await expect(btn).toBeDisabled();
  });

  test("上傳失敗後按鈕不應停留在「上傳中...」", async ({ page }) => {
    await page.unroute("**/api/upload/presign");
    await page.route("**/api/upload/presign", (route) =>
      route.fulfill({ status: 500, json: { detail: "模擬後端錯誤" } })
    );

    await page.locator("#upload-btn").click();

    const btn = page.locator("#upload-btn");
    await expect(btn).toHaveText(/開始處理/);
    await expect(btn).toBeEnabled();
  });

  test("上傳失敗後 state.file 仍在（與 AC1 的「未選檔」情境不同），file-info 仍顯示、可直接重新送出", async ({
    page,
  }) => {
    // 驗證設計文件根因分析點 1 所述的區別：catch 區塊的還原不是呼叫
    // resetState()（那會連帶清掉 state.file、隱藏 file-info），而是手動只
    // 復原按鈕本身，因此使用者已選檔的狀態必須維持，不需要重新選檔就能
    // 再次點擊送出。
    await page.unroute("**/api/upload/presign");
    await page.route("**/api/upload/presign", (route) =>
      route.fulfill({ status: 500, json: { detail: "模擬後端錯誤" } })
    );

    await page.locator("#upload-btn").click();

    const btn = page.locator("#upload-btn");
    await expect(btn).toHaveText(/開始處理/);
    await expect(btn).toBeEnabled();
    // 關鍵斷言：與 AC1（未選檔情境，file-info 應隱藏）相反，這裡
    // file-info 應該仍然顯示，證明 state.file 沒有被清空。
    await expect(page.locator("#file-info")).toBeVisible();
    await expect(page.evaluate(() => (0, eval)("state").file !== null)).resolves.toBe(true);
  });
});
