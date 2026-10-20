import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Agent, AgentKpi, Filters, RootCause, Summary, Week } from "./types";
import { FilterBar } from "./components/FilterBar";
import { StatTiles } from "./components/StatTiles";
import { AgentsChart, ResolveTimeChart, RootCausesChart, WeeklyVolumeChart } from "./components/Charts";
import { TicketTable } from "./components/TicketTable";
import { UploadPanel } from "./components/UploadPanel";

interface Dashboard {
  summary: Summary;
  weeks: Week[];
  causes: RootCause[];
  agentKpis: AgentKpi[];
}

export default function App() {
  const [filters, setFilters] = useState<Filters>({ agentId: null, week: null });
  const [agents, setAgents] = useState<Agent[]>([]);
  const [allWeeks, setAllWeeks] = useState<Week[]>([]);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Options for the filters: every agent and every week, regardless of filters.
  useEffect(() => {
    Promise.all([api.agents(), api.weekly({ agentId: null, week: null })])
      .then(([a, w]) => (setAgents(a), setAllWeeks(w)))
      .catch((e: Error) => setError(e.message));
  }, [refreshKey]);

  useEffect(() => {
    let current = true;
    Promise.all([api.summary(filters), api.weekly(filters), api.rootCauses(filters), api.agentKpis(filters)])
      .then(([summary, weeks, causes, agentKpis]) => {
        if (current) {
          setData({ summary, weeks, causes, agentKpis });
          setError(null);
        }
      })
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [filters, refreshKey]);

  const onImported = useCallback(() => setRefreshKey((k) => k + 1), []);
  const empty = data !== null && data.summary.total === 0 && filters.agentId === null && filters.week === null;

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <h1>Support Ticket Tracker</h1>
          <p>Weekly support KPIs from imported ticket exports. All data is fake.</p>
        </div>
        <a href={`${import.meta.env.VITE_API_URL ?? "/api"}/docs`} className="link-button">API docs</a>
      </header>

      {error && <p className="error-text" role="alert">{error}</p>}

      {empty ? (
        <>
          <div className="notice">No tickets yet. Import a CSV below, or start with the sample file, to see the dashboard.</div>
          <UploadPanel onImported={onImported} />
        </>
      ) : (
        <>
          <FilterBar agents={agents} weeks={allWeeks} filters={filters} onChange={setFilters} />
          {data && (
            <>
              <StatTiles summary={data.summary} />
              <div className="grid">
                <WeeklyVolumeChart weeks={data.weeks} selectedWeek={filters.week} />
                <ResolveTimeChart weeks={data.weeks} selectedWeek={filters.week} />
                <RootCausesChart causes={data.causes} />
                <AgentsChart agents={data.agentKpis} selectedAgent={filters.agentId} />
              </div>
            </>
          )}
          <TicketTable filters={filters} refreshKey={refreshKey} />
          <div style={{ height: 16 }} />
          <UploadPanel onImported={onImported} />
        </>
      )}
    </div>
  );
}
