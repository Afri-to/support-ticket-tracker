import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { dashboardRoutes, mockFetch, sample } from "./test/mockApi";

afterEach(() => vi.unstubAllGlobals());

describe("dashboard", () => {
  it("shows headline numbers and tickets", async () => {
    mockFetch(dashboardRoutes());
    render(<App />);
    expect(await screen.findByText("Still open")).toBeInTheDocument();
    expect(screen.getByText("6.0 h")).toBeInTheDocument();
    expect(await screen.findByText("TCK-000001")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument(); // the unresolved ticket
  });

  it("re-queries every panel when a filter changes", async () => {
    const { calls } = mockFetch(dashboardRoutes());
    render(<App />);
    const agent = await screen.findByLabelText("Agent");
    await waitFor(() => expect(within(agent).getByText("Ben Ortiz")).toBeInTheDocument());

    await userEvent.selectOptions(agent, "2");
    await waitFor(() => expect(calls.some((c) => c.includes("/kpis/summary?agent_id=2"))).toBe(true));
    expect(calls.some((c) => c.includes("/tickets?agent_id=2"))).toBe(true);
    // the agent chart compares all agents, so it keeps every agent
    expect(calls.filter((c) => c.includes("/kpis/agents")).every((c) => !c.includes("agent_id"))).toBe(true);

    await userEvent.selectOptions(screen.getByLabelText("Week"), "2026-07-06");
    await waitFor(() => expect(calls.some((c) => c.includes("from=2026-07-06&to=2026-07-12"))).toBe(true));

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByLabelText("Agent")).toHaveValue("");
  });

  it("offers each chart as a table", async () => {
    mockFetch(dashboardRoutes());
    render(<App />);
    const card = await screen.findByRole("region", { name: "Tickets per week" });
    await userEvent.click(within(card).getByRole("button", { name: "Show table" }));
    expect(within(card).getByText("Jul 13 – Jul 19")).toBeInTheDocument();
  });

  it("guides a first-time visitor to import data", async () => {
    mockFetch(dashboardRoutes({ "/kpis/summary": { ...sample.summary, total: 0, open: 0 } }));
    render(<App />);
    expect(await screen.findByText(/No tickets yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import CSV" })).toBeDisabled();
  });

  it("shows a readable message when the server is down", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    render(<App />);
    expect((await screen.findAllByRole("alert"))[0]).toHaveTextContent("Couldn't reach the server");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

it("keeps the import summary visible after a first import fills the dashboard", async () => {
  const { default: userEvent } = await import("@testing-library/user-event");
  let total = 0;
  const summaryRoute = () => new Response(JSON.stringify({ ...sample.summary, total }), { status: 200 });
  const routes = dashboardRoutes({
    "/imports": { import_id: 1, filename: "t.csv", total_rows: 5, imported: 5, duplicates: 0, already_imported: 0, invalid: 0, errors: [] },
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace(/^\/api/, "");
    if (path.startsWith("/imports")) total = 5;
    if (path.startsWith("/kpis/summary")) return summaryRoute();
    const key = Object.keys(routes).sort((a, b) => b.length - a.length).find((k) => path.startsWith(k))!;
    void init;
    return new Response(JSON.stringify(routes[key as keyof typeof routes]), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByText(/No tickets yet/);
  await userEvent.upload(screen.getByLabelText("CSV file"), new File(["x"], "t.csv", { type: "text/csv" }));
  await userEvent.click(screen.getByRole("button", { name: "Import CSV" }));
  await waitFor(() => expect(screen.queryByText(/No tickets yet/)).not.toBeInTheDocument());
  expect(screen.getByRole("status")).toHaveTextContent("5 imported");
});
