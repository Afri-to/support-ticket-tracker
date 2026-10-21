import { expect, test, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

const SAMPLE = fileURLToPath(new URL("../../data/sample_tickets.csv", import.meta.url));
const PASSWORD = "correct horse battery";

const tile = (page: Page, label: string) =>
  page.locator(".tile", { has: page.getByText(label, { exact: true }) }).locator(".tile-value");

test("new user imports a CSV, filters the dashboard and keeps their data", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  // Create an account
  await page.goto("/");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(email)).toBeVisible();
  await expect(page.getByText(/No tickets yet/)).toBeVisible();

  // Upload the sample file
  await page.getByLabel("CSV file").setInputFiles(SAMPLE);
  await page.getByRole("button", { name: "Import CSV" }).click();
  await expect(page.getByRole("status")).toContainText("4,789 imported, 159 duplicates removed, 0 already imported, 52 invalid rows.");

  // The dashboard updates
  await expect(tile(page, "Tickets")).toHaveText("4,789");
  await expect(page.getByRole("region", { name: "Tickets per week" }).locator("svg").first()).toBeVisible();
  await expect(page.getByText("1–25 of 4,789")).toBeVisible();

  // Filtering by agent changes every number
  const agent = page.getByRole("combobox", { name: "Agent" });
  const firstAgent = (await agent.locator("option").nth(1).textContent())!;
  await agent.selectOption({ label: firstAgent });
  await expect(tile(page, "Tickets")).not.toHaveText("4,789");
  const agentTotal = await tile(page, "Tickets").textContent();
  await expect(page.getByText(`of ${agentTotal}`)).toBeVisible();
  await expect(page.locator("tbody tr").first()).toContainText(firstAgent);
  await page.getByRole("button", { name: "Clear filters" }).click();

  // Search the table
  await page.getByLabel("Search tickets").fill("TCK-000001");
  await expect(page.getByText("1–1 of 1")).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(1);

  // Uploading the same file again changes nothing
  await page.getByLabel("CSV file").setInputFiles(SAMPLE);
  await page.getByRole("button", { name: "Import CSV" }).click();
  await expect(page.getByRole("status")).toContainText("0 imported");
  await expect(tile(page, "Tickets")).toHaveText("4,789");

  // Sign out, sign back in: the data is still there
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(tile(page, "Tickets")).toHaveText("4,789");
});

test("a visitor explores the read-only demo", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the demo" }).click();
  await expect(page.getByText("Demo account (read-only)")).toBeVisible();
  await expect(tile(page, "Tickets")).toHaveText("4,789");
  await expect(page.getByText(/The demo account is read-only/)).toBeVisible();
  await page.getByRole("region", { name: "Top root causes" }).getByRole("button", { name: "Show table" }).click();
  await expect(page.getByRole("region", { name: "Top root causes" }).locator("tbody tr")).toHaveCount(8);
});

test("a wrong password shows a clear message", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password").fill("wrong password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText("Email or password is incorrect.");
});
