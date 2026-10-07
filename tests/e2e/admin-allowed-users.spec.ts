import { test, expect, Page, Route } from "@playwright/test";

// SDLCAIP2-64: 管理者儀表板 使用者白名單管理 UI（AC1-AC15）

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

const THREE: Item[] = [
  { email: "a@x.com", last_login: "2026-09-20T08:30:00Z" },
  { email: "b@x.com", last_login: null },
  { email: "c@x.com", last_login: "2026-09-21T01:02:03Z" },
];

test.describe("使用者白名單管理 UI（SDLCAIP2-64）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("AC1/AC2: 顯示 email 與本地時間，null 顯示「—」", async ({ page }) => {
    await setup(page, THREE);
    await enter(page);
    await expect(rows(page)).toHaveCount(3);
    const r0 = rows(page).nth(0).locator("td");
    await expect(r0.nth(0)).toHaveText("a@x.com");
    const t0 = (await r0.nth(1).innerText()).trim();
    expect(t0).not.toMatch(/T.*Z/);
    expect(t0.length).toBeGreaterThan(0);
    await expect(rows(page).nth(1).locator("td").nth(1)).toHaveText("—");
  });

  test("AC3: 空清單顯示「清單為空」且表格隱藏", async ({ page }) => {
    await setup(page, []);
    await enter(page);
    await expect(page.locator("#allowed-users-status-text")).toHaveText("清單為空");
    await expect(page.locator("#allowed-users-table-wrap")).toBeHidden();
  });

  test("AC4: 新增 201 立即出現且排序、清空輸入、body 正確", async ({ page }) => {
    const mock = await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 201, json: { email: "bb@x.com", last_login: null } }),
    });
    await enter(page);
    await page.locator("#allowed-users-input").fill("bb@x.com");
    await page.locator("#allowed-users-add-btn").click();
    await expect(rows(page)).toHaveCount(4);
    await expect(rows(page).nth(2).locator("td").first()).toHaveText("bb@x.com");
    await expect(page.locator("#allowed-users-input")).toHaveValue("");
    expect(JSON.parse(mock.postBodies[0])).toEqual({ email: "bb@x.com" });
  });

  test("AC5: 重複（200）顯示「已存在」資訊樣式、列數不變", async ({ page }) => {
    await setup(page, THREE, {
      postHandler: (route) => route.fulfill({ status: 200, json: { email: "a@x.com", last_login: null } }),
    });
    await enter(page);
    await page.locator("#allowed-users-input").fill("a@x.com");
    await page.locator("#allowed-users-add-btn").click();
    const msg = page.locator("#allowed-users-msg");
    await expect(msg).toHaveText("已存在");
    await expect(msg).toHaveAttribute("data-kind", "info");
    const colors = await page.evaluate(() => {
      const m = getComputedStyle(document.getElementById("allowed-users-msg")!).color;
      const probe = document.createElement("span");
      probe.style.color = "var(--danger)";
      document.body.appendChild(probe);
      const d = getComputedStyle(probe).color;
      probe.remove();
      return { m, d };
    });
    expect(colors.m).not.toBe(colors.d);
    await expect(rows(page)).toHaveCount(3);
  });

  test("AC6: 422 顯示固定中文訊息，不顯示 detail", async ({ page }) => {
    await setup(page, THREE, {
      postHandler: (route) =>
        route.fulfill({
          status: 422,
          json: { detail: [{ loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" }] },
        }),
    });
    await enter(page);
    await page.locator("#allowed-users-input").fill("not-an-email");
    await page.locator("#allowed-users-add-btn").click();
    await expect(page.locator("#allowed-users-msg")).toHaveText("email 格式不正確");
    const text = await page.locator("#allowed-users-card").innerText();
    expect(text).not.toContain("loc");
    expect(text).not.toContain("value_error");
    expect(text).not.toContain("msg");
  });

  test("AC7: 空輸入不送請求，顯示「請輸入 email」", async ({ page }) => {
    const mock = await setup(page, THREE);
    await enter(page);
    await page.locator("#allowed-users-input").fill("   ");
    await page.locator("#allowed-users-add-btn").click();
    await expect(page.locator("#allowed-users-msg")).toHaveText("請輸入 email");
    expect(mock.postCount).toBe(0);
  });

  test("AC8: 二段式移除、取消、編碼路徑、取代前一個確認態", async ({ page }) => {
    const mock = await setup(page, THREE, {
      deleteHandler: (route) => route.fulfill({ status: 204 }),
    });
    await enter(page);
    const rowA = rows(page).nth(0);
    const rowB = rows(page).nth(1);
    await rowA.locator(".au-remove").click();
    await expect(rowA.locator(".au-confirm")).toHaveText("確認移除");
    await expect(rowA.locator(".au-cancel")).toHaveText("取消");
    await rowA.locator(".au-cancel").click();
    await expect(rowA.locator(".au-remove")).toBeVisible();
    await expect(rowA.locator(".au-confirm")).toHaveCount(0);

    await rowA.locator(".au-remove").click();
    await rowB.locator(".au-remove").click();
    await expect(rowA.locator(".au-remove")).toBeVisible();
    await expect(rowB.locator(".au-confirm")).toBeVisible();

    await rowA.locator(".au-remove").click();
    await rowA.locator(".au-confirm").click();
    await expect(rows(page)).toHaveCount(2);
    await expect(page.locator('#allowed-users-tbody tr[data-email="a@x.com"]')).toHaveCount(0);
    expect(mock.deleteUrls).toHaveLength(1);
    expect(mock.deleteUrls[0]).toContain("/api/admin/allowed-users/a%40x.com");
  });

  test("AC9: DELETE 404 顯示「找不到此 email」並重載清單", async ({ page }) => {
    const mock = await setup(page, THREE, {
      deleteHandler: async (route) => {
        mock.items = mock.items.filter((i) => i.email !== "a@x.com");
        await route.fulfill({ status: 404, json: { detail: "nf" } });
      },
    });
    await enter(page);
    expect(mock.getCount).toBe(1);
    await rows(page).nth(0).locator(".au-remove").click();
    await rows(page).nth(0).locator(".au-confirm").click();
    await expect(page.locator("#allowed-users-msg")).toHaveText("找不到此 email");
    await expect(rows(page)).toHaveCount(2);
    expect(mock.getCount).toBe(2);
  });

  test("AC10: POST 503 / DELETE 500 / 網路中斷 → 區塊內錯誤、清單不變、按鈕恢復", async ({ page }) => {
    let mode: "503" | "abort" = "503";
    const mock = await setup(page, THREE, {
      postHandler: (route) => (mode === "abort" ? route.abort() : route.fulfill({ status: 503, json: { detail: "db" } })),
      deleteHandler: (route) => route.fulfill({ status: 500, json: { detail: "boom" } }),
    });
    await enter(page);
    const input = page.locator("#allowed-users-input");
    const msg = page.locator("#allowed-users-msg");
    await input.fill("n@x.com");
    await page.locator("#allowed-users-add-btn").click();
    await expect(msg).toBeVisible();
    await expect(msg).toHaveText("新增失敗，請稍後再試");
    await expect(rows(page)).toHaveCount(3);
    await expect(page.locator("#allowed-users-add-btn")).toBeEnabled();

    mode = "abort";
    await page.locator("#allowed-users-add-btn").click();
    await expect(msg).toHaveText("新增失敗，請稍後再試");
    await expect(page.locator("#allowed-users-add-btn")).toBeEnabled();

    await rows(page).nth(0).locator(".au-remove").click();
    await rows(page).nth(0).locator(".au-confirm").click();
    await expect(msg).toHaveText("移除失敗，請稍後再試");
    await expect(rows(page)).toHaveCount(3);
    await expect(rows(page).nth(0).locator("button")).toBeEnabled();
    expect(mock.deleteUrls).toHaveLength(1);
  });

  test("AC11: 清單載入失敗顯示錯誤與重試，用量不受影響", async ({ page }) => {
    const mock = await setup(page, THREE, { getStatus: 500 });
    await enter(page);
    await expect(page.locator("#allowed-users-status-text")).toHaveText("讀取白名單失敗");
    await expect(page.locator("#allowed-users-retry-btn")).toBeVisible();
    await expect(page.locator("#admin-by-date-tbody tr")).toHaveCount(1);
    mock.getStatus = 200;
    await page.locator("#allowed-users-retry-btn").click();
    await expect(rows(page)).toHaveCount(3);
    await expect(page.locator("#allowed-users-retry-btn")).toBeHidden();
  });

  test("AC12: XSS 安全，email 以文字顯示、不執行、刪除路徑正確編碼", async ({ page }) => {
    const evil = `"><img src=x onerror=window.__xss=1>`;
    const quote = "a'b@x.com";
    const mock = await setup(
      page,
      [
        { email: evil, last_login: null },
        { email: quote, last_login: null },
      ],
      { deleteHandler: (route) => route.fulfill({ status: 204 }) },
    );
    await enter(page);
    await expect(rows(page)).toHaveCount(2);
    await expect(page.locator("#allowed-users-tbody tr .au-email").first()).toHaveText(evil);
    await expect(page.locator("#allowed-users-tbody tr .au-email").nth(1)).toHaveText(quote);
    await expect(page.locator("#allowed-users-tbody img")).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__xss)).toBeUndefined();

    const evilRow = page.locator("#allowed-users-tbody tr").filter({ hasText: "img src" });
    await evilRow.locator(".au-remove").click();
    await evilRow.locator(".au-confirm").click();
    await expect(rows(page)).toHaveCount(1);
    expect(mock.deleteUrls[0]).toContain("/api/admin/allowed-users/" + encodeURIComponent(evil));
    expect(await page.evaluate(() => (window as any).__xss)).toBeUndefined();
  });

  test("AC13: 非管理者看不到入口；直接開啟時 403 不顯示資料", async ({ page }) => {
    const mock = await setup(page, THREE, { role: "user", getStatus: 403 });
    await openDashboard(page);
    await expect(page.locator("#admin-dashboard-btn")).toBeHidden();
    await page.evaluate(() => {
      (0, eval)("showView")("view-admin");
      (0, eval)("openAdminDashboard")();
    });
    await expect(page.locator("#allowed-users-status-text")).toHaveText("僅限管理者存取");
    await expect(rows(page)).toHaveCount(0);
    expect(mock.getCount).toBeGreaterThan(0);
  });

  test("AC14: 請求進行中新增鈕與列按鈕 disabled，完成後恢復", async ({ page }) => {
    await setup(page, THREE, {
      postHandler: async (route) => {
        await new Promise((r) => setTimeout(r, 400));
        await route.fulfill({ status: 201, json: { email: "z@x.com", last_login: null } });
      },
    });
    await enter(page);
    await page.locator("#allowed-users-input").fill("z@x.com");
    await page.locator("#allowed-users-add-btn").click();
    await expect(page.locator("#allowed-users-add-btn")).toBeDisabled();
    await expect(rows(page).nth(0).locator("button")).toBeDisabled();
    await expect(rows(page)).toHaveCount(4);
    await expect(page.locator("#allowed-users-add-btn")).toBeEnabled();
    await expect(rows(page).nth(0).locator("button")).toBeEnabled();
  });

  test("AC15: 管理者移除自己的 email 與一般列行為相同", async ({ page }) => {
    const mock = await setup(page, [...THREE, { email: SELF, last_login: null }], {
      deleteHandler: (route) => route.fulfill({ status: 204 }),
    });
    await enter(page);
    await expect(rows(page)).toHaveCount(4);
    const self = page.locator(`#allowed-users-tbody tr[data-email="${SELF}"]`);
    await self.locator(".au-remove").click();
    await self.locator(".au-confirm").click();
    await expect(rows(page)).toHaveCount(3);
    expect(mock.deleteUrls[0]).toContain(encodeURIComponent(SELF));
    await expect(page.locator("#allowed-users-msg")).toBeHidden();
  });
});
