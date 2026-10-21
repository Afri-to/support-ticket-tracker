import type {
  User,
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

export class ApiError extends Error {
  constructor(message: string, readonly status = 0) {
    super(message);
  }
}

/** Called when the session has ended (401) so the app can show the sign-in screen. */
let onSignedOut: () => void = () => {};
export function setSignedOutHandler(handler: () => void) {
  onSignedOut = handler;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { credentials: "same-origin", ...init });
  } catch {
    throw new ApiError("Couldn't reach the server. Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : firstValidationMessage(body) ?? `Request failed (${response.status}).`;
    if (response.status === 401 && !path.startsWith("/auth/")) onSignedOut();
    throw new ApiError(detail, response.status);
  }
  return body as T;
}

/** FastAPI's 422 body lists field errors; turn the first into a sentence. */
function firstValidationMessage(body: unknown): string | null {
  const detail = (body as { detail?: { loc?: string[]; msg?: string }[] })?.detail;
  if (!Array.isArray(detail) || !detail[0]) return null;
  const field = detail[0].loc?.at(-1);
  if (field === "email") return "Enter a valid email address.";
  if (field === "password") return "Use a password of at least 8 characters.";
  return detail[0].msg ?? null;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

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
  me: () => request<User>("/auth/me"),
  register: (email: string, password: string) => request<User>("/auth/register", json({ email, password })),
  login: (email: string, password: string) => request<User>("/auth/login", json({ email, password })),
  demo: () => request<User>("/auth/demo", { method: "POST" }),
  logout: () => fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "same-origin" }),
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
