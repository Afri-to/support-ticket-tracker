import { vi } from "vitest";

/** Replace fetch with a fake API. `routes` maps a path prefix to a response body. */
export function mockFetch(routes: Record<string, unknown>) {
  const calls: string[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push(`${init?.method ?? "GET"} ${url}`);
    const path = url.replace(/^\/api/, "");
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => path.startsWith(k));
    if (!key) return new Response(JSON.stringify({ detail: "Not found" }), { status: 404 });
    const body = routes[key];
    if (body instanceof Response) return body.clone();
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

export const sample = {
  agents: [
    { id: 1, name: "Ana Torres" },
    { id: 2, name: "Ben Ortiz" },
  ],
  summary: { total: 5, open: 1, avg_resolve_hours: "6.0", median_resolve_hours: "5.0" },
  weekly: [
    { week_start: "2026-07-06", opened: 3, closed: 3, avg_resolve_hours: "4.0" },
    { week_start: "2026-07-13", opened: 2, closed: 1, avg_resolve_hours: "12.0" },
  ],
  causes: [
    { category: "Network", root_cause: "Wi-Fi dropout", tickets: 2, share_pct: "40.0" },
    { category: "Printer", root_cause: "Paper jam", tickets: 2, share_pct: "40.0" },
  ],
  agentKpis: [
    { agent_id: 1, agent: "Ana Torres", tickets: 3, open: 0, avg_resolve_hours: "6.0" },
    { agent_id: 2, agent: "Ben Ortiz", tickets: 2, open: 1, avg_resolve_hours: "6.0" },
  ],
  tickets: {
    total: 2,
    items: [
      { ticket_id: "TCK-000002", agent: "Ben Ortiz", category: "Printer", root_cause: "Paper jam", priority: "High",
        opened_at: "2026-07-07T09:00:00Z", closed_at: null, resolve_hours: null },
      { ticket_id: "TCK-000001", agent: "Ana Torres", category: "Network", root_cause: "Wi-Fi dropout", priority: "Critical",
        opened_at: "2026-07-06T09:00:00Z", closed_at: "2026-07-06T11:30:00Z", resolve_hours: "2.5" },
    ],
  },
};

export const unauthorized = () =>
  new Response(JSON.stringify({ detail: "Sign in to continue." }), { status: 401 });

export function dashboardRoutes(overrides: Record<string, unknown> = {}) {
  return {
    "/auth/me": { email: "tester@example.com", is_demo: false },
    "/agents": sample.agents,
    "/kpis/summary": sample.summary,
    "/kpis/weekly": sample.weekly,
    "/kpis/root-causes": sample.causes,
    "/kpis/agents": sample.agentKpis,
    "/tickets": sample.tickets,
    ...overrides,
  };
}
