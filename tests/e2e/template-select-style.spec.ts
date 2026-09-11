import { test, expect } from "@playwright/test";

// SDLCAIP2-36: 會議模板選擇區塊的視覺風格與頁面不一致
//
// 沿用 template-selection.spec.ts 既有的登入繞過與注入結果資料手法，
// 切換到結果畫面後同時可看到 #template-select 與 .meeting-info-grid
// input，用 getComputedStyle 逐一比對 border/border-radius/color/
// font-family，驗證 AC1（樣式一致）在真實瀏覽器渲染下成立，而不只是
// 靠讀原始碼比對 CSS 規則文字。

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const MINUTES = {
  job_id: "e2e-job-style-1",
  template: "general",
  meeting_info: { date: "2026-01-01", time: "10:00", location: "會議室 A", participants: ["Alice"] },
  summary: "原始摘要",
  action_items: [],
  decisions: ["原始決議"],
  sections: [{ title: "原始標題", content: "原始內容" }],
};

test.describe("模板選擇下拉選單樣式一致性（SDLCAIP2-36）", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((token) => {
      sessionStorage.setItem("id_token", token);
    }, fakeIdToken("e2e-template-style-user@example.com"));
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

  test("#template-select 的 border/border-radius/color/font-family 與 .meeting-info-grid input 一致", async ({
    page,
  }) => {
    const infoInput = page.locator(".meeting-info-grid input").first();
    await expect(infoInput).toBeVisible();
    const templateSelect = page.locator("#template-select");
    await expect(templateSelect).toBeVisible();

    const properties = [
      "borderWidth",
      "borderStyle",
      "borderColor",
      "borderRadius",
      "color",
      "fontFamily",
      "fontSize",
      "padding",
    ];

    const referenceStyle = await infoInput.evaluate(
      (el, props: string[]) => {
        const computed = getComputedStyle(el);
        return Object.fromEntries(props.map((p) => [p, computed.getPropertyValue(p) || (computed as any)[p]]));
      },
      properties,
    );

    const targetStyle = await templateSelect.evaluate(
      (el, props: string[]) => {
        const computed = getComputedStyle(el);
        return Object.fromEntries(props.map((p) => [p, computed.getPropertyValue(p) || (computed as any)[p]]));
      },
      properties,
    );

    expect(targetStyle).toEqual(referenceStyle);
  });
});
