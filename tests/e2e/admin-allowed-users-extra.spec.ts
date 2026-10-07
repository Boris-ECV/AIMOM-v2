import { test, expect, Page, Route } from "@playwright/test";

// SDLCAIP2-64 tester: strengthened + edge-case tests (complements admin-allowed-users.spec.ts)

function fakeIdToken(email: string): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ email })).toString("base64url");
  return `${header}.${payload}.fakesig`;
}

const SELF = "admin-self@example.com";

type Item = { email: string; last_login: string | null };

interface Mock {
  items: Item[];
  getCount: number;
  postCount: number;
  postBodies: string[];
  deleteUrls: string[];
  getStatus: number;
  getAbort: boolean;
  postHandler?: (route: Route) => Promise<void>;
  deleteHandler?: (route: Route) => Promise<void>;
  role: string;
}

async function setup(page: Page, items: Item[], opts: Partial<Mock> = {}): Promise<Mock> {
  const mock: Mock = {
    items: [...items],
    getCount: 0,
    postCount: 0,
    postBodies: [],
    deleteUrls: [],
    getStatus: 200,
    getAbort: false,
    role: "admin",
    ...opts,
  };
  await page.route("**/api/me", (route) => route.fulfill({ status: 200, json: { role: mock.role, email: SELF } }));
  await page.route("**/api/admin/usage", (route) =>
    route.fulfill({
      status: 200,
      json: {
        by_date: [{ date: "2026-09-23", calls: 1, input_tokens: 10, output_tokens: 20, estimated_cost: 0.1 }],
        by_user: [{ user_id: "u1", calls: 1, input_tokens: 10, output_tokens: 20, estimated_cost: 0.1 }],
        total_calls: 1,
        total_estimated_cost: 0.1,
      },
    }),
  );
  await page.route("**/api/admin/allowed-users", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      mock.getCount++;
      if (mock.getAbort) return route.abort();
      if (mock.getStatus !== 200) return route.fulfill({ status: mock.getStatus, json: { detail: "x" } });
      return route.fulfill({ status: 200, json: mock.items });
    }
    if (method === "POST") {
      mock.postCount++;
      mock.postBodies.push(route.request().postData() || "");
      if (mock.postHandler) return mock.postHandler(route);
      return route.fulfill({ status: 500, json: { detail: "x" } });
    }
    return route.fallback();
  });
  await page.route("**/api/admin/allowed-users/**", async (route) => {
    if (route.request().method() === "DELETE") {
      mock.deleteUrls.push(route.request().url());
      if (mock.deleteHandler) return mock.deleteHandler(route);
      return route.fulfill({ status: 500, json: { detail: "x" } });
    }
    return route.fallback();
  });
  return mock;
}

async function openDashboard(page: Page) {
  await page.goto("/");
  await page.evaluate((token) => sessionStorage.setItem("id_token", token), fakeIdToken(SELF));
  await page.reload();
  await expect(page.locator("#app-shell")).toBeVisible();
}

async function enter(page: Page) {
  await openDashboard(page);
  await expect(page.locator("#admin-dashboard-btn")).toBeVisible();
  await page.locator("#admin-dashboard-btn").click();
  await expect(page.locator("#view-admin")).toBeVisible();
}

const rows = (page: Page) => page.locator("#allowed-users-tbody tr");
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
const input = (p: Page) => p.locator("#allowed-users-input");
const msg = (p: Page) => p.locator("#allowed-users-msg");
const addBtn = (p: Page) => p.locator("#allowed-users-add-btn");

const THREE: Item[] = [
  { email: "a@x.com", last_login: "2026-09-20T08:30:00Z" },
  { email: "b@x.com", last_login: null },
  { email: "c@x.com", last_login: "2026-09-21T01:02:03Z" },
];

