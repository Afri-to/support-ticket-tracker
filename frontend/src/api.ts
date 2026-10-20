import type {
  Agent,
  AgentKpi,
  Filters,
  ImportSummary,
  RootCause,
  Summary,
  TicketPage,
  Week,
} from "./types";
import { weekEnd } from "./format";

// "/api" in development (proxied by Vite); set VITE_API_URL="" when the API
// serves this app itself, or a full URL when it lives elsewhere.
const BASE = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Couldn't reach the server. Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`;
    throw new ApiError(detail);
  }
  return body as T;
}

/**
 * Query string for the shared filters. Charts that compare across one dimension
 * leave that filter out and highlight the selection instead: the weekly charts
 * show every week, the agent chart shows every agent.
 */
export function filterQuery(f: Filters, { week = true, agent = true } = {}): URLSearchParams {
  const q = new URLSearchParams();
  if (agent && f.agentId !== null) q.set("agent_id", String(f.agentId));
  if (week && f.week) {
    q.set("from", f.week);
    q.set("to", weekEnd(f.week));
  }
  return q;
}

export const api = {
  agents: () => request<Agent[]>("/agents"),
  summary: (f: Filters) => request<Summary>(`/kpis/summary?${filterQuery(f)}`),
  weekly: (f: Filters) => request<Week[]>(`/kpis/weekly?${filterQuery(f, { week: false })}`),
  rootCauses: (f: Filters) => {
    const q = filterQuery(f);
    q.set("limit", "8");
    return request<RootCause[]>(`/kpis/root-causes?${q}`);
  },
  agentKpis: (f: Filters) => request<AgentKpi[]>(`/kpis/agents?${filterQuery(f, { agent: false })}`),
  tickets: (f: Filters, search: string, limit: number, offset: number) => {
    const q = filterQuery(f);
    if (search.trim()) q.set("search", search.trim());
    q.set("limit", String(limit));
    q.set("offset", String(offset));
    return request<TicketPage>(`/tickets?${q}`);
  },
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportSummary>("/imports", { method: "POST", body: form });
  },
};
