import type { Agent, Filters, Week } from "../types";
import { weekLabel } from "../format";

interface Props {
  agents: Agent[];
  weeks: Week[];
  filters: Filters;
  onChange: (f: Filters) => void;
}

/** One row of filters above everything they affect. */
export function FilterBar({ agents, weeks, filters, onChange }: Props) {
  const active = filters.agentId !== null || filters.week !== null;
  return (
    <div className="filters" role="group" aria-label="Filters">
      <label className="field">
        Week
        <select
          value={filters.week ?? ""}
          onChange={(e) => onChange({ ...filters, week: e.target.value || null })}
        >
          <option value="">All weeks</option>
          {[...weeks].reverse().map((w) => (
            <option key={w.week_start} value={w.week_start}>{weekLabel(w.week_start)}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Agent
        <select
          value={filters.agentId ?? ""}
          onChange={(e) => onChange({ ...filters, agentId: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">All agents</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </label>
      {active && (
        <button type="button" className="link-button" onClick={() => onChange({ agentId: null, week: null })}>
          Clear filters
        </button>
      )}
    </div>
  );
}
