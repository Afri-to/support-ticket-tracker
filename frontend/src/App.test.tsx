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