test.describe("SDLCAIP2-64 tester 強化", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("AC1: 標題、API 順序保留、last_login 為本地時間格式而非原始 ISO", async ({ page }) => {
    const items: Item[] = [
      { email: "c@x.com", last_login: "2026-09-21T01:02:03Z" },
      { email: "a@x.com", last_login: "2026-09-20T08:30:00Z" },
    ];
    await setup(page, items);
    await enter(page);
    await expect(page.locator("#allowed-users-card")).toContainText("使用者白名單");
    await expect(rows(page)).toHaveCount(2);
    await expect(rows(page).nth(0).locator("td").first()).toHaveText("c@x.com");
    await expect(rows(page).nth(1).locator("td").first()).toHaveText("a@x.com");
    const cell = (await rows(page).nth(0).locator("td").nth(1).innerText()).trim();
    const expected = await page.evaluate((iso) => new Date(iso).toLocaleString("zh-TW"), items[0].last_login!);
    expect(cell).toBe(expected);
    expect(cell).not.toContain("2026-09-21T01:02:03");
    expect(cell).not.toContain("Z");
  });

  test("AC3: 空清單不顯示任何 tbody 列或表格", async ({ page }) => {
    await setup(page, []);
    await enter(page);
    await expect(page.locator("#allowed-users-status-text")).toHaveText("清單為空");
    await expect(rows(page)).toHaveCount(0);
    await expect(page.locator("#allowed-users-table")).toBeHidden();
  });

  test("AC4: 無整頁重載、不重新 GET、新增後 input 已清空、body 正確且已 trim", async ({ page }) => {
    const mock = await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 201, json: { email: "0first@x.com", last_login: null } }),
    });
    await enter(page);
    await page.evaluate(() => ((window as any).__marker = "alive"));
    await input(page).fill("  0first@x.com  ");
    await addBtn(page).click();
    await expect(rows(page).nth(0).locator("td").first()).toHaveText("0first@x.com");
    await expect(input(page)).toHaveValue("");
    expect(await page.evaluate(() => (window as any).__marker)).toBe("alive");
    expect(mock.getCount).toBe(1);
    expect(mock.postBodies).toHaveLength(1);
    expect(JSON.parse(mock.postBodies[0])).toEqual({ email: "0first@x.com" });
  });

  test("AC5: 重複 200 -> 無重複列、輸入文字保留、非錯誤樣式", async ({ page }) => {
    await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 200, json: { email: "a@x.com", last_login: null } }),
    });
    await enter(page);
    await input(page).fill("a@x.com");
    await addBtn(page).click();
    await expect(msg(page)).toHaveText("已存在");
    await expect(msg(page)).not.toHaveAttribute("data-kind", "error");
    await expect(input(page)).toHaveValue("a@x.com");
    await expect(page.locator('#allowed-users-tbody tr[data-email="a@x.com"]')).toHaveCount(1);
    await expect(rows(page)).toHaveCount(3);
  });

  test("AC6: 422 detail 陣列不外洩、清單與輸入保留、前端不驗證格式（請求照送）", async ({ page }) => {
    const mock = await setup(page, THREE, {
      postHandler: (route) =>
        route.fulfill({
          status: 422,
          json: { detail: [{ loc: ["body", "email"], msg: "SECRET_DETAIL_TEXT", type: "value_error.email" }] },
        }),
    });
    await enter(page);
    await input(page).fill("not-an-email");
    await addBtn(page).click();
    await expect(msg(page)).toHaveText("email 格式不正確");
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("SECRET_DETAIL_TEXT");
    expect(body).not.toContain("object Object");
    await expect(rows(page)).toHaveCount(3);
    await expect(input(page)).toHaveValue("not-an-email");
    expect(mock.postCount).toBe(1);
  });

  test("AC7: Enter 鍵空白輸入不送請求；有值時 Enter 可送出", async ({ page }) => {
    const mock = await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 201, json: { email: "e@x.com", last_login: null } }),
    });
    await enter(page);
    await input(page).fill("   ");
    await input(page).press("Enter");
    await expect(msg(page)).toHaveText("請輸入 email");
    expect(mock.postCount).toBe(0);
    await input(page).fill("e@x.com");
    await input(page).press("Enter");
    await expect(rows(page)).toHaveCount(4);
    expect(mock.postCount).toBe(1);
  });

  test("AC8: 確認態不送請求、同時只有一列在確認態、取消不送請求", async ({ page }) => {
    const mock = await setup(page, THREE, { deleteHandler: (route) => route.fulfill({ status: 204 }) });
    await enter(page);
    await rows(page).nth(0).locator(".au-remove").click();
    await rows(page).nth(1).locator(".au-remove").click();
    await expect(page.locator("#allowed-users-tbody .au-confirm")).toHaveCount(1);
    await expect(page.locator("#allowed-users-tbody .au-cancel")).toHaveCount(1);
    await page.waitForTimeout(200);
    expect(mock.deleteUrls).toHaveLength(0);
    await rows(page).nth(1).locator(".au-cancel").click();
    await expect(page.locator("#allowed-users-tbody .au-confirm")).toHaveCount(0);
    await expect(page.locator("#allowed-users-tbody .au-remove")).toHaveCount(3);
    expect(mock.deleteUrls).toHaveLength(0);
    await rows(page).nth(1).locator(".au-remove").click();
    await rows(page).nth(1).locator(".au-confirm").click();
    await expect(rows(page)).toHaveCount(2);
    await expect(rows(page).nth(0).locator("td").first()).toHaveText("a@x.com");
    await expect(rows(page).nth(1).locator("td").first()).toHaveText("c@x.com");
    expect(mock.deleteUrls).toHaveLength(1);
    expect(mock.deleteUrls[0]).toContain("/api/admin/allowed-users/b%40x.com");
  });

  test("AC9: 404 訊息在重載後仍存在，且重載後的清單為伺服器最新狀態", async ({ page }) => {
    const mock = await setup(page, THREE, {
      deleteHandler: async (route) => {
        mock.items = mock.items.filter((i) => i.email !== "a@x.com");
        await route.fulfill({ status: 404, json: { detail: "nf" } });
      },
    });
    await enter(page);
    await rows(page).nth(0).locator(".au-remove").click();
    await rows(page).nth(0).locator(".au-confirm").click();
    await expect.poll(() => mock.getCount).toBe(2);
    await expect(rows(page)).toHaveCount(2);
    await page.waitForTimeout(300);
    await expect(msg(page)).toBeVisible();
    await expect(msg(page)).toHaveText("找不到此 email");
    await expect(rows(page).nth(0).locator("td").first()).toHaveText("b@x.com");
    await expect(rows(page).nth(0).locator("button")).toBeEnabled();
  });

  test("AC10: DELETE 網路中斷與 POST 5xx 錯誤在區塊內且按鈕恢復", async ({ page }) => {
    const mock = await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 502, json: {} }),
      deleteHandler: (route) => route.abort(),
    });
    await enter(page);
    await input(page).fill("n@x.com");
    await addBtn(page).click();
    await expect(page.locator("#allowed-users-card #allowed-users-msg")).toHaveText("新增失敗，請稍後再試");
    await expect(input(page)).toHaveValue("n@x.com");
    await expect(input(page)).toBeEnabled();
    await expect(rows(page)).toHaveCount(3);
    await rows(page).nth(1).locator(".au-remove").click();
    await rows(page).nth(1).locator(".au-confirm").click();
    await expect(msg(page)).toHaveText("移除失敗，請稍後再試");
    await expect(rows(page)).toHaveCount(3);
    await expect(page.locator("#allowed-users-tbody button")).toHaveCount(3);
    for (let i = 0; i < 3; i++) await expect(rows(page).nth(i).locator("button")).toBeEnabled();
    await expect(addBtn(page)).toBeEnabled();
    expect(mock.deleteUrls).toHaveLength(1);
  });

  test("AC11: 載入失敗（網路中斷）顯示重試；重試仍失敗保持錯誤；成功後恢復；用量表仍顯示", async ({ page }) => {
    const mock = await setup(page, THREE, { getAbort: true });
    await enter(page);
    await expect(page.locator("#allowed-users-status-text")).toHaveText("讀取白名單失敗");
    await expect(page.locator("#admin-by-date-tbody tr")).toHaveCount(1);
    await page.locator("#allowed-users-retry-btn").click();
    await expect.poll(() => mock.getCount).toBe(2);
    await expect(page.locator("#allowed-users-status-text")).toHaveText("讀取白名單失敗");
    mock.getAbort = false;
    await page.locator("#allowed-users-retry-btn").click();
    await expect(rows(page)).toHaveCount(3);
    expect(mock.getCount).toBe(3);
  });

  test("AC12: 新增含惡意 email 的 201 回應也以純文字顯示", async ({ page }) => {
    const evil = `"><img src=x onerror=window.__xss=1>`;
    await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 201, json: { email: evil, last_login: null } }),
    });
    await enter(page);
    await input(page).fill(evil);
    await addBtn(page).click();
    await expect(rows(page)).toHaveCount(4);
    await expect(page.locator("#allowed-users-tbody img")).toHaveCount(0);
    await expect(page.locator("#allowed-users-tbody .au-email").first()).toHaveText(evil);
    expect(await page.evaluate(() => (window as any).__xss)).toBeUndefined();
  });

  test("AC13: 一般使用者 403 時無列、無表格", async ({ page }) => {
    await setup(page, THREE, { role: "user", getStatus: 403 });
    await openDashboard(page);
    await expect(page.locator("#admin-dashboard-btn")).toBeHidden();
    await page.evaluate(() => {
      (0, eval)("showView")("view-admin");
      (0, eval)("openAdminDashboard")();
    });
    await expect(page.locator("#allowed-users-status-text")).toHaveText("僅限管理者存取");
    await expect(rows(page)).toHaveCount(0);
    await expect(page.locator("#allowed-users-table")).toBeHidden();
  });

  test("AC14: POST 進行中 input 也 disabled、雙擊只送一次請求", async ({ page }) => {
    const mock = await setup(page, THREE, {
      postHandler: async (route) => {
        await delay(500);
        await route.fulfill({ status: 201, json: { email: "z@x.com", last_login: null } });
      },
    });
    await enter(page);
    await input(page).fill("z@x.com");
    await addBtn(page).dblclick();
    await expect(addBtn(page)).toBeDisabled();
    await expect(input(page)).toBeDisabled();
    for (let i = 0; i < 3; i++) await expect(rows(page).nth(i).locator("button")).toBeDisabled();
    await expect(rows(page)).toHaveCount(4);
    await expect(addBtn(page)).toBeEnabled();
    await expect(input(page)).toBeEnabled();
    expect(mock.postCount).toBe(1);
  });

  test("AC14: DELETE 進行中取消鈕與新增鈕 disabled、雙擊只送一次 DELETE", async ({ page }) => {
    const mock = await setup(page, THREE, {
      deleteHandler: async (route) => {
        await delay(500);
        await route.fulfill({ status: 204 });
      },
    });
    await enter(page);
    await rows(page).nth(0).locator(".au-remove").click();
    await rows(page).nth(0).locator(".au-confirm").dblclick();
    await expect(addBtn(page)).toBeDisabled();
    await expect(input(page)).toBeDisabled();
    await expect(rows(page).nth(0).locator(".au-cancel")).toBeDisabled();
    await expect(rows(page)).toHaveCount(2);
    await expect(input(page)).toBeEnabled();
    expect(mock.deleteUrls).toHaveLength(1);
  });

  test("AC15: 自己的 email 與一般列同樣需二段確認，確認前不送請求", async ({ page }) => {
    const mock = await setup(page, [{ email: SELF, last_login: null }, ...THREE], {
      deleteHandler: (route) => route.fulfill({ status: 204 }),
    });
    await enter(page);
    const self = page.locator(`#allowed-users-tbody tr[data-email="${SELF}"]`);
    await self.locator(".au-remove").click();
    await expect(self.locator(".au-confirm")).toBeVisible();
    expect(mock.deleteUrls).toHaveLength(0);
    await self.locator(".au-confirm").click();
    await expect(self).toHaveCount(0);
    expect(mock.deleteUrls).toHaveLength(1);
  });

  test("401 於新增時不當機：回到登入閘道且無 pageerror", async ({ page }) => {
    await setup(page, THREE, { postHandler: (route) => route.fulfill({ status: 401, json: { detail: "x" } }) });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await enter(page);
    await input(page).fill("n@x.com");
    await addBtn(page).click();
    await expect(page.locator("#auth-gate")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
