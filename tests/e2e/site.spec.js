import { test, expect } from "@playwright/test";

const pages = [
  { path: "/", title: /TickerTruth/i },
  { path: "/pricing.html", title: /TickerTruth/i },
  { path: "/methodology.html", title: /TickerTruth/i },
  { path: "/sample-queries.html", title: /TickerTruth/i },
  { path: "/contact.html", title: /TickerTruth/i },
];

for (const { path, title } of pages) {
  test(`${path} loads`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res.status()).toBeLessThan(400);
    await expect(page).toHaveTitle(title);
  });
}

test("unknown path returns a 404", async ({ page }) => {
  const res = await page.goto("/this-page-does-not-exist");
  expect(res.status()).toBe(404);
});

test("contact form blocks submission with missing required fields", async ({ page }) => {
  await page.goto("/contact.html");
  await page.click("#submit-btn");
  const nameInput = page.locator("#name");
  await expect(nameInput).toHaveJSProperty("validity.valid", false);
});

test("contact form submits successfully and shows a confirmation", async ({ page }) => {
  await page.route("**/api/contact", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) })
  );

  await page.goto("/contact.html");
  await page.fill("#name", "Jane Doe");
  await page.fill("#email", "jane@example.com");
  await page.click("#submit-btn");

  await expect(page.locator("#form-status")).toContainText(/thanks|received|sent/i, { timeout: 5000 });
});
