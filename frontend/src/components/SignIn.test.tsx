import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { dashboardRoutes, mockFetch, unauthorized } from "../test/mockApi";

afterEach(() => vi.unstubAllGlobals());

const signedOut = (extra: Record<string, unknown> = {}) =>
  dashboardRoutes({ "/auth/me": unauthorized(), ...extra });

it("shows the sign-in screen when nobody is signed in", async () => {
  mockFetch(signedOut());
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Explore the demo" })).toBeInTheDocument();
});

it("signs in and opens the dashboard", async () => {
  const { calls, fetchMock } = mockFetch(signedOut({ "/auth/login": { email: "ana@example.com", is_demo: false } }));
  render(<App />);
  await userEvent.type(await screen.findByLabelText("Email"), "ana@example.com");
  await userEvent.type(screen.getByLabelText("Password"), "correct horse");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByText("ana@example.com")).toBeInTheDocument();
  expect(calls).toContain("POST /api/auth/login");
  const init = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/auth/login"))![1]!;
  expect(JSON.parse(String(init.body))).toEqual({ email: "ana@example.com", password: "correct horse" });
});

it("shows the server's message for a wrong password", async () => {
  mockFetch(signedOut({
    "/auth/login": new Response(JSON.stringify({ detail: "Email or password is incorrect." }), { status: 401 }),
  }));
  render(<App />);
  await userEvent.type(await screen.findByLabelText("Email"), "ana@example.com");
  await userEvent.type(screen.getByLabelText("Password"), "wrong password");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
});

it("turns validation errors into plain sentences", async () => {
  mockFetch(signedOut({
    "/auth/register": new Response(
      JSON.stringify({ detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters" }] }),
      { status: 422 },
    ),
  }));
  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Create an account" }));
  await userEvent.type(screen.getByLabelText("Email"), "ana@example.com");
  await userEvent.type(screen.getByLabelText("Password"), "short");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Use a password of at least 8 characters.");
});

it("opens the read-only demo", async () => {
  mockFetch(signedOut({ "/auth/demo": { email: "demo@support-ticket-tracker.dev", is_demo: true } }));
  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Explore the demo" }));
  expect(await screen.findByText("Demo account (read-only)")).toBeInTheDocument();
  expect(await screen.findByText(/The demo account is read-only/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Import CSV" })).not.toBeInTheDocument();
});

it("returns to sign-in after signing out", async () => {
  const { calls } = mockFetch(dashboardRoutes({ "/auth/logout": {} }));
  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(calls).toContain("POST /api/auth/logout");
});

it("returns to sign-in when the session expires mid-visit", async () => {
  mockFetch(dashboardRoutes({ "/kpis/summary": unauthorized() }));
  render(<App />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument());
});
