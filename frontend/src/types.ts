// Shapes returned by the backend API. Decimals arrive as strings.

export interface Agent {
  id: number;
  name: string;
}

export interface Summary {
  total: number;
  open: number;
  avg_resolve_hours: string | null;
  median_resolve_hours: string | null;
}

export interface Week {
  week_start: string; // YYYY-MM-DD, a Monday
  opened: number;
  closed: number;
  avg_resolve_hours: string | null;
}

export interface RootCause {
  category: string;
  root_cause: string;
  tickets: number;
  share_pct: string;
}

export interface AgentKpi {
  agent_id: number;
  agent: string;
  tickets: number;
  open: number;
  avg_resolve_hours: string | null;
}

export interface Ticket {
  ticket_id: string;
  agent: string;
  category: string;
  root_cause: string;
  priority: "Low" | "Medium" | "High" | "Critical";
  opened_at: string;
  closed_at: string | null;
  resolve_hours: string | null;
}

export interface TicketPage {
  total: number;
  items: Ticket[];
}

export interface RowProblem {
  code: string;
  message: string;
}

export interface ImportSummary {
  import_id: number;
  filename: string;
  total_rows: number;
  imported: number;
  duplicates: number;
  already_imported: number;
  invalid: number;
  errors: { line: number; ticket_id: string; problems: RowProblem[] }[];
}

export interface Filters {
  agentId: number | null;
  week: string | null; // week_start of the selected week, or null for all weeks
}

export interface User {
  email: string;
  is_demo: boolean;
}
