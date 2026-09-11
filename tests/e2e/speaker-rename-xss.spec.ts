import { test, expect } from "@playwright/test";

// SDLCAIP2-31: 講者重新命名輸入框渲染未轉義使用者輸入，DOM-based XSS 風險（e2e）
//
// 沿用 speaker-naming.spec.ts 的登入繞過手法（塞入假 id_token 到
// sessionStorage）與 state 注入手法（(0, eval)("state") 走一次間接 eval
// 取得 index.html 內嵌 <script> 的頂層詞法綁定）。
//
// 這份 e2e spec 是本故事需要的一環：pytest 的靜態字串檢查只能確認原始碼
// 中的 template literal 有沒有寫上 esc(...)，無法驗證瀏覽器實際解析
// innerHTML 之後，屬性值是否真的沒有在引號處被截斷、有沒有多長出
// onmouseover 這類屬性、以及有沒有觸發 alert —— 這些都只有透過真的
// 渲染 DOM 並讀取 element.value / outerHTML / dialog 事件才能斷言，
// 因此本故事宣告需要 e2e 覆蓋。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

async function setupTranscript(page: import("@playwright/test").Page, segments: unknown, speakers: Record<string, string> = {}) {
  await page.goto("/");
  await page.evaluate((token) => {
    sessionStorage.setItem("id_token", token);
  }, fakeIdToken("e2e-speaker-xss-user@example.com"));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();

  await page.evaluate(
    ({ segments, speakers }) => {
      const s = (0, eval)("state");
      s.jobId = "e2e-speaker-xss-job-1";
      s.segments = segments;
      s.speakers = speakers;
      (0, eval)("renderTranscript")();
      (0, eval)("showView")("view-result");
      (0, eval)("switchTab")("transcript");
    },
    { segments, speakers }
  );
  await expect(page.locator("#view-result")).toBeVisible();
  await expect(page.locator("#tab-transcript")).toBeVisible();
}

test.describe("講者重新命名輸入框 XSS 修補（SDLCAIP2-31）", () => {
  test("正常講者標籤與姓名維持原樣渲染（無迴歸）", async ({ page }) => {
    await setupTranscript(page, [{ start: 0, speaker: "Speaker 1", text: "大家好。" }]);

    const row = page.locator("#speaker-rename-area .rename-row").first();
    await expect(row.locator("label")).toHaveText("Speaker 1");
    await expect(row.locator("input")).toHaveValue("Speaker 1");

    const outerHTML = await row.locator("input").evaluate((el) => el.outerHTML);
    expect(outerHTML).not.toContain("onmouseover");
  });

  test("講者標籤含 HTML/屬性特殊字元時被中和，不執行 alert，value 讀出完整字面值", async ({ page }) => {
    const dialogs: string[] = [];
    page.on("dialog", async (dialog) => {
      dialogs.push(dialog.message());
      await dialog.dismiss();
    });
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    const maliciousSpeaker = 'Speaker" onmouseover="alert(1)';
    await setupTranscript(page, [{ start: 0, speaker: maliciousSpeaker, text: "hi" }]);

    const input = page.locator("#speaker-rename-area .rename-row").first().locator("input");

    // value 屬性讀出的字面值必須「完整等於」原始輸入字串，未在內嵌引號處被截斷
    await expect(input).toHaveValue(maliciousSpeaker);

    // DOM 上不應多出 onmouseover（或其他非預期）屬性
    const attrNames = await input.evaluate((el) =>
      Array.from(el.attributes).map((a) => a.name).sort()
    );
    expect(attrNames).toEqual(["onchange", "placeholder", "type", "value"]);

    // 觸發 mouseover，確認沒有 onmouseover handler 可以執行
    await input.hover();
    await page.waitForTimeout(100);

    expect(dialogs).toEqual([]);
    expect(pageErrors).toEqual([]);
  });

  test("已輸入過、含特殊字元的講者姓名被中和，value 讀出完整字面值，不渲染成子元素，不執行 alert", async ({ page }) => {
    // 注意：<label> 一律顯示原始講者標籤 sp（見 renderTranscript() `<label>${esc(sp)}</label>`），
    // 從不顯示 state.speakers[sp]；已輸入過的自訂姓名實際渲染於 <input value="...">
    // （renderTranscript() 中 `esc(state.speakers[sp] || sp)`，即設計文件 docs/design/SDLCAIP2-31.md
    // 確認的漏洞核心注入點）。本測試因此針對 <input> 的 value 屬性斷言，而非 <label>。
    const dialogs: string[] = [];
    page.on("dialog", async (dialog) => {
      dialogs.push(dialog.message());
      await dialog.dismiss();
    });
    const pageErrors: Error[] = [];
    page.on("pageerror", (err) => pageErrors.push(err));

    const maliciousName = "<img src=x onerror=alert(1)>";
    await setupTranscript(
      page,
      [{ start: 0, speaker: "Speaker 1", text: "hi" }],
      { "Speaker 1": maliciousName }
    );

    const row = page.locator("#speaker-rename-area .rename-row").first();
    const input = row.locator("input");

    // value 屬性讀出的字面值必須「完整等於」原始輸入字串，不會被解析成子元素
    await expect(input).toHaveValue(maliciousName);
    const imgCount = await row.locator("img").count();
    expect(imgCount).toBe(0);

    const attrNames = await input.evaluate((el) =>
      Array.from(el.attributes).map((a) => a.name).sort()
    );
    expect(attrNames).toEqual(["onchange", "placeholder", "type", "value"]);

    expect(dialogs).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
});
